from kombu.mixins import ConsumerMixin

import pull_global_vars as gv
import uuid
import time
import os
#from util import *
import json
import traceback
from pull_util import *
from kombu import Connection
from kombu.pools import producers
#from pull_util import trans2json, g_logger
from redis_oper import *
from kombu import Exchange, Queue

JSONRPC_ERROR = 122001
RESULTS_ERROR = 122009
COPYRIGHT = 0
UNCOPYRIGHT = 1
UNDETECT = 2
WORKING = 3
OVERALL_RESULTS = (COPYRIGHT, UNCOPYRIGHT, UNDETECT, WORKING)

class worker_result(ConsumerMixin):

    def __init__(self, connection, exchange, queue, routing_key):
        self.connection = connection
        self.exchange = exchange
        self.queue = queue
        self.routing_key = routing_key
        self.pushresult_connection = Connection(gv.pushresult_url)
        self.pushresult_exchange = Exchange(gv.pushresult_exchange)

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

    def check_input_params(self, data):
        result = [0, 0]
        if not data.has_key('jsonrpc'):
            result[0] = 122001
            result[1] = "There is no key named jsonrpc"
            g_logger.error(
                trans2json("input params check failed: %s" % result[1]))
        elif not data.has_key('results'):
            result[0] = 122009
            result[1] = "There is no key named result"
            g_logger.error(
                trans2json("input result check failed: %s" % result[1]))
        else:
            g_logger.info(trans2json("----Params check done.----"))
        return result

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

    def parse_data_pushresult(self, data, set_redis):
        for result in data['results']:
            message = {}
            message['params'] = {}
            message['jsonrpc'] = '2.0'
            message['id'] = 2

            message['params']['client_id'] = result['extra_info']['client_id']
            if result['extra_info'].has_key('url'):
                message['params']['url'] = result['extra_info']['url']
            if result['extra_info'].has_key('seed_file'):
                message['params']['seed_file'] = result[
                    'extra_info']['seed_file']
            message['params']['result'] = []
            if len(set_redis) > 0:
                for i in set_redis:
                    i = eval(i)
                    result_tmp = {}
                    for i in i.values():
                        if i in OVERALL_RESULTS:
                            result_tmp['status'] = i
                        else:
                            result_tmp['file_path'] = i
                    message['params']['result'].append(result_tmp)
            else:
                result_tmp = {}
                result_tmp['file_path'] = result['extra_info']['file_path']
                if len(result['matches']) > 0:
                    result_tmp['status'] = COPYRIGHT 
                else:
                    result_tmp['status'] = UNCOPYRIGHT 
                message['params']['result'].append(result_tmp)
            self.send_task_pushresult(message)

    def send_task_pushresult(self, data):
        message = json.dumps(data)
        g_logger_info.info(
            trans2json("send to push result message %s" % (data),"qb_pull_send_result"))
        with producers[self.pushresult_connection].acquire(block=True) as producer:
            producer.publish(message,
                             serializer='json',
                             compression='bzip2',
                             exchange=self.pushresult_exchange,
                             declare=[self.pushresult_exchange],
                             routing_key=gv.pushresult_routing_key)

    def process_task(self, body, message):
        try:
            #data = body
            g_logger_info.info(
                trans2json("receive vddb query result message %s" % (body),"qb_pull_receive_vddb"))
            data = json.loads(body)
            result = self.check_input_params(data)
            if result[0] != 0:
                error_message = self.trans_error_json(result, data)
                g_logger.error("response info %s" % error_message)
                message.ack()
            else:
                # check redis
                #ret_code, set_redis = checkDnaFromRedis(data)
                if ret_code == gv.RESULT_WAIT:
                    message.ack()
                    return
                # push to result
                self.parse_data_pushresult(data, set_redis)
                message.ack()
        except Exception:
            message.ack()
            g_logger.error(trans2json(
                "fetch_query_result_process errors happend %s" % str(traceback.format_exc())))
