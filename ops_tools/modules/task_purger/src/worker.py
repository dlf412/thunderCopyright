#!/usr/bin/env python
#coding: utf-8

import os
import signal
import time
import json
import traceback
from datetime import datetime
from logging.handlers import SysLogHandler

import yaml
import requests
import MySQLdb as mdb
from kombu import Exchange, Connection, Queue as MqQueue
from kombu.exceptions import MessageStateError
from kombu.mixins import ConsumerMixin

from utils import execute_sql, insert_vddb, timeit
from common.mylogger import mylogger
from common import dbpc


# ==============================================================================
#  Global variables
# ==============================================================================
cfg = None
logger = None

# def stop_all(signum, frame):
#     logger.warning('@@@ kill all by %d.' % os.getpid())
#     time.sleep(0.2)
#     os.killpg(os.getpgid(os.getpid()), signal.SIGKILL) 
#     return



class PurgeWorker(ConsumerMixin):
    
    def __init__(self, connection, queue, db_conn, insert_sql):
        self.connection = connection
        self.queue = queue
        self.db_conn = db_conn
        self.insert_sql = insert_sql
        logger.info('Init MQ ok!')


    def get_consumers(self, Consumer, channel):
        return [Consumer(queues=[self.queue],
                         accept=['pickle', 'json'],
                         callbacks=[self.process_task])]


    def process_task(self, body, message):
        logger.info('Got message: %r' % body)
        try:
            self.process_msg(body, self.db_conn, self.insert_sql)
            message.ack()
        except Exception as e:
            logger.error('process_task ERROR: << %s >>' % traceback.format_exc())
        logger.info('============================')


    def process_msg(self, body, db_conn, sql):
        if isinstance(body, (str, unicode)):
            body = json.loads(body)
            
        params = body.get('params')
        
        task_uuid    = params.get('external_id')
        client_id    = params.get('additional_info').get('client_id')
        thunder_hash = params.get('thunder_hash')
        digest       = params.get('digest')
        # URL
        url = params.get('url')
        url_loc  = url.get('location')
        url_hash = url.get('hash')
        # Seed
        seed_file = params.get('seed_file', {})
        seed_hash  = seed_file.get('hash', '')
        swift_path = seed_file.get('path', '')

        algorithm = params.get('digest_algorithm')
        mime_type = params.get('mime_type')
        file_name = params.get('file_name')
        file_size = params.get('file_size')

        if cfg['vddb-async']['should-insert']:
            logger.info('Insert to vddb: %s' % task_uuid)
            insert_vddb(cfg['vddb-async']['url'], [thunder_hash, url_hash, seed_hash], logger)

        record = (cfg['custom-type'], client_id, thunder_hash, url_loc,
                  digest, algorithm,
                  mime_type, file_name, file_size, swift_path)
        try:
            execute_sql(db_conn, sql, record)
        except mdb.IntegrityError:
            pass


# ==============================================================================
#  Mirror functions
# ==============================================================================    
def parse_args():
    from optparse import OptionParser

    parser = OptionParser()
    parser.add_option("-c", "--cfg", metavar="FILE", help="YAML config FILE")
    parser.add_option("-d", "--db", metavar="STRING", choices=("mysql", "hbase"),
                      help="Database type: mysql/hbase.")
    parser.add_option("--log-file", metavar="FILE", help="Log to file")
    parser.add_option("--log-level", metavar="STRING", help="Log level")

    (opts, args) = parser.parse_args()
    if not opts.cfg:
        config_path = os.getenv('PROG_CONFIG')
        if config_path:
            opts.cfg = config_path
        else:
            parser.error('Config file is required!')

    return opts, args


def load_config():
    opts, args = parse_args()
    with open(opts.cfg, 'r') as f:
        config = yaml.load(f)

        if opts.log_file:
            config['log']['file'] = opts.log_file
        if opts.log_level:
            config['log']['level'] = opts.log_level

        config['log']['level'] = config['log']['level'].upper()
    return config


def loop():
    task_mq_cfg = cfg['task-mq']
    mq_url        = task_mq_cfg['url']
    routing_key   = task_mq_cfg['routing-key']
    exchange_name = task_mq_cfg['exchange']
    queue_name    = task_mq_cfg['queue']
    insert_sql    = cfg['db']['sqls']['insert']

    while True:
        try:
            purge_conn = mdb.connect(**cfg['db']['args'])
            purge_conn.cursor().execute("set names utf8")
            with Connection(mq_url) as conn:
                exchange = Exchange(exchange_name)
                queue = MqQueue(queue_name, exchange, routing_key=routing_key)
                worker = PurgeWorker(conn, queue, purge_conn, insert_sql)
                worker.run()
            purge_conn.close()
        except KeyboardInterrupt:
            raise
        except Exception as e:
            logger.info('loop() Exception: << %s >>' % traceback.format_exc())
            time.sleep(0.5)


def main():
    global cfg, logger, execute_sql
    
    cfg = load_config()
    log_cfg = cfg['log']
    log_file = log_cfg['file']
    log_level = log_cfg['level']

    logger = mylogger()
    logger.init_logger('task-purger', log_level, log_file,
                       SysLogHandler.LOG_LOCAL1) # For debug

    logger.info('Starting...................')
    
    execute_sql = timeit(execute_sql, 'SQL', logger)
    # signal.signal(signal.SIGQUIT, stop_all)
    # signal.signal(signal.SIGTERM, stop_all)

    dbpc_cfg = cfg['dbpc']
    DBPC_HOST      = dbpc_cfg['host']
    DBPC_PORT      = int(dbpc_cfg['port'])
    DBPC_SERVICE   = dbpc_cfg['service']
    DBPC_COMPONENT = dbpc_cfg['component']
    DBPC_INTERVAL  = int(dbpc_cfg['interval'])
    t_dbpc = dbpc.dbpc(DBPC_HOST, DBPC_PORT,
                       DBPC_SERVICE, DBPC_COMPONENT,
                       DBPC_INTERVAL)
    t_dbpc.start()

    try:
        loop()
    except KeyboardInterrupt:
        pass
    logger.info('Stopping...................')
    print 'THE END.'


if __name__ == '__main__':
    main()
