from server import server, catch_and_die
from tm_sqls import *
from task_stat import *
from db_txn import db_execute, db_insert, db_result, db_txn

from collections import defaultdict, namedtuple
from functools import partial
import traceback
from os import getenv
from signal import SIGQUIT
import simplejson as json
from subprocess import PIPE, Popen
from urllib import urlencode
from celery.result import ResultSet
import celery
import time
import os
import sys
import Queue
from redis import RedisError
__filedir__ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, __filedir__)
from task import Task, TaskRes
from logger import g_logger
from utils import trans2json

ExecutorResult = namedtuple('ExecutorResult', ['code', 'backend_code',
                                               'matches', 'crr'])
TaskContent = namedtuple('TaskContent', ['submit_at', 'from_reverse', 'site_asset_id',
                           'deadline', 'id', 'retries', 'account',
                           'uuid', 'created_at', 'format', 'priority', 'scope',
                           'queued_at', 'dna_url', 'external_id'])
class manager(server):
    def __init__(self, config, pool, manager_conf, pick_conf, cleaner):
        super(manager, self).__init__(manager_conf, pick_conf)
        self.path = getenv('MW_HOME')
        assert self.path != None
        self.tasks = ResultSet([])

        self.backoff = int(config['retry_backoff'])
        self.powlim = int(config['max_backoff_power'])
        # backend codes to retry
        # CONFIRM: we're not retrying with other codes
        codes = []
        if config['retry_forever_list'] != '':
            codes += [int(c) for c in config['retry_forever_list'].split(',')]
        if config['retry_sometime_list'] != '':
            codes += [int(c) for c in config['retry_sometime_list'].split(',')]
        self.backend_retry = set(codes)
        # thresholds
        self.thresholds = defaultdict(lambda: {})
        self.thresholds['audio']['score'] = int(config["fp_audio_score"])
        self.thresholds['video']['score'] = int(config["fp_video_score"])
        self.thresholds['audio']['duration'] = int(config["fp_audio_duration"])
        self.thresholds['video']['duration'] = int(config["fp_video_duration"])

        self.task_set_join_timeout = int(config['task_set_join_timeout'])

        self.pool = pool
        self.cleaner = cleaner
        self.taskm = defaultdict(dict)

    @catch_and_die('mwtm_manager')
    def run(self):
        while True:
            self.loop()

    @staticmethod
    def record(t, pid=0):
        yield db_execute(BEGIN_QUERY, pid, t.id)
        #c, r = yield db_insert(QUERY_EVENT, t.uuid, pid)
        #if c <= 0:
        #    yield db_result()
        #else:
        #    yield db_result(r)

    def one_request(self, wait=False):
        with self.req_cond:
            return self.reqq.get(wait)

    def task_check(self, t, accs, backends):
        if not t.account in accs:
            self.logger.debug("account %s maybe deleted" % t.account)
            return False
        for b in accs[t.account].backends:
            if not b.backend in backends:
                self.logger.warning('backend %s for account %s ' +
                                    'inconsistent with backends in db',
                                    b.backend, t.account)
                return False
        return True

    def buf_tasks(self, reqs):
        accs = self.accounts()
        backends = self.backends()
        for t in reqs:
            try:
                self.logger.info("receivce task from picker, task_uuid: %s, "
                                 "site_asset_id: %s" % (t.uuid, t.site_asset_id))
                self.logger.debug("receive task info:%s" % t._asdict())
                g_logger.info(trans2json(message="site_asset_id:%s, "
                    "task_uuid:%s, external_id:%s" % (t.site_asset_id, t.uuid, t.external_id),
                    action="receive picked task"))
                if not self.task_check(t, accs, backends):
                    self.reply(t)
                    continue
                acc = accs[t.account]._asdict()
                acc["backends"] = [v._asdict() for v in acc["backends"]]
                backs = {}
                for k, v in backends.iteritems():
                    backs[k] = v._asdict()
                self.logger.debug("add task's account: %s, backends: %s" % (acc, backs))

                ct = Task().query.delay(t._asdict(), acc, backs)
                self.taskm[ct.task_id]['celery_task'] = ct
                self.taskm[ct.task_id]['task'] = t
                self.tasks.add(ct)
                self.logger.info("add task to celery, task_uuid: %s, "
                                 "site_asset_id: %s, celery_uuid: %s " % \
                                 (t.uuid, t.site_asset_id, ct.task_id))
                g_logger.info(trans2json(message="site_asset_id:%s, "
                              "task_uuid:%s, external_id:%s" % (t.site_asset_id, t.uuid,
                              t.external_id), action="add task to celery"))

            except Exception, ex:
                self.reply(t)
                self.logger.error("catch exception from buf tasks, "
                                  "task_uuid: %s , site_asset_id: %s" % (t.uuid,
                                  t.site_asset_id), exc_info=True)
                continue
            try:
                db_txn(self.pool, partial(self.record, t))
            except Exception:
                self.logger.error("failed to record execution for task %s" % t.uuid)

    def parse_query_res(self, query_res):
        self.logger.debug("ret task from task_executor: %s" % (query_res.task))
        t, ret, out, err = TaskContent(**query_res.task), query_res.ret, \
                           query_res.out, query_res.err
        state, res = 0, None
        if ret == -SIGQUIT:
            self.logger.error("task from account %s killed " +
                              "by ops using SIGQUIT, not going to " +
                              "retry", t.uuid, t.account)
            state = OPS_KILLED
        else:
            try:
                res = json.loads(out)
            except:
                self.logger.error("failed to read/parse output from " +
                                  "executor for task %s from account " +
                                  "%s", t.uuid, t.account)
                state = BAD_OUTPUT
            else:
                for k in ("code", "backend_code", "matches", "crr"):
                    if not k in res:
                        res[k] = None
                res = ExecutorResult(**res)
        return t, state, res

    def task_finished(self, celery_id, query_res):
        try:
            t = self.taskm[celery_id]['task']
            self.logger.info("finished query, task_id:%s, "
                             "site_asset_id: %s, celery_id:%s, "
                             "ret: %s, err: %s " %
                             (t.uuid, t.site_asset_id, celery_id,
                              query_res.ret, query_res.err))
            self.logger.debug("task_id:%s, out: %s", t.uuid, query_res.out)
            self.logger.debug("finished task info: %s" % str(t))
            #parse query result
            g_logger.info(trans2json(message="site_asset_id:%s, "
                          "task_uuid:%s, external_id:%s " % (t.site_asset_id, t.uuid,
                          t.external_id), action="task finished query from celery"))
            if not isinstance(query_res, TaskRes): #means catch some exception
                self.cleaner.request((t, BAD_OUTPUT, None))
            else:
                _, state, res = self.parse_query_res(query_res)
                self.cleaner.request((t, state, res))
        except Exception, ex:
            self.cleaner.request((t, BAD_OUTPUT, None))
            self.logger.error("task finished catch unhandle exception, "
                              "task_uuid:%s" % t.uuid, exc_info=True)
        finally:
            #discard task from resultset
            self.logger.debug("reply task to picker, task_uuid: %s" % t.uuid)
            self.reply(t)
            self.tasks.discard(self.taskm[celery_id]['celery_task'])
            del self.taskm[celery_id]
        #add new task
        try:
            req = None
            req = self.one_request()
            self.buf_tasks([req])
        except Queue.Empty:
            self.logger.info("no task in manager queue")
        except Exception:
            self.reply(req)
            self.logger.error("catch some exception when add task, just return "
                              "to picker task_uuid: %s" % \
                              req.uuid if req else req, exc_info=True)

    def loop(self):
        try:
            if self.tasks.results != []:
                self.tasks.join_native(callback=self.task_finished,
                        propagate=False, timeout=self.task_set_join_timeout)
            else:
                self.logger.info("task(ResultSet) is empty, buf tasks from request")
                self.buf_tasks(self.requests(True))
        except celery.exceptions.TimeoutError:
            self.logger.info("task check timeout, buf tasks from request")
            self.buf_tasks(self.requests())
        except RedisError:
            self.logger.info("catch redis error", exc_info=True)
            time.sleep(1)
        except:
            self.logger.error("unhandler exception in manager loop",
                              exc_info=True)
