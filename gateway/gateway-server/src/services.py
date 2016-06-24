#coding: utf-8

import gevent
from kombu import Exchange, Connection
from kombu.pools import producers

from utils import (log_normal, log_bill, log_info,
                   LOG_DEBUG, LOG_INFO, LOG_WARN, LOG_WARNING, LOG_ERROR, LOG_CRITICAL)


# ==============================================================================
#  Exceptions
# ==============================================================================
class QueryBrokerError(Exception): pass


# ==============================================================================
#  Services
# ==============================================================================
class QueryBroker(object):
    """
    ::Reference: http://seals.vobile.cn/trac/vdna/wiki/thunder_querybroker
    """

    def __init__(self, logger, routing_key, exchange_name, publish_timeout, mq_url):
        log_normal(logger, {
            'action': 'config-querybroker',
            'info': {
                'routing_key': routing_key,
                'exchange_name': exchange_name,
                'mq_url': mq_url
            }
        }, LOG_INFO)
        self.logger = logger
        self.ROUTING_KEY = routing_key
        self.exchange = Exchange(exchange_name, type='fanout')
        self.publish_timeout = publish_timeout
        self.connection =  Connection(mq_url)


    def push(self,
             progress,
             client_id,
             client_address,
             digest,
             digest_algorithm,
             file_name,
             file_size,
             host_name,
             referer,
             thunder_hash,
             mime_type,
             protocol,
             task_uuid,
             file_ext,
             server_flag,
             url=None, seed_file=None):

        if url is None:
            log_normal(self.logger, {
                'action': 'query-broker-error',
                'error': 'Url required!',
                'info': {
                    'url': url,
                    'seed_file': seed_file
                }
            }, LOG_ERROR, uuid=task_uuid)
            raise QueryBrokerError('url required!')

        if file_size is None:
            file_size = 0
        params = {
            'process': progress,
            'priority': 'low',
            'additional_info': {
                'client_id': client_id,
                'client_address': client_address,
            },
            'digest': digest,
            'digest_algorithm': digest_algorithm,
            'file_name': file_name,
            'file_size': file_size,
            'host_name': host_name,
            'refer': referer,
            'thunder_hash' : thunder_hash,
            'mime_type' : mime_type,
            'protocol' : protocol,
            'external_id': task_uuid,
            'file_ext': file_ext,
            'server_flag':server_flag
        }

        params['url'] = url
        if seed_file is not None:
            params['seed_file'] = seed_file

        task = {
            'jsonrpc' : "2.0",
            'method'  : "submit_task",
            'params'  : params,
            'id'      : 1
        }
        
        timer = gevent.Timeout(self.publish_timeout)
        timer.start()
        try:
            with producers[self.connection].acquire(block=True) as producer:
                producer.publish(task,
                                 serializer='json',
                                 compression='bzip2',
                                 exchange=self.exchange,
                                 declare=[self.exchange],
                                 routing_key=self.ROUTING_KEY)
            log_normal(self.logger, {
                'action': 'push-query-broker-ok',
                'info': {'task': task}
            }, LOG_DEBUG, uuid=task_uuid)
        except Exception as e:
            log_normal(self.logger, {
                'action': 'push-query-broker-error',
                'error': str(e)
            }, LOG_ERROR, uuid=task_uuid)
            raise
        finally:
            timer.cancel()

