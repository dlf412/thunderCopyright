#!/usr/bin/env python

import sys
import os
try:
    import json
except:
    import simplejson as json
from cas_utils import *

tmp_dir = os.path.dirname (sys.argv[0])
tmp_dir = os.popen ('cd %s;pwd' % tmp_dir).read ().strip ()
g_bin_dir = os.path.abspath (tmp_dir)
g_base_dir = os.path.dirname (g_bin_dir)
tmp_dir = None

class config (object):
    def __init__ (self):
        self.conf_dict = {}
        self.dbpc_dict = {}
        self.mq_dict = {}
        self.conf_dict['bin_dir'] = os.path.join (g_base_dir, 'bin');
        self.conf_dict['etc_dir'] = os.path.join (g_base_dir, 'etc');
        self.conf_dict['var_dir'] = os.path.join (g_base_dir, 'var');
        self.conf_dict['tools_dir'] = os.path.join (self.conf_dict['bin_dir'], 'tools');

    def parse (self, confile):
        try:
            if (not os.path.exists (confile)):
                raise Exception('config file not exists')
            fp = open (confile, "r");
            content = fp.read ();
            fp.close ();

            dict_tmp = json.loads (content);

            self.conf_dict['log_level'] = dict_tmp['general']['log_level']
            self.conf_dict['log_file'] = dict_tmp['general']['log_file']
            self.conf_dict['retry_times'] = dict_tmp['general']['retry_times']
            self.conf_dict['retry_sleep'] = dict_tmp['general']['retry_sleep']
            self.conf_dict['redis'] = dict_tmp['redis']
            self.conf_dict['hot_queue'] = dict_tmp['hot_queue']
            self.conf_dict['downloader_cnt'] = dict_tmp['downloader_cnt']
            self.conf_dict['task_expire_time'] =  dict_tmp['task_expire_time']
            self.conf_dict['dispatcher_interval'] = dict_tmp['dispatcher_interval']
            self.conf_dict['watch_interval'] = dict_tmp.get('watch_interval', 10)
            #self.conf_dict['redis']['host'] = dict_tmp['redis']['host']
            #self.conf_dict['redis']['port'] = dict_tmp['redis']['port']
            self.conf_dict['warden'] = {}
            self.conf_dict['warden']['heartbeat_interval'] = dict_tmp['task_warden']['heartbeat_interval']
            self.conf_dict['warden']['timeout'] = dict_tmp['task_warden']['task_timeout']
            self.conf_dict['warden']['download_timeout'] = dict_tmp['task_warden']['total_download_time']
            
            self.conf_dict['statsd'] = {}
            self.conf_dict['statsd']['host'] = dict_tmp['statsd']['host']
            self.conf_dict['statsd']['port'] = dict_tmp['statsd']['port']
            
            self.mq_dict['server'] = dict_tmp['rabbitmq']['server']
            self.mq_dict['task_download'] = {}
            self.mq_dict['task_download']['queue_name'] = dict_tmp['rabbitmq']['task_download']['queue_name']
            self.mq_dict['task_download']['routing_key'] = dict_tmp['rabbitmq']['task_download']['routing_key']
            self.mq_dict['task_download']['exchange_name'] = dict_tmp['rabbitmq']['task_download']['exchange_name']
            self.mq_dict['task_download']['exchange_type'] = dict_tmp['rabbitmq']['task_download']['exchange_type']
            self.mq_dict['task_download_high'] = {}
            self.mq_dict['task_download_high']['queue_name'] = dict_tmp['rabbitmq']['task_download_high']['queue_name']
            self.mq_dict['task_download_high']['routing_key'] = dict_tmp['rabbitmq']['task_download_high']['routing_key']
            self.mq_dict['task_download_high']['exchange_name'] = dict_tmp['rabbitmq']['task_download_high']['exchange_name']
            self.mq_dict['task_download_high']['exchange_type'] = dict_tmp['rabbitmq']['task_download_high']['exchange_type']
            self.mq_dict['task_finish'] = {}
            self.mq_dict['task_finish']['queue_name'] = dict_tmp['rabbitmq']['task_finish']['queue_name']
            self.mq_dict['task_finish']['routing_key'] = dict_tmp['rabbitmq']['task_finish']['routing_key']
            self.mq_dict['task_finish']['exchange_name'] = dict_tmp['rabbitmq']['task_finish']['exchange_name']
            self.mq_dict['task_finish']['exchange_type'] = dict_tmp['rabbitmq']['task_finish']['exchange_type']
            self.dbpc_dict['host'] = dict_tmp['dbpc']['host']
            self.dbpc_dict['port'] = dict_tmp['dbpc']['port']
            self.dbpc_dict['service'] = dict_tmp['dbpc']['service']
            self.dbpc_dict['component'] = dict_tmp['dbpc']['component']
            self.dbpc_dict['interval'] = dict_tmp['dbpc']['interval']
            self.dbpc_dict['try_times_limit'] = dict_tmp['dbpc']['try_times_limit']


        except Exception, err:
            raise Exception (err)

gconf = config ()

if __name__ ==  "__main__":
    dbg_on ()
    if (len (sys.argv) == 1):
        print "Usage: %s config_file" %(sys.argv[0])
        sys.exit (1)
    config_file = sys.argv[1]
    salog_init ("ut@config", syslog.LOG_INFO)
    salog_debug ("'parse config file':'%s'" %config_file)

    try:
        gconf.parse (config_file)
    except Exception, msg:
        print_dbg ("'config file %s parsed failed: %s'" %(config_file, msg))
        sys.exit (1)
    print_dbg (gconf.conf_dict)
    print_dbg (gconf.zk_dict)
    print_dbg (gconf.query_dict)
