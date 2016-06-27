#!/usr/bin/env python
#coding: utf-8

__author__ = (
    'weet', 'qian_linfeng@mysite.cn'
    'hxz','huang_xuezhong@mysite.cn'
)

"""
    TODO:
    =====
      1. Unit tests
"""

import os
import json
import uuid
import socket
import rfc822
from datetime import datetime
from logging.handlers import SysLogHandler
try:
    import cPickle as pickle
except:
    import pickle

import web
from web.wsgiserver import format_exc
import redis

from common import dbpc
from common import mylogger
from common.utils import url_scheme
from common.services import mysystem
from services import QueryBroker
from utils import (log_normal, log_bill, log_info,
                   LOG_DEBUG, LOG_INFO, LOG_WARN, LOG_WARNING, LOG_ERROR, LOG_CRITICAL)

# ==============================================================================
#  Load configurations from json file
# ==============================================================================
CONFIG_PATH = os.getenv('GATEWAY_CONFIG')
config = None
with open(CONFIG_PATH, 'r') as f:
    config = json.load(f)

APIKEYS            = None
APIKEY_LAST_MODIFY = 0
APIKEY_CHECK       = config['apikey']['check']
APIKEY_FILE        = config['apikey']['file']
LOG_FILE           = config['log']['file']
LOG_LEVEL          = config['log']['level'].upper()
HTTP500_DELAY      = config['http500_delay']
HTTP503_DELAY      = config['http503_delay']
DEFAULT_JSONRPC_ID = config['default_jsonrpc_id']
CACHE_MAX_AGE      = config['cache_max_age']
RETRY_AFTER        = config['retry_after']
SERVER_FLAG        = config.get('server_flag', 0) 
if SERVER_FLAG != 1:
    SERVER_FLAG = 0 
PROCESSING_RETRY   = config.get('processing_retry', False)

uploader = config['uploader']
REDIS_SERVER    = uploader['redis_server']
REDIS_LIST_NAME = uploader['redis_list_name']
MAX_LIST_LEN    = uploader['max_list_len']
PICKLE_DIR      = uploader['pickle_dir']
PICKLE_EXT      = uploader['pickle_ext']
del uploader

digest_lower = config['digest_lower']
DIGEST_TRANSFORM  = digest_lower['transform']
IGNORE_ALGORITHMS = digest_lower['ignore_algorithms']
del digest_lower

cheating = config['cheating']
CHEATING_ALL          = cheating['all']
CHEATING_FILETYPE     = cheating['file_type']
CHEATING_FILESIZE     = cheating['file_size']
CHEATING_AUDIO        = cheating['audio']
CHEATING_NO_EXT_PASS  = cheating['file_no_ext_pass']
CHEATING_NO_MATCH     = True
CHEATING_UNRECOGNIZED = True

NO_MATCH_TYPES        = [e.lower() for e in cheating.get('no_match', [])]
UNRECOGNIZED_TYPES    = [e.lower() for e in cheating.get('unrecognized', [])]
WORKING_AS_PASS       = cheating['working_as_pass']
SUSPICIOUS_MIME_TYPES = cheating['suspicious_mime_types']
SUSPICIOUS_EXTENSIONS = cheating['suspicious_extensions']
PASS_AUDIO_MIME_TYPES = cheating['pass_audio_mime_types'] 
PASS_AUDIO_EXTENSIONS = cheating['pass_audio_extensions']
del cheating

error_codes = {
    "error_params"       : 262144, # 0x40000
    "error_not_hit"      : 262148, # 0x40004
    "error_apikey"       : 262147, # 0x40003
    "error_server_error" : 327680, # 0x50000
    "error_server_busy"  : 327683  # 0x50003
}
ERROR_PARAMS       = error_codes['error_params']
ERROR_NOT_HIT      = error_codes['error_not_hit']
ERROR_APIKEY       = error_codes['error_apikey']
ERROR_SERVER_ERROR = error_codes['error_server_error']
ERROR_SERVER_BUSY  = error_codes['error_server_busy']
del error_codes

wrap_header = lambda header: ('http-'+header).replace('-', '_').upper()
headers = {
    "referer"     : "Referer",
    "last_query"  : "If-Modified-Since",
    "cur_query"   : "Date",
    "progress"    : "X-Progress",
    "client_addr" : "X-Client-Address",
    "client_id"   : "X-Client-ID",
    "file_name"   : "X-File-Name",
    "file_size"   : "X-File-Size",
    "mime_type"   : "X-Mime-Type",
    "url"         : "X-URL",
    "user_agent"  : "USER-AGENT"
}
HEADER_REFERER     = wrap_header(headers['referer'])
HEADER_LAST_QUERY  = wrap_header(headers['last_query'])
HEADER_CUR_QUERY   = wrap_header(headers['cur_query'])
HEADER_PROGRESS    = wrap_header(headers['progress'])
HEADER_CLIENT_ADDR = wrap_header(headers['client_addr'])
HEADER_CLIENT_ID   = wrap_header(headers['client_id'])
HEADER_FILE_NAME   = wrap_header(headers['file_name'])
HEADER_FILE_SIZE   = wrap_header(headers['file_size'])
HEADER_MIME_TYPE   = wrap_header(headers['mime_type'])
HEADER_URL         = wrap_header(headers['url'])
HEADER_USER_AGENT  = wrap_header(headers['user_agent'])
del wrap_header, headers

media_wise = config['vddb_async']
MEDIA_WISE_URL         = media_wise['url']
MEDIA_WISE_USER        = media_wise['user']
MEDIA_WISE_PASSWD      = media_wise['passwd']
MEDIA_WISE_ALL_MATCHES = media_wise['all_matches']
MEDIA_WISE_REQ_TIMEOUT = media_wise['req_timeout']
del media_wise

query_broker = config['query_broker']
BROKER_MQ_URL         = query_broker['mq_url']
BROKER_JSONRPC_METHOD = query_broker['jsonrpc_method']
BROKER_EXCHANGE       = query_broker['exchange']
BROKER_ROUTING_KEY    = query_broker['routing_key']
BROKER_PUB_TIMEOUT    = query_broker['publish_timeout']
del query_broker

dbpc_config = config['dbpc']
DBPC_HOST      = dbpc_config['host']
DBPC_PORT      = dbpc_config['port']
DBPC_SERVICE   = dbpc_config['service']
DBPC_COMPONENT = dbpc_config['component']
DBPC_INTERVAL  = dbpc_config['interval']
del dbpc_config

del config


HOST_NAME = socket.gethostname()
STATUS_COPYRIGHTED = 0
STATUS_UNCOPYRIGHTED = 1
STATUS_UNDETECTED = 2
STATUS_WORKING = 3

OVERALL_WORKING = 3
# Task finished
OVERALL_HAS_COPYRIGHTED = 0
OVERALL_ALL_UNDETECTED = 2
OVERALL_UNDETECTED_UNCOPYRIGHTED = 1



# ==============================================================================
#  Helper functions
# ==============================================================================
#### APIKEY things ####
def load_apikey(uuid=None):
    global APIKEY_LAST_MODIFY, APIKEYS
    last_apikey = APIKEYS
    
    with open(APIKEY_FILE, 'r') as f:
        APIKEY_LAST_MODIFY = os.stat(APIKEY_FILE).st_mtime
        data = json.load(f)
        APIKEYS = data.values()
        log_normal(logger, {
            'action': 'load-apikey-from-file',
            'info': {
                'file': APIKEY_FILE,
                'file_modify': os.stat(APIKEY_FILE).st_mtime,
                'apikey_last_modify': APIKEY_LAST_MODIFY,
                'last_apikeys': last_apikey,
                'apikeys': APIKEYS
            }
        }, LOG_INFO, uuid=uuid)
        return APIKEYS


def get_apikey():
    if os.stat(APIKEY_FILE).st_mtime <= APIKEY_LAST_MODIFY:
        return APIKEYS

    return load_apikey()


#### Wrapper ####
def wrap_result(req_id, overall, listing):
    """
    result
    ======
    status：0:copyrighted, 1:uncopyrighted, 2:undetected, 3:working.


    Examples:
    =========
      {
          "jsonrpc": "2.0",
          "result":
           {
             "overall": overall,
             "listing": listing  /// <Optional>
           },
           "id": 1
      }
    """
    result = { 'overall': overall }
    # if overall != 2 and overall != 3:
    #     # 2 -> not all undetected
    #     # 3 -> not has working
    #     result['listing'] = listing
    # else:
    if overall == OVERALL_HAS_COPYRIGHTED:
        lst_len = len(listing)
        copyrighted_cnt = 0
        for item in listing:
            status = item['status']
            if status == STATUS_COPYRIGHTED:
                copyrighted_cnt += 1
        if 0 < copyrighted_cnt < lst_len:
            result['listing'] = listing

    msg = json.dumps({
        'jsonrpc' : '2.0',
        'id'      : req_id,
        'result'  : result
    })
    return msg


def wrap_error(code, message, data):
    """
    Error:
    ======
    :param code: Error code, See: <Error Code List>
    :param message：Error message (String)
    :param data: If parameter error, this will be an array of error parameter names.
                 Example -> ["key"] means `key` not given or invalid.


    Error Code List:
    ================
    Used by gateway:
    ----------------
    0x10001 (65537): Parameter error, say thunder has invalid query parameter.
    0x10002 (65538): If query seed file by hash and hash not hit, then you should submit seed file to query.
    0x10003 (65539): apikey error
    0x20001 (131073): Internal Server Error(HTTP 500)
    0x20002 (131074): Server busy

    Example:
    ========
    {
          "jsonrpc": "2.0",
           "error":
           {
               "code":131074,
               "message": "Server is busy",
               "data": 10
           },
           "id": null
    }
    """
    msg = json.dumps({
        'jsonrpc': '2.0',
        'id': None,
        'error': {
            'code'    : code,
            'message' : message,
            'data'    : data
        }
    })
    return msg


# ==============================================================================
#  Main class
# ==============================================================================
class Query(object):
    """
    Request:
    =======
      See::
        * `Query.__init__()`
        * `Query.GET()`
        * `Query.POST()`

    Response:
    =========
      See::
        * `wrap_result()`
        * `wrap_error()`
    """

    def __init__(self):
        """
        Headers:
        ========
        Header-Name	Type	Required	 	Description
        --------------------------------------------------------
        Referer		String	N	 		Referential url. If seed-file given this is not required.
        X-Progress	String	N	 		The rate of progress of target download file.
        X-Client-ID	String	Y			Thunder client id
        X-File-Name	String	given url -> Y,
                                given seed-file -> N	The file name of target download file (UTF-8 encoded). If seed-file given this is not required.
        X-File-Size	String	given url -> Y,
                                given seed-file -> N	The size of target download file. If seed-file given this is not required.
        X-Mime-Type	String	N		        The mime-type of target download file. If seed-file given this is not required.
        X-URL		String	Y			url or seed-file-path

        GetParams:params
        ==========
        Parameter	 Type	 Required	Description
        --------------------------------------------------------
        key		 String	 Y	 	apikey given by mysite.cn must keep it secret.
        hash		 String	 N	 	file_private_id (hash value generate by thunder client)
        digest		 String	 Y	 	The digest of url or seed-file
        digest-algorithm String	 Y	 	Digest algorithm

        Steps:
        ======
          * Parse query_string
          * Auth apikey
          * Parse HTTP headers
          * Check parameters
          * Parse MIME type

        """

        self.uuid = uuid.uuid1().hex

        env = web.ctx.env

        self.error_code = None
        self.error_msg = ''
        self.error_data = []

        params = web.input()
        self.key       = params.get('key', None)
        self.hash      = params.get('hash', None)
        self.digest    = params.get('digest', None)
        self.algorithm = params.get('digest-algorithm', None)

        if not self.authenticated:
            log_normal(logger, {
                'action': 'request-unauthorized',
                'info': {
                    'message': 'unauthorized....',
                    'apikey': self.key
                }
            }, LOG_INFO, uuid=self.uuid)
            raise Unauthorized(wrap_error(ERROR_APIKEY, 'APIKEY Error', ['key']))

        self.referer     = env.get(HEADER_REFERER, None)
        self.last_query  = env.get(HEADER_LAST_QUERY, None)
        self.cur_query   = env.get(HEADER_CUR_QUERY, None)
        self.progress    = env.get(HEADER_PROGRESS, None)
        self.client_addr = env.get(HEADER_CLIENT_ADDR, None)
        self.client_id   = env.get(HEADER_CLIENT_ID, None)
        self.file_name   = env.get(HEADER_FILE_NAME, None)
        self.file_size   = env.get(HEADER_FILE_SIZE, None)
        self.mime_type   = env.get(HEADER_MIME_TYPE, None)
        self.url         = env.get(HEADER_URL, None)
        self.user_agent  = env.get(HEADER_USER_AGENT,None)
        self.request_time = None
        # PRD Section 3.4 requirement.
        try:
            log_info(logger_info, {
                'action': 'show-request-env',
                'info': {
                    # From: Query String
                    'key'          : self.key,
                    'hash'         : self.hash,
                    'digest'       : self.digest,
                    'algorithm'    : self.algorithm,
                    # From: Headers
                    'referer'      : self.referer,
                    'client_id'    : self.client_id,
                    'client_addr'  : self.client_addr,
                    'progress'     : self.progress,
                    'file_name'    : self.file_name,
                    'file_size'    : self.file_size,
                    'mime_type'    : self.mime_type,
                    'url'          : self.url,
                    'user_agent'   : self.user_agent,
                    'request_time' : datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            }, uuid=self.uuid)
            self.request_time = datetime.now()
        except UnicodeDecodeError:
            self.error_code = ERROR_PARAMS
            self.error_msg = 'Parameter encoding unexcept!'
            self.error_data.extend(['Header:Referer',
                                    'Header:X-File-Name',
                                    'Header:X-URL'])
            message = wrap_error(self.error_code, self.error_msg, self.error_data)
            log_normal(logger, {
                'action': 'bad-request',
                'info': message
            }, LOG_WARN, uuid=self.uuid)
            raise web.BadRequest(message)

        try:
            for k in ('last_query', 'cur_query'):
                field = getattr(self, k)
                if field:
                    setattr(self, k, datetime(*rfc822.parsedate(field)[:-3]))
        except TypeError:
            self.error_code = ERROR_PARAMS
            self.error_msg = 'If-Modified-Since or Date error!'
            self.error_data.append('Header:If-Modified-Since')
            self.error_data.append('Header:Date')

        if self.file_size:
            try:
                int(self.file_size)
            except ValueError:
                self.error_code = ERROR_PARAMS
                self.error_msg = 'X-File-Size is not integer!'
                self.error_data.append('X-File-Size')

        if (not self.client_id
            or not self.digest
            or not self.algorithm):
            # Get parameter or header missing
            self.error_code = ERROR_PARAMS
            self.error_msg = 'Parameter not enough!'

        for filed, tag in [
                (self.client_id   , 'X-Client-ID'),
                (self.digest      , 'digest'),
                (self.algorithm   , 'digest-algorithm')]:
            if not filed:
                self.error_data.append(tag)

        self.is_seed = not self.url or self.url.strip().startswith("file://")
        self.ext = None
        if self.file_name:
            parts = self.file_name.rsplit('.', 1)
            if len(parts) >= 2:
                self.ext = parts[-1]

        self.scheme = url_scheme(self.url)

        # If config matched transform the digest(hashinfo) to lower case
        if (DIGEST_TRANSFORM
            and self.algorithm not in IGNORE_ALGORITHMS
            and self.digest):
            self.digest = self.digest.lower()


    @property
    def authenticated(self):
        return (not APIKEY_CHECK) or (self.key in get_apikey())
        
    def check_cheating(self):
        if CHEATING_ALL:
            return IMD_RESULT
        if CHEATING_FILESIZE > 0 and self.file_size is not None:
            file_size = int(self.file_size)
            if file_size < CHEATING_FILESIZE:
                return IMD_RESULT
        if CHEATING_AUDIO:
            if ((self.mime_type and self.mime_type in PASS_AUDIO_MIME_TYPES)
                or (self.ext and self.ext in PASS_AUDIO_EXTENSIONS)):
                return IMD_RESULT
        if CHEATING_FILETYPE:
            if self.mime_type and self.mime_type not in SUSPICIOUS_MIME_TYPES:
                # If mime-type not suspicious. Then check extension
                if not self.ext and CHEATING_NO_EXT_PASS:
                    return IMD_RESULT
                if self.ext and self.ext not in SUSPICIOUS_EXTENSIONS:
                    return IMD_RESULT
        if CHEATING_NO_MATCH and self.url:
            url = self.url.split(":")[0] + "://"
            if url.lower() in NO_MATCH_TYPES:
                return IMD_RESULT
        if CHEATING_UNRECOGNIZED and self.url:
            url = self.url.split(":")[0] + "://"
            if url.lower() in UNRECOGNIZED_TYPES:
                return IMD_RESULT_UNDETECTED 
        return None


    def GET(self):
        """
        Input:
        ======
        GET /query?key=thunder-client&url=http://host/video.mp4&hash=hash-code&f=0 HTTP/1.1
        User-Agent: thunder-windows-client 7.0.x
        ### Update required ###
        X-Thunder-Client: some-pirate-client
        X-Download-Protocol: http
        X-Download-Type: video/mp4

        Steps:
        ======
          * Check params
          * Cheating Case
          * Decode `seed_file`
          * Query mysystem
          * Push query broker if error and has `url`
          * Return result

        """
        # Normal URL File-name and file-size are required!
        # if not self.is_seed and not (self.file_name and self.file_size):
        #     self.error_code = ERROR_PARAMS
        #     self.error_msg = 'Parameter not enough!'
        #     self.error_data.append('X-File-Name')
        #     self.error_data.append('X-File-Size')

        if self.error_code:
            message = wrap_error(self.error_code, self.error_msg, self.error_data)
            log_normal(logger, {
                'action': 'bad-request',
                'info': message
            }, LOG_WARN, uuid=self.uuid)
            raise web.BadRequest(message)

        log_bill(logger_bill, {
            'action': 'get-request',
            'client_id': self.client_id,
            'client_addr': self.client_addr,
            'method': 'GET',
            'hash': self.hash,
            'url': self.url
        }, uuid=self.uuid)

        result = self.check_cheating()
        if result is not None:
            log_normal(logger, {
                'action': 'return-GET-result',
                'tag': 'filter case',
                'client_id' : self.client_id,
                'digest'    : self.digest,
                'user_agent' : self.user_agent, 
                'info': result
            }, LOG_INFO, uuid=self.uuid)
            return result

        overall = None
        if self.hash:
            self.hash = 'thunder_hash#%s' % self.hash
            overall, listing = mw.query(self.hash, self.uuid)

        hash_prefix = 'seed_hash' if self.is_seed else 'url_hash'
        url_hash = '%s#%s' % (hash_prefix, self.digest)
        if overall is None:
            overall, listing = mw.query(url_hash, self.uuid)

        if overall == OVERALL_WORKING:
            web.header('Cache-Control', 'no-cache')
        elif overall is not None:
            web.header('Cache-Control', 'public, max-age=%d' % CACHE_MAX_AGE)
        elif not WORKING_AS_PASS:
            # Two cases: 1. hash from client, 2. hash from gateway.
            web.header('Cache-Control', 'no-cache')
            if self.is_seed:
                web.header('Retry-After' , '%d' % RETRY_AFTER)
                web.header('X-Processing-Retry', '%d' % int(PROCESSING_RETRY))
                result = wrap_error(ERROR_NOT_HIT, 'hash not hit.', [])
                log_normal(logger, {
                    'action': 'hash-not-hit',
                    'info': result
                }, LOG_INFO, uuid=self.uuid)
                return result
            else:
                url_data = {
                    'location': self.url,
                    'hash': url_hash,
                }
                qb.push(self.progress,
                        self.client_id,
                        self.client_addr,
                        self.digest,
                        self.algorithm,
                        self.file_name,
                        self.file_size,
                        HOST_NAME,
                        self.referer,
                        self.hash,
                        self.mime_type,
                        self.scheme,
                        self.uuid,
                        self.ext,
                        SERVER_FLAG,
                        url=url_data)
                overall = OVERALL_WORKING

        result = wrap_result(DEFAULT_JSONRPC_ID, overall, listing)
        if overall == OVERALL_WORKING or overall is None:
            if WORKING_AS_PASS:
                result = IMD_RESULT
            else:
                web.header('Retry-After' , '%d' % RETRY_AFTER)
                web.header('X-Processing-Retry', '%d' % int(PROCESSING_RETRY))

        tag = 'working_as_pass=%r,overall=%r' % (WORKING_AS_PASS, overall)
        request_interval = (datetime.now()-self.request_time).seconds
        log_normal(logger, {
            'action': 'return-GET-result',
            'client_id' : self.client_id,
            'user_agent' : self.user_agent,
            'digest'     : self.digest,
            'request_interval' : str(request_interval),
            'tag': tag,
            'info': result
        }, LOG_INFO, uuid=self.uuid)
        return result


    def POST(self):
        """
        Input:
        ======
        POST /query?key=thunder-client&hash=hash-code&f=0 HTTP/1.1
        Content-Type: application/json-rpc
        Content-Length: xxx
        User-Agent: thunder-windows-client 7.0.x
        X-Thunder-Client: some-pirate-client
        X-Download-Protocol: http
        X-Download-Type: video/mp4

        {
            "jsonrpc": "2.0",
            "id": "1",
            "method": "query",
            "params":
            {
              "seed_file":"torrent content, base64 encoded text",
            }
        }

        PostForm:
        ========
        :param seed_file: Seed file(.torrent) content.

        Steps:
        ======
          * Check params
          * Decode `seed_file`
          * Push query broker
          * Return result

        """
        
        postform = json.loads(web.data())
        jsonrpc_id = postform.get('id', DEFAULT_JSONRPC_ID)
        params = postform.get('params', {})
        seed_file = params.get('seed_file', None)

        if not seed_file:
            self.error_code = ERROR_PARAMS
            self.error_msg = '`seed_file` required!'
            self.error_data.append('seed_file')

        # Error, return
        if self.error_code:
            message = wrap_error(self.error_code, self.error_msg, self.error_data)
            log_normal(logger, {
                'action': 'bad-request',
                'info': {
                    'message': message
                }
            }, LOG_WARN, uuid=self.uuid)
            raise web.BadRequest(message)

        log_bill(logger_bill, {
            'action'      : 'post-request',
            'client_id'   : self.client_id,
            'client_addr' : self.client_addr,
            'method'      : 'POST',
            'hash'        : self.hash,
            'url'         : self.url
        }, uuid=self.uuid)
        
        result = self.check_cheating()
        if result is not None:
            log_normal(logger, {
                'action': 'return-POST-result',
                'tag': 'filter case',
                'info': {
                    'result': result,
                    'mime-type': self.mime_type,
                    'ext': self.ext,
                }
            }, LOG_INFO, uuid=self.uuid)
            return result

        overall = None
        if self.hash:
            self.hash = 'thunder_hash#%s' % self.hash
            overall, listing = mw.query(self.hash, self.uuid)

        seed_file_hash = 'seed_hash#%s' % self.digest
        if overall is None:
            overall, listing = mw.query(seed_file_hash, self.uuid)
            
        if overall == OVERALL_WORKING:
            web.header('Cache-Control', 'no-cache')
        elif overall is not None:
            web.header('Cache-Control', 'public, max-age=%d' % CACHE_MAX_AGE)
        elif not WORKING_AS_PASS:
            # Two cases: 1. hash from client, 2. hash from gateway.
            web.header('Cache-Control', 'no-cache')
            time_now_str = datetime.now().strftime("%M-%S")
            file_name = '%s_%s.torrent' % (time_now_str, self.uuid)
            file_path = os.path.join(PICKLE_DIR, file_name)
            container = datetime.now().strftime('%Y-%m-%d_%H')
            remote_path = '%s/%s' % (container, file_path)
            log_normal(logger, {
                'action': 'upload-to-swift',
                'info': {
                    'message': 'ok.',
                    'remote_path': remote_path
                }
            }, LOG_INFO, uuid=self.uuid)
            url_data = {
                'location': self.url,
                'hash': None,
            }
            seed_file_data = {
                'path': remote_path,
                # base64 str
                'hash': seed_file_hash
            }
            task_info = ((self.progress,
                          self.client_id,
                          self.client_addr,
                          self.digest,
                          self.algorithm,
                          self.file_name,
                          self.file_size,
                          HOST_NAME,
                          self.referer,
                          self.hash,
                          self.mime_type,
                          'torrent',
                          self.uuid,
                          self.ext,
                          SERVER_FLAG),
                         {'url': url_data, 'seed_file': seed_file_data})
            # Push redis server
            r = redis.Redis(REDIS_SERVER)
            list_len = r.llen(REDIS_LIST_NAME)
            if list_len > MAX_LIST_LEN:
                log_normal(logger, {
                    'action': 'redis-list-full',
                    'info': {
                        'max_list_len': MAX_LIST_LEN
                    }
                }, LOG_WARN, uuid=self.uuid)
                raise ServiceUnavailable(wrap_error(ERROR_SERVER_BUSY, "Server Busy", HTTP503_DELAY))
            
            pickle_path = os.path.join(PICKLE_DIR, '%s_%s.%s' % (time_now_str, self.uuid, PICKLE_EXT))
            with open(pickle_path, 'wb') as f:
                pickle.dump((task_info, file_path, container, seed_file), f)
            r.lpush(REDIS_LIST_NAME, pickle_path)
            overall = OVERALL_WORKING

        result = wrap_result(jsonrpc_id, overall, listing)
        if overall == OVERALL_WORKING or overall is None:
            if WORKING_AS_PASS:
                result = IMD_RESULT
            else:
                web.header('Retry-After' , '%d' % RETRY_AFTER)
                web.header('X-Processing-Retry', '%d' % int(PROCESSING_RETRY))

        tag = 'working_as_pass=%r,overall=%r' % (WORKING_AS_PASS, overall)
        log_normal(logger, {
            'action': 'return-POST-result',
            'client_id' : self.client_id,
            'user_agent' : self.user_agent, 
            'tag': tag,
            'info': result
        }, LOG_INFO, uuid=self.uuid)
        return result


# ==============================================================================
#  HTTP Error handlers
# ==============================================================================
class ServiceUnavailable(web.HTTPError):
    def __init__(self, message=None):
        status = "503 Service Unavailable"
        headers = {'Content-Type': 'application/json'}
        web.HTTPError.__init__(self, status, headers, message)


class Unauthorized(web.Unauthorized):
    def __init__(self, message=None):
        if message:
            self.message = message
        web.Unauthorized.__init__(self)


def internalerror():
    """ HTTP 500 handler"""
    # err_msg = wrap_error(ERROR_SERVER_ERROR,'Server Error 500', HTTP500_DELAY)
    log_normal(logger, {
        'action': 'server-internal-error',
        'error': format_exc()
    }, LOG_ERROR)

    # return web.internalerror(err_msg)
    result = wrap_result(DEFAULT_JSONRPC_ID, OVERALL_WORKING, [])
    web.header('Retry-After' , '%d' % RETRY_AFTER)
    web.header('X-Processing-Retry', '%d' % int(PROCESSING_RETRY))
    return web.OK(result)


urls = (
    '/copyrighted', 'Query',
    '/identified', 'Query'
)

app = web.application(urls, globals())
app.internalerror = internalerror


# ==============================================================================
#  Init things
# ==============================================================================
## Init Logger
logger = mylogger.mylogger()
logger_bill = mylogger.mylogger()
logger_info = mylogger.mylogger()
logger.init_logger('gateway', LOG_LEVEL, LOG_FILE, SysLogHandler.LOG_LOCAL1) # For debug
logger_bill.init_logger('gateway-bill', LOG_LEVEL, LOG_FILE, SysLogHandler.LOG_LOCAL0) # For Bill
logger_info.init_logger('gateway-info', LOG_LEVEL, LOG_FILE, SysLogHandler.LOG_LOCAL2) # For Info

log_normal(logger, {
    'action': 'init-logger-ok',
    'info': {
        'level': LOG_LEVEL,
    }
}, LOG_INFO)

IMD_RESULT = wrap_result(DEFAULT_JSONRPC_ID, OVERALL_UNDETECTED_UNCOPYRIGHTED, [])
IMD_RESULT_UNDETECTED = wrap_result(DEFAULT_JSONRPC_ID, OVERALL_ALL_UNDETECTED, [])

## Init APIKEY from file
load_apikey()
## Make task info directory
if not os.path.exists(PICKLE_DIR):
    os.mkdir(PICKLE_DIR)

## Init QueryBroker and mysystem
mw = mysystem(MEDIA_WISE_USER, MEDIA_WISE_PASSWD,
               MEDIA_WISE_URL, MEDIA_WISE_ALL_MATCHES, MEDIA_WISE_REQ_TIMEOUT,
               logger)
if not WORKING_AS_PASS:
    qb = QueryBroker(logger, BROKER_ROUTING_KEY, BROKER_EXCHANGE,
                     BROKER_PUB_TIMEOUT, BROKER_MQ_URL)


if __name__ == '__main__':
    app.run()
else:
    t_dbpc = dbpc.dbpc(DBPC_HOST, DBPC_PORT,
                       DBPC_SERVICE, DBPC_COMPONENT,
                       DBPC_INTERVAL)
    t_dbpc.start()
    app = app.wsgifunc()
