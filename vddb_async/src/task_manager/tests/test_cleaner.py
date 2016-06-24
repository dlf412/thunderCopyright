from cleaner import cleaner
from fetcher import fetcher
from parse_config import parse_config
from loader import load_database
from manager import CANNOT_SPAWN, OPS_KILLED, NO_OUTPUT, ExecutorResult
from utils import make_pool

from db_txn import db_execute, db_insert, db_result, db_txn

from functools import partial
from os import _exit
from threading import Condition, Event, Lock, Thread
from uuid import uuid4
import logging, logging.config


def do_setup(acc, user):
    print acc, user
    uid = str(uuid4())
    yield db_execute('''INSERT INTO task(task_identification, status,
                                         site_asset_id, company_id,
                                         task_priority, user_id, clip_duration,
                                         clip_format)
                             VALUES (%s, 'query', UUID(), %s, 128, %s, 600,
                                     'mp4')''', uid, acc, user)
    _, r = yield db_insert('''INSERT INTO taskQueryHis(task_identification)
                                   VALUES (%s)''', uid)
    yield db_result(uid, r)


def setup(config, pool, acc, user):
    total = 20
    rows = {}
    for _ in xrange(total):
        uid, r = db_txn(pool, partial(do_setup, acc, user))
        print uid, r
        rows[uid] = r

    fetch = fetcher(config, pool, Condition(Lock()), Condition(Lock()))
    clean = cleaner(config, pool, Condition(Lock()), Condition(Lock()))
    ev = Event()
    ev.clear()
    load = Thread(target=load_database, args=(config, pool, ev, [fetch, clean]))  # @IgnorePep8
    load.start()
    ev.wait()
    fetch.start()

    tasks = []
    while len(tasks) < total:
        print 'already fetched: ', len(tasks), 'tasks'
        print 'to fetch tasks from db'
        fetch.request(acc)
        for r in fetch.replies(True):
            ts = r[1]
            print 'fetched', len(ts), 'tasks'
            for t in ts:
                if t.uuid in rows:
                    tasks.append((t, rows[t.uuid]))

    return (clean, tasks)

logging.config.fileConfig('test_log.conf')
config = parse_config('test.conf')
pool = make_pool(config)

account = int(config['test_account'])
user = int(config['test_user'])
clean, tasks = setup(config, pool, account, user)

clean.start()

retry_codes = clean.backend_retry
retry = list(retry_codes)[0]
no_retry = max(retry_codes) + 1

i = 0

for use_row in (True, False):
    for code in (0, CANNOT_SPAWN, OPS_KILLED, NO_OUTPUT):
        t, r = tasks[i]
        i += 1
        print 'cleaning task: ', t.id, t.uuid, r
        clean.request((t, r if use_row else None, code, None))

for use_row in (True, False):
    for exec_code in (0, 1):
        for backend_code in (0, retry, no_retry):
            print i
            t, r = tasks[i]
            i += 1
            print 'cleaning task: ', t.id, t.uuid, r
            res = ExecutorResult(code=exec_code, backend_code=backend_code,
                                 matches=[], crr='')
            clean.request((t, r if use_row else None, 0, res))

_exit(0)
