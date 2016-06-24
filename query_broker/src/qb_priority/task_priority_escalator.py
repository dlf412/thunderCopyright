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
import priority_global_vars as gv
from task_worker import Worker
from kombu import Connection
from priority_util import *
from redis_oper import *
from logging.handlers import SysLogHandler
import MySQLdb
import statsd
import random
from utils import trans2json,digest
import marisa_trie


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

    cas_cfg = cfg['casmq']
    gv.cas_url = cas_cfg['url']
    gv.cas_queue = cas_cfg['queue']
    gv.cas_exchange = cas_cfg['exchange']
    gv.cas_routing_key = cas_cfg['routing_key']

    cashigh_cfg = cfg['cashighmq']
    gv.cashigh_url = cashigh_cfg['url']
    gv.cashigh_queue = cashigh_cfg['queue']
    gv.cashigh_exchange = cashigh_cfg['exchange']
    gv.cashigh_routing_key = cashigh_cfg['routing_key']
 
    dbpc_cfg = cfg['dbpc']
    gv.dbpc_host = dbpc_cfg['host']
    gv.dbpc_port = dbpc_cfg['port']
    gv.dppc_service = dbpc_cfg['service']
    gv.interval = dbpc_cfg['interval']
    gv.dp = dbpc.dbpc(gv.dbpc_host,
                      int(gv.dbpc_port),
                      gv.dppc_service,
                      "query_broker.qb_priority",
                      int(gv.interval))

    taskpriorit_cfg = cfg['taskprioritymq']
    gv.taskpriorit_url = taskpriorit_cfg['url']
    gv.taskpriorit_queue = taskpriorit_cfg['queue']
    gv.taskpriorit_exchange = taskpriorit_cfg['exchange']
    gv.taskpriorit_routing_key = taskpriorit_cfg['routing_key']

    gv.databases = cfg['mysql']

    gv.file_ext_list = cfg['filter']['file_ext']
    gv.min_file_size = cfg['filter']['minfilesize']
    gv.max_file_size = cfg['filter']['maxfilesize']

    gv.suspicious_mime_types = cfg['filter']['suspicious_mime_types']

    statsd_cfg = cfg['statsdserver']
    gv.statsdhost = statsd_cfg['host']
    gv.statsdport = statsd_cfg['port']

    redis_cfg = cfg['redis']
    gv.rds_url_hot = redis_cfg['url_hot']
    gv.rds_cas_high = redis_cfg['cas_high']
    gv.rds_cas_low = redis_cfg['cas_low']
    gv.rds_cas_black = redis_cfg['cas_black']
    gv.ttl = redis_cfg['ttl']

    gv.special_char = cfg['filter'].get('special_char', [])
    
def init_redis():
    gv.rds_url_hot_conn = connect_redis(gv.rds_url_hot)
    
def init_statsd():
    gv.statsd_conn = statsd.client.StatsClient(host=gv.statsdhost, port=gv.statsdport)

def init_logger(cf):
    log_level = cf['log']['level']
    gv.log_file = cf['log']['logfile']
    g_logger.init_logger("query_broker#qb_priority", log_level, gv.log_file, SysLogHandler.LOG_LOCAL2)
    g_logger_info.init_logger("query_broker#qb_priority", log_level, gv.log_file, SysLogHandler.LOG_LOCAL1)

def init_mysql_keyword(cfg):
    db_pool = make_db_pool(cfg['mysql'],2)
    conn = db_pool.connection()
    cursor = conn.cursor()
    cursor.execute('''select trim(keyword) from task_priority_config''')
    key_word_list = [row[0].decode('utf8').lower() for row in cursor.fetchall()]
    gv.keyword_trie = marisa_trie.Trie(key_word_list)

    cursor.execute('''select trim(keyword) from black_list''')
    black_key_word_list = [row[0].decode('utf8').lower() for row in cursor.fetchall()]
    gv.black_keyword_trie = marisa_trie.Trie(black_key_word_list)

    cursor.close()
    conn.close()

def main():
    try:
        args = docopt.docopt(__doc__, version=gv.version)
        cfg_file = get_conf_abspath(args)
        check_conf_validation(cfg_file)
        cfg = parse_conf_file(cfg_file)
        init_logger(cfg)
        get_global_vars(cfg)
        init_mysql_keyword(cfg)
        init_statsd()
        init_redis()
    except:
        g_logger.error(traceback.format_exc())
        sys.exit(1)

    gv.dp.start()
    while True:
        with Connection(gv.taskpriorit_url) as conn:
            try:
                worker = Worker(conn, gv.taskpriorit_exchange, gv.taskpriorit_queue, gv.taskpriorit_routing_key)
                worker.run()
                g_logger.info(trans2json('task priority escalator start'))
            except Exception:
                g_logger.error(trans2json("task priority escalator %s happend!" % str(traceback.format_exc())))
    gv.dp.join()

if __name__ == '__main__':
    main()
