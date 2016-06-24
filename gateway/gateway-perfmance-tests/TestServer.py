#!/usr/bin/env python
#coding: utf-8

import json
import commands

import web


class Tester(object):
    
    def POST(self):
        data = json.loads(web.data())
        try:
            url = data['url']
            concurrent = data['concurrent']
            seconds = data.get('seconds', 20)
        except KeyError as e:
            print e
            return json.dumps({
                'status': 'KeyError',
                'output': str(e)
            })
        CMD = 'ulimit -n 10000 && siege -c %(concurrent)d -t %(seconds)ds %(url)s' % locals()
        print 'Test cmd:', CMD
        status, output = commands.getstatusoutput(CMD)

        result = {
            'status': status,
            'output': output
        }
        return json.dumps(result)


urls = (
    '/test', 'Tester'
)

app = web.application(urls, globals())


if __name__ == '__main__':
    app.run()
