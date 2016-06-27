#!/usr/bin/env python
#coding: utf-8

import json
import subprocess
import hashlib
import base64
from datetime import datetime
import chardet

digest = None

def trans2json(s, action=None, external_id=None):
    try:
        js = {}
        js['msg'] = s
        if action is not None:
            js['action'] = action
        if external_id is not None:
            js['external_id'] = external_id
        if digest is not None:
            js['digest'] = digest
        sjs = json.dumps(js)
        return 'normal'+ '#' + sjs
    except Exception, msg:
        raise Exception('trans to json failed [%s]' %(msg))

def insert_vddb_tmp(url, hash_values, retry=2):
    import requests
    ''' Insert tmp result to Result Management. '''

    hash_values = [v for v in hash_values if v]
    params = {
        'source': 'manual_tmp'
    }
    data = json.dumps({
        'jsonrpc': '2.0',
        'id': None,
        'method': 'insert',
        'params': {
            'site_asset_id': hash_values,
            'match_type': 'no_match'
        }
    })
    logs = []
    resp = None
    while retry > 0:
        try:
            resp = requests.post(url, params=params, data=data, timeout=10)
        except requests.RequestException as e:
            logs.append(e)
        retry = retry-1 if (resp is None or resp.status_code != 200) else 0
    return resp, logs


def convert_field(value):
    if isinstance(value, unicode):
        return value.encode('utf8')
    elif isinstance(value, datetime):
        return value.strftime('%Y-%m-%d %H:%M:%S')
    return value


def execute_sql(conn, sql, args, fetch=False, commit=True):
    cur = conn.cursor()
    sql_args = [convert_field(arg) for arg in args]
    cur.execute(sql, sql_args)

    rows = None
    if fetch:
        conn.commit()
        rows = cur.fetchall()
    elif commit:
        conn.commit()
    cur.close()
    return rows
    
def execute(cmd):
    proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    ret = proc.wait()
    out, err = proc.communicate()
    return ret, out, err

def url_scheme(url):
    scheme = None
    if url:
        if url.startswith('magnet:'):
            scheme = 'magnet'
        else:
            parts = url.split('://', 1)
            if len(parts) >= 2:
                scheme = parts[0]
    return scheme

class HashError(Exception):
    def __str__(self):
        return str(self.__dict__)

class Hash(object):
    """
    ::Reference: http://seals.mysite.cn/trac/vdna/wiki/mysite_thunder/thunder_hash

    Usage:
    ======
        >>> print Hash(url="http://www.baidu.com/dl/some.mp4").value
        76709133b1bcd884611186bdefcdbe2e235ef104
        >>> print Hash(url="http://www.baidu.com/dl/some.mp4").protocol
        http

        >>> print Hash(content="TEST_SEED_FILE_CONTENT").value
        fda6c4d1938082c32afea756bdaf1e031349c23a
        >>> print Hash(content="TEST_SEED_FILE_CONTENT").protocol
        torrent
    """

    def __init__(self, url=None, content=None):
        if url is None and content is None:
            raise ValueError('URL or seed_content required!')

        if url:
            self.arg = url
            self.prefix = 'url_hash'
            self.protocol = url_scheme(url)
            if self.protocol is None:
                ex = HashError()
                ex.message = "Hash url invalid!"
                ex.url = url
                raise ex
        else:
            self.arg = content
            self.prefix = 'seed_hash'
            self.protocol = 'torrent'

        # self.protocol = url.split('://', 1)[0].lower() if url else filename.rsplit('.', 1)[-1].lower()
        # self.prefix = 'url_hash' if url else 'seed_hash'
        self.url = url
        self.content = content


    @property
    def value(self):
        """ Cached property """

        if hasattr(self, '_value'):
            return self._value

        self._value = '%s#%s' % (self.prefix, self.digest)
        return self._value


    @property
    def digest(self):
        if hasattr(self, '_digest'):
            return self._digest

        hash_type_dict = {
            'ftp'     : Hash.sha1_hex,
            'http'    : Hash.sha1_hex,
            'thunder' : Hash.hash_thunder,
            'ed2k'    : Hash.hash_ed2k,
            'magnet'  : Hash.hash_magnet,
            'torrent' : Hash.hash_bt,
        }
        func = hash_type_dict.get(self.protocol.lower(), Hash.sha1_hex)
        try:
            self._digest = func(self.arg)
        except IndexError:
            self._digest = Hash.sha1_hex(self.arg)

        return self._digest


    @staticmethod
    def sha1_hex(s):
        if type(s) == unicode:
            s = s.encode('utf-8')
        return hashlib.sha1(s).hexdigest()

    @staticmethod
    def hash_bt(b64_content):
        bin_content = base64.b64decode(b64_content)
        return Hash.sha1_hex(bin_content)

    @staticmethod
    def hash_ed2k(uri):
        return uri.split('|')[4]

    @staticmethod
    def origin_uri(uri):
        uri = uri.strip()
        t_hash = uri[10:-1] if uri.endswith('/') else uri[10:]
        return base64.b64decode(t_hash)[2:-2]


    @staticmethod
    def hash_thunder(uri):
        origin_uri = Hash.origin_uri(uri)
        scheme = url_scheme(origin_uri)
        if scheme == 'ed2k':
            return Hash.hash_ed2k(origin_uri)
        else:
            return Hash.sha1_hex(origin_uri)

    @staticmethod
    def hash_magnet(uri):
        if uri.startswith('magnet:?xt=urn:btih:'):
            return uri[20:60]
        return Hash.sha1_hex(uri)


if __name__ == '__main__':
    import sys
    import httplib
    import time
    USAGE = '''Generate digest by URL:
    Usage: %s [URL]'''
    if len(sys.argv) < 2:
        print >> sys.stderr, 'Argument not enough'
        print '-' * 20
        print USAGE % sys.argv[0]
        sys.exit(-1)

    url = sys.argv[1]
    h = Hash(url=url)

    print '-' * 40
    print h.digest
    digest = h.digest
    digest_algorithm = ""
    if h.protocol == 'thunder':
        url=Hash.origin_uri(url)
        digest_algorithm = "thunder-"
        print url
        print digest_algorithm

    if url[0:8]=="magnet:?":
       digest_algorithm += "magnet"
    elif url[0:7]=="ed2k://":
       digest_algorithm += "ed2k"
    else:
       digest_algorithm += "sha1"

    api_key = "this-is-TMP-apikey"
    header = { 'Content-type' : 'application/x-www-form-urlencoded', \
    'User-Agent' : 'thunder 7.0.1', \
    'X-Client-ID' : 'client_id123456', \
    'X-File-ID' : 'test',\
    'X-File-Name' : 'testname',\
    'X-File-Size' : '123456',\
    'X-Download-Percentage' : '50',\
    'X-Mime-Type' : 'video/mp4' 
    }

    header['X-URL'] = url

    request_url = '/identified?key=%s&digest=%s&digest-algorithm=%s&' % (api_key,digest,digest_algorithm)
    
    print request_url,url
    host = "service1.vb-xl.net"
    
    while True:
        #conn = httplib.HTTPSConnection (host, 443)
        conn = httplib.HTTPConnection (host, 80)
        conn.request("GET", request_url, None, header)
    
        res = conn.getresponse ()
        results = res.read ()
        r_headers = res.getheaders ()
        print res.status
        print results
        time.sleep(5)
        conn.close()
        j_res = json.loads(results)
        if res.status != 200:
            sys.exit(-1)
        if j_res['result'] is None:
            break
        if j_res['result'].has_key('overall'):
            break
    
