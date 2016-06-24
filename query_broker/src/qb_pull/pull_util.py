import logging
import kombu
from kombu import Connection, Producer, Exchange, Consumer
from mylogger import *
#from syslog_wrap import *
import json
import Queue
import threading
import pull_global_vars as gv
import os
import subprocess
from subprocess import PIPE, Popen
import time
import commands
from utils import trans2json
import traceback
import httplib
from hash import Hash
# g_logger will be initlized in main thread


GENERATE_SUCESS = 0
NOT_COPYWRITE = 1
GENERATE_FAILED = 2
FILTERING = 3

g_logger = mylogger()
g_logger_info = mylogger()

HAS_NONE = 0
NOT_HAS_NONE = 1
task_queue = Queue.Queue()
task_mutex = threading.Lock()

task_logs = 'task_log_list'


class safe_lock(object):

    def __enter__(self):
        task_mutex.acquire()

    def __exit__(self, *args):
        task_mutex.release()

# TODO: more functions should to be apended

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
                    print "Retry, exception: " + str(e)
                    time.sleep(self.delay)
                    exception = e
            # if no success after tries, raise last exception
            raise exception
        return fn


def connect_rabbitmq(mq_url, queue_name):
    try:
        exchange = Exchange(queue_name, type='fanout')
        queue = kombu.Queue(queue_name, exchange, routing_key=queue_name)
        #connection = Connection('amqp://guest:guest@localhost:5672//')
        g_logger.debug(
            trans2json('connect to %s, queue is %s' % (mq_url, queue_name)))
        connection = Connection(mq_url)
        return connection
    except Exception, msg:
        #cas_system_log('error', 'connect rabbitmq failed [%s]' %(msg))
        g_logger.error(trans2json('connect rabbitmq failed [%s]' % (msg)))


@Retry(3, delay=2)
def download_file(swift_path, download_path):
    ret = -1
    err = ''
    try:
        swift_path_list = swift_path.split('/')
        container = swift_path_list[0]
        far_name = swift_path_list[-1]
        swift_name = swift_path[len(container) + 1:len(swift_path)]
        download_far_name = os.path.join(download_path, far_name)
        args = "%s/swift download %s  %s -o %s " % (
            gv.swith_path, container, swift_name, download_far_name)
        ret, _, err = popen(args)
        if ret == 0:
            g_logger.info(trans2json('download file success: %s' % args))
        else:
            g_logger.error(trans2json('swift download file failed: cmd is %s, reason is %s' % (args, err)))
    except:
        g_logger.error(trans2json("download file error, %s") %
                       traceback.format_exc())
    finally:
        return False if ret else True, download_far_name


@Retry(3, delay=2)
def upload_file(upload_path, file_path):
    ret = -1
    err = ''
    try:
        args = "%s/swift upload '%s' '%s' " % (
            gv.swith_path, upload_path, file_path)
        ret, _, err = popen(args)
        if ret == 0:
            g_logger.info(trans2json('upload file success'))
            os.remove(file_path)
        else:
            g_logger.error(trans2json('upload file failed, cmd is %s, reason is %s' % (args, err)))
    except:
        g_logger.error(trans2json(
            "delete or upload bt file %s error %s" % (file_path, traceback.format_exc())))
    finally:
        return False if ret else True


def popen(cmd):
    proc = Popen(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    ret = proc.wait()
    out, err = proc.communicate()
    return ret, out, err

#from redis_oper import writesetredis, getredismembers, deletekey, deletesetredis


def writeHashToRedis(data):
    key_hash = ''
    if data['params'].has_key('files'):
        if len(data['params']['files']) > 1:
            if data['params'].has_key('url'):
                key_hash = data['params']['url']['hash']
            else:
                ret_code, bt_file_name = download_file(
                    data['params']['seed_file']['path'], gv.file_tmpdir)
                if ret_code == True:
                    seed_file_content = ''
                    with open(bt_file_name, 'r') as fp:
                        seed_file_content = fp.read()
                    seed_file_hash = Hash(
                        filename=bt_file_name, content=seed_file_content).value
                    data['params']['seed_file']['hash'] = seed_file_hash
                    key_hash = seed_file_hash
                    try:
                        os.remove(bt_file_name)
                    except OSError:
                        g_logger.error(trans2json(
                            "delete bt file %s  error %s" % (bt_file_name, traceback.format_exc())))
            for i in data['params']['files']:
                key = "%s#%s" % (
                    data['params']['additional_info']['client_id'], key_hash)
                dna_hash = {}
                code = i['code']
                if code == GENERATE_SUCESS:
                    dna_hash[i['hash']] = None
                    dna_hash['file_path'] = i['file_path']
                elif code in (NOT_COPYWRITE, FILTERING):
                    dna_hash[i['hash']] = 0
                    dna_hash['file_path'] = i['file_path']
                elif code == GENERATE_FAILED:
                    dna_hash[i['hash']] = 3
                    dna_hash['file_path'] = i['file_path']
                writesetredis(gv.rds_conn, key, dna_hash)

# 1:copywrite  0: not copy write


def writetoresult(set_redis, client_hash, dna_hash, data, num_matchs):
    for i in set_redis:
        i_dic = eval(i)
        for k, v in i_dic.items():
            if k == dna_hash and v == None:
                result = 1 if num_matchs > 0 else 0
                i_dic[dna_hash] = result
                deletesetredis(gv.rds_conn, client_hash, i)
                writesetredis(gv.rds_conn, client_hash, i_dic)
    ret_code = judgeredis(client_hash)

    if ret_code == HAS_NONE:
        return gv.RESULT_WAIT, ()
    else:
        set_result = getredismembers(gv.rds_conn, client_hash)
        deletekey(gv.rds_conn, client_hash)
        return gv.RESULT_PUSH, set_result


def judgeredis(client_url_hash):
    set_result = getredismembers(gv.rds_conn, client_url_hash)
    if len(set_result) > 0:
        for i in set_result:
            i_dic = eval(i)
            for k, v in i_dic.items():
                if k.split('#')[0] == "file_hash" and v == None:
                    return HAS_NONE
        return NOT_HAS_NONE


def checkDnaFromRedis(data):
    for result in data['results']:
        client_id = result['extra_info']['client_id']
        hash_list = result['site_asset_id']
        url_hash = ''
        seed_hash = ''
        dna_hash = ''
        for hash_result in hash_list:
            if hash_result.split('#')[0] == 'url_hash':
                url_hash = hash_result
            elif hash_result.split('#')[0] == 'seed_hash':
                seed_hash = hash_result
            elif hash_result.split('#')[0] == 'file_hash':
                dna_hash = hash_result
        client_url_hash = "%s#%s" % (client_id, url_hash)
        client_seed_hash = "%s#%s" % (client_id, seed_hash)
        set_url = getredismembers(gv.rds_conn, client_url_hash)
        set_seed = getredismembers(gv.rds_conn, client_seed_hash)

        if len(set_url) > 0:
            return writetoresult(set_url, client_url_hash, dna_hash, data, len(result['matches']))
        elif len(set_seed) > 0:
            return writetoresult(set_seed, client_seed_hash, dna_hash, data, len(result['matches']))
        else:
            return None, ()
        '''

                      return gv.RESULT_WAIT,  None
        return gv.RESULT_PUSH,set_redis
        #copywrite
        if len(result['matches']) > 0:
            if len(set_url) > 0:
                deletekey(gv.rds_conn,client_url_hash)
                return 1
            if len(set_seed) > 0:
                deletekey(gv.rds_conn,client_seed_hash)
                return 1
        #no copy write
        else:
            if len(set_url) > 0:
                if len(set_url) == 1:
                    deletekey(gv.rds_conn,client_url_hash)
                    return 1
                deletesetredis(gv.rds_conn,client_url_hash,dna_hash)
                return 2
            if len(set_seed) > 0:
                if len(set_seed) == 1:
                    deletekey(gv.rds_conn,client_seed_hash)
                    return 1
                deletesetredis(gv.rds_conn,client_seed_hash,dna_hash)      
                return 2
                '''


def set_parent_info(data,message):
    message['params']['parent_info'] = []
    is_file_num = False
    files_size_len = 0
    if data['params'].has_key('files'):
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
def post_to_vddbdnaerror(data, code, dna_hash):
    files_size_len = 0
    if data['params'].has_key('files'):
        files_size_len = len(data['params']['files'])
    message = {}
    message['jsonrpc'] = '2.0'
    message['method'] = 'insert'
    message['id'] = 'null'
    message['params'] = {}
    message['params']['site_asset_id'] = []
    if code in gv.UNRECOGNIZED_ERROR_LIST:
        message['params']['match_type'] = 'unrecognized'
    elif code in gv.NOMATCH_ERROR_LIST:
         message['params']['match_type'] = 'no_match'
    set_parent_info(data,message)
    if (data['params'].has_key('seed_file')  and files_size_len >1) or files_size_len > 1:
        if data['params'].has_key('seed_file'):
            if data['params']['seed_file']['hash'] != None and data['params']['seed_file']['hash'] != '':
                message['params']['site_asset_id'].append(data['params']['seed_file']['hash'] + '-'+dna_hash)
        if data['params'].has_key('url'):
            if data['params']['url']['hash'] != None and data['params']['url']['hash'] != '':
                message['params']['site_asset_id'].append(data['params']['url']['hash'] + '-' + dna_hash)
        if data['params']['thunder_hash'] != None and data['params']['thunder_hash'] != '':
            message['params']['site_asset_id'].append(data['params']['thunder_hash']+'-'+dna_hash)
    else:
        if data['params'].has_key('seed_file'):
            if data['params']['seed_file']['hash'] != None and data['params']['seed_file']['hash'] != '':
                message['params']['site_asset_id'].append(data['params']['seed_file']['hash'])
        if data['params'].has_key('url'):
            if data['params']['url']['hash'] != None and data['params']['url']['hash'] != '':
                message['params']['site_asset_id'].append(data['params']['url']['hash'])
        if data['params']['thunder_hash'] != None and data['params']['thunder_hash'] != '':
            message['params']['site_asset_id'].append(data['params']['thunder_hash'])
    if dna_hash != '':
        message['params']['site_asset_id'].append(dna_hash)
    header = {"Content-Type": "application/json"}
    conn = httplib.HTTPConnection(gv.mediawise_host, int(gv.mediawise_port))
    g_logger_info.info(trans2json("post %s  to  vddb-async matches" % message))
    conn.request('POST', "/vddb-async/matches?source=auto_match", json.dumps(message), header)
