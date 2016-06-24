import logging
import kombu
from kombu import Connection, Producer, Exchange, Consumer
from mylogger import *
#from syslog_wrap import *
try:
    import json
except:
    import simplejson as json
import Queue
import threading
from statsd_operator import statsd_operator
#g_logger will be initlized in main thread
g_logger = mylogger()
g_logger_info = mylogger()

'''
thunder.cas.submit_tasks : total num of query broker's submit tasks
thunder.cas.download_tasks : total num of download tasks
'''
g_statsd = None
SUBMIT_TASKS = 'thunder.cas.submit_tasks'
DOWNLOAD_TASKS = 'thunder.cas.download_tasks'

task_queue = Queue.Queue()
task_mutex = threading.Lock()

task_logs = 'task_log_list'

class safe_lock(object):
    def __enter__(self):
        task_mutex.acquire()
    def __exit__(self, *args):
        task_mutex.release()

def get_external_id(task):
    try:
        if isinstance(task, dict):
            dict_task = task
        else:
            dict_task = json.loads(task)

        if dict_task['params'].has_key('external_id'):
            return dict_task['params']['external_id']
        return None
    except Exception, msg:
        g_logger.debug('get external id failed [%s]' %(msg))
        return None

def connect_rabbitmq(mq_url, queue_name, routing_key):
    try:
        exchange = Exchange(queue_name)
        queue = kombu.Queue(queue_name, exchange, routing_key)
        #connection = Connection('amqp://guest:guest@localhost:5672//')
        connection = Connection(mq_url)
        return connection
    except Exception, msg:
        raise

def redis_url_parse(url):
    try:
        redis_conf = {};
        start_idx = url.find ('redis://');
        if (not (start_idx == 0)):
            raise Exception ("bad redis format (%s)" %url);
        start_idx = len ('redis://');
        end_idx = url.find (':', start_idx);
        if (end_idx < 0):
            raise Exception ("bad redis format (%s)" %url);
        redis_conf['host'] = url[start_idx:end_idx];
        start_idx = end_idx + 1;
        end_idx = url.find ('/', start_idx);
        if (end_idx < 0):
            raise Exception ("bad redis format (%s)" %url);
        redis_conf['port'] = int (url[start_idx:end_idx]);
        start_idx = end_idx + 1;
        redis_conf['db'] = url[start_idx:];
        return redis_conf;
    except Exception, msg:
        raise

def create_error_msg(status, hashkey, task, redis_conn):
    try:
        s = {}
        s['jsonrpc'] = '2.0'
        s['id'] = 1
        s['method'] = 'finish_task'
        s['params'] = {}
        s['params']['error_code'] = 121509
        s['params']['message'] = status

        if hashkey is not None:
            task_key = 'task#' + hashkey
            task_info = redis_conn.get(task_key)
            if task_info is None:
                return None
            j_task_info = json.loads(task_info)
        else:
            if task is not None:
                j_task_info = json.loads(task)

        
        if j_task_info['params'].has_key('additional_info'):
            s['params']['additional_info'] = j_task_info['params']['additional_info'] 
        
        if j_task_info['params'].has_key('url'):
            if j_task_info['params']['url'].has_key('hash'):
                s['params']['url'] = {}
                s['params']['url']['hash'] = j_task_info['params']['url']['hash']
                s['params']['url']['location'] = j_task_info['params']['url']['location']
        
        if j_task_info['params'].has_key('seed_file'):
            if j_task_info['params']['seed_file'].has_key('hash'):
                s['params']['seed_file'] = {}
                s['params']['seed_file']['hash'] = j_task_info['params']['seed_file']['hash']
                s['params']['seed_file']['path'] = j_task_info['params']['seed_file']['path']
        
        if j_task_info['params'].has_key('thunder_hash'):
            s['params']['thunder_hash'] = j_task_info['params']['thunder_hash']

        js = json.dumps(s)
        return js
    except Exception, msg:
        g_logger.error('create error msg failed [%s]' %(msg))
        return None
