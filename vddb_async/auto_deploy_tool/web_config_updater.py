#! /usr/bin/env python

import json
import sys

from check_setting import mysql_url_checker, folder_checker
from file_utility import load_file_content, save_file_content

def config_updater (standard_conf, target_conf):
    standard_content = load_file_content (standard_conf);
    target_content = load_file_content (target_conf);

    standard_dict = json.loads (standard_content);
    target_dict = json.loads (target_content);
    cache_conf = standard_dict['vddb_async']['cache']
    hbase_conf = standard_dict['vddb_async']['hbase']
    dbpc_conf = standard_dict['general']['dbpc']
    #redis
    #conf['server'] = dbpc_conf['host']
    #conf['port'] = dbpc_conf['port']
    #conf['report_interval'] = dbpc_conf['heart_beat_interval']
    for key in ('host', 'port'):
        target_dict['redis_cache'][key] = cache_conf[key]
    for key in ('hostname', 'port'):
        target_dict['hbase'][key] = hbase_conf[key]
    target_dict['dbpc']['server'] = dbpc_conf['host']
    target_dict['filter_vddbcompany'] = standard_dict['vddb_async']['filter_vddbcompany']

    target_dict['dbpc']['port'] = dbpc_conf['port']
    target_dict['dbpc']['service'] = dbpc_conf['service']
    target_dict['dbpc']['report_interval'] = dbpc_conf['heart_beat_interval']
    new_content = json.dumps (target_dict, sort_keys=True, indent=4);
    save_file_content (target_conf, new_content);

def main ():
    if (len (sys.argv) != 3):
        print 'Usage: %s standard_conf target_conf' %sys.argv[0];
        sys.exit ();
    standard_conf = sys.argv[1];
    target_conf = sys.argv[2];
    config_updater (standard_conf, target_conf);

if __name__ == '__main__':
    main ();
