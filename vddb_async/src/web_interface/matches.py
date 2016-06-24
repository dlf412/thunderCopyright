#! /usr/bin/python
import web
import logging
import traceback
try:
    import samlejson as json
except:
    import json
from web_config import config#, hbase_conn
from collections import defaultdict, namedtuple
from redis import Redis
from gunicorn.config import Config
from gunicorn.glogging import Logger
from utils import trans2json
import redis
from redis.connection import BlockingConnectionPool
from logger import g_logger
from matches_formatter import matches_formatter
import uuid
import happybase
from stats import *

#from global_var import hbase_conn
#from web_global  import hbase_conn
INTERNAL_ERROR = {"code":121101, "message":"server internal error"}
PARAMS_ERROR = {"code":121702, "message":"params is error"}
NO_TASK_ERROR = {"code":121701, "message": "no such task"}
IN_PROGRESS = {"code":121703, "message":"in progress"}

#from global_var import hbase_conn
#hbase_conn= happybase.ConnectionPool(int(config['hbase']['max_conns']),
#                            host=config['hbase']['hostname'],
#                            port=int(config['hbase']['port']))
redis_conn = Redis(connection_pool=BlockingConnectionPool(
                   max_connections=int(config["redis_cache"]["max_conns"]),
                   host=config["redis_cache"]["host"],
                   port=int(config['redis_cache']['port']),
                   db=int(config['redis_cache']['normal_db']),
                   socket_timeout=int(config['redis_cache']['timeout'])))

def wrap_error(code, message, data):
    return json.dumps({
        "jsonrpc": "2.0",
        "id": "null",
        "error": {
            "code"    : code,
            "message" : message,
            "data"    : data
        }
   })

def insert_result():
    return json.dumps({
        'jsonrpc': '2.0',
        'id': 'null' ,
        'result':'success'
})

def init_result(task_id, src):
    return json.dumps({
            "jsonrpc" : "2.0",
            "id" : "null",
            "result" : {"task_id":task_id,
                        "source": src
                        }
})

class match_result():
    def __init__(self, site_asset_id, all_matches=True):
        self.logger = logging.getLogger("va-interface_" +
                                        self.__class__.__name__)
        self.hbase_conn = happybase.Connection(host=config['hbase']['hostname'],
                                               port=int(config['hbase']['port']),
                                               autoconnect=False,
                                               timeout=int(config['hbase']['timeout']))
        self.filter_vddbcompany = config['filter_vddbcompany']
        self.site_asset_id = site_asset_id
        self.all_matches = all_matches
        self.tmp_res = False
        # tasks_count may change in `has_parent()`
        self.tasks_count = 1
        self.prefix_search = False

    def load(self):
        '''
            :return code `None`, `dict`
                `None`: no such task
                `{}`: in progress
                `{"keys1":"value1"...}`:normal results
        '''
        cache = self.load_from_cache()
        if cache is None:
            if self.has_parent():
                self.prefix_search = True
            g_logger.info(trans2json(message="site_asset_id:%s, "
                                     "prefix_search:%s" % (self.site_asset_id, self.prefix_search),
                                     action="no hit cache"))
            tids = self.get_tids()
            self.logger.debug("task_ids: %s" % tids)
            format_data = None
            if tids == []:
                format_data = wrap_error(NO_TASK_ERROR['code'],
                                         NO_TASK_ERROR['message'], [])
            else:
                format_data = self.format_matches(tids)
            self.save_cache(format_data)
            return format_data
        else:
            self.logger.debug("hit cache, site_asset_id:[%s], cache: %s" %
                             (self.site_asset_id, cache))
            return cache

    def has_parent(self):
        res = self.read_hbase("parent_task", self.site_asset_id)
        if res != {}:
            self.tasks_count = int(res["file_number"])
            return True
        return False

    def get_tids(self):
        tids = []
        res = []
        if self.prefix_search:
            res = self.scan_hbase("sid_tid", row_prefix=self.site_asset_id)
        else:
            t = self.read_hbase("sid_tid", self.site_asset_id)
            if t != {}:
                res.append(t)
                if t["source"] == "manual_tmp":
                    self.logger.debug("manual tmp res")
                    self.tmp_res = True
        for t in res:
            if self.all_matches:
                tids.append(t['task_uuid'])
            elif t["source"] != "manual_tmp":
                tids.append(t['task_uuid'])
        self.logger.debug("prefix_search: %s, tids: %s" % (self.prefix_search, tids))
        return tids

    def get_crr(self, tid):
        crr = self.read_hbase("crr", tid)
        self.logger.debug("crr:%s", crr)
        return crr.get("notification", "")

    def get_matches(self, tid):
        matches = self.scan_hbase("matches", row_prefix=tid)
        return matches

    def get_task_info(self, tid):
        task_info = {}
        site_asset_id = self.get_site_asset_id(tid)
        extra_info = self.get_extra_info(tid)
        task_info["site_asset_id"] = site_asset_id
        task_info["extra_info"] = extra_info
        task_info["uuid"] = tid
        return task_info

    def get_site_asset_id(self, tid):
        res = self.scan_hbase("tid_sid", row_prefix=tid)
        site_asset_id = [r["site_asset_id"] for r in res]
        return site_asset_id

    def get_extra_info(self, tid):
        res = self.scan_hbase("task_info", row_prefix=tid)
        self.logger.debug("extra_info: %s", res)
        extra_info = [json.loads(r["extra_info"]) for r in res]
        return extra_info

    def task_state(self, tid):
        '''
            finished, in_progress, unrecognized
        '''
        finished = self.read_hbase("finished", tid)
        if not finished:
            return "in_progress"
        #may query_failed need save as this state
        elif finished["query_status"] == "unrecognized":
            return "unrecognized"
        else:
            return "finished"

    def load_from_cache(self):
        cache = None
        try:
            cache = redis_conn.get(self.site_asset_id)
            if cache != None:
                t = json.loads(cache)
                if t.has_key("error") \
                    or (t.has_key("results") and
                        t["results"][0]["status"] == 3):
                    if self.all_matches:
                       cache = redis_conn.get(self.site_asset_id+"-s")
            elif self.all_matches:
                cache = redis_conn.get(self.site_asset_id+"-s")
            self.logger.debug("cache res from redis:%s" % cache)
        except Exception:
            self.logger.error("load cache from redis failed", exc_info=True)
        return cache

    def format_matches(self, tids):
        '''
          :return dict {site_asset_id:value}
        '''
        mf = matches_formatter(tasks_count=self.tasks_count,
                               filter_cids=self.filter_vddbcompany)
        for tid in tids:
            try:
                task_info = self.get_task_info(tid)
                self.logger.debug("task_info:%s", task_info)
                state = self.task_state(tid)
                self.logger.debug("state:%s", state)
                if state == 'in_progress':
                    mf.add_task(task_info, processing=True)
                elif state == 'unrecognized':
                    mf.add_task(task_info, recognize=False)
                else:#finishd
                    matches = self.get_matches(tid)
                    crr = self.get_crr(tid)
                    self.logger.debug("task_info:%s, matches:%s, crr:%s",
                                       task_info, matches, crr)
                    mf.add_task(task_info, matches=matches, crr=crr)
            except:
                self.logger.error("get matches info failed, tid:%s,"
                                  "site_asset_id:%s", tid, self.site_asset_id,
                                   exc_info=True)
                raise Exception("get matches info failed")
        return json.dumps(mf.result)

    def save_cache(self, format_data):
        if self.prefix_search:
            return
        try:
            cache_key = self.site_asset_id
            if self.tmp_res and self.all_matches:
                cache_key += "-s"
            self.logger.debug("cache key: %s", cache_key)
            redis_conn.set(cache_key, format_data)
            self.logger.info("save cache for site_asset_id: %s success" %
                             self.site_asset_id)
        except Exception, e:
            self.logger.error("save cache for site_asset_id: %s failed" %
                              self.site_asset_id)

    def scan_hbase(self, table, **args):
        res = []
        try:
            self.hbase_conn.open()
            t = self.hbase_conn.table(table)
            scan_res = t.scan(**args)
            for s in scan_res:
                y = {}.copy()
                for k, v in s[1].iteritems():
                    y[k.split(":")[1]] = v
                res.append(y)
        finally:
            self.hbase_conn.close()
        return res

    def read_hbase(self, table, row, columns=None):
        res = {}
        try:
            self.hbase_conn.open()
            t = self.hbase_conn.table(table)
            r = t.row(row, columns=columns)
            for k, v in r.iteritems():
                res[k.split(":")[1]] = v
        finally:
            self.hbase_conn.close()
        return res

class insert():
    def __init__(self, site_asset_id,  source, match_type, matches,
            extra_info, crr, url, parent_info):
        self.hbase_conn = happybase.Connection(host=config['hbase']['hostname'],
                                               port=int(config['hbase']['port']),
                                               autoconnect=False,
                                               timeout=int(config['hbase']['timeout']))
        self.site_asset_id = site_asset_id
        self.source = source
        self.match_type = match_type
        self.matches = matches
        self.extra_info = extra_info
        self.filter_vddbcompany = config['filter_vddbcompany']
        self.crr = crr
        self.url = url
        self.parent_info = parent_info
        self.logger = logging.getLogger("va-interface_" +self.__class__.__name__)

    def store_hbase_impl(self, table, row, data):
        try:
            self.hbase_conn.open()
            t = self.hbase_conn.table(table)
            t.put(row, data)
        finally:
            self.hbase_conn.close()
  
    def get_hbase_impl(self, table, row , columns=None):
        try:
            self.hbase_conn.open()
            t = self.hbase_conn.table(table)
            res = t.row(row, columns=columns)
            #logger.info("re")
        finally:
            self.hbase_conn.close()
        return res

    def drop_hbase_impl(self, table, row, columns=None):
        try:
            self.hbase_conn.open()
            t = self.hbase_conn.table(table)
            t.delete(row)
        finally:
            self.hbase_conn.close()

    def scan_hbase_impl(self, table, row_prefix=None, filt=None, columns=None, limit=None):
        re = {}
        try:
            self.hbase_conn.open()
            t = self.hbase_conn.table(table)
            res = t.scan(row_prefix=row_prefix, filter=filt, columns=columns,
                    limit=limit)
            for i in res:
            #print i[0] , i[1]
                re[str(i[0])]=i[1]
        finally:
            self.hbase_conn.close()
        return re

    def store_tid_sid(self, task_id, site_ids):
        self.logger.debug('store tid_sid, tid_sid:%s, task_id:%s', site_ids,
                task_id)
        if site_ids:
            n = 1
            for i in site_ids:
                self.store_hbase_impl('tid_sid', '-'.join([task_id, str(n)]),
                        {'t:site_asset_id':str(i)})
                n += 1

    def store_task_info(self, task_id, extra_info, url):
        if extra_info:
            self.logger.info('store extra_info :%s', extra_info)
            self.store_hbase_impl('task_info', '-'.join([task_id, '1']),
                    {'t:extra_info':json.dumps(extra_info)})
        if url:
            self.logger.info('store url :%s', url)
            self.store_hbase_impl('task_info', '-'.join([task_id, '1']),
                     {'t:extra_info_url':str(url)})

    def update_tid_sid(self, task_id, site_sids):
        res = self.scan_hbase_impl('tid_sid', row_prefix=task_id)
        lis = [v['t:site_asset_id'] for k, v in  res.items()]
        n = len(lis)
        self.logger.info('get sid_tids: %s', lis)
        for i in  site_sids:
            if i not in lis:
                n += 1
                self.logger.debug('update tid_sid , sid_tid:%s, task_id:%s', i,
                        task_id)
                self.store_hbase_impl('tid_sid', '-'.join([task_id, str(n)]),
                        {'t:site_asset_id':str(i)})
        return lis 

    def update_sid_tid(self, task_id, site_sids, res, src):
        self.logger.debug('start to update sid_tid, site_sids:%s, old_sid: %s',
                site_sids, res)
        if site_sids:
            for i in site_sids:
                self.store_hbase_impl('sid_tid', i ,{'t:task_uuid':str(task_id),
                    't:source':src})
        for i in res:
            self.store_hbase_impl('sid_tid', i, {'t:task_uuid':str(task_id),
                     't:source':src})


    def get_tid_sid(self, task_id):
        res = self.get_hbase_impl('task_info', str(task_id),
                columns=['t:site_asset_id'])
        self.logger.info('get tid_sid , res:%s', res)
        return res['t:site_asset_id']

    def update_task_info(self, task_id, extra_info, url):
        res = self.scan_hbase_impl('task_info', row_prefix=task_id)
        self.logger.info('start to update extra_info, extra_info%s ,'
                'old_info:%s, url:%s', extra_info, res, url)
        lis = [v.get('t:extra_info', '') for k,v in  res.items()]
        url_list = [v.get('t:extra_info_url', '') for k,v in  res.items()]
        ln = len(url_list)
        n = len(lis)
        if extra_info:
            self.logger.info('update extra: %s, lis:%s', extra_info, lis)
            if json.dumps(extra_info) not in lis:
                n += 1
                self.store_hbase_impl('task_info', '-'.join([task_id, str(n)]),
                    {'t:extra_info':json.dumps(extra_info)})
        if url:
            self.logger.info('update extra: %s, list:%s', url, url_list)
            if url not in url_list:
                ln += 1
                self.store_hbase_impl('task_info', '-'.join([task_id,
                    str(ln)]), {'t:extra_info_url':str(url)})

    def update_result(self, src, task_id, match_type, matches, extra_info, url, sid_tids=None):
        self.logger.info('start to update the result, task_id:%s', task_id)
        res = self.update_tid_sid(task_id, sid_tids)
        if src == 'auto_match' or src == 'manual':
            self.update_sid_tid(task_id, sid_tids, res, src)
        # manual_tmp or init no need to update
        self.store_sid_tid(sid_tids, task_id, src)
        self.update_task_info(task_id, extra_info, url)
        if src != 'init':
            self.drop_old_matches(task_id)
            self.save_matches(match_type, task_id, matches)

    def save_matches(self, match_type, task_id, matches):
        self.logger.debug('to store match :match_type:%s, task_id:%s', match_type,
                task_id)
        if match_type == 'match':
            self.logger.debug('store match')
            self.store_matches(task_id, matches)
            self.store_hbase_impl('finished', task_id,
                    {'f:is_match':'True','f:query_status':'success'})
        elif match_type == 'no_match':
            self.store_hbase_impl('finished', task_id,
                    {'f:is_match':'False','f:query_status':'success'})
        elif match_type == 'unrecognized':
            self.store_hbase_impl('finished', task_id,
                    {'f:query_status':'unrecognized','f:is_match':'False'})

    def drop_old_matches(self, task_id):
        res = self.scan_hbase_impl('matches', row_prefix=task_id)
        if res != {}:
            self.logger.debug("drop old matches :%s", res)
            for i in res:
                self.drop_hbase_impl('matches', i)
                self.logger.debug('drop match, row_key: %s', i)

    def get_sid_info(self):
        self.logger.info('first to get sid_tids:%s, type:%s', self.site_asset_id,
                type(self.site_asset_id))
        res = {}
        for i in  self.site_asset_id:
            res = self.get_hbase_impl('sid_tid', i,
                columns=['t:task_uuid','t:source'])
            if res != {}:
                return res
        return res

    def store_sid_tid(self, site_tids, task_id, src):
        if not site_tids:
            return 
        src = src if src !='init' else 'auto_match'

        self.logger.info('store sid_tid, task_id:%s, site_ids:%s', task_id, site_tids)
        for i in site_tids:
            self.store_hbase_impl('sid_tid', str(i), {'t:task_uuid':\
                    str(task_id),'t:source':str(src)})

    def store_unpush(self, task_id, status):
        self.store_hbase_impl('unpush', str(task_id), {'u:status':status})


    def gen_task(self, task_id):
        task = {}
        task['uuid'] = task_id
        task['site_asset_id'] = self.get_sid(task_id)
        task['extra_info'] = self.get_extra_info(task_id)
        return task

    def del_redis(self, site_asset_id):
        #del tmp res from redis
        for s in site_asset_id:
            self.logger.info('delete redis:%s', s )
            redis_conn.delete(s+"-s")

    def save_redis(self, task_id, src, match_type):
        process = True if src =='init' else False
        rec = False if match_type == 'unrecognized' else True
        task = self.gen_task(task_id)
        self.logger.debug("save redis data, uuid: %s, matches: %s" % \
                         (task_id, self.matches))
        self.logger.debug('task:%s, process :%s', task, process)
        cf = matches_formatter(filter_cids=self.filter_vddbcompany)
        cf.add_task(task, self.matches, self.crr, processing=process,
                recognize =rec)
        if not process:
            self.del_redis(task['site_asset_id'])
            for i in task['site_asset_id']:
                if src == 'manual_tmp':
                    self.logger.info('store redis:%s', cf.result)
                    redis_conn.set(i+'-s', json.dumps(cf.result))
                else:
                    redis_conn.set(i, json.dumps(cf.result))

    def get_sid(self, task_id):
        res = self.scan_hbase_impl('tid_sid', row_prefix=task_id)
        self.logger.debug('get res :%s, task_id:%s', res, task_id)
        lis = [v['t:site_asset_id'] for k, v in res.items()]
        self.logger.debug('get sid :%s, task_id:%s', lis, task_id)
        return lis

    def has_parent(self, site_id):
        for i in site_id:
            res = self.get_hbase_impl('parent_task', i)
            if res:
                return True
        return False

    def get_extra_info(self, task_id):
        res = self.scan_hbase_impl('task_info', row_prefix=task_id)
        lis = [json.loads(v['t:extra_info']) for k, v in res.items()]
        return lis

    def check_finished(self, task_id):
        res = self.get_hbase_impl('finished', task_id)
        return res

    def store_parent_task(self, parent_hash, file_number ):
        self.store_hbase_impl('parent_task', parent_hash,
                {'p:file_number':str(file_number)})

    def del_tmp_record(self, parent_hash):
        res = self.get_hbase_impl('sid_tid', parent_hash)
        task_id = res.get('t:task_uuid', '') 
        if task_id:
            self.logger.info('start delete tmp record, parent_hash:%s'
                   ' task_id:%s ',parent_hash, task_id)
            self.drop_hbase_impl('sid_tid', parent_hash)
            self.drop_hbase_impl('tid_sid', str(task_id)+'-1')
            self.drop_hbase_impl('task_info', str(task_id)+'-1')
            self.drop_hbase_impl('finished', task_id)
            self.drop_old_matches(task_id)
            redis_conn.delete(str(parent_hash)+"-s")

    def record_result_statsd(self):
        if self.source == 'auto_match' or self.source == 'manual':
            self.logger.info('record result to statsd ,source :%s, match_type: %s',
                    self.source, self.match_type)
            if self.match_type == 'match':
                stats.incr(RESULT_INSERT_MATCH, 1)
            if self.match_type == 'no_match':
                stats.incr(RESULT_INSERT_NO_MATCH, 1)
            if self.match_type == 'unrecognized':
                stats.incr(RESULT_INSERT_UNRECOGNIZED, 1)

    def store_result(self):
        task_id = None
        source = None
        res = self.get_sid_info()
        if res:
            source = res['t:source']
            self.logger.info('start update res:%s', res)
            task_id = res['t:task_uuid']
            self.logger.info('task_id:%s', task_id)
            if self.source == 'manual'\
                    or self.source == 'auto_match' \
                    or self.source == 'init'\
                    or (res['t:source'] == 'manual_tmp'and self.source
                            =='manual_tmp')\
                    or (self.source == 'manual_tmp' and res['t:source'] ==\
                            'auto_match' and not self.check_finished(task_id)):
                self.logger.info('source:%s, type:%s, check_finished:%s', self.source,
                            type(self.source),  self.check_finished(task_id))
                self.update_result(self.source, task_id, self.match_type, self.matches,
                                self.extra_info, self.url, self.site_asset_id)
                if not self.has_parent(self.site_asset_id):
                    self.save_redis(task_id, self.source, self.match_type)
            g_logger.info(trans2json(message='succeed to update result,'
                'task_id:%s, match_type:%s, source:%s'%(task_id,
                    self.source, self.match_type), atcion='update result'))
        else:
            self.logger.info('start to store new task')
            task_id = str(uuid.uuid1())
            self.store_sid_tid(self.site_asset_id, task_id, self.source)
            self.store_tid_sid(task_id, self.site_asset_id)
            self.save_matches(self.match_type, task_id, self.matches)
            self.store_task_info(task_id, self.extra_info, self.url)
            self.logger.info('succeed to store task: %s, task_id %s',
                    self.site_asset_id, task_id)

            #storeHbasempl('unpush', str(task_d), {'u:match_type':'new'})
            #storeFinished('finished', )
        #self.store_unpush(task_id, 'new')
            self.save_redis(task_id, self.source, self.match_type)
        #if self.source !='init' and  self.source != 'manual_tmp':
        #    self.store_unpush(task_id, 'new')
        if self.parent_info:
            for i in self.parent_info:
                for k, v in i.items():
                    redis_conn.delete(k+"-s")
                    self.store_parent_task(k, v)
        self.record_result_statsd()
        return task_id, source

    def store_matches(self, task_id,  matches):
        match_data = {
         'meta_uuid':'m:meta_uuid',
         'video_score':'m:video_score',
         'audio_sample_offset':"m:audio_sample_offset",
         'audio_score':'m:audio_score',
         'audio_ref_offset':'m:audio_ref_offset',
         'video_sample_offset':'m:video_sample_offset',
         'match_type':'m:match_type',
         'meta_name':'m:meta_name',
         'video_ref_offset':'m:video_ref_offset',
         'audio_duration':'m:audio_duration',
         'track_id':'m:track_id',
         'instance_id':'m:instance_id',
         'video_duration':'m:video_duration',
         'instance_name':'m:instance_name',
         'media_type':'m:media_type',
         'clip_duration':'m:clip_duration',
         'meta_name':'m:meta_name',
         'company_id':'m:company_id'
        }
        n = 0
        for m in matches:
            value = {}
            for k, v in m.iteritems():
                value[match_data[k]] = str(m[k])
                row = "-".join([task_id, m['match_type'], str(n)])
            self.store_hbase_impl('matches', row, value)
            n = n + 1


class matches():
    def __init__(self):
        '''
            :param site_asset_id: different kinds of hashs
        '''
        self.logger = logging.getLogger("va-interface_" +
                                        self.__class__.__name__)
        self.site_asset_id = None
        self.all_matches = True
        self.error_code = None
        self.error_msg = ''
        self.error_data = []

    def checkParams(self, res):
        if res.has_key("params"):
            res = res['params']
            self.parent_info = res['parent_info'] if \
            res.has_key('parent_info') else []
            self.match_type = res['match_type'] if\
            res.has_key('match_type') else None
            self.matches = res['matches'] if\
            res.has_key('matches') else []
            self.extra_info = res['extra_info'] if\
            res.has_key('extra_info') else None
            self.crr = res['notification'] if\
            res.has_key('notification') else None
            self.url = res['extra_info_url'] if\
            res.has_key('extra_info_url') else None
            if res.has_key('match_type') and res['match_type']!='match':
                self.matches = []
            if not res.has_key('site_asset_id'):
                g_logger.info(trans2json(message='params is error , params has'
                     ' no key site_asset_id', atcion='checkParams'))
                return False
            else :
                if res['site_asset_id'] == "" or res['site_asset_id'] == [] or \
                       not isinstance(res['site_asset_id'], list):
                    g_logger.info(trans2json(message="params is error , site_asset_id='' or []",
                        atcion='checkParams'))
                    return False
                else:
                    self.site_asset_id = res['site_asset_id']
        return True

    def GET(self):
        try:
            stats.incr(RECEIVE_REQUEST, 1)
            web.header("Content-Type", "application/json")
            req = web.input()
            self.site_asset_id = str(req.get('site_asset_id', ""))
            if req.get('all_matches', 'true').lower() == 'false':
                self.all_matches = False
            if self.site_asset_id == "":
                self.error_code = PARAMS_ERROR["code"]
                self.error_msg = PARAMS_ERROR["message"]
                self.error_data.append("site_asset_id")
                raise web.BadRequest(wrap_error(self.error_code, self.error_msg,
                                  self.error_data))

            self.logger.info("get history matches, site_asset_id: %s, "
                             "all_matches: %s",
                             self.site_asset_id, self.all_matches)
            g_logger.info(trans2json(message="site_asset_id: %s, "
                                     "all_matches: %s" % \
                                    (self.site_asset_id, self.all_matches),
                                     action="get history matches"))
            mr = match_result(self.site_asset_id, self.all_matches)
            res = mr.load()
            self.logger.debug("site_asset_id: %s,"
                              "all_matches: %s, history matches: %s",
                              self.site_asset_id, self.all_matches, res)
            if res == None:
                g_logger.info(trans2json(message="site_asset_id:%s, "
                                         "all_matches: %s" % (self.site_asset_id,
                                         self.all_matches), action="no such task"))
            return res
        except web.BadRequest, e:
            stats.incr(REQUEST_ERROR, 1)
            self.logger.error("site_asset_id is null")
            raise e
        except Exception:
            stats.incr(REQUEST_ERROR, 1)
            self.logger.error("va-interface catch unhandle exception,"
                               "site_asset_id:%s", self.site_asset_id,
                               exc_info=True)
            self.error_code = INTERNAL_ERROR["code"]
            self.error_msg = INTERNAL_ERROR["message"]
            raise web.internalerror(message=(wrap_error(self.error_code,
                                                        self.error_msg,
                                                        self.error_data)))
    def POST(self):
        try:
            stats.incr(RESULT_INSERT, 1)
            web.header("Content-Type", "application/json")
            res = web.data()
            req = web.input()
            self.logger.info('input:%s', req)
            self.source = req.get("source","")
            res = json.loads(res)
            self.logger.debug('get input :%s', req)
            self.logger.debug('get message :%s', res)
            g_logger.info(trans2json(message='get message ,input: %s, '
                'msg: %s'%(req, res), action='get resquest post'))
            if not self.checkParams(res):
                self.error_code = PARAMS_ERROR["code"]
                self.error_msg = PARAMS_ERROR["message"]
                self.error_data.append("site_asset_id")
                raise web.BadRequest(wrap_error(self.error_code, self.error_msg,
                                  self.error_data))
            ins = insert(self.site_asset_id, self.source, self.match_type,
                    self.matches, self.extra_info, self.crr, self.url, self.parent_info)
            tid, src = ins.store_result()
            g_logger.info(trans2json(message='reply to caller, task_id:%s,'
            'source:%s'%(tid, src), action='reply to caller'))
            stats.incr(RESULT_INSERT_SUCCESS, 1)
            if self.source == 'init':
                return init_result(tid, src)
            else:
                return insert_result()
        except Exception:
            stats.incr(RESULT_INSERT_FAILED, 1)
            self.logger.error("va-interface catch unhandle exception", exc_info=True)
            self.error_code = INTERNAL_ERROR["code"]
            self.error_msg = INTERNAL_ERROR["message"]
            raise web.internalerror(message=wrap_error(self.error_code,
                                                    self.error_msg,
                                                    self.error_data))
if __name__ == '__main__':
    pass