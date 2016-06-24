from tm_sqls import *
import happybase

from server import catch_and_die
from datetime import datetime
from DBUtils.PersistentDB import PersistentDB
from functools import partial
import MySQLdb
from os import _exit, getpid
from socket import getfqdn
from time import sleep
from dbpc import dbpc
from kingchecker import Kingchecker
import subprocess
from subprocess import Popen
from redis import Redis
from db_txn import db_execute, db_query, db_result, db_txn
from redis.connection import BlockingConnectionPool
import time
try:
    import simplejson as json
except:
    import json

def trans2json(**kwargs):
    return "normal#"+json.dumps(kwargs)

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
                    #self.logger.info('Retry, exception: %s', e)
                    time.sleep(self.delay)
                    exception = e
            # if no success after tries, raise last exception
            raise exception
        return fn

# making connection pool
def make_hbase_pool(config):
    return happybase.ConnectionPool(int(config['hbase_max_conns']),
                                    host=config['hbase_hostname'],
                                    port=int(config['hbase_port']),
                                    timeout=int(config['hbase_timeout']))

def make_redis_conn(config):
    return Redis(connection_pool=BlockingConnectionPool(
                 max_connections=int(config['redis_cache_max_conns']),
                 host=config["redis_cache_host"],
                 port=int(config['redis_cache_port']),
                 db=int(config['redis_cache_db'])))

def make_db_pool(config, conns):
    # custom connecting method, so we can set up connection config immediately
    # after connecting to the server
    def make_conn(config, *args, **kwargs):
        conn = MySQLdb.connect(host=config["db_host"],
                               port=int(config["db_port"]),
                               user=config["db_user"],
                               passwd=config["db_pass"],
                               db=config["db_name"], charset='utf8',
                               use_unicode=False)
        cur = conn.cursor()
        cur.execute('set time_zone="+0:00"')
        cur.close()
        conn.commit()
        return conn
    # persistent db binds connections to threads
    return PersistentDB(creator=partial(make_conn, config), maxconnections=conns,
                        blocking=True)

# kingship checking and acquisition
@catch_and_die('kingchecker')
def check_kingship(config, pool, kev, module, timeout, logger):
    # use local fully qualified domain name
    # NOTE: fqdn must be properly set on production machines
    host = getfqdn()
    # use pid as port number, since we don't listen on ports
    port = getpid()

    def do_check():
        # NOTE: the algorithm is to use the record locking and auto txn rollback
        #       as a method of synchronization between distributed processes
        #       with where conditions, only 1 contender can update the original
        #       row, and when he updates it with his process info, he's the king
        #       insertion works likewise (with module name as unique key)

        # first, try to sit on the throne which looks like deserted, or like
        # owned by us
        rc, _ = yield db_execute(USURP, host, port, module, host, port,
                                 timeout)
        if rc == 1:             # yes we sat down
            yield db_result(True)
        # we couldn't sit down, is there actually a throne?
        rc, _ = yield db_query(CHECK_THRONE, module)
        if rc == 1:             # yes there is, it's just occupied
            yield db_result(False)
        # the throne is not there yet, make one and sit on it!
        rc, _ = yield db_execute(MAKE_THRONE, module, host, port)
        # the throne belongs to its maker!
        yield db_result(rc == 1)
    # if we started as slave, log on the first time. don't whine every timeout
    first_time = True
    while True:
        for i in [3, 2, 1]:
            is_king = False
            try:
                is_king = db_txn(pool, do_check)
            except:
                logger.error('failed to acquire kingship, %s',
                             'retrying' if i > 1 else 'exiting')
                if i > 1:
                    sleep(3)
            else:
                break
        if is_king:
            if not kev.isSet():
                logger.info('enthroned, to notify task fetcher')
                kev.set()
        elif kev.isSet():
            # we were king and now slave, exit the program so worker threads
            # won't do world-changing work
            # whe we restart, we'll be slave and won't do real work
            logger.info('stepping down, to be restarted as slave')
            _exit(3)  # no longer king, die shamefully
        elif first_time:
            logger.info('starting as slave')
            first_time = False
        # sleep shorter than timeout and try to update our heartbeat early
        # in case other contenders steal our throne
        sleep(timeout / 2)

def datestr(ts):
    return datetime.fromtimestamp(ts).strftime('%Y%m%d')

def start_dbpc(config, module_name):
    '''
        construct a dbpc object then start a new thread
    '''
    dbpc_sender = dbpc(config['dbpc_server'], int(config['dbpc_port']),
            config['dbpc_service'], config['dbpc_component_prefix']+module_name,
                    int(config['dbpc_report_interval']))
    dbpc_sender.start()

def start_kingchecker(config, module_name, timeout):
    '''
        start_kingcheck include two step,
        1.block current thread until it become master
        2.once a certain time interval to check, if found itself not master,
          then exit current process
        #NOTE, this fun should called after start_dbpc if needed
    '''
    host = getfqdn()
    port = getpid()
    king_checker = Kingchecker(module_name, host, port,
            int(timeout), host=config['db_host'],
            port=int(config['db_port']), user=config['db_user'],
            passwd=config['db_pass'], db=config['db_name'])
    king_checker.check_util_king()
    king_checker.start()

def popen(cmd):
    proc = Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    ret = proc.wait()
    out, err = proc.communicate()
    return ret, out, err


