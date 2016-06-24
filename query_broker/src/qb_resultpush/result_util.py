import logging
import kombu
from kombu import Connection, Producer, Exchange, Consumer
from mylogger import *
#from syslog_wrap import *
import json
import Queue
import threading
import result_global_vars as gv
import os
import subprocess
from subprocess import PIPE
import time
import commands

# g_logger will be initlized in main thread

g_logger = mylogger()
g_logger_info = mylogger()

task_queue = Queue.Queue()
task_mutex = threading.Lock()

task_logs = 'task_log_list'


class safe_lock(object):

    def __enter__(self):
        task_mutex.acquire()

    def __exit__(self, *args):
        task_mutex.release()


def trans2json(s, action=None):
    try:
        js = {}
        js['msg'] = s
        if action is not None:
            js['action'] = action
        sjs = json.dumps(js)
        return 'normal'+ '#' + sjs
    except Exception, msg:
        raise Exception('trans to json failed [%s]' %(msg))
