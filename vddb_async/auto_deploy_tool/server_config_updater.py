#!/usr/bin/env python

import os
import json
import sys

import mysql_url_parser
import http_url_parser

from check_setting import folder_checker
from check_setting import mysql_url_checker
from check_setting import http_url_checker


def config_updater (standard_conf, target_conf):
    default_conf = json.loads (open (standard_conf, 'r').read ())
    general_conf = default_conf['general']
    dbpc_conf = general_conf['dbpc']
    mysql_conf = default_conf['vddb_async']['mysql']
    swift_conf = general_conf['swift']
    #cache_conf = default_conf['vddb_async']['cache']
    hbase_conf = default_conf['vddb_async']['hbase']
    mq_conf = default_conf['vddb_async']['mq']
    matches_server = default_conf['vddb_async']['matches_server']
    rabbitmq_conf = default_conf['rabbitmq']
    conf = dict ()
    # media_wise db
    mysql_url_checker (mysql_conf['media_wise'])
    db_conf = mysql_url_parser.parse (mysql_conf['media_wise'])
    conf['db_host'] = json.dumps (db_conf['host'])
    conf['db_user'] = json.dumps (db_conf['user'])
    conf['db_pass'] = json.dumps (db_conf['pass'])
    conf['db_name'] = json.dumps (db_conf['db'])
    #statsd
    stats_conf = general_conf['statsd']
    # dbpc
    dbpc_url = "http://%s:%d" % (dbpc_conf['host'], dbpc_conf['port'])
    #http_url_checker (dbpc_url)
    conf['dbpc_server'] = json.dumps (dbpc_conf['host'])
    conf['dbpc_port'] = dbpc_conf['port']
    conf['dbpc_report_interval'] = dbpc_conf['heart_beat_interval']
    conf['dbpc_service'] = dbpc_conf['service']
    #conf['redis_cache_host'] = cache_conf['host']
    #conf['redis_cache_port'] = cache_conf['port']
    conf['hbase_hostname'] = hbase_conf['hostname']
    conf['hbase_port'] = hbase_conf['port']

    #mq
    conf['mq_connection'] = json.dumps(mq_conf['connection'])
    conf['matches_server'] = matches_server
    conf['query_queue'] = rabbitmq_conf['task_query']['queue_name']
    conf['query_exchange'] = rabbitmq_conf['task_query']['exchange_name']
    conf['query_routing_key'] = rabbitmq_conf['task_query']['routing_key']
    conf['result_exchange'] = rabbitmq_conf['query_result']['exchange_name']
    conf['result_routing_key'] = rabbitmq_conf['query_result']['routing_key']
    # swift
    conf['swift_auth'] = swift_conf['ST_AUTH']
    conf['swift_user'] = swift_conf['ST_USER']
    conf['swift_key'] = swift_conf['ST_KEY']
    conf['statsd_host'] = stats_conf['host']
    conf['statsd_port'] = stats_conf['port']
    for key in conf:
        value = ""
        if type (conf[key]) == list or type (conf[key]) == tuple:
            value = ",".join (conf[key])
        else:
            value = str (conf[key])
        os.system ("sed -i 's#^[[:space:]]*%s[[:space:]]*=.*#%s = %s#g' %s" 
                % (key, key, value, target_conf))

def main ():
    if (len (sys.argv) != 3):
        print 'Usage: %s standard_conf target_conf' % (sys.argv[0], )
        sys.exit ()
    standard_conf = sys.argv[1]
    target_conf = sys.argv[2]
    config_updater (standard_conf, target_conf)

if __name__ == "__main__":
    main ()
