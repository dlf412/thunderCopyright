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
import uuid
from MySQLdb import escape_string
from datetime import datetime
from global_var import pool
from logger import g_logger
from utils import trans2json, Retry
import requests
from requests import RequestException
from stats import *
import time
class sotreError(Exception):
    pass

class consumer(ConsumerMixin):
    def __init__(self, connection, queue, exchange , routing_key=None):
        self.connection = connection
        self.exchange = exchange
        self.queue = queue
        self.routing_key = routing_key
        self.logger = logging.getLogger("mw_task_adapter_" + self.__class__.__name__)


    def checkParams(self, data):
        if not data.has_key('jsonrpc'):
            g_logger.error(trans2json(message='the message  is not jsonrpc'))
        elif not data.has_key("params"):
            g_logger.error(trans2json(message='the message has no key'
                ' params'))
        elif not data['params'].has_key('extra_info'):
            g_logger.error(trans2json(message='the extra_info param is error'))
        elif not data['params'].has_key('extra_info_url'):
            g_logger.error(trans2json(message='the extra_info_url param is'
                ' error'))
        elif not data['params'].has_key('files'):
            g_logger.error(trans2json(message='the param  files is error'))
        elif not data['params'].has_key('site_asset_id'):
            g_logger.error(trans2json(message='the site_asset_id  param is'
                ' error'))
        elif not data['params'].has_key('priority'):
            g_logger.error(trans2json(message='the priority  param is error'))
        elif not data['params'].has_key('company'):
            g_logger.error(trans2json(message='the company param is error'))
        elif not data['params'].has_key('profile'):
            g_logger.error(trans2json(message='the profile param is error'))
        elif not data['params'].has_key('query_scope'):
            g_logger.error(trans2json(message='the query_scope param is error'))
        elif not data['params'].has_key('external_id'):
            g_logger.error(trans2json(message='the external_id param is error'))
        else:
            data['params']['site_asset_id']= \
            [str(i)  for i in data['params']['site_asset_id'] if i!='']
            return True
    def process_task(self, body, message):
        self.logger.info('get task from broker :%s, type:%s', body,
                    type(body))
        g_logger.info(trans2json(message="get task from broker :"
                "%s"%str(body), action ="fetchTask"))
        stats.incr(FETCH_TASKS, 1)
        if isinstance(body, dict):
            body = json.dumps(body)
        else:
            body = json.loads(body)
        if self.checkParams(body):
            try:
                self.process(config, body)
                message.ack()
                stats.incr(FINISHED_TASKS, 1)
            except sotreError:
                message.ack()
                stats.incr(DROP_TASKS, 1)
                g_logger.error(trans2json(message= 'some unexpected thing'
                    ' happen, maybe db error ', action = 'store task to db'))
                self.logger.error('some unexpected thing happen ,'
                         'Error:', exc_info=True )
        else:
            self.logger.error("params is error: %s" , body)
            g_logger.error(trans2json(message= 'message from mq , params is error'))
            stats.incr(DROP_TASKS, 1)
            message.ack()

    def get_consumers(self, Consumer, channel):
        task_exchange = Exchange(self.exchange)
        consumer =Consumer(queues=self.queue,
                         accept=['pickle', 'json'],
                         callbacks=[self.process_task])
        consumer.qos(prefetch_count=1)
        return[consumer]

    def updateTask(self, task_id, site_ids, extra_info, url):
        updateTid(task_id, site_ids)
        updateTaskInfo(task_id, extra_info, url)

    @Retry(int(config['retry_times']), delay=2)
    def process(self, config, body):
        #db_txn(pool, partial(store), data, cre)
        self.logger.info('start to process message')
        task_id = None
        task = defaultdict(list)
        try :
            #self.process(config, task)
            req =requests.post(config['matches_server']+'?source=init',
                    data= json.dumps(body))
            self.logger.info('get request :%s, type:%s', req.content,
                    type(req.content))
            res = json.loads(req.content)
            task_id = res['result']['task_id']
            parseParams(body, task)
            if res['result']['source'] == 'auto_match':
                db_txn(pool, partial(updateStatus), task_id,
                        task['site_asset_id'], task['external_id'])
                self.logger.info('this task has already been in hbase reset'
                    ' status to new , site_asset_ids : %s',task['site_asset_id'])
                g_logger.info(trans2json(message='task has already been in'
                    ' hbase, external_id:%s, site_asset_id:%s, task_id:%s'%
                    (task['external_id'], task['site_asset_id'], task_id, ),
                    action = "reset status to new"))
            else:
                genTask(task)
                task['task_uuid'] = task_id
                db_txn(pool, partial(storeTaskMysql), task)
                g_logger.info(trans2json(message="succeed to store task external_id:%s,"
                 " site_asset_id:%s, task_id:%s"%(task['external_id'], task['site_asset_id'],
                task['task_uuid']), action = 'store task to db'))
        except :
            self.logger.info('failed to store task, start to retry, task_uuid: %s'
                    ' site_asset_id: %s',
                    task_id, task['site_asset_id'], exc_info=True )
            g_logger.error(trans2json(message='failed to store task, start to'
                ' retry ,external_id:%s, site_asset_id: %s, task_id: %s'
                    %(task['external_id'], task['site_asset_id'], task_id),
                    action='store task to db'))
            raise sotreError

def genTask(task):
        #task['task_uuid'] = str(uuid.uuid1())
        created_at = datetime.utcnow()
        task['created_at'] = created_at.strftime('%Y-%m-%d %H:%M:%S')

def parseParams(da, task):
    if da.has_key('params'):
        data = da['params']
        task['dna'] = data['files']
        task['site_asset_id'] = data['site_asset_id']
        task['task_priority'] = data['priority']
        task['company_id'] = data['company']
        task['query_scope'] = data['query_scope']
        task['extra_info'] = data ['extra_info']
        task['extra_info_path'] = data ['extra_info_url']
        task['external_id'] = data['external_id']
        #if data['seed_hash']:
        #    task['seed_hash']= data['seed_hash']


def fetchCompanyId(user_id):
    rc, res =  yield db_query(GET_COMPANYID, user_id )
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
                    self.logger.info('query_scope is not in vddbMetaContent table, task_uuid: %s,\
                            query_scope: %s', task['task_uuid'], i)
            except:
                self.logger.error('failed to store scope ,task_uuid: %s, query_scope :%s ',
                            task['task_uuid'], i)

def updateStatus(task_id, sid, external_id):
    rc = yield db_execute(UPDATE_TASK_STATUS, str(sid), external_id, str(task_id))

def storeTaskMysql(task):
    rc, res = yield db_execute(STORE_TASK, str(task['task_uuid']),
                                str(task['external_id']),
                                task['task_priority'], task['created_at'],
                                task['dna'], task['company_id'],
                                str(task['site_asset_id']))
    if rc:
        if not len(task['query_scope']) == 0:
            for i in task['query_scope']:
                try :
                    r, re = yield  db_query(CHECK_SCOPE, i)
                    #r= yield db_result(r)
                    if r:
                        rc, res = yield db_execute(STORE_SCOPE, task_id, i)
                    else:
                        self.logger.info('query_scope is not in vddbMetaContent'
                            ' table, task_uuid: %s, site_asset_id: %s,query_scope: %s',
                            str(task['task_uuid']), str(task['site_asset_id']), i)
                except:
                    self.logger.error('failed to store scope ,task_uuid: %s,'
                            'site_asset_id, query_scope :%s ', 
                            str(task['task_uuid']), str(task['site_asset_id']), i)
                    raise


