#! /usr/bin/env python

import sys
import threading
import dbpc
import getopt
from cas_config import gconf
from download_task_process import download_task_process
from watch_task_status import watch_task_status
from logging.handlers import SysLogHandler
from cas_utils import g_logger, g_logger_info

g_version = 'thunder1.2.1.0'

def print_usage ():
    print 'Usage: '
    print '%s [-v][-h] [-f config_file]' % sys.argv[0]
    print '\t-v: print version'
    print '\t-h: help information'
    print '\t-f: set config-file\'s absolute path'
    sys.exit (0)

def print_version ():
    print 'cas version: %s' % g_version
    sys.exit (0)

def get_opt ():
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


class task_warden(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.th = watch_task_status() 
        self.setDaemon(True)

    def run(self):
        self.th.run()

def main():
    try:
        get_opt ()
         
        print "mq dict ", gconf.mq_dict
        print "conf dict" , gconf.conf_dict
        g_logger.init_logger('CAS_watcher', gconf.conf_dict['log_level'], gconf.conf_dict['log_file'], SysLogHandler.LOG_LOCAL2)
        g_logger_info.init_logger('CAS_watcher', gconf.conf_dict['log_level'], gconf.conf_dict['log_file'], SysLogHandler.LOG_LOCAL1)

        watcher = task_warden()
        watcher.start()

        dp_th = dbpc.dbpc (gconf.dbpc_dict['host'],
                        gconf.dbpc_dict['port'],
                        gconf.dbpc_dict['service'],
                        gconf.dbpc_dict['component']+"-watcher",
                        gconf.dbpc_dict['interval'])
        dp_th.start ()

        watcher.join()
        dp_th.join()
    except Exception, msg:
        raise Exception('start service failed [%s]' %(msg))
        import traceback
        traceback.print_exc()
        sys.exit (-1)

if __name__ == '__main__':
    main()
