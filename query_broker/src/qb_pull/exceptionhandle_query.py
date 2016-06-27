#!/usr/bin/env python
# coding: utf-8
'''
Usage:
    exceptionhandle_query.py <config_file>
    exceptionhandle_query.py (--help|--version)

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
import pull_global_vars as gv
from worker_query import Worker_query
from kombu import Connection
from pull_util import *
import threading
from fetch_query_result_process import worker_result
from redis_oper import connect_redis
import time
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

    finsh_cfg = cfg['finshmq']
    gv.finsh_url = finsh_cfg['url']
    gv.finsh_queue = finsh_cfg['queue']
    gv.finsh_exchange = finsh_cfg['exchange']
    gv.finsh_routing_key = finsh_cfg['routing_key']

    vddb_querycfg = cfg['vddbquerymq']
    gv.vddb_queryurl = vddb_querycfg['url']
    gv.vddb_queryqueue = vddb_querycfg['queue']
    gv.vddb_queryexchange = vddb_querycfg['exchange']
    gv.vddb_queryrouting_key = vddb_querycfg['routing_key']

    vddb_resultcfg = cfg['vddbresultmq']
    gv.vddb_resulturl = vddb_resultcfg['url']
    gv.vddb_resultqueue = vddb_resultcfg['queue']
    gv.vddb_resultexchange = vddb_resultcfg['exchange']
    gv.vddb_resultrouting_key = vddb_resultcfg['routing_key']

    dbpc_cfg = cfg['dbpc']
    gv.dbpc_host = dbpc_cfg['host']
    gv.dbpc_port = dbpc_cfg['port']
    gv.dppc_service = dbpc_cfg['service']

    gv.interval = dbpc_cfg['interval']
    gv.dp = dbpc.dbpc(gv.dbpc_host,
                      int(gv.dbpc_port),
                      gv.dppc_service,
                      "query_broker.qb_pull",
                      int(gv.interval))

    meidawise_cfg = cfg['vddbasync']
    gv.mysystem_url = meidawise_cfg['url']
    gv.mysystem_host = meidawise_cfg['host']
    gv.mysystem_user = meidawise_cfg['user']
    gv.mysystem_passwd = meidawise_cfg['passwd']
    gv.mysystem_port = meidawise_cfg['port']

    gv.file_tmpdir = cfg['tmpdir']

    cas_cfg = cfg['casmq']
    gv.cas_url = cas_cfg['url']
    gv.cas_queue = cas_cfg['queue']
    gv.cas_exchange = cas_cfg['exchange']
    gv.cas_routing_key = cas_cfg['routing_key']

    pushresult_cfg = cfg['pushresultmq']
    gv.pushresult_url = pushresult_cfg['url']
    gv.pushresult_queue = pushresult_cfg['queue']
    gv.pushresult_exchange = pushresult_cfg['exchange']
    gv.pushresult_routing_key = pushresult_cfg['routing_key']

    gv.company = cfg['company']

    #gv.ZIP_EXTENSIONS = cfg['zip_extensions']

    statsd_cfg = cfg['statsdserver']
    gv.statsdhost = statsd_cfg['host']
    gv.statsdport = statsd_cfg['port']

    redis_cfg = cfg['redis']
    gv.rds_url_hot = redis_cfg['url_hot']
    gv.rds_cas_high = redis_cfg['cas_high']
    gv.rds_cas_low = redis_cfg['cas_low']
    gv.rds_cas_black = redis_cfg['cas_black']

def init_statsd():
    gv.statsd_conn = statsd.client.StatsClient(host = gv.statsdhost, port = gv.statsdport)
def init_logger(cf):
    log_level = cf['log']['level']
    if cf['log'].has_key('logfile'):
        gv.log_file = cf['log']['logfile']
        g_logger.init_logger(
            "query_broker#qb_pull", log_level, gv.log_file, SysLogHandler.LOG_LOCAL2)
        g_logger_info.init_logger(
            "query_broker#qb_pull", log_level, gv.log_file, SysLogHandler.LOG_LOCAL1)
    else:
        g_logger.init_logger(
            "query_broker#qb_pull", log_level, 'syslog', SysLogHandler.LOG_LOCAL2)
        g_logger_info.init_logger(
            "query_broker#qb_pull", log_level, 'syslog', SysLogHandler.LOG_LOCAL1)
        
class fetch_query_result(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        with Connection(gv.vddb_resulturl) as conn:
            self.th = worker_result(
                conn, gv.vddb_resultexchange, gv.vddb_resultqueue, gv.vddb_resultrouting_key)

    def run(self):
        g_logger.info(trans2json("start fetch query result service"))
        self.th.run()


def main():
    args = docopt.docopt(__doc__, version=gv.version)
    cfg_file = get_conf_abspath(args)
    check_conf_validation(cfg_file)
    cfg = parse_conf_file(cfg_file)
    init_logger(cfg)
    get_global_vars(cfg)
    init_statsd()
    gv.dp.start()
    thread_tasker = fetch_query_result()
    thread_tasker.start()
    while True:
        with Connection(gv.finsh_url) as conn:
            try:
                worker = Worker_query(conn)
                g_logger.info(
                    trans2json("start exceptionhandle and query service"))
                worker.run()
            except Exception:
                g_logger.error(
                    trans2json("error happend! %s" % str(traceback.format_exc())))
    thread_tasker.join()
    gv.dp.join()
if __name__ == '__main__':
    main()
