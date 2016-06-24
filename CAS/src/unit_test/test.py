import kombu
from kombu import Connection, Producer, Exchange, Consumer
import time
import json
import sys
import threading
sys.path.append('../')
from download_task_process import download_task_process
#from syslog_wrap import *
from cas_utils import *
from statsd_operator import statsd_operator
import json
import redis
from redis_operater import redis_operater

class fetch_jobs(threading.Thread):
    def __init__(self, mq_url, queue_name):
        threading.Thread.__init__(self)
        self.th = download_task_process(mq_url, queue_name) 

    def run(self):
        self.th.run()

def test4():
    s = {}
    s['jsonrpc'] = 2.0
    s['params'] = {}
    s['params']['prioruty'] = 'low'
    s['params']['additional_info'] = {}
    s['params']['additional_info']['client_id'] = 1
    s['params']['additional_info']['client_address'] = 'http://123.com'
    print 's is ',s
    a = {}
    a['jsonrpc'] = '2.0'
    a['params'] = {}
    a['params']['priotiry'] = 'high'
    a['params']['additional_info'] = s['params']['additional_info']
    print 'a is' , a

def fill(s):
    js = {}
    js['msg'] = s
    sjs = json.dumps(js)
    return sjs

def test1():
    #salog_init_ex ('testxxx', 'LOG_DEBUG');
    #g_logger.init_logger('CAS_test', 'LOG_DEBUG', 'syslog')
    g_logger.init_logger('CAS_test', 'LOG_DEBUG', './log_test')
    
    g_logger.debug(fill('=====xxxxxtest start ====xxxx'))
    dispatcher = fetch_jobs('amqp://guest:guest@localhost:5672//', 'test')
    dispatcher.start()
    dispatcher.join()

def test2(status):
    hashkey = sys.argv[1]
    conn = redis.Redis(host='127.0.0.1', port=6379, db=0)
    primary_key = str(hashkey)
    init_flow = {}
    init_flow['status'] = status
    init_flow['time'] = time.time()
    s = json.dumps(init_flow)
    log_key = 'task#' + str(primary_key) + '#log'
    conn.set(log_key, s)

def read_logIn_redis():
    conn = redis.Redis(host='127.0.0.1', port=6379, db=0)
    lsize = conn.llen('task_log_list')
    print "list size is ", lsize
    for l in conn.lrange('task_log_list', 0, lsize):
        print l
        print conn.get(l)

def test3(status, pri):
    hashkey = sys.argv[1]
    conn = redis.Redis(host='127.0.0.1', port=6379, db=0)
    rp = redis_operater(conn)
    primary_key = str(hashkey)
    init_flow = {}
    init_flow['status'] = status
    init_flow['time'] = time.time()
    s = json.dumps(init_flow)
    log_key = 'task#' + str(primary_key) + '#log'
    rp.update_work_flow(hashkey, s, pri)


def test4():
    conn = redis.Redis(host='127.0.0.1', port=6379, db=0)
    lsize = conn.llen('task_log_list')
    rp = redis_operater(conn)
    init_flow = {}
    init_flow['status'] = 'finish'
    init_flow['time'] = time.time()
    
    for l in conn.lrange('task_log_list', 0, lsize):
        work_flow = conn.get(l)
        if work_flow is not None:
            work_flow = json.loads(work_flow)
        hashkey = l[5:-4]
        primary_key = str(hashkey)
        s = json.dumps(init_flow)
        rp.update_work_flow(hashkey, s, 'low')

def test5():
    conn = redis.Redis(host='127.0.0.1', port=6379, db=0)
    
    print "====first====="
    for l in conn.lrange('task_log_list', 0, 10):
        print l

    print "====second====="
    for l in conn.lrange('task_log_list', 5, 10):
        print l

if __name__ == '__main__':
    #test2('processing')
    test3('processing', 'low')
    #test3('url_seed_finish', 'low')
    #test3('finish', 'low')
    #test3('error#500#3', 'low')
    #test5()

