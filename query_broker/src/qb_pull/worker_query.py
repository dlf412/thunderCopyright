from kombu.mixins import ConsumerMixin

import pull_global_vars as gv
import uuid
import utils
from utils import trans2json
import time
import os
import json
from kombu import Connection
from kombu.pools import producers
from pull_query import *
from pull_util import *
import traceback
from kombu import Exchange, Queue
#from mediawise import submittask
import httplib
import urllib
from redis_oper import *
from hot_url_queue import HotUrlQueue

JSONRPC_ERROR = 122001
METHOD_ERROR = 122002
PARAMS_ERROR = 122003
CLIENT_ID_ERROR = 122004
ERROR_CODE_ERROR = 122008




HIGH_QUEUE = 'high'
BLACK_QUEUE = 'black'
LOW_QUEUE = 'low'

class Worker_query(ConsumerMixin):

    def __init__(self, connection):
        self.connection = connection
        self.vddb_connection = Connection(gv.vddb_queryurl)
        self.vddb_exchange = Exchange(gv.vddb_queryexchange)
        self.pushresult_connection = Connection(gv.pushresult_url)
        self.pushresult_exchange = Exchange(gv.pushresult_exchange)
        self.huq_black = HotUrlQueue(url = gv.rds_cas_black)
        self.huq_low = HotUrlQueue(url = gv.rds_cas_low)
        self.huq_high = HotUrlQueue(url = gv.rds_cas_high)

    def get_consumers(self, Consumer, channel):
        task_exchange = Exchange(gv.finsh_exchange)
        task_queues = Queue(
            gv.finsh_queue, task_exchange, routing_key=gv.finsh_routing_key)
        return [Consumer(queues=task_queues,
                         accept=['pickle', 'json'],
                         callbacks=[self.process_task])]


    def on_consume_ready(self, connection, channel, consumers):
        for consumer in consumers:
            consumer.qos(prefetch_count=1)

    def check_input_params(self, data):
        method = "finish_task"
        result = [0, 0]
        if not data.has_key('jsonrpc'):
            result[0] = JSONRPC_ERROR
            result[1] = "There is no key named jsonrpc"
            g_logger.error(
                trans2json("input params check failed: %s" % result[1]))
        elif not data.has_key('method') or data['method'] != method:
            result[0] = METHOD_ERROR
            result[1] = "There is no key named method or method is not " + method
            g_logger.error(
                trans2json("input params check failed: %s" % result[1]))
        elif not data.has_key('params'):
            result[0] = PARAMS_ERROR
            result[1] = "There is no key named params"
            g_logger.error(
                trans2json("input params check failed: %s" % result[1]))
        elif not data['params']['additional_info'].has_key('client_id') or data['params']['additional_info']['client_id'] == '':
            result[0] = CLIENT_ID_ERROR
            result[1] = "There is no key named client_id in params or client_id is null "
            g_logger.error(
                trans2json("input params check failed: %s" % result[1]))
        elif not data['params'].has_key('error_code'):
            result[0] = ERROR_CODE_ERROR
            result[1] = "There is no key named error_code"
            g_logger.error(
                trans2json("input params check failed: %s" % result[1]))
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

    def parse_and_send_casmessage(self, data):
        message = {}
        message['jsonrpc'] = '2.0'
        message['method'] = 'submit'
        message['id'] = data['id']

        message['params'] = {}
        message['params']['additional_info'] = data['params']['additional_info'].copy()
        message['params']['thunder_hash'] = data['params']['thunder_hash']
        message['params']['downloader_time'] = 0
        message['params']['downloader_retry'] = 0
        message['params']['refer'] = data['params']['refer']
        message['params']['digest'] = data['params']['digest']
        message['params']['digest_algorithm'] = data['params']['digest_algorithm']
        message['params']['protocol'] = data['params']['protocol']
        message['params']['mime_type'] = data['params']['mime_type']
        message['params']['priority'] = data['params']['priority']
        message['params']['is_duplicated'] = 0
        message['params']['external_id'] = data['params']['external_id']
        message['params']['file_name'] = data['params']['file_name']
        if data['params'].has_key('url'):
            message['params']['url'] = {}
            message['params']['url'] = data['params']['url'].copy()
        if data['params'].has_key('seed_file'):
            message['params']['seed_file'] = {}
            message['params']['seed_file']['path'] = data['params']['seed_file']['path']
            message['params']['seed_file']['hash'] = data['params']['seed_file']['hash']
        priority = data['params']['priority']
        digest = data['params']['digest']
        url_hot = int(data['params'].get('hot', 1))
        if priority == HIGH_QUEUE:
            self.send_bttask_to_cas(self.huq_high,message,url_hot)
        elif priority == BLACK_QUEUE:
            self.send_bttask_to_cas(self.huq_black,message,url_hot)
        elif priority == LOW_QUEUE:
            self.send_bttask_to_cas(self.huq_low,message,url_hot)

    def set_parent_info(self,data,message):
        message['params']['parent_info'] = []
        is_file_num = False
        files_size_len = len(data['params']['files'])
        if data['params'].has_key('seed_file'):
            if data['params']['seed_file']['hash'] != None and data['params']['seed_file']['hash'] != '':
                seed_hash_dic = {}
                seed_hash = data['params']['seed_file']['hash']
                seed_hash_dic[seed_hash] = files_size_len 
                message['params']['parent_info'].append(seed_hash_dic)
        if data['params'].has_key('url') and files_size_len > 1:
              if data['params']['url']['hash'] != None and data['params']['url']['hash'] != '':
                url_hash_dic = {}
                url_hash = data['params']['url']['hash']
                url_hash_dic[url_hash] = files_size_len
                message['params']['parent_info'].append(url_hash_dic)
        if data['params']['thunder_hash'] != None and data['params']['thunder_hash'] != '' and files_size_len > 1:
            thunder_hash_dic = {}
            thunder_hash = data['params']['thunder_hash']
            thunder_hash_dic[thunder_hash] = files_size_len
            message['params']['parent_info'].append(thunder_hash_dic)
            
    def parse_and_send_vddbmessage(self, data):
        files_size_len = len(data['params']['files'])
        for dna in data['params']['files']:
            if dna['code'] == 0:
                message = {}
                message['jsonrpc'] = '2.0'
                message['method'] = 'query'
                message['id'] = data['id']

                message['params'] = {}
                message['params']['external_id'] = data[
                    'params']['external_id']
                message['params']['site_asset_id'] = []
       
                self.set_parent_info(data,message)
                message['params']['extra_info'] = {}
                message['params']['extra_info']['url_hash']=''
                message['params']['extra_info']['thunder_hash'] = ''
                message['params']['extra_info']['seed_hash'] = ''
                message['params']['extra_info']['digest'] = data['params']['digest']
                #message['params']['extra_info']['file_num'] = files_size_len
                message['params']['extra_info_url'] = ''
                message['params']['extra_info']['client_id'] = data[
                    'params']['additional_info']['client_id']
                if (data['params'].has_key('seed_file')  and files_size_len >1) or files_size_len > 1:
                    if data['params'].has_key('seed_file'):
                        if data['params']['seed_file']['hash'] != None and data['params']['seed_file']['hash'] != '':
                            message['params']['site_asset_id'].append(
                                data['params']['seed_file']['hash'] + '-' + dna['hash'])
                            message['params']['extra_info']['seed_file'] = data[
                                'params']['seed_file']['path']
                            message['params']['extra_info']['seed_hash'] = data['params']['seed_file']['hash']
                            message['params']['extra_info_url'] = data[
                                'params']['seed_file']['path']  
                    if data['params'].has_key('url'):
                        if data['params']['url']['hash'] != None and data['params']['url']['hash'] != '':
                            message['params']['site_asset_id'].append(
                                data['params']['url']['hash'] + '-' + dna['hash'])
                            message['params']['extra_info'][
                                'url'] = data['params']['url']['location']
                            message['params']['extra_info']['url_hash'] = data['params']['url']['hash']
                    if data['params']['thunder_hash'] != None and data['params']['thunder_hash'] != '':
                        message['params']['site_asset_id'].append(data['params']['thunder_hash']+'-'+dna['hash'])
                        message['params']['extra_info']['thunder_hash'] = data['params']['thunder_hash']
            
                else:
                    if data['params'].has_key('seed_file'):
                        if data['params']['seed_file']['hash'] != None and data['params']['seed_file']['hash'] != '':
                            message['params']['site_asset_id'].append(data['params']['seed_file']['hash'])
                            message['params']['extra_info']['seed_file'] = data['params']['seed_file']['path']
                            message['params']['extra_info']['seed_hash'] = data['params']['seed_file']['hash']
                            message['params']['extra_info_url'] = data['params']['seed_file']['path']   
                    if data['params'].has_key('url'):
                        if data['params']['url']['hash'] != None and data['params']['url']['hash'] != '':
                            message['params']['site_asset_id'].append(
                                data['params']['url']['hash'])
                            message['params']['extra_info'][
                                'url'] = data['params']['url']['location']
                            message['params']['extra_info']['url_hash'] = data['params']['url']['hash']
                    if data['params']['thunder_hash'] != None and data['params']['thunder_hash'] != '':
                        message['params']['site_asset_id'].append(data['params']['thunder_hash'])
                        message['params']['extra_info']['thunder_hash'] = data['params']['thunder_hash']

                message['params']['files'] = dna['path']

                message['params']['site_asset_id'].append(dna['hash'])

                message['params']['extra_info']['file_path'] = dna['file_path']
                message['params']['priority'] = 0
                message['params']['company'] = gv.company
                message['params']['profile'] = 'default'
                message['params']['query_scope'] = []

                self.send_task_to_vddb(message)
            else:
                post_to_vddbdnaerror(data, dna['code'], dna['hash'])


    def send_bttask_to_cas(self,rds_conn,data,url_hot):
        try:
            message = json.dumps(data)
            rds_conn.set_hot(message,url_hot)
            g_logger_info.info(trans2json("send to cas bt download task %s" % (data),"qb_pull_send_cas"))
            gv.statsd_conn.incr("thunder.querybroker.qbpull.send_to_cas_download", 1)
        except Exception:
            g_logger.error(trans2json("send cas redis bt task errors happend %s" % str(traceback.format_exc())))
           
    def send_task_to_vddb(self, data):
        message = json.dumps(data)
        #message = data
        g_logger_info.info(trans2json("send to vddb async query %s" % (data),"qb_pull_send_vddb"))
        gv.statsd_conn.incr("thunder.querybroker.qbpull.send_to_vddb_query", 1)
        with producers[self.vddb_connection].acquire(block=True) as producer:
            producer.publish(message,
                             serializer='json',
                             compression='bzip2',
                             exchange=self.vddb_exchange,
                             declare=[self.vddb_exchange],
                             routing_key=gv.vddb_queryrouting_key)

    def process_task(self, body, message):
        try:
            data = json.loads(body)
            utils.digest = data['params']['digest']
            g_logger_info.info(trans2json("receive CAS finsh  message %s" % (data),"qb_pull_receive_cas"))
            gv.statsd_conn.incr("thunder.querybroker.qbpull.receive_cas_finish_message", 1)
            result = self.check_input_params(data)
            if result[0] != 0:
                error_message = self.trans_error_json(result, data)
                message.ack()
                g_logger.error(trans2json("response info %s" % error_message))
                return
            else:
                # check error code
                error_code = int(data['params']['error_code'])
                # download correct
                if error_code == gv.DOWNLOAD_SUCCESS:
                    # write to redis url/bt hash and dna  hash
                    #writeHashToRedis(data)
                    # get query hash result
                    if data['params'].has_key('files'):
                        self.parse_and_send_vddbmessage(data)
                        message.ack()
                        return
                    else:
                        self.parse_and_send_casmessage(data)
                        message.ack()
                        return
                else:
                    # download error
                    if error_code in gv.UNRECOGNIZED_ERROR_LIST:
                        post_to_vddbdnaerror(data,error_code,'')
                    message.ack()
                    return
        except Exception:
            message.ack()
            g_logger.error(
                trans2json("worker_query errors happend %s" % str(traceback.format_exc())))
