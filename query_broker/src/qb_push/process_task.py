#!/usr/bin/env python
# coding: utf-8
'''
Usage:
    process_task.py <config_file>
    process_task.py (--help|--version)

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
import push_global_vars as gv
from push_worker import Worker
from kombu import Connection
from push_util import *
from logging.handlers import SysLogHandler
import statsd
from utils import trans2json


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
    qb_cfg = cfg['qbmq']
    gv.qb_url = qb_cfg['url']
    gv.qb_queue = qb_cfg['queue']
    gv.qb_exchange = qb_cfg['exchange']
    gv.qb_routing_key = qb_cfg['routing_key']

    dbpc_cfg = cfg['dbpc']
    gv.dbpc_host = dbpc_cfg['host']
    gv.dbpc_port = dbpc_cfg['port']
    gv.interval = dbpc_cfg['interval']
    gv.dppc_service = dbpc_cfg['service']
    gv.dp = dbpc.dbpc(gv.dbpc_host,
                      int(gv.dbpc_port),
                      gv.dppc_service,
                      "query_broker.qb_push",
                      int(gv.interval))

    meidawise_cfg = cfg['vddbasync']
    gv.mysystem_url = meidawise_cfg['url']
    gv.mysystem_host = meidawise_cfg['host']
    gv.mysystem_user = meidawise_cfg['user']
    gv.mysystem_passwd = meidawise_cfg['passwd']

    pushresult_cfg = cfg['pushresultmq']
    gv.pushresult_url = pushresult_cfg['url']
    gv.pushresult_queue = pushresult_cfg['queue']
    gv.pushresult_exchange = pushresult_cfg['exchange']
    gv.pushresult_routing_key = pushresult_cfg['routing_key']

    taskpriorit_cfg = cfg['taskprioritymq']
    gv.taskpriorit_url = taskpriorit_cfg['url']
    gv.taskpriorit_queue = taskpriorit_cfg['queue']
    gv.taskpriorit_exchange = taskpriorit_cfg['exchange']
    gv.taskpriorit_routing_key = taskpriorit_cfg['routing_key']


    statsd_cfg = cfg['statsdserver']
    gv.statsdhost = statsd_cfg['host']
    gv.statsdport = statsd_cfg['port']


def init_mysql(cfg):
    gv.mysql_conn = connect_db(cfg['mysql'])


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
            "query_broker#qb_push", log_level, gv.log_file, SysLogHandler.LOG_LOCAL2)
        g_logger_info.init_logger(
            "query_broker#qb_push", log_level, gv.log_file, SysLogHandler.LOG_LOCAL1)
    else:
        g_logger.init_logger(
            "query_broker#qb_push", log_level, 'syslog', SysLogHandler.LOG_LOCAL2)
        g_logger_info.init_logger(
            "query_broker#qb_push", log_level, 'syslog', SysLogHandler.LOG_LOCAL1)


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
        with Connection(gv.qb_url) as conn:
            try:
                worker = Worker(
                    conn, gv.qb_exchange, gv.qb_queue, gv.qb_routing_key)
                g_logger.info(trans2json('query_broker qb_push service start'))
                worker.run()
            except Exception:
                g_logger.error(
                    trans2json("qb_push %s happend!" % str(traceback.format_exc())))
    gv.dp.join()
if __name__ == '__main__':
    main()
