#!/usr/bin/env python
#coding: utf-8

import unittest
import json
import uuid
from datetime import datetime

import requests
import commands

TEST_URL = 'http://127.0.0.1:8080/copyrighted'
TEST_CASES_FILE = 'case_tmp.json'
POST_FILE = 'post_new.json'

class TestRequest(unittest.TestCase):

    def setUp(self):
        with open(TEST_CASES_FILE, 'r') as f:
            self.cases = json.load(f)
            self.get_cases = []
            self.post_cases = []
            for case in self.cases:
                if case['method'] == 'GET':
                    self.get_cases.append(case)
                elif case['method'] == 'POST':
                    self.post_cases.append(case)
                else:
                    raise ValueError(str(case))


    def test_GET(self):
        print '<<TEST GET>>'
        file_name = u'测试中文'.encode('gbk')
        for case in self.get_cases:
            headers = {
                'X-Progress': '20%',
                'X-Client-ID': '[client-id]',
                'X-Client-Address': '[client-address]',
                'X-File-Name': file_name, # '[file-name]',
                'X-File-Size': '12345',
                'X-Mime-Type': 'audio/mp4',
                'X-URL': case['url'].encode('utf-8')
            }
            params = {
                'key': 'this-is-TMP-apikey',
                'hash': 'hash-GET-2',
                'digest': 'digest-GET-2',
                'digest-algorithm': 'sha1'
            }

            resp = requests.get(TEST_URL, headers=headers, params=params)
            print resp.status_code, resp.text
            self.assertTrue(resp.status_code == 200)

    def test_POST(self):
        print '<<TEST POST>>'
        with open(POST_FILE, 'r') as f:
            data = f.read()

        data = json.dumps({
            'id': 'id',
            'params': {
                'seed_file': json.loads(data)['seed_file']
            }
        })
        headers = {
            'X-Progress': '20%',
            'X-Client-ID': '[client-id]',
            'X-Client-Address': '[client-address]',
            'X-File-Name': '[file-name]',
            'X-Mime-Type': 'audio/mp4',
            'X-URL': 'test.torrent'
        }
        params = {
            'key': 'this-is-TMP-apikey',
            'hash': 'hash-POST-3',
            'digest': 'digest-POST-3',
            'digest-algorithm': 'sha1'
        }
        t1 = datetime.now()
        resp = requests.post(TEST_URL, headers=headers, params=params, data=data)
        t2 = datetime.now()
        print 'DT:', t2-t1
        print resp.status_code, resp.text
        self.assertTrue(resp.status_code == 200)


if __name__ == '__main__':
    unittest.main()
