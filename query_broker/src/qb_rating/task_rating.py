# coding:utf-8
from kombu.mixins import ConsumerMixin

import rating_global_vars as gv
import uuid
import time
import os
import json
from kombu import Connection
from kombu.pools import producers
from rating_util import *
from kombu import Exchange, Queue
import traceback
import sys
from mysystem import http_request


class Worker(ConsumerMixin):

    def __init__(self, connection, exchange, queue, routing_key):
        self.connection = connection
        self.exchange = exchange
        self.queue = queue
        self.routing_key = routing_key
        self.cas_connection = Connection(gv.cas_url)
        self.pushresult_connection = Connection(gv.pushresult_url)
        self.pushresult_exchange = Exchange(gv.pushresult_exchange)
        

    def get_consumers(self, Consumer, channel):
        task_exchange = Exchange(self.exchange)
        task_queues = Queue(
            "task_rating_queue", task_exchange, routing_key="task_rating_queue")
        return [Consumer(queues=task_queues,
                         accept=['pickle', 'json'],
                         callbacks=[self.process_task])]

    def on_consume_ready(self, connection, channel, consumers):
        for consumer in consumers:
            consumer.qos(prefetch_count=1)

    def send_task_cas(self, data):
        data['params']['downloader_time'] = 0
        data['params']['downloader_retry'] = 0
        message = json.dumps(data)
        g_logger_info.info(trans2json("send to cas message %s" % (data),"qb_rating_send_cas"))
        gv.statsd_conn.incr("thunder.querybroker.qbpriority.send_to_cas", 1)
        task_exchange = Exchange(gv.cas_exchange)
        with producers[self.cas_connection].acquire(block=True) as producer:
            producer.publish(message,
                             serializer='json',
                             compression='bzip2',
                             exchange=task_exchange,
                             declare=[task_exchange],
                             routing_key=gv.cas_routing_key)

    def check_task_priority_rating(self,data):
        file_name = ''
        file_size = 0
        is_keyword = False
        is_size = False
        is_ext = False
        is_mintype = False
        file_name_extension = ''
        #reload(sys)
        #sys.setdefaultencoding('utf-8') 
        #todo video_rating
        if data['params']['file_name']!= None and data['params']['file_name'] != '':
            file_name = data['params']['file_name']
            message={}
            message['action'] = 'video_rating' 
            message['rating_longvideo_addscore'] = -1
            message['video_list']=[]
            video_list_dic={}
            video_list_dic['video_id'] = 1
            video_list_dic['title'] = file_name
            video_list_dic['poster_url'] = 'http://xx'
            video_list_dic['duration'] = 1000
            video_list_dic['finder'] = 'search_kw_in_ugc_searchpage'
            message['video_list'].append(video_list_dic)

            resp, logs = http_request(gv.video_rating_url, data=json.dumps(message), timeout=5)
            ret_data = resp.json()

            result = ret_data.get('result', [])
            g_logger.info(trans2json("rating result is %s"%result))
            if result:
                score = result[0]['score']
                if int(score) > int(gv.score):
                    is_keyword = True
        if data['params']['file_ext'] != '' and data['params']['file_ext']!= None:
            file_ext = data['params']['file_ext']
            if file_ext in gv.file_ext_list:
                is_ext = True
                
        if data['params']['file_size'] != '' and data['params']['file_size'] != None:
            file_size = data['params']['file_size']
            file_size_mb = int(int(file_size) / 1048576)
            if int(gv.min_file_size) < file_size_mb < int(gv.max_file_size):
                is_size = True

        g_logger.debug(trans2json("%d,%d,%d" % (is_keyword, is_ext, is_size)))
        if is_keyword and is_ext and is_size:
            data['params']['priority'] = 'high'
            gv.statsd_conn.incr("thunder.querybroker.qbrating.high_task", 1)
        else:
            gv.statsd_conn.incr("thunder.querybroker.qbrating.low_task", 1)

    def process_task(self, body, message):
        try:
            #data = body
            data = json.loads(body)
            g_logger_info.info(
                trans2json("receive process task message %s" % (data),"qb_rating_receive_process"))
            gv.statsd_conn.incr("thunder.querybroker.qbpriority.receive_qb_push", 1)
        
            self.check_task_priority_rating(data)
            self.send_task_cas(data)
            message.ack()
        except Exception:
            g_logger.error(
                trans2json("process_task errors happend %s" % str(traceback.format_exc())))
            message.ack()
