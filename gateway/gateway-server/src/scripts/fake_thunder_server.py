#!/usr/bin/env python
#coding: utf-8


import logging
import web

"""
   Dependencies:
   =============
     sudo aptitude install python-dev python-pip
     sudo aptitude remove python-gevent
     sudo pip installl gevent web.py gunicorn

   Usage:
   ======
     gunicorn -D -p /tmp/thunder-server.pid -k gevent -w 16 --worker-connections=1000 -b 0.0.0.0:8085 fake_thunder_server:app

"""


class ThunderServer(object):
    
    def GET(self):
        params = web.input()
        gcid = params.get('gcid', None)
        url = params.get('url', None)
        r = params.get('r', None)
        return 'ok'


urls = (
    '/info', 'ThunderServer'
)
app = web.application(urls, globals())

if __name__ == '__main__':
    app.run()
else:
    app = app.wsgifunc()

