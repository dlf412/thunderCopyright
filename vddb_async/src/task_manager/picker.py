
from server import observer, catch_and_die

from collections import defaultdict
from time import time
from logger import g_logger
from utils import trans2json
from stats import stats, PICKED


class picker(observer):
    def __init__(self, config, pick_cond, fetcher, manager):
        super(picker, self).__init__(pick_cond)

        self.fetcher = fetcher
        self.manager = manager

        if 'refresh_pending_queue_interval' in config:
            self.intv = int(config['refresh_pending_queue_interval'])
        else:
            self.intv = 300

        self.picked = defaultdict(lambda: set())
        self.buf = {}
        self.next_fetch = {}
        # NOTE: tho this member is called fetching, it records the tasks sent
        #       to be picked.
        #       it's called fetching because the accounts inside it are having
        #       their tasks fetched
        self.fetching = {}

    @catch_and_die('mwtm_picker')
    def run(self):
        while True:
            self.loop()

    def pick_and_fetch(self, ts, acc):
        self.logger.debug('picking %s tasks for account %s from buf, max %s',
                          len(ts), acc, self.accs[acc].max_conc)
        self.maybe_fetch(acc)
        for t in ts:
            self.pick(t)
        return len(ts)

    def pick_buf(self, acc, n=None):
        if acc in self.buf:
            buf = self.buf[acc]
            ts = buf[0:n]
            del buf[0:n]
            if len(buf) <= 0:
                del self.buf[acc]
                self.trigger_fetch(acc)
            return self.pick_and_fetch(ts, acc)

        self.logger.debug('picking for %s tasks for account %s without ' +
                          'tasks, max %s, but not fetching', n, acc,
                          self.accs[acc].max_conc)

    def pick(self, t):
        self.picked[t.account].add(t.id)
        if t.account in self.fetching:
            self.fetching[t.account].add(t.id)
        self.manager.request(t)
        self.logger.info('picked task %s for account %s, site_asset_id %s',
                         t.uuid, t.account, t.site_asset_id)
        g_logger.info(trans2json(action="picked task to query",
                                 message="task_uuid: %s, site_asset_id: %s, external_id: %s" % \
                                 (t.uuid, t.site_asset_id, t.external_id)))
        stats.incr(PICKED, 1)

    @staticmethod
    def add_load(loads, backends, load):
        for b in backends:
            loads[b] += load

    def pick_hipri(self, accs, backends):
        for (a, p) in accs.iteritems():
            if p.max_conc <= 0:
                continue

            sp = self.picked[a]
            tc = len(sp)
            # running task count may be greater than max conc setting
            # when the setting is newly tuned down
            # just don't pick tasks for this account
            if tc > p.max_conc or not a in self.buf:
                continue
            self.pick_buf(a, p.max_conc - tc)
            # no account reloading when picking, safe to assert
            assert len(sp) <= p.max_conc, ('len(sp): %s, p.max_conc: %s'
                                           % (len(sp), p.max_conc))

    def pick_lopri(self, accs, backends):
        loads = defaultdict(lambda: 0)
        for a, ts in self.picked.iteritems():
            assert a in accs
            p = accs[a]
            bes = [b.backend for b in p.backends]
            l = 0
            if p.max_conc > 0:
                l = len(ts) if len(ts) > p.min_conc else p.min_conc
            else:
                l = len(ts)
            self.logger.debug('adding running load %s to backends %s for ' +
                              'account %s', l, bes, a)
            self.add_load(loads, bes, l)

        lo_accs = set([a for (a, p) in accs.iteritems() \
                       if p.max_conc <= 0 and a in self.buf])
        todel = set()
        tc = defaultdict(lambda: 0)
        while len(lo_accs) != 0:
            # do not iterate over accounts with fully loaded backends
            lo_accs -= todel
            todel = set()
            # iterate over lo pri accounts and pick 1 task from each if possible
            # we'd like to be fair among these accounts
            # pick from the acccount with least running tasks first
            for a in sorted(lo_accs, key=lambda a: len(self.picked[a])):
                p = accs[a]
                for b in p.backends:
                    be = b.backend
                    if not be in backends:
                        self.logger.warning('backend setting for account %s ' +
                                            'inconsistent with backends in db',
                                            a)
                        todel.add(a)
                        break
                    if loads[be] >= backends[be].capacity:
                        todel.add(a)
                        break
                else:
                    if self.pick_buf(a, 1) > 0:
                        bes = [b.backend for b in p.backends]
                        self.logger.debug('adding requested load %s to ' +
                                          'backends %s for account %s', 1, bes,
                                          a)
                        self.add_load(loads, bes, 1)
                    else:
                        todel.add(a)

    def loop(self):
        accs = self.accounts()
        now = time()
        # check for timeout fetch
        for a, t in dict(**self.next_fetch).iteritems():
            if not a in accs:
                del self.next_fetch[a]
                continue
            # trigger timeout fetch as needed by the way
            if t <= now and not a in self.fetching:
                self.logger.info('timeout fetching tasks for account %s', a)
                self.trigger_fetch(a)
        # trigger fetching for new accounts
        for a in accs.keys():
            if not a in self.next_fetch:
                self.logger.info('to fetch tasks for new account %s', a)
                self.trigger_fetch(a)
        # clear things for newly deleted accounts
        for d in self.buf, self.fetching, self.picked:
            for a in d.keys():
                if not a in accs:
                    del d[a]
        # clear data for finished procs
        finished = self.manager.replies()
        for t in finished:
            if not t.account in accs:
                continue
            self.logger.info('task %s finished for account %s site_asset_id %s', t.uuid,
                              t.account, t.site_asset_id)
            self.picked[t.account].discard(t.id)
        # buffer newly fetched tasks
        reps = self.fetcher.replies()
        for a, ts in reps:
            if not a in accs:
                continue
            if len(ts) == 0:
                if a in self.fetching:
                    del self.fetching[a]
                if a in self.buf:
                    del self.buf[a] # in case tasks were failed/deleted by ops
                continue
            if not a in self.fetching:
                self.buf[a] = ts
            else:
                self.logger.debug('fetched %s tasks for account %s: %s', len(ts),
                                  a, [t.uuid for t in ts])
                self.logger.debug('recently picked/finished tasks for account ' +
                                  '%s: %s', a, [t for t in self.fetching[a]])
                self.logger.debug('picked tasks for account %s: %s', a,
                                  [t for t in self.picked[a]])
                # tasks from the fetching set and the picked set are excluded
                # checking only the fetching set is not enough, since some tasks
                # may be picked but not yet marked as in query status when the
                # fetching was in progress
                # if the task is still in picked set, at least we won't exec
                # a task more than once at the same time.
                # if a task is executed more than once at the same time, since
                # fetching is a set, more than max_conc tasks will be spawned
                # if a task execs really fast, it may be executed twice, not but
                # at the same time
                self.buf[a] = [t for t in ts \
                               if not t.id in self.fetching[a] and \
                               not t.id in self.picked[a]]
                del self.fetching[a]
                self.logger.debug('buffered %s tasks for account %s: %s',
                                  len(self.buf[a]), a,
                                  [t.uuid for t in self.buf[a]])
        # update accounts info again, so it is as updated as backends as possible
        accs = self.accounts()
        backends = self.backends()
        self.logger.debug('to pick for hipri accounts')
        self.pick_hipri(accs, backends)
        self.logger.debug('to pick for lopri accounts')
        self.pick_lopri(accs, backends)
        # wait till next timeout flush
        if len(self.next_fetch) > 0:
            next_fetch = min(self.next_fetch.values())
            if next_fetch > now:
                with self.req_cond:
                    if self.fetcher.repq.empty() and self.manager.repq.empty():
                        self.req_cond.wait(next_fetch - now)
        else:                   # any account should set next fetch time
            assert len(accs) == 0
            with self.req_cond:
                self.req_cond.wait()

    def trigger_fetch(self, acc):
        if acc in self.fetching:
            return

        self.fetcher.request(acc)
        self.fetching[acc] = set()
        self.next_fetch[acc] = time() + self.intv

    def maybe_fetch(self, acc):
        if acc in self.buf:
            buf = self.buf[acc]
            if len(buf) > self.accs[acc].min_buf or acc in self.fetching:
                return
            self.logger.info('to fetch for account %s, %s tasks left', acc,
                             len(buf))
            self.trigger_fetch(acc)
