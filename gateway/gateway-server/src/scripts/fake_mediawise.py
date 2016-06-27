#!/usr/bin/env python
#coding: utf-8

import random
import json

import web

"""
   Dependencies:
   =============
     sudo aptitude install python-dev python-pip
     sudo aptitude remove python-gevent
     sudo pip installl gevent web.py gunicorn

   Usage:
   ======
     gunicorn -D -p /tmp/mysystem.pid -k gevent -w 16 --worker-connections=1000 -b 0.0.0.0:8081 fake_mysystem:app

"""


rand = random.Random()

class mysystemServer(object):
    
    def GET(self):
        params = web.input()
        action = params.get('check_status', None)
        outputformat = params.get('outputformat', None)
        username = params.get('username', None)
        password = params.get('password', None)
        query_type = params.get('type', None)
        query_id = params.get('id', None) # hash

        error_data = {
            'Head': {
                'ErrorCode': 1002
            }
        }
        working_data = {
            'Body': {
                'Query': [
                    {
                        'QueryLog': {
                            'Status': 2
                        }
                    }
                ]
            }
        }
        unmatch_data = {
            'Body': {
                'Query': [
                    {
                        'QueryLog': {
                            'Status': 0
                        },
                        'Match': []
                    }
                ]
            }
        }
        match_data = {
            'Body': {
                'Query': [
                    {
                        'QueryLog': {
                            'Status': 0
                        },
                        'Match': ['result-1', 'result-2']
                    }
                ]
            }
        }

        result = None
        score = rand.randint(0, 99)
        if score < 15:
            result = error_data
        elif score < 30:
            result = working_data
        elif score < 60:
            result = unmatch_data
        elif score < 100:
            result = match_data

        result['Head'] = { 'ErrorCode': 0 }
        return json.dumps(result)


urls = (
    '/service/mysystem', 'mysystemServer'
)

app = web.application(urls, globals())

if __name__ == '__main__':
    app.run()
else:
    app = app.wsgifunc()
