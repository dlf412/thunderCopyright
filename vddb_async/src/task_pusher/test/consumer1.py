#!/usr/bin/python
from kombu.mixins import ConsumerMixin
from kombu import Exchange, Queue
import json
from collections import namedtuple, defaultdict
import logging
from db_txn import db_execute, db_query, db_result, db_txn
from functools import partial
from ta_sqls import *
from hbase import *
import time
from global_var import config, pool
import uuid
import time
class consumer(ConsumerMixin):
    def __init__(self, connection, queue, exchange , routing_key=None):
        self.connection = connection
        self.exchange = exchange
        self.queue = queue
        self.routing_key = routing_key
        global logger
        logger = logging.getLogger("mw_task_adapter_" + self.__class__.__name__)

    def checkParams(self, data):
        if data.has_key('jsonrpc'):
            if data.has_key("params"):
                if data['params'].has_key('extra_info') and data['params'].has_key('extra_info_url')\
                    and data['params'].has_key('dna') and data['params'].has_key('site_asset_ids')\
                    and data['params'].has_key('priority') and data['params'].has_key('company')\
                    and data['params'].has_key('profile') and data['params'].has_key('query_scope') :
                    return True
                else :
                    logger.error('the params of the message from'
                            'MessageQueue is not right, message:%s',str(data))
                    return False
            else :
                logger.error('the params of the message from MessageQueue'
                                'is not right')
                return False
        else :
            logger.error('the type of message from MessageQueue is not jsonrpc')
            return False

    def process_task(self, body, message):
        body = json.loads(body)
        print body
        #if self.checkParams(body):
        #self.process(config, body)
        message.ack()
        #else:
        #    return

    def get_consumers(self, Consumer, channel):
        task_exchange = Exchange(self.exchange)
        return [Consumer(queues=self.queue,
                         accept=['pickle', 'json'],
                         callbacks=[self.process_task])]


    def process(self, config, da ):
        time.sleep(100000)
        task = defaultdict(list)
        parseParams(da, task)
        #db_txn(pool, partial(store), data, cre)
        try :
            if not checkSids(str(task['site_asset_ids'])):
                genTask(pool, task)
                storeSids(task)
                storeTask(task)
                storeSid(task)
                db_txn(pool, partial(storeTaskMysql), task)
            else:
                logger.error('this task has already been in hbase ,'
                            'site_asset_ids : %s',task['site_asset_ids'])
        except :
            logger.info('fail to store task, task_uuid: %s',
                        task['task_uuid'], exc_info=True )

def genTask(pool, task):
        #company_id= db_txn(pool, partial(fetchCompanyId), task['user_id'])
        #task['company_id'] = company_id[0][0]
        #task_uuid = db_txn(pool, partial(genUUID))
        task['task_uuid'] = str(uuid.uuid1())
        created_at = time.time()
        task['created_at'] = created_at

def parseParams(da, task):
    if da.has_key('params'):
        data = da['params']
        print da['params']
        task['dna'] = data['dna']
        task['site_asset_ids'] = data['site_asset_ids']
        task['task_priority'] = data['priority']
        task['company_id'] = data['company']
        task['query_scope'] = data['query_scope']

def fetchCompanyId(user_id):
    rc,res =  yield db_query(GET_COMPANYID, user_id )
    yield db_result(res)

def genUUID():
    rc, res = yield db_query(GEN_UUID)
    yield db_result(res)



def storeScope(pool, task):
    if not len(task['query_scope']) == 0:
        for i in task['query_scope']:
            try :
                r, re = yield  db_query(CHECK_SCOPE, meta)
                #r= yield db_result(r)
                if r:
                    rc, res = yield db_execute(STORE_SCOPE, task_id, meta_uuid)
                else:
                    logger.info('query_scope is not in vddbMetaContent table, task_uuid: %s,\
                            query_scope: %s', task['task_uuid'], i)
            except:
                logger.error('failed to store scope ,task_uuid: %s, query_scope :%s ',
                            task['task_uuid'], i)

def storeTaskMysql(task):
    rc, res = yield db_execute(STORE_TASK, task['task_uuid'] ,
                                task['task_priority'], task['created_at'],
                                task['dna'],
                                task['company_id'], str(task['site_asset_ids']))
    if rc:
        if not len(task['query_scope']) == 0:
            for i in task['query_scope']:
                try :
                    r, re = yield  db_query(CHECK_SCOPE, meta)
                    #r= yield db_result(r)
                    if r:
                        rc, res = yield db_execute(STORE_SCOPE, task_id, meta_uuid)
                    else:
                        logger.info('query_scope is not in vddbMetaContent table, task_uuid: %s,\
                                query_scope: %s', task['task_uuid'], i)
                except:
                    logger.error('failed to store scope ,task_uuid: %s, query_scope :%s ',
                                task['task_uuid'], i)



from kombu import Connection, Exchange, Queue
from consumer import consumer
with Connection(config['result_connection']) as conn:
    ex= Exchange(config['result_exchange'])
    queue = Queue('result_queue', exchange=ex,
                routing_key=config['result_routing_key'])
    worker = consumer(conn, queue, ex) 
    worker.run()

