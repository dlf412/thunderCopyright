#!/usr/bin/env python
# coding: utf-8
'''
Usage:
    worker.py <config_file>
    worker.py (--help|--version)

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
from black_deal import *
from kombu import Connection
from logging.handlers import SysLogHandler
import MySQLdb
import statsd
import marisa_trie
from common.mylogger import mylogger
from common import dbpc
from DBUtils.PersistentDB import PersistentDB
from functools import partial
import global_vars as gv
from high2low import *



gv.g_logger= mylogger()

version = '1.0.0.0'

# the major dirs
bin_dir = os.path.dirname(os.path.abspath(__file__))
if os.path.islink(os.getenv('PWD')):
    bin_dir = os.getenv('PWD')
run_dir = os.getenv('PWD')
#os.chdir(bin_dir)

def make_db_pool(database, conns):
    # custom connecting method, so we can set up connection config immediately
    # after connecting to the server
    user = database[8:].split(':')[0]
    #port = database[8:].split(':')[2].split('/')[0]
    db = database[8:].split('/')[1]
    p_h = database[8:].split(':')[1]
    passwd = p_h.split('@')[0]
    host = p_h.split('@')[1].split('/')[0]
    def make_conn(database, *args, **kwargs):
        conn = MySQLdb.connect(host=host,
                               port=3306,
                               user=user,
                               passwd=passwd,
                               db=db, charset='utf8',
                               use_unicode=False)
        cur = conn.cursor()
        cur.execute('set time_zone="+0:00"')
        cur.close()
        conn.commit()
        return conn
    # persistent db binds connections to threads
    return PersistentDB(creator=partial(make_conn, database), maxconnections=conns,
                        blocking=True)

def get_conf_abspath(args):
    os.chdir(run_dir)
    conf_path = args['<config_file>']
    conf_abs_path = os.path.abspath(conf_path)
    os.chdir(bin_dir)
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

    hightmp_cfg = cfg['download_task_tmp']
    gv.tmphigh_url = hightmp_cfg['url']
    gv.tmphigh_queue = hightmp_cfg['queue']
    gv.tmphigh_exchange = hightmp_cfg['exchange']
    gv.tmphigh_routingkey = hightmp_cfg['routing_key']

    low_cfg = cfg['task_download']
    gv.low_url = low_cfg['url']
    gv.low_queue = low_cfg['queue']
    gv.low_exchange = low_cfg['exchange']
    gv.low_routingkey = low_cfg['routing_key']

    high_cfg = cfg['task_download_high']
    gv.high_url = high_cfg['url']
    gv.high_queue = high_cfg['queue']
    gv.high_exchange = high_cfg['exchange']
    gv.high_routingkey = high_cfg['routing_key']

    dbpc_cfg = cfg['dbpc']
    dbpc_host = dbpc_cfg['host']
    dbpc_port = dbpc_cfg['port']

    dppc_service = dbpc_cfg['service']
    interval = dbpc_cfg['interval']
    gv.d = dbpc.dbpc(dbpc_host,int(dbpc_port),dppc_service,"ops_tools_black_list",int(interval))
    gv.redis_url = cfg['redis']
    statsd_cfg = cfg['statsdserver']

    gv.statsdhost = statsd_cfg['host']
    gv.statsdport = statsd_cfg['port']


def init_logger(cf):
    log_level = cf['log']['level']
    if cf['log'].has_key('logfile'):
        log_file = cf['log']['logfile']
        gv.g_logger.init_logger(
            "ops_tools#black_list", log_level, log_file, SysLogHandler.LOG_LOCAL2)
    else:
        gv.g_logger.init_logger(
            "ops_tools#black_list", log_level, 'syslog', SysLogHandler.LOG_LOCAL2)

def init_statsd():
    gv.statsd_conn = statsd.client.StatsClient(host=gv.statsdhost, port=gv.statsdport)

def init_mysql_keyword(cfg):
    db_pool = make_db_pool(cfg['mysql'],2)
    conn = db_pool.connection()
    cursor = conn.cursor()
    cursor.execute('''select trim(keyword) from black_list''')
    key_word_list = [row[0].decode('utf8').lower() for row in cursor.fetchall()]
    gv.keyword_trie = marisa_trie.Trie(key_word_list)
    cursor.close()
    conn.close()

def main():
    args = docopt.docopt(__doc__, version='1.0.0.0')
    cfg_file = get_conf_abspath(args)
    check_conf_validation(cfg_file)
    cfg = parse_conf_file(cfg_file)
    init_logger(cfg)
    get_global_vars(cfg)
    init_mysql_keyword(cfg)
    gv.redisoper=high2low(gv.redis_url)
    init_statsd()
    gv.d.start()
    while True:
        with Connection(gv.tmphigh_url) as conn:
            try:
                worker = Worker(
                    conn, gv.tmphigh_exchange, gv.tmphigh_queue, gv.tmphigh_routingkey)
                gv.g_logger.info('ops_tools black list start')
                worker.run()
            except Exception:
                gv.g_logger.error("ops_tools black list start %s happend!" % str(traceback.format_exc()))
    gv.d.join()
if __name__ == '__main__':
    main()
