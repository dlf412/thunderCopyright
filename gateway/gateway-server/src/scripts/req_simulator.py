#!/usr/bin/env python
#coding: utf-8

import sys
import json
import base64
import requests


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

"""
ab -n 6000 -c 600 \
-H "X-Client-ID: some-id" \
-H "X-File-Name: some.mp4" \
-H "X-File-Size: 12354" \
-H "X-URL: thunder://QUFlZDJrOi8vfGZpbGV8JUU2JTlEJTgzJUU1JThBJTlCJUU3JTlBJTg0JUU2JUI4JUI4JUU2JTg4JThGLkdhbWUub2YuVGhyb25lcy5TMDRFMTAuRW5kLiVFNCVCOCVBRCVFOCU4QiVCMSVFNSVBRCU5NyVFNSVCOSU5NS5IRFRWcmlwLjYyNFgzNTIubXA0fDMxOTcxNzEwNXwxMjJhZmZiZTExYjFiNjkzOGQ1MWUwNzMxNjc3NTRhMnxoPWhjNmZibm9oZm9hdXgzc2trcXh5emp4dXNvaDVhdXR3fC9aWg==" \
"http://182.92.9.187:8080/copyrighted?key=this-is-TMP-apikey&digest-algorithm=sha1&digest=953109996fc9a5841b44ab4e37b12b83025b9eb3 "
"""


SCHEME = 'http'
HOST = '127.0.0.1'
PORT = 8964
URL = '{}://{}:{}/copyrighted'.format(SCHEME, HOST, PORT)
APIKEY = 'this-is-TMP-apikey'


def clear_empty(dicts):
    """ 清除空字符串 """
    for d in dicts:
        [d.pop(k)
         for k, v in d.iteritems()
         if (v is None
             or (isinstance(v, (str, unicode)) and len(v)==0))]


def gateway_get(case):

    headers = {
        'X-Progress': '[progress]',
        'X-Client-ID': '[client-id]',
        'X-File-Name': '[file-name]',
        'X-File-Size': '[file-size]',
        'X-Mime-Type': '[mime-type]',
        'X-URL': case['url']
    }

    # For `query_string`: http://en.wikipedia.org/wiki/Query_string
    params = {
        'key': APIKEY,
        'hash': '[hash]',
        'digest': '[digest]',
        'digest-algorithm': '[digest-algorithm]'
    }

    # 清除空字符串
    # clear_empty([headers, params])
    
    resp = requests.get(URL, headers=headers, params=params)
    print resp.status_code
    print resp.headers
    print resp.text
    

def gateway_post(case):
    
    headers = {
        'X-Progress': '[progress]',
        'X-Client-ID': '[client-id]',
        'X-Mime-Type': '[mime-type]',
    }
    
    # For `query_string`: http://en.wikipedia.org/wiki/Query_string
    params = {
        'key': APIKEY,
        'hash': '[hash]',
        'digest': '[digest]',
        'digest-algorithm': '[digest-algorithm]'
    }

    path = case['file-name']
    with open(path, 'r') as f:
        content = base64.b64encode(f.read())
        
    data = {
        'seed_file': content,
        'seed_encoded': True
    }

    # 清除空字符串
    # clear_empty([headers, params])

    resp = requests.post(URL, headers=headers, params=params, data=json.dumps(data))
    print resp.status_code
    print resp.headers
    print resp.text


if __name__ == '__main__':
    cases = []
    with open('cases.json') as f:
        cases = json.loads(f.read())

    for case in cases:
        if case['method'] == 'GET':
            gateway_get(case)
        else:
            gateway_post(case)
