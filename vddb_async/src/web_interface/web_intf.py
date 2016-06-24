#! /usr/bin/python

import os
import sys
import web
import logging.config

bin_dir = os.path.dirname(os.path.realpath(__file__))
work_dir = os.path.dirname(bin_dir)
sys.path.insert(0, bin_dir)
from matches import matches
from dbpc import dbpc
from web_config import config


#logging.config.fileConfig("/".join([work_dir, 'etc', 'log.conf']),
#        disable_existing_loggers=False)

urls = (
        '/*.*/matches', 'matches'
)

app = web.application(urls, globals())
if __name__ == '__main__':
    app.run()
else:
    d = dbpc(config['dbpc']['server'], int(config['dbpc']['port']),
             'thunder', config['dbpc']['component']+"matches_interface",
             int(config['dbpc']['report_interval']))
    d.start()
    app = app.wsgifunc()
