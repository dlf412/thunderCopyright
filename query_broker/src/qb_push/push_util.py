import logging
import kombu
from kombu import Connection, Producer, Exchange, Consumer
from mylogger import *
#from syslog_wrap import *
import json
import Queue
import threading
import push_global_vars as gv
import os
import subprocess
from subprocess import PIPE, Popen
import time
import commands
from utils import trans2json
import traceback
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


class Retry(object):
    default_exceptions = (Exception)

    def __init__(self, tries, exceptions=None, delay=0):
        """
        Decorator for retrying function if exception occurs

        tries -- num tries
        exceptions -- exceptions to catch
        delay -- wait between retries
        """
        self.tries = tries
        if exceptions is None:
            exceptions = Retry.default_exceptions
        self.exceptions = exceptions
        self.delay = delay

    def __call__(self, f):
        def fn(*args, **kwargs):
            exception = None
            for _ in range(self.tries):
                try:
                    return f(*args, **kwargs)
                except self.exceptions, e:
                    print "Retry, exception: " + str(e)
                    time.sleep(self.delay)
                    exception = e
            # if no success after tries, raise last exception
            raise exception
        return fn


# TODO: more functions should to be apended
def connect_rabbitmq(mq_url, queue_name):
    try:
        exchange = Exchange(queue_name, type='fanout')
        queue = kombu.Queue(queue_name, exchange, routing_key=queue_name)
        #connection = Connection('amqp://guest:guest@localhost:5672//')
        g_logger.debug(
            trans2json('connect to %s, queue is %s' % (mq_url, queue_name)))
        connection = Connection(mq_url)
        return connection
    except Exception, msg:
        #cas_system_log('error', 'connect rabbitmq failed [%s]' %(msg))
        g_logger.error(trans2json('connect rabbitmq failed [%s]' % (msg)))


@Retry(3, delay=2)
def download_file(swift_path, download_path):
    ret = 0
    err = ''
    try:
        swift_path_list = swift_path.split('/')
        container = swift_path_list[0]
        far_name = swift_path_list[-1]
        swift_name = swift_path[len(container) + 1:len(swift_path)]
        download_far_name = os.path.join(download_path, far_name)
        args = "%s/swift download %s  %s -o %s " % (
            gv.swith_path, container, swift_name, download_far_name)
        ret, _, err = popen(args)
        g_logger.info(trans2json('download file success: %s' % args))
    except Exception:
        g_logger.error(trans2json("download file error%s") %
                       traceback.format_exc())
    finally:
        return False if ret or err else True, download_far_name


@Retry(3, delay=2)
def upload_file(upload_path, file_path):
    ret = 0
    err = ''
    try:
        args = "%s/swift upload '%s' '%s' " % (
            gv.swith_path, upload_path, file_path)
        ret, _, err = popen(args)
        os.remove(file_path)
        g_logger.info(trans2json('upload file success'))
    except OSError:
        g_logger.error(trans2json(
            "delete or upload bt file %s  error %s" % (file_path, traceback.format_exc())))
    finally:
        return False if ret or err else True


def popen(cmd):
    proc = Popen(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    ret = proc.wait()
    out, err = proc.communicate()
    return ret, out, err
