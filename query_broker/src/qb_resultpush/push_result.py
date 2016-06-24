#!/usr/bin/env python
# coding: utf-8
'''
Usage:
    result_push.py <config_file>
    result_push.py (--help|--version)

Arguments:
    config_file     the path of config_file

Options:
    -h --help       show this help message and exit
    -v --version    show version and exit
'''
import time
import sys
import os
import json
import shutil
import docopt
from schema import Schema, SchemaError
import traceback
import dbpc
import result_global_vars as gv
from worker_push import Worker
from kombu import Connection
from result_util import *
from logging.handlers import SysLogHandler
import statsd


def get_conf_abspath(args):
    os.chdir(gv.run_dir)
    conf_path = args['<config_file>']
    conf_abs_path = os.path.abspath(conf_path)
    os.chdir(gv.bin_dir)
    return conf_abs_path


def check_conf_validation(cf):
    try:
        Schema(lambda x: os.path.exists(x),
               error='config file should exists').validate(cf)
    except SchemaError as e:
        exit(e)

def parse_conf_file(cfg_file):
    with open(cfg_file) as f:
        return json.load(f)


def get_global_vars(cfg):

    pushresult_cfg = cfg['pushresultmq']
    gv.pushresult_url = pushresult_cfg['url']
    gv.pushresult_queue = pushresult_cfg['queue']
    gv.pushresult_exchange = pushresult_cfg['exchange']
    gv.pushresult_routing_key = pushresult_cfg['routing_key']

    dbpc_cfg = cfg['dbpc']
    gv.dbpc_host = dbpc_cfg['host']
    gv.dbpc_port = dbpc_cfg['port']
    
    gv.dppc_service = dbpc_cfg['service']
    '''
    gv.component = dbpc_cfg['component']
    '''
    gv.interval = dbpc_cfg['interval']

    #gv.try_times_limit = dbpc_cfg['try_times_limit']
    gv.dp = dbpc.dbpc(gv.dbpc_host,
                      int(gv.dbpc_port),
                      gv.dppc_service,
                      "query_broker.qb_resultpush",
                      int(gv.interval))
    gv.thunder_server = cfg['thunderserver']['host']

    statsd_cfg = cfg['statsdserver']

    gv.statsdhost = statsd_cfg['host']
    gv.statsdport = statsd_cfg['port']

    gv.is_push = cfg['is_push']

def init_statsd():
    gv.statsd_conn = statsd.client.StatsClient(
        host=gv.statsdhost, port=gv.statsdport)


def init_logger(cf):
    #log_level_map = {'ERROR': 40, 'WARN': 30, 'INFO': 20, 'DEBUG': 10}
    #module = cf['module']
    log_level = cf['log']['level']
    if cf['log'].has_key('logfile'):
        gv.log_file = cf['log']['logfile']
        g_logger.init_logger(
            "query_broker#qb_resultpush", log_level, gv.log_file, SysLogHandler.LOG_LOCAL2)
        g_logger_info.init_logger(
            "query_broker#qb_resultpush", log_level, gv.log_file, SysLogHandler.LOG_LOCAL1)
    else:
        g_logger.init_logger(
            "query_broker#qb_resultpush", log_level, 'syslog', SysLogHandler.LOG_LOCAL2)
        g_logger_info.init_logger(
            "query_broker#qb_resultpush", log_level, 'syslog', SysLogHandler.LOG_LOCAL1)


def main():
    args = docopt.docopt(__doc__, version=gv.version)
    cfg_file = get_conf_abspath(args)
    check_conf_validation(cfg_file)
    cfg = parse_conf_file(cfg_file)
    init_logger(cfg)
    get_global_vars(cfg)
    gv.dp.start()
    init_statsd()
    while True:
        with Connection(gv.pushresult_url) as conn:
            try:
                worker = Worker(
                    conn, gv.pushresult_exchange, gv.pushresult_queue, gv.pushresult_routing_key)
                g_logger.info(
                    trans2json('push result  to thunder service start'))
                worker.run()
            except Exception:
                g_logger.error(
                    trans2json("result_push %s happend!" % (traceback.format_exc())))
    gv.dp.join()
if __name__ == '__main__':
    main()
