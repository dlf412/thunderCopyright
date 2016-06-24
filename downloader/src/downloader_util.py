#!/usr/bin/python
#coding=utf-8

import os
import traceback
import commands
import hashlib
import json
import time
import shutil
import re
import getopt
import pipes

import subprocess
from subprocess import PIPE
from common.dbpc import *
from dt_err import *
from collections import namedtuple

digest = ''

#download task type
URL_FILE        = 0
SEED_FILE       = 1
URL_SEED        = 2
OUTPUT_URL_SEED = 3
RETRY_INFO      = 10

#file_type
VIDEO           = 0
AUDIO           = 1
TORRENT         = 3
OTHER_FILE      = 4

error_json = ''' { "jsonrpc": "2.0", "id": 1, "method": "finish_task", "params": { "error_code": 0, "message": ""} } '''

invalid_torrent =  "This file is neither Torrent nor Metalink file. Skipping"

re_torrent_file_number = "(\d+)\|(\./.*.)\n.*\(([\d,]+)\)"

InputData = namedtuple('InputData', ['location', 'hash_data'])

def process_dbpc(config):
    config = config.get('dbpc', None)
    host = config.get('host', '192.168.1.146')
    port = config.get('port', 5800)
    service = config.get('service', 'thunder1.0')
    component = config.get('component', 'downloader')
    send_interval = config.get('interval', 120)
    return dbpc(host, port, service, component, send_interval)

def cleaner(etc_data):
    config = json.loads(etc_data)
    downloader_path = config.get('download_dir', '/tmp/downloader')
    clean_dirs = [downloader_path]
    clean_time = config.get('clean_time', 48)*3600
    while True:
        try:
            for clean_dir in clean_dirs:
                dirs = os.listdir(clean_dir)
                new_dirs = [os.path.join(clean_dir, d_) 
                        for d_ in dirs if os.path.isdir(os.path.join(clean_dir, d_))]

                current_time = int(time.time())
                for d_ in new_dirs:
                    m_time = os.path.getmtime(d_)
                    if (current_time - m_time) > clean_time:
                        delete_path(d_)
        except OSError:
            #this case just happends in the dir has been deleted
            pass
        except Exception:
            traceback.print_exc()
            pass
                         
        finally:
            time.sleep(3600)

class Retry(object):
    default_exceptions = (Exception)

    def __init__(self, tries, exceptions=None, delay=0):
        """
        Decorator for retrying function if exception occurs
        tries -- num tries
        exceptions -- exceptions to catch
        delay -- wait between retries
        """
        self.tries = tries
        if exceptions is None:
            exceptions = Retry.default_exceptions
        self.exceptions = exceptions
        self.delay = delay

    def __call__(self, f):
        def fn(*args, **kwargs):
            exception = None
            for _ in range(self.tries):
                try:
                    return f(*args, **kwargs)
                except self.exceptions, e:
                    time.sleep(self.delay)
                    exception = e
            # if no success after tries, raise last exception
            raise exception
        return fn

#this is lambda for judge has_key data
keys_value = lambda info_data, key1, key2:\
        info_data[key1][key2]\
        if info_data.get(key1, None) is not None\
        and info_data.get(key1, None).get(key2, None) is not None\
        else None


@Retry(3, 2)
def get_urlfiletype(url):
    get_url_type_cmd = ''' wget -S --spider '%s' -T 100 -t 3 ''' %url
    (status, output) = commands.getstatusoutput(get_url_type_cmd)
    output_list = output.split('\n')
    for i in output_list:
        if i.find("Content-Type") >=0:
            return  i.split(":")[1].split("/")[1]

@Retry(3, 2)
def create_dir(path):
    os.makedirs(path)

@Retry(3, 2)
def delete_file(file_path):
    if os.path.exists(file_path):
        os.remove(file_path)

def delete_path(path):
    if os.path.exists(path):
        ret = os.system("rm -rf %s" % pipes.quote(path))
        if ret:
            raise Exception("delete path error, cmd ret=%d" % ret)


#recording the file_list
def trans2json(external_id, key, k, v):
    if external_id is None:
        external_id = 'None'
    try:
        js = {"action":key, k:v}
        sjs = json.dumps(js)
        return 'normal'+ '#' + external_id + '#' + sjs 
    except Exception, msg:
        raise Exception('trans to json failed [%s]' %(msg))

#return all file in 
def traverse_folder(rootpath):
    return list(os.path.join(root, file_path.encode('utf-8')\
            if isinstance(file_path, unicode) else file_path)\
            for root, dirs, files in os.walk(rootpath)  for file_path in files )

def call_subprocess(args):
    fd = subprocess.Popen(args, stdout=PIPE, stderr=PIPE, shell=True)
    while fd.poll() is None:
        time.sleep(1)
    output, err = fd.communicate()
    return fd.poll(), output, err

def judge_torrent(bt_path):
    args = "aria2c -S %s" % (pipes.quote(bt_path))
    ret, output = commands.getstatusoutput(args)
    if ret: 
        raise Exception("call aria2c error, not install or other")
    return output

@Retry(3, 2)
def mv_file(old, new):
    shutil.move(old, new)

@Retry(3, 2)
def download_swift_file(swift_location, remote_path, download_path):
    container = re.search(r'([-_\d]+/)', remote_path).group(0)
    path = remote_path.replace(container, "")
    container = container.replace("/", "")
    args = "%s/swift download %s %s -o %s " % (
            pipes.quote(swift_location),
            pipes.quote(container), pipes.quote(path),
            pipes.quote(download_path)
            )
    print "swift download cmd is %s" % args
    ret, output, err = call_subprocess(args)
    if ret or err:
        raise dt_error(ERR_UPLOAD, "swift download failed, need process: [%s]" % str(err))
'''
    upload need todo

'''

def get_hash_type(task_info):
    external_id, hash_data, task_type, priority = None, None, None, None
    try:
        json_data = json.loads(task_info)
        json_data = json_data.get('params')
        external_id = json_data.get('external_id', None)
        priority = json_data.get('priority', 'low')
        if 'url' in json_data and 'seed_file' in json_data:
            if len(json_data.get('seed_file').get('hash', "")) is not 0:
                hash_data = json_data.get('seed_file').get('hash')
                task_type = URL_SEED
            else:
                hash_data = json_data.get('url').get('hash')
                task_type = OUTPUT_URL_SEED
        elif 'seed_file' in json_data:
            hash_data = json_data.get('seed_file').get('hash')
            task_type = SEED_FILE
        elif 'url' in json_data:
            hash_data = json_data.get('url').get('hash')
            task_type = URL_FILE
        else:
            pass
    finally:
        return external_id, hash_data, task_type, priority

def hash_log(hash_data, message):
    return hash_data + "#" + message

@Retry(3, 2)
def judge_file(file_path):
    if os.path.exists(file_path):
        cmd = "file -i %s"% (pipes.quote(file_path))
        (status, output) = commands.getstatusoutput(cmd)
        return output

@Retry(3, 2)
def judge_compressed_file(info_data, compress_sets):
    file_type = re.search(r':\s+.*/([^;]+);\s+', info_data).group(1)
    if file_type in compress_sets:
        return True
    else:
        return False

def judge_audio_video(info_data):
    if re.search(r'Video', info_data):
        return VIDEO
    elif re.search(r'Audio', info_data):
        return AUDIO
    else:
        return OTHER_FILE

def gethash_filesize(filename):
    if not os.path.isfile(filename):
        return
    myhash = hashlib.sha1()
    f = file(filename,'rb')
    file_size = os.path.getsize(filename)
    while True:
        b = f.read(8096)
        if not b :
            break
        myhash.update(b)
    f.close()
    return myhash.hexdigest(), file_size

class redis_operater(object):
    def __init__(self, redis_conn):
        self.pri_suffix = {'low':'', 'high':'#high'}
        self.redis_conn = redis_conn
    
    def redis_info_exists(self, hashkey, pri):
        try:
            nhk = hashkey + self.pri_suffix[pri]
            ret = self.redis_conn.hexists(nhk, 'task_index')
            return ret
        except Exception, msg:
            raise Exception('judge redis info exists failed[%s]' % str(msg))
    
    def find_primary_key(self, hashkey, pri):
        try:
            nhk = hashkey + self.pri_suffix[pri]
            if self.redis_conn.hexists(nhk, 'valid'):
                return nhk
            else:
                return self.redis_conn.hget(nhk, 'task_index')
        except Exception, msg:
            raise Exception('find primary hash key failed [%s]' % str(msg))
    
    def update_work_flow(self, hashkey, message, pri):
        data = {"status": message, "time": time.time()}
        data = json.dumps(data)
        try:
            primary_key = self.find_primary_key(hashkey, pri)
            if primary_key is None:
                raise
            log_key = 'task#' + str(primary_key) + '#log'
            self.redis_conn.set(log_key, data) 
        except Exception, reason:
            msg = str(reason)
            raise Exception('update work flow failed [%s]' % msg )

    #this func should be used when redis crash and all info store in redis lost
    def init_redis_info(self, hk, hashtype, pri, task):
        try:
            init_flow = {}
            init_flow['status'] = 'init'
            init_flow['time'] = time.time()
            s = json.dumps(init_flow)
            hashkey = hk + self.pri_suffix[pri]
            log_key = 'task#' + str(hashkey) + '#log'
            self.redis_conn.set(log_key, s)
            task_index = 'task#' + str(hashkey)
            self.redis_conn.hset(hashkey, 'task_index', task_index)
            self.redis_conn.hset(hashkey, 'valid', 1)
            self.redis_conn.set(task_index, task)
            self.redis_conn.lpush('task_log_list', log_key)
            hash_list = 'list#' + str(hashkey)
            self.redis_conn.lpush(hash_list, hashkey)
        except Exception,msg:
            raise Exception('init work flow failed [%s]' %(msg))
