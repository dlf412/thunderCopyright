from __future__ import absolute_import
import os
import sys
import logging
import logging.config
import traceback
from urllib import urlencode
from celery.result import ResultSet

__filedir__ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, __filedir__)

from app import app
from parse_config import parse_config
from db_txn import db_txn, db_execute, db_insert, db_result
from subprocess import PIPE, Popen


path = os.getenv("MW_HOME")
#config = parse_config('/'.join([path, 'etc', 'vddb_async.conf']))
logging.config.fileConfig('/'.join([path, 'etc', 'logging.conf']), disable_existing_loggers=False)

from logger import g_logger
from utils import trans2json
from stats import stats, QUERY_VDDB
import time

class TaskRes():
    def __init__(self, task, ret, out, err):
        self.task = task
        self.ret = ret
        self.out = out
        self.err = err

class TaskException(Exception):
    def __init__(self, ret=None, out=None, err=None):
        self.ret = ret
        self.out = out
        self.err = err

class Task():

    @app.task()
    def query(t, account, backends):
        #account {..., backends:[{'extra':, 'account':, 'backend':}]}
        #backends {id:{'capacity':, 'id':, 'vddb_address':}}
        logger = logging.getLogger("mw_celery_task")
        try:
            logger.info("receive task to query: task_uuid: %s, "
                        "site_asset_id: %s" % (t['uuid'], t['site_asset_id']))

            g_logger.info(trans2json(message="site_asset_id:%s, "
                          "task_uuid:%s, external_id:%s" % (t['site_asset_id'], t['uuid'],
                          t['external_id']), action="get task from celery"))

            urls = []
            for b in account['backends']:
                be = backends[b['backend']]#{'capacity':, 'id':, 'vddb_address':}
                opts = dict(level=b['level'], mode=b['mode'], extra=b['extra'])
                if account['hot'] == 'true':
                    opts['hot_user'] = account['hot_user']
                    opts['hot_pass'] = account['hot_pass']
                # if account['slicing'] == 'true':
                #     opts['slice'] = p['slice_duration']
                qs = urlencode(opts.items())
                urls.append('vdna://%s:%s@%s/?%s' % (account['backend_user'],
                                                     account['backend_pass'],
                                                     be['vddb_address'], qs))
            args = ['/'.join([os.getenv('MW_HOME'), 'lib', 'task_executor.py']),
                    '--task', str(t['id']), '--task-uuid', t['uuid'],
                    '--timestamp', str(t['created_at']),
                    '--account', str(account['id']),
                    '--site-domain', account['domain'],
                    '--site-asset-id', t['site_asset_id'],
                    '--clip-format', t['format'],
                    '--dna-url', t['dna_url']]
            if account['slicing'] == 'true':
                args.extend(['--slice-duration', str(account['slice_duration'])])
            if account['allow_partial'] == 'false':
                args.append('--fail-partial')
            # reverse query ingestion triggering is done by reverse_trigger.py
            # if account['do_reverse'] == 'true':
            #     args.extend('--reverse-query')
            for u in urls:
                args.extend(['--backend', u])
            if t['scope'] != None:
                for s in t['scope']:
                    args.extend(['--scope', s])
            for r in account['rules']:
                args.append('--' + r)
        except Exception:
            logger.error("generate command line failed, "
                         "uuid: %s, site_asset_id: %s" % \
                         (t['uuid'], t['site_asset_id']), exc_info=True)
            logger.debug("task: %s, account: %s, backends: %s" % \
                        (t, account, backends))
            raise TaskException(err="query failed, generate execute cmd failed")
        else:
            # bufsize=-1 usually means fully buffer the output, usually, ugh
            # please contact zhang_yichao@vobile.cn if stdout is blocked
            proc = None
            try:
                start_time = time.time()
                proc = Popen(args, close_fds=True, stdout=PIPE, bufsize= -1)
                #row = db_txn(pool, partial(self.record, t, proc.pid)) 
                logger.info("spawn a process to query, task_uuid: %s, "
                            "site_asset_id: %s, just wait til finished" %
                            (t['uuid'], t['site_asset_id']))
                g_logger.info(trans2json(message="site_asset_id:%s, "
                              "task_uuid:%s, external_id:%s" % (t['site_asset_id'],
                              t['uuid'], t['external_id']), action="start query vddb"))
                out, err = proc.communicate()
                ret = proc.wait()
                logger.info("query finished, return to manager, "
                            "task_uuid: %s, site_asset_id: %s, "
                            "ret: %s, out: %s, err: %s"
                             % (t['uuid'], t['site_asset_id'], ret, out, err))
                g_logger.info(trans2json(message="site_asset_id:%s, "
                             "task_uuid:%s, external_id:%s" % (t['site_asset_id'],
                              t['uuid'], t['external_id']), action="query vddb finished"))
                end_time = time.time()
                stats.timing(QUERY_VDDB, int(end_time-start_time)*1000)
                return TaskRes(t, ret, out, err)
            except:
                logger.error("spawn process catch exception, uuid: %s, "
                             "site_asset_id: %s, " % \
                             (t['uuid'], t['site_asset_id']),  exc_info=True)
                logger.debug("task: %s, account: %s" % (t, account))
                raise TaskException(err="query failed, spawn process failed")
