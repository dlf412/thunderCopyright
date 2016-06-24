# coding:utf-8
import priority_global_vars as gv
import os
import json
import traceback
import sys
import ast
from datetime import datetime
from kombu import Connection
from kombu.pools import producers
from priority_util import *
from redis_oper import *
from hot_url_queue import HotUrlQueue
from kombu import Exchange, Queue
from kombu.mixins import ConsumerMixin
import utils

CLIENT = 0
SERVER = 1
ADD_OK = 1
ADD_ERROR = -1
GET_ERROR = -2
MEMBER_EXISTS = -3
HIGH_QUEUE     =  'high_queue'
LOW_QUEUE      =  'low_queue'
BLACK_QUEUE    =  'low_queue'

URL_HOT        =  'hot'
TASK_INFO      =  'task_info'
CREATE_TIME    =  'create_time'
UPDATE_TIME    =  'update_time'

class Worker(ConsumerMixin):

    def __init__(self, connection, exchange, queue, routing_key):
        reload(sys)
        sys.setdefaultencoding('utf-8')
        self.connection = connection
        self.exchange = exchange
        self.queue = queue
        self.routing_key = routing_key
        self.is_operredis_error = False
        self.url_hot = 1
        self.is_duplicate = False
        self.client_id = ''
        self.digest = ''
        self.server_flag  =  CLIENT
        self.huq_url_hot  =  gv.rds_url_hot_conn
        self.huq_black    =  HotUrlQueue(url = gv.rds_cas_black)
        self.huq_low      =  HotUrlQueue(url = gv.rds_cas_low)
        self.huq_high     =  HotUrlQueue(url = gv.rds_cas_high)
        self.RESULT_HIGH  =  {'priority':'high','conn':self.huq_high}
        self.RESULT_BLACK =  {'priority':'black','conn':self.huq_black}
        self.RESULT_LOW   =  {'priority':'low','conn':self.huq_low}


    def get_consumers(self, Consumer, channel):
        task_exchange = Exchange(self.exchange)
        task_queues = Queue(self.queue, task_exchange, routing_key=self.routing_key)
        return [Consumer(queues=task_queues,
                         accept=['pickle', 'json'],
                         callbacks=[self.process_task])]

    def on_consume_ready(self, connection, channel, consumers):
        for consumer in consumers:
            consumer.qos(prefetch_count=1)

    def send_task_to_cas(self,rds_conn,priority):
        try: 
            if not self.is_duplicate:
                message = get_task_info(self.huq_url_hot,self.digest)
                url_hot = get_url_hot(self.huq_url_hot,self.digest)
                rds_conn.set_hot(message,url_hot)
                '''
                message_log = ast.literal_eval(message)
                message_log['params']['hot'] = url_hot
                '''
                g_logger_info.info(trans2json("send to cas message %s" %str(message),"qb_priority_send_cas_"+priority))
            else:
                g_logger_info.info(trans2json("Task is duplicate, ignore it"))
        except Exception:
            g_logger.error(trans2json("send cas redis task errors happend %s" % str(traceback.format_exc())))
    
    def special_characters_filter(self,file_name):
        for char in gv.special_char:
            file_name = file_name.replace(char,'')
        return file_name

    def check_task_priority(self, data):
        file_name = data['params'].get('file_name','')
        file_name = self.special_characters_filter(file_name).decode('utf8').lower()
        file_ext = data['params'].get('file_ext', None)
        file_size = data['params'].get('file_size',0)
        is_keyword = False
        is_size = False
        is_ext = False

        is_black_keyword = self.check_keywords(file_name,gv.black_keyword_trie)
        if is_black_keyword:
            return self.RESULT_BLACK

        is_ext = file_ext in gv.file_ext_list

        file_size_mb = int(int(file_size) / 1048576)
        if int(gv.min_file_size) < file_size_mb < int(gv.max_file_size):
            is_size = True

        if is_ext and is_size:
            is_keyword = self.check_keywords(file_name,gv.keyword_trie)

        if is_keyword:
            data['params']['priority'] = self.RESULT_HIGH['priority']
            return self.RESULT_HIGH
        else:
            data['params']['priority'] = self.RESULT_LOW['priority']
            return self.RESULT_LOW

    def check_keywords(self, file_name,keyword_trie):
        for i in range(len(file_name)):
            if next(keyword_trie.iter_prefixes(file_name[i:]), False):
                return True
        return False

    def url_task_exists(self,rds_conn,digest):
        if not get_task_info(rds_conn,digest):
            return False
        return True

    def write_client_info(self,rds_conn,data):
        if not client_id_exists(rds_conn,self.digest,self.client_id):
            if write_client_id(rds_conn,self.digest,self.client_id,gv.ttl) == ADD_OK:
                if self.url_task_exists(rds_conn,self.digest):
                    self.update_url_task(rds_conn,self.digest)
                else:
                    self.write_url_task(rds_conn,data)
        else:
            self.is_duplicate = True

    def write_digest_updatetime(self,rds_conn,time,digest):
        update_time = time[0:8]
        set_digest_updatetime(rds_conn,update_time,digest)

    def update_url_task(self,rds_conn,digest):
        incr_url_hot(rds_conn,digest)
        current_time = datetime.now().strftime('%Y%m%d%H%M%S')
        self.write_digest_updatetime(rds_conn,current_time,digest)
        write_update_time(rds_conn,digest,current_time)
        
    def write_url_task(self,rds_conn,data):
        current_time = datetime.now().strftime('%Y%m%d%H%M%S')
        data['params']['createtime'] = current_time
        task = {} 
        task['hot'] = 1
        task['task_info'] = json.dumps(data)
        task['create_time'] = current_time
        task['update_time'] = current_time
        key = "hot#" + self.digest
        rds_conn.hmset(key,task)
        self.write_digest_updatetime(rds_conn,current_time,self.digest)
        
    def write_server_info(self,rds_conn,data):
        if self.url_task_exists(rds_conn,self.digest):
            self.update_url_task(rds_conn,self.digest)
        else:
            self.write_url_task(rds_conn,data)
        
    def record_url_hot(self,data):
        try:
            def url_hot_transaction_callable(pipe):
                if self.server_flag == CLIENT:
                    self.write_client_info(self.huq_url_hot,data)
                elif self.server_flag == SERVER:
                    self.write_server_info(self.huq_url_hot,data)
            result = self.huq_url_hot.transaction(url_hot_transaction_callable)
        except Exception:
            self.is_operredis_error = True
            g_logger.error(trans2json("operator redis errors happend %s" % str(traceback.format_exc())))

    def init_task_info(self,data):
        self.is_duplicate = False
        self.url_hot =  1
        self.client_id = data['params']['additional_info']['client_id']
        self.digest = data['params']['digest']
        self.server_flag = data['params'].get('server_flag', CLIENT)
        data['params']['downloader_time'] = 0
        data['params']['downloader_retry'] = 0
        
    def process_task(self, body, message):
        try:
            data = json.loads(body)
            message.ack()
            utils.digest = data['params']['digest']
            self.init_task_info(data)
            g_logger_info.info(trans2json("receive process task message %s" % (data),"qb_priority_receive_process"))
            gv.statsd_conn.incr("thunder.querybroker.qbpriority.receive_qb_push", 1)
            result = self.check_task_priority(data)
            self.record_url_hot(data)
            self.send_task_to_cas(result['conn'],result['priority'])
        except Exception:
            g_logger.error(trans2json("process_task errors happend %s" % str(traceback.format_exc())))
            
