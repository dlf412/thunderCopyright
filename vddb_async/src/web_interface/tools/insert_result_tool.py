#!/usr/bin/env python
#coding: utf-8


import re
import sys
import json
import base64
import hashlib
import httplib
import subprocess
from optparse import OptionParser

result_wrapper = {
    "jsonrpc": "2.0",
    "method" : "insert",
    "params": {
        "site_asset_id":"",
        "match_type":"no_match",
        "matches":[
                {
                    'video_score': 99,
                    'meta_uuid': '970ae0ba-773b-11e1-a7b2-080027cf46d6',
                    'video_sample_offset': 0,
                    'match_type': 'video',
                    'media_type':'video',
                    'meta_name': 'Auto_Rule306_Movie',
                    'video_ref_offset': 0,
                    'audio_duration': 0,
                    'track_id': 0.0,
                    'instance_id': '9752d1cc-773b-11e1-a7b2-080027cf46d6',
                    'video_duration': 307,
                    'instance_name': 'cappella.flv.xfp.0'
                }
            ]
    },
    "id": "null"
}

def popen(cmd):
    proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    ret = proc.wait()
    out, err = proc.communicate()
    return ret, out, err

class HashError(Exception):
    def __str__(self):
        return str(self.__dict__)

class ParamsError(Exception): pass

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
            self.url = url
            self.prefix = 'url_hash'
            try:
                if url.startswith('magnet:'):
                    self.protocol = 'magnet'
                else:
                    self.protocol = url.split('://', 1)[0].lower()
            except Exception as e:
                ex = HashError()
                ex.message = "Hash url invalid!"
                ex.error = str(e)
                ex.url = url
                raise ex
        else:
            self.content = content
            self.prefix = 'seed_hash'
            self.protocol = 'torrent'

    @property
    def value(self):
        """ Cached property """

        hash_type_dict = {
            'ftp'     : Hash.sha1_hex,
            'http'    : Hash.sha1_hex,
            'ed2k'    : Hash.hash_ed2k,
            'magnet'  : Hash.hash_magnet,
            'torrent' : Hash.hash_bt,
            'thunder': Hash.hash_thunder
        }

        func = hash_type_dict.get(self.protocol.lower(), Hash.sha1_hex)
        self._value = '%s#%s' % (self.prefix, func(self.url))
        return self._value

    @staticmethod
    def sha1_hex(s):
        if type(s) == unicode:
            s = s.encode('utf-8')
        return hashlib.sha1(s).hexdigest()

    @staticmethod
    def hash_bt(b64_content):
        """  !!! *tmp* !!! """
        return Hash.sha1_hex(b64_content)

    @staticmethod
    def hash_ed2k(uri):
        return uri.split('|')[4]

    @staticmethod
    def hash_thunder(uri):
        uri = uri.strip()
        t_hash = uri[10:-1] if uri.endswith('/') else uri[10:]
        origin_uri = base64.b64decode(t_hash)[2:-2]
        return Hash(url=origin_uri).value.split('#')[1]

    @staticmethod
    def hash_magnet(uri):
        try:
            return re.search(r"\b\w{40}\b", uri).group(0)
        except:
            raise HashError("invalid magnet url")

def ingest(host, port, hash, match_type, matches=None, is_tmp=False):
    global result_wrapper
    source = "manual_tmp"
    if not is_tmp:
        source = "manual"

    result_wrapper['params']['match_type'] = match_type
    if match_type == 'match':
        if matches:
            result_wrapper['params']['matches'] = matches["matches"]
    else:
        result_wrapper['params']['matches'] = []

    result_wrapper['params']['site_asset_id'] = [hash]
    print result_wrapper

    header = {"Content-Type": "application/json"}
    conn = httplib.HTTPConnection(host, port)
    conn.request('POST', "/vddb-async/matches?source=%s"%source,
                 json.dumps(result_wrapper), header)
    res = conn.getresponse ()

    status = res.status
    reason = res.reason

    results = res.read ()

    if status == 200:
        print "=== ingest success ==="
    else:
        print "code:",status
        print "msg:",reason
        print "result:",results
        print "=== ingest failed ==="
        exit(1)

def raiseParamsError(parser, option):
    print "%s is None" % option
    print parser.usage
    raise ParamsError

def main():
    try:
        usage = ("usage: python %s -H host -P port -u url -m match_type "
                "[-s hash] [-i matches info file] [--tmp] [--lower]" % sys.argv[0])
        parser = OptionParser(usage=usage, version="%prog 1.0.0.1")
        parser.add_option('-H', '--host', action='store', dest='host',
                          help='ingest host')
        parser.add_option('-P', '--port', action='store', dest='port',
                          type=int, help='ingest port')
        parser.add_option('-s', '--hash', action='store', dest='hash',
                          help='hash for ingest')
        parser.add_option('-u', '--url', action='store', dest='url',
                          help='url for ingest')
        parser.add_option('-m', '--match_type', action='store', dest='match_type',
                          help='match_type [match/no_match/unrecognized]')
        parser.add_option('--tmp', action='store_true', dest='tmp_result',
                          default=False, help='result is tmp, default [False]')
        parser.add_option('-i', '--match_file', action='store', dest='match_file',
                          help='matched info file')
        parser.add_option('--lower', action='store_true', dest='lower_hash',
                          default=False, help='lower hash')
        (options, _) = parser.parse_args()
        if options.host is None:
            raiseParamsError(parser, "host")
        elif options.port is None:
            raiseParamsError(parser, "port")
        elif options.url is None and not options.hash:
            raiseParamsError(parser, "url and hash")
        elif options.match_type is None:
            raiseParamsError(parser, "match_type")
    except:
        exit(1)

    url = options.url
    if url != None:
        url = url.strip()
    host = options.host
    port = options.port
    match_type = options.match_type
    match_file = options.match_file
    is_tmp = options.tmp_result
    lower_hash = options.lower_hash

    matches = None
    try:
        if match_file:
            with open(match_file, "r") as f:
                matches = json.loads(f.read())
    except Exception, e:
        print e
        exit(1)

    input_hash = options.hash
    if input_hash is None:
        h = Hash(url=url)
        input_hash = h.value
    else:
        input_hash = input_hash.strip()

    if lower_hash:
        input_hash = input_hash.lower()

    print "url: ", url
    print "match_type: ", match_type
    print "hash: ", input_hash
    print "matches: ", matches
    print "tmp result:", is_tmp
    ingest(host, port, input_hash, match_type, matches, is_tmp)

if __name__ =='__main__':
    main()
