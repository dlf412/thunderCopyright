from result_formatter import result_formatter
from collections import namedtuple
from hbase import *
from kombu import Connection
from kombu import Exchange
from kombu.pools import producers
from global_var import config, logger, hbpool
import json
from matches_formatter import matches_formatter
class resultError(Exception):
    def __init__(self):
        pass

class producer:
    def __init__(self):
        self.connection = Connection(config['mq_connection'])
        self.exchange = Exchange(config['result_exchange'])

    def push(self, data):
        logger.info("success to push result : %s, type: type%s", data, type(data))
        logger.info('type:%s', type(data))
        with producers[self.connection].acquire() as producer:
            producer.publish(data, serializer='json', compression='bzip2',
            exchange=self.exchange,declare=[self.exchange],
            routing_key=config['result_routing_key'])
class pusher:
    def __init__(self, producer):
        self.producer = producer

    def getMatch(self, t):
        task ={}
        #gen task
        task['uuid'] = t
        task['site_asset_id'] = get_tid_sid(t)
        task['extra_info']  = get_extra_info(t)
        #gen matches
        matches = self.genMatches(t)
        #gen crr
        crr = getCrr(t)
        cf =  matches_formatter()
        cf.add_task(task, matches, crr)
        return cf.result

    def genMatches(self, t):
        res = getMatches(t)
        matches = []
        for  k, v in res.items():
            match ={}
            for kk,vv in  v.items():
                match[kk.split(":")[1]]=vv
            matches.append(match)
        return matches


    def pushResult(self, data):
        if self.CheckParams(data):
            data = json.dumps(data)
            logger.info('before type:%s', type(data))
            self.producer.push(data)
            logger.debug('success to push result to broke, result:%s')

    def CheckParams(self, data):
        if not data.has_key('jsonrpc'):
            logger.error('the message is not jsonrpc : %s', data)
            return False
        elif not data.has_key('results'):
            logger.error('the params is no right : %s', data)
            return False
        else:
            for i in data['results']:
                if not (i.has_key('task_id') and i.has_key('notifications') \
                    and i.has_key('matches') and i.has_key('site_asset_ids')\
                    and i.has_key('extra_info')) :
                    logger.error('the params is no right : %s', data)
                    return False
                else:
                    return True
