#!/usr/bin/env python
#coding: utf-8

# from gevent import monkey
# monkey.patch_all()
# import gevent

import os
import time
import signal
import traceback
# import json
# from datetime import datetime
import Queue
from multiprocessing import Pool, Manager  # Process, 
from logging.handlers import SysLogHandler
# try:
#     import cPickle as pickle
# except:
#     import pickle

import yaml
import statsd
# import requests
import MySQLdb as mdb
from kombu import Exchange, Connection, Queue as MqQueue
from kombu.mixins import ConsumerMixin

from common.utils import execute_sql, insert_vddb_tmp
from common.mylogger import mylogger
from common.dbpc import dbpc


# ==============================================================================
#  Global variables
# ==============================================================================
cfg = None
logger = None
flag_queue = None


# ==============================================================================
#  Helper functions
# ==============================================================================
def gen_statsd_client(info):
    STATSD_HOST   = info['host']
    STATSD_PORT   = info['port']
    STATSD_PREFIX = info['prefix']
    return statsd.StatsClient(STATSD_HOST, STATSD_PORT,
                              prefix=STATSD_PREFIX)

    
def gen_db_conn(info):
    conn = mdb.connect(**info)
    conn.cursor().execute("set names utf8")
    return conn
    

def stop_all(signum, frame):
    logger.warning('@@@ kill all by %d.' % os.getpid())
    os.killpg(os.getpgid(os.getpid()), signal.SIGKILL) 
    

# ==============================================================================
#  Core functions
# ==============================================================================
class InsertWorker(ConsumerMixin):

    def __init__(self,
                 connection,      # MQ connection
                 queue,           # MQ Queue
                 db_conn,         # Database connection
                 insert_todo_sql, # Database info
                 flag_queue,      # Process queue for stop the worker
                 statsd_client,
                 statsd_key):
        self.connection = connection
        self.queue = queue
        self.flag_queue = flag_queue
        self.db_conn = db_conn
        self.insert_todo_sql = insert_todo_sql
        self.statsd_client = statsd_client
        self.statsd_key = statsd_key


    def get_consumers(self, Consumer, channel):
        return [Consumer(queues=[self.queue],
                         accept=['pickle', 'json'],
                         callbacks=[self.process_task])]


    def process_task(self, body, message):
        logger.debug('[process_task.body]: %s' % str(body))
        self.process_msg(body, self.db_conn, self.insert_todo_sql)
        message.ack()
        self.statsd_client.incr(self.statsd_key)


    def process_msg(self, body, conn, sql):
        params = body.get('params')

        # task_uuid    = params.get('external_id')
        client_id    = params.get('additional_info').get('client_id')
        thunder_hash = params.get('thunder_hash')
        digest       = params.get('digest')
        # URL
        url = params.get('url')
        url_loc  = url.get('location')
        url_hash = url.get('hash')
        # Seed
        seed_file = params.get('seed_file', {})
        seed_hash  = seed_file.get('hash', '')
        swift_path = seed_file.get('path', '')

        algorithm = params.get('digest_algorithm')
        mime_type = params.get('mime_type')
        file_name = params.get('file_name')
        file_size = params.get('file_size')

        digest = url_hash if url_hash else seed_hash
        record = (cfg['custom-type'], client_id, thunder_hash, url_loc,
                  digest, algorithm,
                  mime_type, file_name, file_size, swift_path)
        try:
            execute_sql(conn, sql, record, commit=True)
        except mdb.IntegrityError:
            pass


def loop_get(flag_queue, db_info):
    task_mq_cfg = cfg['task-mq']
    mq_url          = task_mq_cfg['url']
    routing_key     = task_mq_cfg['routing-key']
    exchange_name   = task_mq_cfg['exchange']
    queue_name      = task_mq_cfg['queue']
    insert_todo_sql = db_info['sqls']['insert-todo']

    statsd_cfg = cfg['statsd']
    statsd_client = gen_statsd_client(statsd_cfg)
    STATSD_KEY = statsd_cfg['key-get']
    
    while True:
        todo_conn = gen_db_conn(db_info['todo-db'])
        with Connection(mq_url) as conn:
            exchange = Exchange(exchange_name, type='fanout')
            queue = MqQueue(queue_name, exchange, routing_key=routing_key)
            worker = InsertWorker(conn, queue, todo_conn, insert_todo_sql, flag_queue,
                                  statsd_client, STATSD_KEY)
            try:
                worker.run()
            except KeyboardInterrupt:
                break
            except Exception:
                logger.error('loop_get Exception: %r' % traceback.format_exc())
                time.sleep(0.5)
            finally:
                todo_conn.close()

    logger.warning('@@@ Exit: loop_get: ()')


def _do_insert(done_conn, insert_done_sql, record):
    rid, thunder_hash, digest = record[0], record[3], record[5]
    try:
        logger.info('inserting mysql %d' % rid)
        execute_sql(done_conn, insert_done_sql, record[1:-1], commit=True)
        logger.info('inserting vddb %d' % rid)
        resp, logs = insert_vddb_tmp(cfg['vddb-async-url'], [thunder_hash, digest])
        if not resp or resp.status_code != 200:
            raise ValueError('Insert result management Failed! <%r>' % (logs,))
        logger.info('inserted mysql %d' % rid)
    except mdb.IntegrityError:
        pass
    except Exception:
        logger.error('_do_insert requests.Exception: %r' % traceback.format_exc())
        time.sleep(0.5)

    
def do_insert(flag_queue, task_queue, res_queue, db_info):
    logger.info('Starting: do_insert()')
    insert_done_sql = db_info['sqls']['insert-done']
    delete_todo_sql = db_info['sqls']['delete-todo']
    
    done_conn = gen_db_conn(db_info['done-db'])
    todo_conn = gen_db_conn(db_info['todo-db'])

    statsd_cfg = cfg['statsd']
    statsd_client = gen_statsd_client(statsd_cfg)
    STATSD_KEY = statsd_cfg['key-insert']
    
    while True:
        try:
            record = task_queue.get()
            _do_insert(done_conn, insert_done_sql, record)
            execute_sql(todo_conn, delete_todo_sql, (record[0],), commit=True)
            res_queue.put(True)
            statsd_client.incr(STATSD_KEY)
        except Exception:
            res_queue.put(False)
            done_conn.close()
            done_conn = gen_db_conn(db_info['done-db'])
            todo_conn.close()
            todo_conn = gen_db_conn(db_info['todo-db'])
            logger.error('loop_insert requests.Exception: %r' % traceback.format_exc())
            time.sleep(0.5)

    done_conn.close()
    todo_conn.close()
    logger.warning('@@@ Exit: do_insert()')


def loop_insert(flag_queue, task_queue, res_queue, db_info):

    logger.info('Starting: loop_insert() => %s' % (cfg['vddb-async-url']))

    select_todo_sql = db_info['sqls']['select-todo']
    select_limit = db_info['select-limit']
    
    todo_conn = gen_db_conn(db_info['todo-db'])

    while True:
        try:
            while not res_queue.empty():
                ok = res_queue.get()
                
            rows = execute_sql(todo_conn, select_todo_sql,
                               (select_limit, ), fetch=True)
            for record in rows:
                logger.info('Deleted mysql %d' % record[0])
                task_queue.put(record)
                
            time.sleep(1)
            results = []
            results_ok = 0
            rows_len = len(rows)
            for i in range(rows_len):
                try:
                    ok = res_queue.get(timeout=5)
                except Queue.Empty():
                    ok = False
                if ok:
                    results_ok += 1
                results.append(ok)
                
            if rows_len == 0:
                time.sleep(db_info['select-interval'])
            logger.info('One turn: (%d/%d), %r' % (results_ok, rows_len, results))
        except KeyboardInterrupt:
            break
        except Exception:
            todo_conn.close()
            todo_conn = gen_db_conn(db_info['todo-db'])
            logger.error('loop_insert Exception: %r' % traceback.format_exc())
            time.sleep(0.5)
    
    todo_conn.close()
    logger.warning('@@@ Exit: loop_insert()')


# ==============================================================================
#  Mirror functions
# ==============================================================================
def parse_args():
    from optparse import OptionParser

    parser = OptionParser()
    parser.add_option("-c", "--cfg", metavar="FILE", help="YAML config FILE")
    parser.add_option("-d", "--db", metavar="STRING", choices=("mysql", "hbase"),
                      help="Database type: mysql/hbase.")
    parser.add_option("--log-file", metavar="FILE", help="Log to file")
    parser.add_option("--log-level", metavar="STRING", help="Log level")

    (opts, args) = parser.parse_args()
    if not opts.cfg:
        config_path = os.getenv('PROG_CONFIG')
        if config_path:
            opts.cfg = config_path
        else:
            parser.error('Config file is required!')

    return opts, args


def load_config():
    opts, args = parse_args()
    with open(opts.cfg, 'r') as f:
        config = yaml.load(f)

        if opts.db:
            config['db-type'] = opts.db
        if opts.log_file:
            config['log']['file'] = opts.log_file
        if opts.log_level:
            config['log']['level'] = opts.log_level
        config['log']['level'] = config['log']['level'].upper()

    return config


def main():
    global cfg, logger, flag_queue
    # global execute_sql, insert_vddb, _do_insert

    cfg = load_config()
    logger = mylogger()
    p_manager = Manager()
    flag_queue = p_manager.Queue()

    log_cfg = cfg['log']
    log_file = log_cfg['file']
    log_level = log_cfg['level']
    logger.init_logger('tmp-result-generator', log_level, log_file,
                       SysLogHandler.LOG_LOCAL1) # For debug

    
    signal.signal(signal.SIGQUIT, stop_all)
    signal.signal(signal.SIGTERM, stop_all)

    logger.info('==================[Starting....]===================')
    db_type = cfg['db-type']
    db_info = cfg['db'][db_type]
    pool_size_get = cfg['pool-size-get']
    pool_size_insert = cfg['pool-size-insert']
    

    dbpc_cfg = cfg['dbpc']
    DBPC_HOST      = dbpc_cfg['host']
    DBPC_PORT      = int(dbpc_cfg['port'])
    DBPC_SERVICE   = dbpc_cfg['service']
    DBPC_COMPONENT = dbpc_cfg['component']
    DBPC_INTERVAL  = int(dbpc_cfg['interval'])
    t_dbpc = dbpc(DBPC_HOST, DBPC_PORT,
                  DBPC_SERVICE, DBPC_COMPONENT,
                  DBPC_INTERVAL)
    t_dbpc.start()
    
    pool_get = Pool(pool_size_get)
    for i in range(pool_size_get):
        pool_get.apply_async(loop_get, args=(flag_queue, db_info))
    pool_get.close()
    
    manager = Manager()
    res_queue = manager.Queue(pool_size_insert)
    task_queue = manager.Queue(pool_size_insert)
    pool_insert = Pool(pool_size_insert)
    for i in range(pool_size_insert):
        pool_insert.apply_async(do_insert, args=(flag_queue, task_queue, res_queue, db_info))
    pool_insert.close()

    try:
        loop_insert(flag_queue, task_queue, res_queue, db_info)
    except KeyboardInterrupt:
        pass
        
    stop_all(None, None)
    print '<THE END>'
    logger.info('======================[THE END]==================')


if __name__ == '__main__':
    main()
