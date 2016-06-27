from kombu.mixins import ConsumerMixin

from mysystem import *
import push_global_vars as gv
import uuid
import time
import os
import json
from kombu import Connection
from kombu.pools import producers
from push_query import query_hash
from push_util import *
from kombu import Exchange, Queue
import base64
import traceback
from utils import trans2json
import utils


class Worker(ConsumerMixin):

    def __init__(self, connection, exchange, queue, routing_key):
        self.connection = connection
        self.exchange = exchange
        self.queue = queue
        self.routing_key = routing_key
        self.cas_connection = Connection(gv.cas_url)
        self.pushresult_connection = Connection(gv.pushresult_url)
        self.pushresult_exchange = Exchange(
            gv.pushresult_exchange)

        self.taskpriority_connection = Connection(gv.taskpriorit_url)
        self.taskpriority_exchange = Exchange(gv.taskpriorit_exchange)
    

    def get_consumers(self, Consumer, channel):
        task_exchange = Exchange(self.exchange, type='fanout')
        task_queues = Queue(
            self.queue, task_exchange, routing_key=self.routing_key)
        return [Consumer(queues=task_queues,
                         accept=['pickle', 'json'],
                         callbacks=[self.process_task])]

    def on_consume_ready(self, connection, channel, consumers):
        for consumer in consumers:
            consumer.qos(prefetch_count=1)

    def trans_error_json(self, result, data):
        res = {}
        res['jsonrpc'] = "2.0"
        if data.has_key('id'):
            res['id'] = data['id']
        res['error'] = {}
        res['error']['code'] = result[0]
        res['error']['message'] = result[1]
        error_message = json.dumps(res)
        return error_message

    def check_input_params(self, data):
        method = "submit_task"
        result = [0, 0]
        if not data.has_key('jsonrpc'):
            result[0] = 121201
            result[1] = "There is no key named jsonrpc"
            g_logger.error(
                trans2json("input params check failed: %s" % result[1]))
        elif not data.has_key('method') or data['method'] != method:
            result[0] = 121202
            result[
                1] = "There is no key named method or method is not " + method
            g_logger.error(
                trans2json("input params check failed: %s" % result[1]))
        elif not data.has_key('params'):
            result[0] = 121203
            result[1] = "There is no key named params"
            g_logger.error(
                trans2json("input params check failed: %s" % result[1]))
        elif not data['params'].has_key('additional_info'):
            result[0] = 121204
            result[
                1] = "There is no key named client_id in params or client_id is null "
            g_logger.error(
                trans2json("input params check failed: %s" % result[1]))
        elif not data['params'].has_key('external_id') or data['params']['external_id'] == '':
            result[0] = 121210
            result[1] = "There is no key named external_id or external_id is null"
            g_logger.error(
                trans2json("input params check failed: %s" % result[1]))
        elif not data['params']['thunder_hash']:
            if data['params'].has_key('url'):
                if not data['params']['url']['hash']:
                    if data['params'].has_key('seed_file'):
                        if not data['params']['seed_file']['hash']:
                            result[0] = 121211
                            result[1] = "There is no hash in params"
                            g_logger.error(trans2json("input params check failed: %s" % result[1]))
        else:
            g_logger.debug(trans2json("----Params check done.----"))
        return result


    def send_task_pushresult(self, data):
        message = json.dumps(data)
        g_logger_info.info(trans2json("send to push result message %s" % (data),"qb_push_push_result"))
        gv.statsd_conn.incr("thunder.querybroker.qbpush.send_qbresultpush", 1)
        with producers[self.pushresult_connection].acquire(block=True) as producer:
            producer.publish(message,
                             serializer='json',
                             compression='bzip2',
                             exchange=self.pushresult_exchange,
                             declare=[self.pushresult_exchange],
                             routing_key=gv.pushresult_routing_key)

    def send_task_priority_escalator(self, data):
        data['params']['downloader_time'] = 0
        data['params']['downloader_retry'] = 0
        message = json.dumps(data)
        g_logger_info.info(trans2json("send to send task priority escalator message %s" % (data),"qb_push_send_priority"))
        gv.statsd_conn.incr("thunder.querybroker.qbpush.send_qbpriority", 1)
        with producers[self.taskpriority_connection].acquire(block=True) as producer:
            producer.publish(message,
                             serializer='json',
                             compression='bzip2',
                             exchange=self.taskpriority_exchange,
                             declare=[self.taskpriority_exchange],
                             routing_key=gv.taskpriorit_routing_key)

    def process_task(self, body, message):
        try:
            data = body
            #data = json.loads(body)
            utils.digest = data['params']['digest']
            g_logger_info.info(trans2json("receive gateway task message %s" % (body),'qb_push_receive_gateway'))
            #g_logger_info.info(trans2json("task_uuid:%s"%data['params']['external_id']))
            gv.statsd_conn.incr("thunder.querybroker.qbpush.receive_gateway_message", 1)
            result = self.check_input_params(data)
            if result[0] != 0:
                error_message = self.trans_error_json(result, data)
                g_logger.error(trans2json("response info %s" % error_message))
            else:
                ret_code, result = query_hash(data)
                if ret_code is None:
                    self.send_task_priority_escalator(data)
            message.ack()
            return
        except Exception:
            g_logger.error(
                trans2json("process_task errors happend %s" % str(traceback.format_exc())))
            message.ack()
