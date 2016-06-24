#!/usr/bin/env python
#coding: utf-8

import time

import tornado.httpserver
import tornado.ioloop
import tornado.web

from tornado import gen
from tornado.web import asynchronous
from tornado.ioloop import IOLoop
from tornado.options import define, options


class getToken(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    @gen.engine
    def get(self):
        loop = IOLoop.instance()
        yield gen.Task(loop.add_timeout, time.time() + 0.2)
        self.write("token")
        self.finish()


application = tornado.web.Application([
    (r'/hello', getToken),
])



if __name__ == '__main__':

    define("host", default="0.0.0.0", help="Bind host")
    define("port", default=8001, type=int, help="Bind port")
    define("backlog", default=128, type=int, help="Backlog")
    define("processes", default=4, type=int, help="Number of processes")
    
    options.parse_command_line()
    print 'Listening on => ', '%s:%d * %d * %d' % (options.host, options.port,
                                                   options.processes, options.backlog)
    
    # http_server = tornado.httpserver.HTTPServer(application, ssl_options={
    #     "certfile": "cert.pem",
    #     "keyfile": "key.pem",
    # })
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.bind(options.port, options.host, backlog=options.backlog)
    http_server.start(options.processes)
    IOLoop.instance().start()
