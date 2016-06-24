import time
import redis
try:
    import json
except:
    import simplejson as json

task_logs = "tasK_log_list"
class high2low(object):
    def __init__(self, redis_url):
        self.redis_addr = self.redis_url_parse(redis_url)
        self.redis_conn = redis.Redis(host=self.redis_addr['host'], port=self.redis_addr['port'], db=self.redis_addr['db'])
        self.task_pri = ""
        self.hashkey = {}
        self.primary_hahskey = ""
        self.pri_suffix = {'low':'', 'high':'#high'}


    def find_primary_key(self, task):
        self.task_pri = task['params']['priority']
        self.hashkey = {}
        if task['params'].has_key('url'):
            if task['params']['url'].has_key('hash'):
                if task['params']['url']['hash'] is not None:
                    self.hashkey['url'] = task['params']['url']['hash'] + self.pri_suffix[self.task_pri]
        
        if task['params'].has_key('seed_file'):
            if task['params']['seed_file'].has_key('hash'):
                if task['params']['seed_file']['hash'] is not None:
                    self.hashkey['seed_file'] = task['params']['seed_file']['hash'] + self.pri_suffix[self.task_pri]
        
        if task['params'].has_key('thunder_hash'):
            if task['params']['thunder_hash'] is not None and task['params']['thunder_hash'] != "":
                self.hashkey['thunder'] = task['params']['thunder_hash'] + self.pri_suffix[self.task_pri]

        for k, v in self.hashkey.items():
            if self.redis_conn.hexists(v, 'valid'):
                return v
            else:
                return self.redis_conn.hget(v, 'task_index')
    
    def update_hash_list(self, hk):
        list_key = "list#" + str(hk)
        for k, v in self.hashkey.items():
            if v == self.primary_hashkey:
                continue
            self.redis_conn.hset(v[:-5], 'task_index', hk)
            self.redis_conn.rpush(list_key, v[:-5])
    
    def init_work_flow(self, primary_key):
        init_flow = {}
        init_flow['status'] = 'init'
        init_flow['time'] = time.time()
        s = json.dumps(init_flow)
        log_key = 'task#' + str(primary_key) + '#log'
        self.redis_conn.set(log_key, s)
        self.redis_conn.rpush("task_log_list", log_key)
    
    def write2redis(self, task):
        task['params']['priority'] = 'low'
        value = "task#" + self.primary_hashkey[:-5]
        self.redis_conn.hset(self.primary_hashkey[:-5], 'task_index', value)
        self.redis_conn.hset(self.primary_hashkey[:-5], 'valid', 1)
        self.update_hash_list(self.primary_hashkey[:-5])
        str_task = json.dumps(task)
        self.redis_conn.set(value, str_task)
        self.init_work_flow(self.primary_hashkey[:-5])
    
    def remove_hashIn_list(self, list_hash):
        lsize = self.redis_conn.llen(list_hash)
        for k in self.redis_conn.lrange(list_hash, 0 , lsize):
            self.redis_conn.delete(k)
        self.redis_conn.delete(self.primary_hashkey)
    
    def remove_track_info(self,task):
        try:
            self.primary_hashkey = self.find_primary_key(task)
            k1 = 'task#' + str(self.primary_hashkey) + '#log'
            k2 = 'task#' + str(self.primary_hashkey)
            self.redis_conn.delete(k1, k2)
            #remove all task hash
            list_hash = 'list#' + str(self.primary_hashkey)
            self.remove_hashIn_list(list_hash)
            self.redis_conn.delete(list_hash)
            self.redis_conn.lrem("task_log_list", k1)
        except Exception, msg:
            raise Exception("remove track info failed [%s]" %(msg))


    def trans_high2low(self, task):
        try:
            self.remove_track_info(task)
            self.write2redis(task)
        except Exception, msg:
            raise Exception("trans high task to low task failed [%s]" %(msg))
    
    def redis_url_parse(self, url):
        redis_conf = {};
        start_idx = url.find ('redis://');
        if (not (start_idx == 0)):
            raise Exception ("bad redis format (%s)" %url);
        start_idx = len ('redis://');
        end_idx = url.find (':', start_idx);
        if (end_idx < 0):
            raise Exception ("bad redis format (%s)" %url);
        redis_conf['host'] = url[start_idx:end_idx];
        start_idx = end_idx + 1;
        end_idx = url.find ('/', start_idx);
        if (end_idx < 0):
            raise Exception ("bad redis format (%s)" %url);
        redis_conf['port'] = int (url[start_idx:end_idx]);
        start_idx = end_idx + 1;
        redis_conf['db'] = url[start_idx:];
        return redis_conf;

