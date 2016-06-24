from server import server, catch_and_die
from tm_sqls import *  # @UnusedWildImport

from db_txn import db_execute, db_query, db_result, db_txn

from collections import namedtuple
from functools import partial

VDDB_SCOPE_LIMIT = 32

class fetcher(server):
    def __init__(self, config, pool, fetch_cond, buf_cond):
        super(fetcher, self).__init__(fetch_cond, buf_cond)
        self.pool = pool

    @staticmethod
    def do_renew():
        rc, _ = yield db_execute(RENEW_TASKS)
        yield db_result(rc)

    def renew_tasks(self):
        return db_txn(self.pool, self.do_renew)

    @catch_and_die('mwtm_fetcher')
    def run(self):
        accs = self.accounts()
        assert accs != None

        self.logger.info('to renew tasks on startup')
        try:
            renewed = self.renew_tasks()
        except:
            self.logger.error('failed to renew tasks, some tasks may be left '
                              + 'unrun', exc_info=True)
        else:
            self.logger.info('renewed %s tasks on startup', renewed)

        while True:
            self.loop()

    @staticmethod
    def fetch_for_account(acc, p):
        c, rs = yield db_query(FETCH_TASKS, acc, p.max_buf)
        ts = []
        if c > 0:
            t_ = namedtuple('_', rs[0]._fields + ('scope',))
        for r in rs:
            t = r._asdict()
            if r.queued_at == None or r.queued_at == 0:
                t['queued_at'] = r.created_at
            if r.submit_at == None or r.submit_at == 0:
                t['submit_at'] = r.created_at
            if (r.deadline == None or r.deadline == 0) and \
               (p.time_limit != None and p.time_limit != 0):
                t['deadline'] = t['submit_at'] + p.time_limit

            rc2, rs2 = yield db_query(FETCH_SCOPE, r.id)
            if rc2 > VDDB_SCOPE_LIMIT:
                t['scope'] = None
            else:
                t['scope'] = [r2.content for r2 in rs2]
            ts.append(t_(**t))

        yield db_result(ts)

    def fetch_one(self, acc, p):
        return db_txn(self.pool, partial(self.fetch_for_account, acc, p))

    def loop(self):
        reqs = self.requests(True)
        assert reqs != []

        accs = self.accounts()
        self.logger.info('fetch task accounts: %s', reqs)
        self.logger.debug("all accounts: %s",  accs.keys())

        for a in reqs:
            rep = (a, [])
            if a in accs:
                try:
                    rep = (a, self.fetch_one(a, accs[a]))
                except:
                    self.logger.error('failed to fetch tasks for account %s',
                                      a, exc_info=True)
                else:
                    self.logger.info('fetched %s tasks for account %s',
                                     len(rep[1]), a)
                    self.logger.debug("tasks: %s" % ([t.uuid for t in rep[1]]))
            self.reply(rep)
