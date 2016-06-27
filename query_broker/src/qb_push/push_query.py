import json
from mysystem import *
import push_global_vars as gv
from push_util import *
import time
from utils import trans2json
#from hash import Hash


def url_scheme(url):
    scheme = None
    parts = url.split('://', 1)
    if len(parts) >= 2:
        scheme = parts[0]
    return scheme


def query_vddb_async(req_hash, data):
    g_logger.debug(trans2json("query vddb async by hash %s" % str(req_hash)))
    
    mysystem = mysystem(gv.mysystem_user, gv.mysystem_passwd,
                          gv.mysystem_url, False,3, g_logger)
    uuid = data['params']['external_id']
    ret, status_listing = mysystem.query(req_hash, uuid)
    return ret, status_listing
    '''
    working_cnt = 0
    copyrighted_cnt = 0
    uncopyrighted_cnt = 0
    status_cnt = len(status_listing)
    for status in status_listing:
        if status['status'] == 0:
            copyrighted_cnt += 1
        if status['status'] == 1:
            uncopyrighted_cnt += 1
        if status['status'] == 3:
            working_cnt += 1
    # all can not check ,
    if ret == 2:
        ret_code = 2
        return ret_code, status_listing
    if status_cnt > 0:
        if copyrighted_cnt == status_cnt or working_cnt == status_cnt or uncopyrighted_cnt == status_cnt:
            ret_code = 1
            return ret_code, status_listing
    return 4, None
    '''

def query_hash(data):
    if data['params'].has_key('url'):
        if data['params']['url']['hash'] != None and data['params']['url']['hash'] != '':
            ret_code, result = query_vddb_async(
                data['params']['url']['hash'], data)
            return ret_code, result
    if data['params']['thunder_hash'] != None and data['params']['thunder_hash'] != '':
        ret_code, result = query_vddb_async(
            data['params']['thunder_hash'], data)
        return ret_code, result
    if data['params'].has_key('seed_file'):
        seed_file_hash = ''
        if data['params']['seed_file']['hash'] != '':
            seed_file_hash = data['params']['seed_file']['hash']
            ret_code, result = query_vddb_async(seed_file_hash, data)
            return ret_code, result
    return None, []
