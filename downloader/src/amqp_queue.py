#!/usr/bin/python
# coding=utf-8

import json
import time
import traceback
import redis
import statsd
import time
import socket

from logging.handlers import SysLogHandler
from kombu import Connection, Exchange, Queue, Consumer, eventloop, Producer

from kombu.transport.librabbitmq import ConnectionError
from kombu.pools import producers

from common.mylogger import *
from downloader_util import *

from common.task_container import TaskContainer, TaskContainerError

SPLIT_FAR_FAILED = 121502
SWIFT_OPER_FAILED = 121503
DOWNLOAD_FAILED = 121509
UNKNOWN_ERROR = 121510
INVALID_TORRENT = 121512

UN_DETECTED = 2

class Amqp():
    def __init__(self, logger_name, log_path, config 
            , config_name, Send_Q=None, Ack_Q=None, Task_Done_Q=None):

        self.send_q         = Send_Q
        self.ack_q          = Ack_Q
        self.task_done_q    = Task_Done_Q

        config              = json.loads(config)

        self.config = config

        mq_config           = config.get(config_name)
        log_config          = config.get('log')

        self.r_key          = mq_config.get("routing_key")
        self.queue_name     = mq_config.get("queue")
        self.exch_name      = mq_config.get("exchange")
        self.addr           = mq_config.get("url")

        self.exch           = Exchange(self.exch_name)
        self.queue          = Queue(self.queue_name, self.exch, self.r_key)
        self.conn           = Connection(self.addr)
        
        self.tc             = TaskContainer(config.get('redis_url'), 
                    finish_expire=config.get('finish_task_expire', 3600))

        self.statsd_host    = config.get('statsd').get('host')
        self.statsd_port    = config.get('statsd').get('port')
        self.statsd_con     = statsd.client.StatsClient(self.statsd_host, self.statsd_port)

        self.hash_data      = None
        self.logger         = mylogger()
        self.info_logger    = mylogger()
        self.host_name      = socket.gethostname()

        self.d_time         = config.get("download_task_timeout", 10800)
        self.d_retry        = config.get("download_retry_times", 100)

        self.logger.init_logger(logger_name
                , log_config.get('log_level')
                , log_path
                , SysLogHandler.LOG_LOCAL2)

        self.info_logger.init_logger(logger_name
                , log_config.get('log_level')
                , log_path
                , SysLogHandler.LOG_LOCAL1)

    def set_consumer(self):
        self.consumer = self.conn.Consumer(self.queue
                , callbacks=[self.process_task])
        self.consumer.qos(prefetch_count=1)
        self.consumer.consume()

    def get_queue(self):
        self.logger.debug('queue name is: [%s], init success' % self.queue_name)
        while True:
            try:
                self.conn.drain_events(timeout=1)
            except socket.timeout, e:
                #this case means self.conn timeout
                pass
            except ConnectionError,e:
                self.logger.error('some error happens: [%s]' % e)
                time.sleep(10)
                self.conn.release()
                self.conn = Connection(self.addr)
                try:
                    self.consumer = self.conn.Consumer(self.queue
                            , callbacks=[self.process_task])
                    self.consumer.qos(prefetch_count=1)
                    self.consumer.consume()
                except Exception, reason:
                    #this case means there is net interupt
                    self.logger.error('re connectting to rabbitmq, error: [%s]' % reason)
            except Exception, e:
                self.logger.error('unkown error happens: [%s]' % e)
            finally:
                time.sleep(0.1)

    def record_statsd(self, msg):
        try:
            self.statsd_con.incr(msg, 1)
        except Exception:
            pass

    def process_task(self, body, message):
        try:
            self.logger.info('get new task is: [%s]' % body)
            if not body:
                self.logger.error('receive message body is none, ignored, directly send ack')
                message.ack()
                return
            task_info = body

            if isinstance(body, dict):
                self.logger.debug("body is dict type, change its to json")
                task_info = json.dumps(task_info)

            task = json.loads(task_info) 
            if 'params' not in task:
                self.logger.error('params not in receive message body, ignored, directly send ack')
                message.ack()
                return

            if 'digest' not in task['params']:
                self.logger.error('digest not in params, ignored, directly send ack')
                message.ack()
                return
            
            digest = task['params']['digest']
            if self.tc.set_task_status(digest, 'processing') is None:
                self.logger.error('digest not in task_container, ignored, directly send ack')
                message.ack()
                return
            
            # incr task tries here for starting
            self.tc.incr_task_tries(digest)
            
            ex_id, hash_data, task_type, task_priority = get_hash_type(task_info)
            self.info_logger.info(trans2json(
                ex_id, 
                'task_input', 
                "task_info", 
                task))

            '''
            if hash_data is None:
                self.logger.error('some importannt error happens, url hash data is none')
                message.ack()
                return
            '''
            self.send_q.put(task_info)
            task_info_ack = self.ack_q.get(block=True)
            self.logger.info('get ack info, send message ack to rabbitmq')
            message.ack()
            self.record_statsd("thunder.downloader." + self.queue_name + ".all")
            self.record_statsd("thunder.downloader." + self.queue_name + "." + self.host_name)
            self.logger.debug('send ack to message')
        except Exception, reason:
            self.logger.error("some error happens: [%s]" % str(reason))

    def update_retry_download(self, task_info):
        pass

    def get_producer(self):
        self.producer =  producers[self.conn].acquire(block=True)

    def put_fin_task(self, Fin_Q): 
        self.logger.debug('queue name is: [%s], init success' % self.queue_name)
        # 121521 is offline download polling timeout
        downloader_failed = {
                121509:'download_failed', 
                121508:'unsupported_download',
                121502:'split_far_failed',
                121503:'swift_opration_faild',
                121510:'unknow_error',
                121512:'invalid_torrent'
                }
        downloader_failed = [SPLIT_FAR_FAILED, SWIFT_OPER_FAILED, DOWNLOAD_FAILED, UNKNOWN_ERROR, INVALID_TORRENT]
        while True:
            try:
                fin_info = Fin_Q.get(block=True)
                self.logger.info(
                        'new fin task generate: [%s] ' 
                        % (fin_info))
                ex_id, hash_data, task_type, priority = get_hash_type(fin_info)
                fin_task     = json.loads(fin_info)
                error_code   = fin_task.get('params').get('error_code')

                digest = fin_task['params']['digest']

                d_time = self.tc.get_task_execute_time(digest)
                d_retry = self.tc.get_task_tries(digest)

                fin_task['params']['downloader_retries'] = d_retry
                fin_task['params']['downloader_time'] = d_time

                #this happend when download failed
                if error_code in downloader_failed:
                    if d_time < self.d_time and d_retry < self.d_retry:
                        r_mess = "error"
                        self.logger.info('download failed, cas will restart later, digest:%s, cost_time:%d, tries:%d' %(digest, d_time, d_retry))
                        self.tc.set_task_status(digest, r_mess)
                        continue

                self.record_statsd("thunder.downloader.finish_all.all")
                record_info = 'thunder.downloader.finish_all.' + self.host_name
                self.record_statsd(record_info)
                self.record_task_info(fin_task)

                for i in range(5):
                    try:
                        self.producer.publish(
                                json.dumps(fin_task),
                                serializer='json', 
                                declare=[self.queue], 
                                exchange=self.exch, 
                                routing_key=self.r_key, 
                                compression='zlib'
                                )
                        break
                    except Exception, reason:
                        time.sleep(20)
                        self.logger.error('some error happens when record finish message: [%s]' 
                                % reason)
                        self.conn.release()
                        self.conn = Connection(self.addr)
                        self.producer =  producers[self.conn].acquire(block=True)
                        if UN_DETECTED == i:
                            self.logger.error(
                                    'important errors happen, this message not record to rmqp, discard: [%s]'
                                    % json.dumps(fin_task))
                            continue

                self.info_logger.info(trans2json(
                    ex_id, 
                    'task_output', 
                    "task_info", 
                    json.loads(fin_info)
                    ))
                self.tc.set_task_info(digest, json.dumps(fin_task))
                self.tc.set_task_status(digest, 'finish')
            except TaskContainerError, reason:
                traceback.print_exc()
                self.logger.error("task container connection maybe lost: [%s], I will reconnect" % str(reason))
                self.tc = TaskContainer(self.config.get('redis_url'), 
                        finish_expire=self.config.get('finish_task_expire', 3600))

            except Exception, reason:
                traceback.print_exc()
                self.logger.error("error happens: [%s]" % str(reason))

    def record_task_info(self, task_info):

        # add for offline download
        '''        OFFLINE_SUCCESS = 0
                OFFLINE_TIMEOUT = -1
                OFFLINE_HTTP_ERROR = -2
                OFFLINE_STATUS_ERROR = -3
                OFFLINE_DOWNLOAD_ERROR = -4 # 下载文件出错
                OFFLINE_GENURL_ERROR = -5 # 生成url失败
                OFFLINE_UNKNOWN_ERROR = -6 # 其它未知错误
        '''
        offline_download_errcode = {
                0: 'success',
                -1: 'offline_timeout',
                -2: 'offline_http_error',
                -3: 'offline_status_error',
                -4: 'offline_download_error',
                -5: 'offline_genurl_error',
                -6: 'offline_unknown_error'
                }

        partial_download_errcode = {
                0: 'success',
                1: 'partial_disable_ignore',
                2: 'url_type_unsupport_ignore',
                3: 'bt_unsupport_ignore',
                4: 'ext_unsupport_ignore',
                5: 'multi_file_unsupport_ignore',
                6: 'file_size_small_ignore',
                -1: 'partial_down_error',
                -2: 'gen_dna_far_error',
                -3: 'get_dna_stat_error',
                -4: 'get_dna_len_error',
                -5: 'calc_dl_size_error',
                -6: 'exception_error',
                -7: 'partial_download_timeout'
                }

        downloader_failed = {
                121509:'download_failed', 
                121508:'unsupported_download',
                121502:'split_far_failed',
                121503:'swift_opration_faild',
                121510:'unknow_error',
                121512:'invalid_torrent'
                }
        un_detect = {
                121500:'parse_input_failed'
                }
        success           = {
                121511:"filter_torrent"
                }
        partial_code = task_info['params'].get('partial_errcode', None)
        code      = task_info['params']['error_code']
        
        offline_code = task_info['params'].get('offline_errcode', None)
        '''
        timer process, need record the downloadertime  
        '''
        if partial_code is not None:
            self.record_statsd('thunder.downloader.partial_download.all.%s' % partial_download_errcode[partial_code])
            self.record_statsd('thunder.downloader.partial_download.%s.%s' % (self.host_name, partial_download_errcode[partial_code]))

        if offline_code is not None:
            self.record_statsd('thunder.downloader.offline_download.all.%s' % offline_download_errcode[offline_code])
            self.record_statsd('thunder.downloader.offline_download.%s.%s' % (self.host_name, offline_download_errcode[offline_code]))

        if code in downloader_failed:
            self.record_statsd('thunder.downloader.download_failed.all')
            self.record_statsd('thunder.downloader.download_failed.' + downloader_failed[code])
            #record_info = 'thunder.download.download_failed.' + self.host_name + '.' + downloader_failed[code]
            #self.record_statsd(record_info)
        elif code in success:
            self.record_statsd('thunder.downloader.download_success.all')
            record_info = 'thunder.downloader.download_success.' + self.host_name
            self.record_statsd(record_info)
        elif code in un_detect:
            self.record_statsd('thunder.downloader.download_undetect.all')
            self.record_statsd('thunder.downloader.download_undetect.' + self.host_name)
        else:
            files   = task_info['params'].get('files', None)
            if not files:
                self.record_statsd('thunder.downloader.download_success.all')
                record_info = 'thunder.downloader.download_success.' + self.host_name
                self.record_statsd(record_info)
                return
            for f in files:
                if 2 != f.get('code'):
                    self.record_statsd('thunder.downloader.download_success.all')
                    record_info = 'thunder.downloader.download_success.' + self.host_name
                    self.record_statsd(record_info)
                    return
            self.record_statsd('thunder.downloader.download_undetect.all')
            self.record_statsd('thunder.downloader.download_undetect.' + self.host_name)

    def get_task_type(self, task_type):
        if task_type is OUTPUT_URL_SEED:
            return "url", "url_seed_finish"
        elif task_type is URL_SEED\
                or task_type is SEED_FILE:
            return "seed_file", "finish"
        else:
            return "url", "finish"


    def parse_hash_priority(self, task_info, fin_task):
        try:
            json_data = json.loads(task_info)
            #this case means if seed_file hash is not exist, need check url hash
            if fin_task:
                if keys_value(json_data, "params", "url") is not None:
                    hash_data = json_data['params']['url']['hash']
                    task_type = URL_FILE
                elif keys_value(json_data, "params", "seed_file") is not None:
                    hash_data = json_data['params']['seed_file']['hash']
                    task_type = SEED_FILE
                else:
                    self.logger.error("some important errors happen, no url or seed file find need check")
                    raise Exception("no url or seed_file find")
            else:
                if keys_value(json_data, "params", "seed_file") is not None:
                    hash_data = json_data['params']['seed_file']['hash']
                    task_type = SEED_FILE
                elif keys_value(json_data, "params", "url") is not None:
                    hash_data = json_data['params']['url']['hash']
                    task_type = URL_FILE
                else:
                    self.logger.error("some important errors happen, no url or seed file find need check")
                    raise Exception("no url or seed_file find")
            if keys_value(json_data, "params", "priority") is None:
                task_priority = "low"
            else:
                task_priority = json_data['params']['priority']
            self.logger.debug("hash_data is: [%s], task_priority is : [%s]" % (hash_data, task_priority))
            return task_type, hash_data, task_priority
        except Exception, reason:
            self.logger.error('error happens parse hash priority: [%s]' % str(reason))
            return None, None, None

    def __del__(self):
        self.conn.release()

def get_download_task(Send_Q, Ack_Q, Task_Done_Q, etc_data, log_path):
    try:
        mq_data = json.loads(etc_data)
        queue_name = "highdownloadmq"\
                if mq_data.get('is_high_queue', 0)\
                else "downloadmq"
        amqp = Amqp("downloader"
                , log_path
                , etc_data
                , queue_name
                , Send_Q
                , Ack_Q
                , Task_Done_Q)
        amqp.set_consumer()
        amqp.get_queue()
    except Exception, reason:
        traceback.print_exc()
        sys.stderr.write("#downloader# block error: init get_download_task failed, some configure error\n")
        sys.exit(1)


def record_fin_task(Fin_Q, etc_data, log_path):
    try:
        queue_name = "finishmq"
        fin_queue = Amqp("downloader"
                , log_path
                , etc_data
                , "finishmq")
        fin_queue.get_producer()
        fin_queue.put_fin_task(Fin_Q)
    except Exception, reason:
        traceback.print_exc()
        sys.stderr.write("#downloader# block error: record_fin_task failed, some configure error\n")
        sys.exit(1)

'''
    def tran_log(self, message):
        return self.hash_data + "#" + message
'''

