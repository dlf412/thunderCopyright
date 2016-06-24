from kombu.mixins import ConsumerMixin
import result_global_vars as gv
import uuid
import time
import os
import json
from kombu import Connection
from kombu.pools import producers
from result_util import *
from kombu import Exchange, Queue
import base64
import traceback
from mediawise import http_request
import urllib


class Worker(ConsumerMixin):

    def __init__(self, connection, exchange, queue, routing_key):
        self.connection = connection
        self.exchange = exchange
        self.queue = queue
        self.routing_key = routing_key
        self.cas_connection = Connection(gv.pushresult_url)

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
            result[0] = 121201
            result[1] = "There is no key named jsonrpc"
            g_logger.error(
                trans2json("input params check failed: %s" % result[1]))
        elif not data.has_key('params'):
            result[0] = 121209
            result[1] = "There is no key named params"
            g_logger.error(
                trans2json("input params check failed: %s" % result[1]))
        else:
            g_logger.debug(trans2json("----Params check done.----"))
        return result

    def push_thunder(self, data):
        if data['params'].has_key('url'):
            url_temp = data['params']['url']
            url = urllib.unquote(url_temp)
        else:
            return
        client_id = data['params']['client_id']
        r = 0
        if data['params']['result'] != None and data['params']['result'] != 'None':
            for result in data['params']['result']:
                r = result['status']
                if r == 1:
                    break
        else:
            r = 3
        params = {
            'gcid': client_id,
            'url': url,
            'r': r
        }
        resp, logs = http_request(
            gv.thunder_server, params=params, timeout=5)
        if resp.text == "ok":
            g_logger_info.info(trans2json("%s" % params))
            g_logger.info(trans2json("push to thunder server successs"))
        else:
            g_logger_info.info(trans2json("%s" % params))
            g_logger.info(trans2json("push to thunder server error "))
            

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

    def process_task(self, body, message):
        try:
            data = json.loads(body)
            g_logger_info.info(trans2json("receive result message %s" % (data),"qb_resultpush_receive_result"))
            gv.statsd_conn.incr("thunder.querybroker.qbresultpush.receive_push_message", 1)
            result = self.check_input_params(data)
            if result[0] != 0:
                error_message = self.trans_error_json(result, data)
                g_logger.error(trans2json("response info %s" % error_message))
                message.ack()
                return
            else:
                # push to thunder
                if gv.is_push:
                    self.push_thunder(data)
                #g_logger.info(trans2json("push to thunder server"))
                message.ack()
                return
        except Exception:
            g_logger.error(
                trans2json("some errors happend %s" % str(traceback.format_exc())))
            message.ack()
