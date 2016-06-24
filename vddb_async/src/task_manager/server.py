import logging
from Queue import Queue
from os import _exit
from threading import Condition, Lock, Thread


class observer(Thread):
    def __init__(self, req_cond=None):
        if req_cond == None:
            req_cond = Condition(Lock())
        super(observer, self).__init__()
        self.logger = logging.getLogger('mwtm_' + self.__class__.__name__)
        self.accq = Queue()
        self.accs = None
        self.beq = Queue()
        self.bes = None
        self.req_cond = req_cond

    def update_accounts(self, accs):
        with self.req_cond:
            self.accq.queue.clear()
            self.accq.put(accs)
            self.req_cond.notifyAll()

    def accounts(self):
        with self.req_cond:
            while not self.accq.empty():
                self.accs = self.accq.get(False)
        return self.accs

    def update_backends(self, backends):
        with self.req_cond:
            self.beq.queue.clear()
            self.beq.put(backends)
            self.req_cond.notifyAll()

    def backends(self):
        with self.req_cond:
            while not self.beq.empty():
                self.bes = self.beq.get(False)
        return self.bes


class server(observer):
    def __init__(self, req_cond=None, rep_cond=None):
        if rep_cond == None:
            rep_cond = Condition(Lock())
        super(server, self).__init__(req_cond)
        self.reqq = Queue()
        self.repq = Queue()
        self.rep_cond = rep_cond

    def request(self, req):
        with self.req_cond:
            self.reqq.put(req)
            self.req_cond.notifyAll()

    def requests(self, block=False):
        reqs = []
        if block:
            reqs.append(self.reqq.get(True))
        with self.req_cond:
            while not self.reqq.empty():
                reqs.append(self.reqq.get(False))
        return reqs

    def reply(self, rep):
        with self.rep_cond:
            self.repq.put(rep)
            self.rep_cond.notifyAll()

    def replies(self, block=False):
        reps = []
        if block:
            reps.append(self.repq.get(True))
        with self.rep_cond:
            while not self.repq.empty():
                reps.append(self.repq.get(False))
        return reps

    def wait(self, timeout=None):
        with self.req_cond:
            if self.reqq.empty():
                self.req_cond.wait(timeout)


class cluster(server):
    class member(Thread, object):
        def __init__(self, owner):
            super(cluster.member, self).__init__()
            self.owner = owner

        def __getattr__(self, name):
            return getattr(self.owner, name)

    def __init__(self, cls, servers, req_cond=None, rep_cond=None):
        super(cluster, self).__init__(req_cond, rep_cond)
        self.reqq = Queue()
        self.repq = Queue()
        self.rep_cond = rep_cond

        self.servers = [cls(self) for i in xrange(servers)]

    def requests(self, block=False):
        if block:
            return [self.reqq.get(True)]
        with self.req_cond:
            if not self.reqq.empty():
                return [self.reqq.get(False)]
            else:
                return []

    def start(self):
        for s in self.servers:
            s.start()

def catch_and_die(logger):
    def catcher(f):
        def new_f(*args, **kwargs):
            try:
                f(*args, **kwargs)
            except:
                logging.getLogger(logger).error('function call fails with ' +
                                                'exception', exc_info=True)
                _exit(1)
        return new_f
    return catcher
