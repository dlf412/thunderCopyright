#! /usr/bin/env python

import sys
import threading
import dbpc
import getopt
from cas_config import gconf
from download_task_process import download_task_process
import cas_utils
from logging.handlers import SysLogHandler
from statsd_operator import statsd_operator

g_version = 'thunder1.2.1.0'

def print_usage():
    print 'Usage: '
    print '%s [-v][-h] [-f config_file]' % sys.argv[0]
    print '\t-v: print version'
    print '\t-h: help information'
    print '\t-f: set config-file\'s absolute path'
    sys.exit (0)

def print_version():
    print 'cas version: %s' % g_version
    sys.exit (0)

def get_opt():
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'vhf:')
    except getopt.GetoptError, err:
        raise Exception (err)

    config_file = ""
    if len (opts) == 0:
        print_usage ()

    for o, a in opts:
        if o == '-v':
            print_version ()
        if o == '-h':
            print_usage ()
        if o == '-f':
            config_file = a
            break

    try:
        gconf.parse (config_file)
    except Exception, err:
        raise Exception("config file %s parsed failed: %s\n" %(config_file, str (err)))


class fetch_jobs(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        #g_logger.debug(trans2json('=== routing_key is %s' %(routing_key)))
        #self.th = download_task_process(mq_url, queue_name, 'submit_task') 
        self.th = download_task_process()
        self.setDaemon(True)

    def run(self):
        self.th.run()


def main():
    try:
        get_opt ()
         
        print "mq dict ", gconf.mq_dict
        print "conf dict" , gconf.conf_dict
        cas_utils.g_logger.init_logger('CAS_dicpatcher', gconf.conf_dict['log_level'], gconf.conf_dict['log_file'], SysLogHandler.LOG_LOCAL2)
        cas_utils.g_logger_info.init_logger('CAS_dispatcher', gconf.conf_dict['log_level'], gconf.conf_dict['log_file'], SysLogHandler.LOG_LOCAL1)
        cas_utils.g_statsd = statsd_operator(gconf.conf_dict['statsd']['host'], gconf.conf_dict['statsd']['port'])
        
        thread_tasker = fetch_jobs() 
        thread_tasker.start() 

        dp_th = dbpc.dbpc (gconf.dbpc_dict['host'],
                        gconf.dbpc_dict['port'],
                        gconf.dbpc_dict['service'],
                        gconf.dbpc_dict['component']+"-dispatcher",
                        gconf.dbpc_dict['interval'])
        dp_th.start ()

        #join threads
        thread_tasker.join()
        dp_th.join()
    except Exception, msg:
        raise Exception('start service failed [%s]' %(msg))
        import traceback
        traceback.print_exc()
        sys.exit (-1)

if __name__ == '__main__':
    main()
