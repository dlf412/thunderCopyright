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
     gunicorn -D -p /tmp/mediawise.pid -k gevent -w 16 --worker-connections=1000 -b 0.0.0.0:8081 fake_mediawise:app

"""


rand = random.Random()

class MediaWiseServer(object):
    
    def GET(self):
        params = web.input()

        error_data = {
            'error': {
                'error_code': 1002
            }
        }
        working_data = {
            'results':[{
                'status': 3
            }]
        }
        unmatch_data = {
            'results': [{
                'status': 1
            }]
        }
        match_data = {
            'results': [{
                'status': 0
            }]
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

        return json.dumps(result)


urls = (
    '/vddb-async/matches', 'MediaWiseServer'
)

app = web.application(urls, globals())

if __name__ == '__main__':
    app.run()
else:
    app = app.wsgifunc()
