#!/usr/bin/env python
#coding: utf-8

import sys
import json
import base64
import requests
import uuid

# from optparse import OptionParser
# parser = OptionParser()
# parser.add_option("-f", "--file", dest="filename",
#                   help="write report to FILE")
# parser.add_option("-q", "--quiet",
#                   action="store_false", dest="verbose", default=True,
#                   help="don't print status messages to stdout")
# (options, args) = parser.parse_args()
# print 'options:', options
# print 'args:', args


SCHEME = 'http'
HOST = '10.162.207.221'
PORT = 8080
URL = '{}://{}:{}/copyrighted'.format(SCHEME, HOST, PORT)
APIKEY = 'this-is-TMP-apikey'

argc = len (sys.argv);
if (argc != 2): 
    print 'usage: %s json_conf' % sys.argv[0]
    sys.exit (-1)

json_conf = sys.argv[1]


def clear_empty(dicts):
    for d in dicts:
        [d.pop(k)
         for k, v in d.iteritems()
         if (v is None
             or (isinstance(v, (str, unicode)) and len(v)==0))]


def gateway_get(case):

    headers = {
        'X-Progress': '10',
        'X-Client-ID': 'client_id123456',
        'X-Client-Address':'192.168.60.136',
        'X-File-Name': 'qa_test',
        'X-File-Size': '123456',
        'X-Mime-Type': 'video/mp4',
        'X-URL': case['url'].encode('utf-8')
    }
    print "URL==============", case['url']
    # For `query_string`: http://en.wikipedia.org/wiki/Query_string
    params = {
        'key': APIKEY,
        'hash': uuid.uuid1().hex,
        #'hash': str(uuid.uuid1()),
        'digest': '018e206e00bdc68374ff32bb0245d98ea703090e',
        'digest-algorithm': 'sha1'
    }

    # 清除空字符串
    # clear_empty([headers, params])
    
    resp = requests.get(URL, headers=headers, params=params, verify=False)
    print resp.status_code
    print resp.headers
    print resp.text
    

def gateway_post(case):
    
    headers = {
        'X-Progress': '10',
        'X-Client-Address':'192.168.60.136',
        'X-Client-ID': 'client_id123456',
        'X-Mime-Type': 'video/mp4',
        'X-URL': case['url'].encode('utf-8')
    }
    
    path = case['file-name']
    with open(path, 'r') as f:
        content = base64.b64encode(f.read())
        
    # For `query_string`: http://en.wikipedia.org/wiki/Query_string
    params = {
        #'key': 'this-is-TMP-apikey',
        'key': '',
        'hash': uuid.uuid1().hex,
        'digest': case['digest'],
        'digest-algorithm': 'sha1'
    }
    data = {
        'seed_file': content,
        'seed_encoded': True
    }

    # 清除空字符串
    # clear_empty([headers, params])

    resp = requests.post(URL, headers=headers, params=params, data=json.dumps(data), verify=False)
    print resp.status_code
    print resp.headers
    print resp.text


if __name__ == '__main__':
    cases = []
    with open(json_conf) as f:
        cases = json.loads(f.read())

    for case in cases:
        if case['method'] == 'GET':
            gateway_get(case)
        else:
            gateway_post(case)
