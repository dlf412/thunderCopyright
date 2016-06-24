#!/usr/bin/env python

import os
import sys
from os import _exit, getenv
from sys import stderr
#from version import gversion

PROGRAM_INFO = "VddbAsync task_manager 1.2.1.0"

if len(sys.argv) > 1:
    print PROGRAM_INFO
    sys.exit(0)

path = getenv('MW_HOME')
if path == None:
    stderr.write("MW_HOME not set in environment, program cannot start.")
    _exit(1)
sys.path.append('/'.join([path, 'lib']))
os.environ['PATH'] = ':'.join([os.environ['PATH'], '/'.join([path, 'bin'])])


from cleaner import cleaner_cluster
from manager import manager
from parse_config import parse_config
from fetcher import fetcher
from loader import load_database
from picker import picker
from utils import check_kingship, make_db_pool, start_dbpc, make_hbase_pool, \
                  make_redis_conn
#from dbpcer import dbpcer
from dbpc import dbpc

import logging.config
from threading import Condition, Event, Lock, Thread
import getopt

DB_RESERVE_CONN = 5

def main():
    # use MW_HOME to find etc/ & var/ directories
    path = getenv('MW_HOME')
    if path == None:
        stderr.write("MW_HOME not set in environment, program cannot start.")
        _exit(1)
    logging.config.fileConfig('/'.join([path, 'etc', 'logging.conf']),
                              disable_existing_loggers=False)
    config = parse_config('/'.join([path, 'etc', 'vddb_async.conf']))
    start_dbpc(config, 'task_manager')

    # make db connection pool, assign 1 connection to each db accessing thread
    # kingship checker + db loader + task fetcher +
    # task cleanup : a total of 4 threads, + 1 manager thread pool
    db_pool = make_db_pool(config, DB_RESERVE_CONN + int(config['cleaner_threads_num']))
    # kingship granted event, all threads wait till this event is set
    hbase_pool = make_hbase_pool(config)

    kev = Event()
    kev.clear()
    # db load finished eventm all threads wait till this event is set
    lev = Event()
    lev.clear()
    # conditions each thread wait on, named after the waiter
    fetch_cond = Condition(Lock())
    pick_cond = Condition(Lock())
    manage_cond = Condition(Lock())
    clean_cond = Condition(Lock())
    # kingship checker
    check = Thread(target=check_kingship,
                   args=(config, db_pool, kev, config['tm_module_name'],
                         # NOTE: if task manager stops working for X minutes, the
                         #       tasks won't be scheduled and executed for X
                         #       minutes since tasks have to be finished in a
                         #       timely fashion, the task manager master timeout
                         #       should not be too long
                         int(config['tm_master_timeout']),
                         logging.getLogger('mwtm_tmcheck')))
    check.start()
    # all other threads wait here
    kev.wait()
    # this event is never cleared
    #assert kev.isSet()
    # worker threads, created in dependence order
    fetch = fetcher(config, db_pool, fetch_cond, pick_cond)
    clean = cleaner_cluster(config, db_pool, hbase_pool, clean_cond, manage_cond)
    manage = manager(config, db_pool, manage_cond, pick_cond, clean)
    pick = picker(config, pick_cond, fetch, manage)
    # db config observers, loader will notify them when there's new data loaded
    observers = [fetch, pick, manage, clean]
    load = Thread(target=load_database, args=(config, db_pool, lev, observers))
    # start the loader, and make other threads wait for the first load
    load.start()
    lev.wait()
    assert lev.isSet()

    # start all other threads
    fetch.start()
    clean.start()
    manage.start()
    pick.start()

    # threads never returns, so joining is quite pointless here

main()
