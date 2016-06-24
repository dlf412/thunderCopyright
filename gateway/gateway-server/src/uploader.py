#!/usr/bin/env python
#coding: utf-8

from gevent import monkey
monkey.patch_all()

import time
import json
import base64
import traceback
import os
from os.path import getmtime, getsize
from logging.handlers import SysLogHandler
try:
    import cPickle as pickle
except:
    import pickle

    
import redis
import gevent
from gevent.pool import Pool
from swiftclient import Connection as SwiftConnection
from swiftclient.exceptions import ClientException


from common import dbpc
from common.mylogger import mylogger
from services import QueryBroker
from utils import (log_normal,
                   LOG_DEBUG, LOG_INFO, LOG_WARN,
                   LOG_WARNING, LOG_ERROR, LOG_CRITICAL)

SWIFT_RETRY_TIMES = 2
SWIFT_TIMEOUT = 5

def process_isalive(pid):
    isalive = True
    try:
        os.kill(pid, 0)
    except OSError:
        isalive = False
    return isalive


def swift_upload(container, path, auth, user, key):
    conn = SwiftConnection(auth, user, key, snet=False, insecure=True)
    put_headers = { 'x-object-meta-mtime': "%f" % getmtime(path) }
    retry = SWIFT_RETRY_TIMES 
    while retry > 0:
        try:
            with open(path, 'rb') as fd:
                conn.put_object(container, path, fd,
                                content_length=getsize(path), headers=put_headers)
            return True
        except ClientException:
            log_normal(logger, {
                'action': 'upload-error',
                'error': 'swift client exception'
            }, LOG_ERROR)
            conn.put_container(container, headers={})
            retry -= 1
    return False


def do_task(logger, pickle_path, swift_auth, swift_user, swift_key):
    
    with open(pickle_path, 'rb') as f:
        task_info, file_path, container, seed_file = pickle.load(f)

    with open(file_path, 'wb') as f:
        seed_file_bin = base64.b64decode(seed_file)
        f.write(seed_file_bin)

    uuid = task_info[0][-2]
    log_normal(logger, {
        'action': 'going-todo-task',
        'info': {
            'pickle_path': pickle_path,
            'task_info': task_info
        }
    }, LOG_INFO, uuid=uuid)

    try:
        g = gevent.spawn(swift_upload, container, file_path, swift_auth, swift_user, swift_key)
        if not g.get(block=True, timeout=SWIFT_TIMEOUT):
            g.kill()
            raise Exception('Swift Upload Faile!')
            
        log_normal(logger, {
            'action': 'upload-ok',
        }, LOG_INFO, uuid=uuid)
        _args, _kwargs = task_info
        qb.push(*_args, **_kwargs)
        log_normal(logger, {
            'action': 'push-querybroker-ok',
        }, LOG_INFO, uuid=uuid)
    except Exception:
        log_normal(logger, {
            'action': 'upload-error',
            'error': traceback.format_exc()
        }, LOG_ERROR, uuid=uuid)
    finally:
        os.remove(file_path) 
        os.remove(pickle_path)


def _loop_tasks(logger, redis_server, redis_list_name,
               pickle_dir, pickle_ext, pickle_corrupt_time,
               broker_routing_key, broker_exchange, broker_mq_url,
               swift_auth, swift_user, swift_key):

    log_normal(logger, {'action': 'uploader-started'}, LOG_INFO)
    
    try:
        if not os.path.exists(pickle_dir):
            os.mkdir(pickle_dir)
    except OSError:
        pass

    r = redis.Redis(redis_server)
    def push_redis():
        ts_now = time.time()
        for path in os.listdir(pickle_dir):
            path = os.path.join(pickle_dir, path)
            if path.endswith(pickle_ext):
                ts_file = os.path.getmtime(path)
                
                if ts_now - ts_file > pickle_corrupt_time:
                    os.remove(path)
                else:
                    r.lpush(redis_list_name, path)

    def start_empty_archieve():
        if os.path.exists(PID_FILE):
            return

        with open(PID_FILE, 'w') as f:
            f.write(str(os.getpid()))
        time.sleep(0.2)
        with open(PID_FILE, 'r') as f:
            pid = int(f.read().strip())
        if pid == os.getpid():
            log_normal(logger, {
                'action': 'empty-archieve-starting',
                'info': {
                    'pid': pid
                }
            }, LOG_INFO)
            r.ltrim(redis_list_name, 0, -1)
            push_redis()
            log_normal(logger, {'action': 'empty-archieve-done'}, LOG_INFO)
            os.remove(PID_FILE)

    if r.llen(redis_list_name) == 0:
        log_normal(logger, {'action': 'no-task-in-redis-queue'}, LOG_INFO)
        start_empty_archieve()

    # Main loop.
    p = Pool(POOL_SIZE)
    while process_isalive(os.getppid()):
        res = r.brpop(redis_list_name, timeout=1)
        if not res:
            continue
        _, pickle_path = res
        log_normal(logger, {
            'action': 'got-redis-task',
            'info': {
                'pickle_path': pickle_path
            }
        }, LOG_INFO)
        p.wait_available()
        p.apply_async(do_task, (logger, pickle_path, swift_auth, swift_user, swift_key))

    p.join()
    # Delete pid file
    if os.path.exists(PID_FILE):
        try:
            os.remove(PID_FILE)
        except OSError:
            pass

    log_normal(logger, {'action': 'exit-uploader-process'}, LOG_INFO)


def loop_tasks(logger, redis_server, redis_list_name,
               pickle_dir, pickle_ext, pickle_corrupt_time,
               broker_routing_key, broker_exchange, broker_mq_url,
               swift_auth, swift_user, swift_key):
    while process_isalive(os.getppid()):
        try:
            _loop_tasks(logger, redis_server, redis_list_name,
                        pickle_dir, pickle_ext, pickle_corrupt_time,
                        broker_routing_key, broker_exchange, broker_mq_url,
                        swift_auth, swift_user, swift_key)
        except Exception:
            log_normal(logger, {
                'action': 'main-loop-exception',
                'error': traceback.format_exc()
            }, LOG_ERROR)
            time.sleep(0.5)


CONFIG_PATH = os.getenv('GATEWAY_CONFIG')
config = None
with open(CONFIG_PATH, 'r') as f:
    config = json.load(f)

LOG_FILE  = config['log']['file']
LOG_LEVEL = config['log']['level'].upper()

uploader = config['uploader']
REDIS_SERVER        = uploader['redis_server']
REDIS_LIST_NAME     = uploader['redis_list_name']
MAX_LIST_LEN        = uploader['max_list_len']
POOL_SIZE           = uploader['pool_size']
PID_FILE            = uploader['pid_file']
PICKLE_DIR          = uploader['pickle_dir']
PICKLE_EXT          = uploader['pickle_ext']
PICKLE_CORRUPT_TIME = uploader['pickle_corrupt_time']
del uploader

swift = config['swift']
SWIFT_AUTH      = swift['auth']
SWIFT_USER      = swift['user']
SWIFT_KEY       = swift['key']
del swift

query_broker = config['query_broker']
BROKER_MQ_URL         = query_broker['mq_url']
BROKER_JSONRPC_METHOD = query_broker['jsonrpc_method']
BROKER_EXCHANGE       = query_broker['exchange']
BROKER_ROUTING_KEY    = query_broker['routing_key']
BROKER_PUB_TIMEOUT    = query_broker['publish_timeout']
del query_broker

dbpc_config = config['dbpc']
DBPC_HOST      = dbpc_config['host']
DBPC_PORT      = dbpc_config['port']
DBPC_SERVICE   = dbpc_config['service']
DBPC_INTERVAL  = dbpc_config['interval']
del dbpc_config

del config

logger = mylogger()
logger.init_logger('gateway-uploader', LOG_LEVEL, LOG_FILE, SysLogHandler.LOG_LOCAL1) # For debug
qb = QueryBroker(logger, BROKER_ROUTING_KEY, BROKER_EXCHANGE,
                 BROKER_PUB_TIMEOUT, BROKER_MQ_URL)


DBPC_COMPONENT = 'gateway-uploader'
if __name__ == '__main__':
    t_dbpc = dbpc.dbpc(DBPC_HOST, DBPC_PORT,
                       DBPC_SERVICE, DBPC_COMPONENT,
                       DBPC_INTERVAL)
    t_dbpc.start()
    
    loop_tasks(logger, REDIS_SERVER, REDIS_LIST_NAME,
               PICKLE_DIR, PICKLE_EXT, PICKLE_CORRUPT_TIME,
               BROKER_ROUTING_KEY, BROKER_EXCHANGE, BROKER_MQ_URL,
               SWIFT_AUTH, SWIFT_USER, SWIFT_KEY)
