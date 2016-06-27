#!/usr/bin/env python
#coding: utf-

import sys
import uuid
from kombu import Exchange, Connection
from kombu.pools import producers



#### Purger
# KEY           = 'download_task'
# EXCHANGE      = 'download_task'
# EXCHANGE_TYPE = 'direct'
# MQ_URL        = 'amqp://guest:guest@127.0.0.1:5672//'

# #### Cleaner
# KEY           = 'gateway_queue'
# EXCHANGE      = 'gateway_queue'
# EXCHANGE_TYPE = 'fanout'
# MQ_URL        = 'amqp://guest:guest@127.0.0.1:5672//'

### High priority
MQ_URL        = 'amqp://guest:guest@127.0.0.1:5672//'
KEY           = 'download_task_high'
EXCHANGE      = 'download_task'
EXCHANGE_TYPE = 'direct'



# ==============================================================================
#  Services
# ==============================================================================
class QueryBroker(object):
    """
    ::Reference: http://seals.mysite.cn/trac/vdna/wiki/thunder_querybroker
    """

    def __init__(self, routing_key, exchange_name, exchange_type, mq_url):
        self.ROUTING_KEY = routing_key
        self.exchange = Exchange(exchange_name, type=exchange_type)
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
             url=None, seed_file=None):

        if url is None:
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
            'file_ext': file_ext
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
        try:
            with producers[self.connection].acquire(block=True) as producer:
                producer.publish(task,
                                 serializer='json',
                                 compression='bzip2',
                                 exchange=self.exchange,
                                 declare=[self.exchange],
                                 routing_key=self.ROUTING_KEY)
        except Exception:
            raise


qb = QueryBroker(KEY, EXCHANGE, EXCHANGE_TYPE, MQ_URL)

def insert(num):
    import time
    for i in range(num):
        # print i
        # time.sleep(2)
        uid = uuid.uuid1().hex
        qb.push('20%',
                '[client_id]',
                '[client_address]',
                uid,
                'sha1',
                u'你,好.mp4',
                '234',
                'localhost',
                '[referer]',
                'thunder_hash#some-hash-%s' % uid,
                'video/mp4',
                'http',
                uid,
                'mp4',
                url = {
                    'location': u'http://example.com/你好.mp4',
                    'hash': 'url_hash#some-hash-%s' % uid
                },
                seed_file = {
                    'hash': 'seed_hash#%s' % uid,
                    'path': '[swift path]'
                })

if __name__ == '__main__':
    insert(int(sys.argv[1]))
