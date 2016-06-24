# coding:utf-8
from kombu.mixins import ConsumerMixin

import worker as wr
import os
import json
from kombu import Connection
from kombu.pools import producers
from kombu import Exchange, Queue
import traceback
import sys
import global_vars as gv
from high2low import *

class Worker(ConsumerMixin):

    def __init__(self, connection, exchange, queue, routing_key):
        self.connection = connection
        self.exchange = exchange
        self.queue = queue
        self.routing_key = routing_key
        self.high_connection = Connection(gv.high_url)
        self.low_connection = Connection(gv.low_url)

        self.high_exchange = Exchange(gv.high_exchange)
        self.low_exchange = Exchange(gv.low_exchange)

    def get_consumers(self, Consumer, channel):
        task_exchange = Exchange(self.exchange)
        task_queues = Queue(
           self.queue, task_exchange, routing_key=self.routing_key)
        return [Consumer(queues=task_queues,
                         accept=['pickle', 'json'],
                         callbacks=[self.process_task])]

    def on_consume_ready(self, connection, channel, consumers):
        for consumer in consumers:
            consumer.qos(prefetch_count=1)

    def send_task_down_high(self, data):
        message = json.dumps(data)
        gv.g_logger.info("send to download high %s" % (data))
        gv.statsd_conn.incr("thunder.ops_tools.white_list.send_download_high", 1)
        with producers[self.high_connection].acquire(block=True) as producer:
            producer.publish(message,
                             serializer='json',
                             compression='bzip2',
                             exchange=self.high_exchange,
                             declare=[self.high_exchange],
                             routing_key=gv.high_routingkey)

    def send_task_down_low(self, data):
        message = json.dumps(data)
        gv.g_logger.info("send to task download low %s" % (data))
        gv.statsd_conn.incr("thunder.ops_tools.white_list.send_download_low", 1)
        with producers[self.low_connection].acquire(block=True) as producer:
            producer.publish(message,
                             serializer='json',
                             compression='bzip2',
                             exchange=self.low_exchange,
                             declare=[self.low_exchange],
                             routing_key=gv.low_routingkey)

    def check_task_blacklist(self, data):
        file_name = ''
        is_keyword = False
        file_name_extension = ''
        reload(sys)
        sys.setdefaultencoding('utf-8')
        if data['params']['file_name']!= '' and data['params']['file_name'] != None:
            file_name = data['params']['file_name'].decode('utf8').lower()
            is_keyword = self.check_keywords(file_name)
        if is_keyword:
            gv.g_logger.info("white word match %s"%(file_name))
            gv.redisoper.trans_high2low(data)
            self.send_task_down_low(data)
        else:
            self.send_task_down_high(data)

    def check_keywords(self, file_name):
        for i in range(len(file_name)):
            if next(gv.keyword_trie.iter_prefixes(file_name[i:]), False):
                return True
        return False

    def process_task(self, body, message):
        try:
            data = json.loads(body)
            message.ack()
            gv.g_logger.info("get download_high_tmp message %s"%(data))
            gv.statsd_conn.incr("thunder.ops_tools.white_list.get_download_high_tmp", 1)
            self.check_task_blacklist(data)
  
        except Exception:
            gv.g_logger.error("process_task errors happend %s" % str(traceback.format_exc()))
            message.ack()
