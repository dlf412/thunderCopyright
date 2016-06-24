#!/usr/bin/env python
#coding: utf-8

import time
import json
import yaml
import traceback
from datetime import datetime

import MySQLdb as mdb
from kombu import Exchange, Connection, Queue as MqQueue
from kombu.mixins import ConsumerMixin


cfg = None

# ==============================================================================
#  Helper functions
# ==============================================================================
def convert_field(value):
    if isinstance(value, unicode):
        return value.encode('utf8')
    elif isinstance(value, datetime):
        return value.strftime('%Y-%m-%d %H:%M:%S')
    return value


def execute_sql(conn, sql, args, fetch=False, commit=True):
    cur = conn.cursor()
    sql_args = [convert_field(arg) for arg in args]
    cur.execute(sql, sql_args)

    rows = None
    if fetch:
        conn.commit()
        rows = cur.fetchall()
    elif commit:
        conn.commit()
    cur.close()
    return rows
    

class Cleaner(ConsumerMixin):

    def __init__(self, connection, queue, db_conn, insert_sql, limit):
        self.connection = connection
        self.queue = queue
        self.db_conn = db_conn
        self.insert_sql = insert_sql
        self.limit = limit
        self.part_level = 0
        self.done_tasks = 0
        self._t1 = time.time()
        self.t1 = time.time()
        self.db_costs = []
        self.sum_db_costs = []
        self.total_costs = 0
        self.total_db_costs = 0

    def get_consumers(self, Consumer, channel):
        try:
            cus = [Consumer(queues=[self.queue],
                            accept=['pickle', 'json'],
                            callbacks=[self.process_task])]
        except Exception:
            print traceback.format_exc()
        return cus

    def print_process(self):
        self.part_level += 1
        now = time.time()
        sum_cost = now - self._t1
        self._t1 = now
        sum_db_cost = sum(self.db_costs)
        self.db_costs = []
        self.sum_db_costs.append(sum_db_cost)
        print 'Done tasks (%2d0%%): %-5d    cost: %.2f(s), db-cost: %.2f(s)' % (self.part_level, self.done_tasks, sum_cost, sum_db_cost)

    def db_commit(self):
        t1 = time.time()
        self.db_conn.commit()
        t2 = time.time()
        dt = t2-t1
        self.sum_db_costs.append(dt)
        
    def process_task(self, body, message):
        # print 'Got message:', body
        try:
            self.process_msg(body, self.db_conn, self.insert_sql)
            message.ack()
            self.done_tasks += 1
        except Exception:
            print '>> process_task ERROR: { %s }' % traceback.format_exc()

        if self.done_tasks % cfg['db']['count-per-commit'] == 0:
            self.db_commit()

        if self.done_tasks < self.limit and (float(self.done_tasks)/self.limit - self.part_level * 0.1) >= 0.0999999:
            self.print_process()
        elif self.done_tasks >= self.limit:
            self.db_commit()
            self.print_process()
            now = time.time()
            self.total_costs = now - self.t1
            self.total_db_costs = sum(self.sum_db_costs)
            print '-' * 60
            print 'Stopping.....'
            self.should_stop = True


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

        record = (cfg['custom-type'], client_id, thunder_hash, url_loc,
                  digest, algorithm,
                  mime_type, file_name, file_size, swift_path)
        try:
            t1 = time.time()
            execute_sql(db_conn, sql, record, commit=False)
            t2 = time.time()
            self.db_costs.append(t2-t1)
        except mdb.IntegrityError as e:
            print '>> DB error: { %r }' % e


def parse_args():
    from optparse import OptionParser

    parser = OptionParser()
    parser.add_option("-c", "--cfg", metavar="FILE", help="YAML config FILE")
    parser.add_option("-n", "--number", metavar="INTEGER", help="Number of messages to clean.")

    (opts, args) = parser.parse_args()
    if not opts.cfg:
        parser.error('Config file is required!')
    if not opts.number:
        parser.error('Number(n) is required!')

    return opts, args


def load_config():
    opts, args = parse_args()
    with open(opts.cfg, 'r') as f:
        config = yaml.load(f)
    config['number'] = int(opts.number)
    return config


def main():
    global cfg
    cfg = load_config()
    task_mq_cfg = cfg['task-mq']
    mq_url        = task_mq_cfg['url']
    routing_key   = task_mq_cfg['routing-key']
    exchange_name = task_mq_cfg['exchange']
    exchange_type = task_mq_cfg['type']
    queue_name    = task_mq_cfg['queue']
    insert_sql    = cfg['db']['sqls']['insert']

    clean_conn = mdb.connect(**cfg['db']['args'])
    clean_conn.cursor().execute("set names utf8")

    def on_declared(name, messages, consumers):
        # print 'declared:', name, messages, consumers
        pass

    exchange = Exchange(exchange_name, type=exchange_type)
    queue = MqQueue(queue_name, exchange,
                    routing_key=routing_key, on_declared=on_declared)
    print '''MQ information:
    mq_url        = %s
    exchange_name = %s
    exchange_type = %s
    routing_key   = %s
    queue_name    = %s ''' % (mq_url, exchange_name, exchange_type, routing_key, queue_name)
    print '-' * 60
    t1 = time.time()
    try:
        with Connection(mq_url) as conn:
            worker = Cleaner(conn, queue, clean_conn, insert_sql, cfg['number'])
            worker.run()
    except KeyboardInterrupt:
        print '>> KeyboardInterrupt'

    worker.db_commit()
    clean_conn.close()
    
    t2 = time.time()
    print '=' * 80
    print '''DONE: < %d > tasks cleaned,
    Worker: cost = %.2f(s), db-cost = %.2f(s)
    Total : cost = %.2f(s)
    ''' % (worker.done_tasks,
           worker.total_costs, worker.total_db_costs,
           t2-t1)


if __name__ == '__main__':
    main()
