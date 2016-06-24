#!/usr/bin/python
#coding: utf-8

import sys
import json
import base64
import requests
import unittest
import copy

class Gateway:
    def clear_empty(self,dicts):
        """ 清除空字符串 """
        for d in dicts:
            [d.pop(k)
             for k, v in d.iteritems()
             if (v is None
                 or (isinstance(v, (str, unicode)) and len(v)==0))]

    def gateway_get(self,case):
        ''' gateway get  requests\
            xxx
        '''
        URL = '{}://{}:{}/copyrighted'.format(case['scheme'], case['host'], case['port'])
        headers = {
            'X-Progress': case['X-Progress'],
            'X-Client-ID': case['X-Client-ID'],
            'X-File-Name': case['X-File-Name'],
            'X-File-Size': case['X-File-Size'],
            'X-Mime-Type': case['X-Mime-Type'],
            'X-URL': case['url'].encode('utf-8')
        }

        params = {
            'key': case['key'],
            'hash': case['hash'],
            'digest': case['digest'],
            'digest-algorithm': case['digest-algorithm']
        }

        # 清除空字符串
        # clear_empty([headers, params])
        
        resp = requests.get(URL, headers=headers, params=params, verify=False)
        #print resp.status_code
        #print resp.headers
        #print resp.text
        return resp
        

    def gateway_post(self,case):
        URL = '{}://{}:{}/copyrighted'.format(case['scheme'], case['host'], case['port'])
        headers = {
            'X-Progress': case['X-Progress'],
            'X-Client-ID': case['X-Client-ID'],
            'X-Mime-Type': case['X-Mime-Type']
        }
        
        params = {
            'key': case['key'],
            'hash': case['hash'],
            'digest': case['digest'],
            'digest-algorithm': case['digest-algorithm']
        }

        path = case['seed_file']
        with open(path, 'r') as f:
            content = base64.b64encode(f.read())
            #print 'cotent###############', content
        data = {
            'seed_file': content,
            'seed_encoded': True
        }

        # 清除空字符串
        # clear_empty([headers, params])

        resp = requests.post(URL, headers=headers, params=params, data=json.dumps(data), verify=False)
        #print resp.status_code
        #print resp.headers
        #print resp.text
        return resp

    def set_value(self,template_json,case_json):
        use_json=copy.copy(template_json)
        for k, v in case_json.iteritems():
            use_json[k]=v
        return use_json

    def test_result(self,expect_result,resp):
        print expect_result
        print resp.status_code
        print resp.text
        resp_result=json.dumps(resp.text)

