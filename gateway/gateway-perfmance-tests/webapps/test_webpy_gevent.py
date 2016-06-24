#!/usr/bin/env python
#coding: utf-8

from gevent import monkey; monkey.patch_all()
import gevent

import json

import web
from web.wsgiserver import CherryPyWSGIServer


'''
    Test command:
    =============
      gunicorn --certfile=cert.pem --keyfile=key.pem -k gevent -w 32 -b 0.0.0.0:8002 test_webpy_gevent:wsgiapp 2>/dev/null 1>/dev/null
'''



# CherryPyWSGIServer.ssl_certificate = "cert.pem"
# CherryPyWSGIServer.ssl_private_key = "key.pem"

class Hello(object):
    def GET(self):
        print web.input()
        for k, v in web.ctx.iteritems():
            print '>>> ', k, ' --> ', v

        gevent.sleep(0.2)
        return 'Hi, there!'


class Query(object):
    
    def GET(self):
        pass


    def POST(self):
        print vars(web.input())
        for k, v in web.ctx.iteritems():
            print '>>> ', k, ' --> ', v
            
        data = json.loads(web.data())
        web.header('Content-Type', 'application/json')
        return json.dumps({'status': 'ok', 'data': data['key']})


urls = (
    '/hello', 'Hello',
    '/query', 'Query',
)

app = web.application(urls, globals())
wsgiapp = app.wsgifunc()



if __name__ == '__main__':
    app.run()
