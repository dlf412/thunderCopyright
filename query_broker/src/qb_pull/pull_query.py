import json
from mysystem import *
from utils import trans2json
import pull_global_vars as gv
from pull_util import *
from hash import Hash
#from redis_oper import write2redis
import base64
import time

MEDIA_REQ_TIMEOUT = 3

def query_hash(data):
    result_hash_list = []
    start_time=time.time() 
    if data['params'].has_key('url'):
        if data['params']['url']['hash'] != None and data['params']['url']['hash'] != '':
            ret_code, result = query_vddb_async(
                data['params']['url']['hash'], data)
            if ret_code == 1:
                end_time = time.time()
                #gv.statsd_conn.timing("thunder.querybroker_qbpull", (end_time-start_time)*1000)
                return ret_code, result
            result_hash_list.append((ret_code, result))
    if data['params']['thunder_hash'] != None and data['params']['thunder_hash'] != '':
        ret_code, result = query_vddb_async(
            data['params']['thunder_hash'], data)
        if ret_code == 1:
            end_time = time.time()
            #gv.statsd_conn.timing("thunder.querybroker_qbpull", (end_time-start_time)*1000)
            return ret_code, result
        result_hash_list.append((ret_code, result))
    if data['params'].has_key('seed_file'):
        seed_file_hash = ''
        if data['params']['seed_file']['hash'] != '':
            seed_file_hash = data['params']['seed_file']['hash']
        else:
            ret_code, bt_file_name = download_file(
                data['params']['seed_file']['path'], gv.file_tmpdir)
            if ret_code:
                client_id = data['params']['additional_info']['client_id']
                with open(bt_file_name, 'rb') as fp:
                    seed_file_content = fp.read()
                seed_file_hash = Hash(
                    filename=bt_file_name, content=seed_file_content).value
                data['params']['seed_file']['hash'] = seed_file_hash
                try:
                    os.remove(bt_file_name)
                except OSError:
                    g_logger.error(trans2json(
                        "delete bt file %s  error %s" % (bt_file_name, traceback.format_exc())))
        ret_code, result = query_vddb_async(seed_file_hash, data)
        if ret_code == 1:
            end_time = time.time()
            #gv.statsd_conn.timing("thunder.querybroker_qbpull", (end_time-start_time)*1000)
            return ret_code, result
        result_hash_list.append((ret_code, result))
    if data['params'].has_key('files'):
        hash_list = []
        data_list = []
        for i in data['params']['files']:
            dna_hash = i['hash']
            hash_list.append(dna_hash)
            data_list.append(data)
        result_list = map(query_vddb_async, hash_list, data_list)
        for i in range(len(result_list)):
            if result_list[i][0] == 1:
                end_time = time.time()
                #gv.statsd_conn.timing("thunder.querybroker_qbpull", (end_time-start_time)*1000)
                return result_list[i][0], result_list[i][1]
    end_time = time.time()
    #gv.statsd_conn.timing("thunder.querybroker_qbpull", (end_time-start_time)*1000)
    return 3, None

def url_scheme(url):
    scheme = None
    parts = url.split('://', 1)
    if len(parts) >= 2:
        scheme = parts[0]
    return scheme


def query_vddb_async(req_hash, data):

    g_logger.debug(trans2json("query vddb async by hash %s" % str(req_hash)))

    mysystem = mysystem(gv.mysystem_user, gv.mysystem_passwd,
                          gv.mysystem_url, False, MEDIA_REQ_TIMEOUT, g_logger)
    uuid = data['params']['external_id']
    ret, status_listing = mysystem.query(req_hash, uuid)

    working_cnt = 0
    copyrighted_cnt = 0
    uncopyrighted_cnt = 0
    status_cnt = len(status_listing)
    for status in status_listing:
        if status['status'] == STATUS_COPYRIGHTED:
            copyrighted_cnt += 1
        if status['status'] == STATUS_UNCOPYRIGHTED:
            uncopyrighted_cnt += 1
        if status['status'] == STATUS_WORKING:
            working_cnt += 1
    # all can not check
    if ret == STATUS_UNDETECTED:
        ret_code = 2
        return ret_code, status_listing
    if status_cnt > 0:
        if copyrighted_cnt == status_cnt or working_cnt == status_cnt or uncopyrighted_cnt == status_cnt:
            ret_code = 1
            return ret_code, status_listing
    return 4, None
