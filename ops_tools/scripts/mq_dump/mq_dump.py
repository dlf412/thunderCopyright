#!/usr/bin/env python
#coding: utf-8

import os
import sys
import time
import json
import yaml
import traceback
import csv
# from datetime import datetime

from kombu import Exchange, Connection, Queue as MqQueue
from kombu.mixins import ConsumerMixin
from kombu.exceptions import MessageStateError

cfg = None

class Cleaner(ConsumerMixin):

    def __init__(self, connection, queue, limit):
        self.connection = connection
        self.queue = queue
        self.limit = limit
        self.part_level = 0
        self.done_tasks = 0
        self._t1 = time.time()
        self.t1 = time.time()
        self.total_costs = 0

        self.csvf = open(cfg['outfile'], 'wb')
        self.csvwriter = csv.writer(self.csvf)


    def get_consumers(self, Consumer, channel):
        try:
            cus = [Consumer(queues=[self.queue],
                            accept=['pickle', 'json'],
                            callbacks=[self.process_task])]
        except Exception:
            print traceback.format_exc()
            self.should_stop = True
        return cus

    def print_process(self):
        self.part_level += 1
        now = time.time()
        sum_cost = now - self._t1
        self._t1 = now
        self.csvf.flush()
        print 'Done tasks (%2d0%%): %-5d    cost: %.2f(s)' % (self.part_level, self.done_tasks, sum_cost)

    def finish(self):
        self.print_process()
        now = time.time()
        self.total_costs = now - self.t1
        print '-' * 60
        print 'Stopping.....'
        self.csvf.flush()
        self.csvf.close()
        self.should_stop = True

    def process_task(self, body, message):
        # print 'Got message:', body
        try:
            self.process_msg(body)
            # message.requeue()
            self.done_tasks += 1
        except MessageStateError as e:
            print '>>> %r' % e
        except Exception:
            print '>> process_task ERROR: { %s }' % traceback.format_exc()
            self.finish()

        if (self.done_tasks < self.limit
            and (float(self.done_tasks)/self.limit - self.part_level * 0.1) >= 0.0999999):
            self.print_process()
        elif self.done_tasks >= self.limit:
            self.finish()


    def save_record(self, record):
        self.csvwriter.writerow(record)


    def process_msg(self, body):
        if isinstance(body, (str, unicode)):
            body = json.loads(body)

        params = body.get('params')

        record = []
        for accessor in cfg['dump-fields']:
            cur = params
            if isinstance(accessor, (str, unicode)):
                accessor = [accessor]
            for key in accessor:
                cur = cur[key]
            if isinstance(cur, unicode):
                cur = cur.encode('utf-8')
            record.append(cur)

        self.save_record(record)


def parse_args():
    from optparse import OptionParser

    parser = OptionParser()
    parser.add_option("-c", "--cfg", metavar="FILE", help="YAML config FILE")
    parser.add_option("-o", "--outfile", metavar="FILE", help="Output file name.")
    parser.add_option("-n", "--number", metavar="INTEGER", help="Number of messages to clean.")

    (opts, args) = parser.parse_args()
    if not opts.cfg:
        parser.error('Config file is required!')
    if not opts.outfile:
        opts.outfile = 'output.csv'
    if not opts.number:
        parser.error('Number(n) is required!')

    if os.path.exists(opts.outfile):
        res = raw_input("Replace output file <%s>? [y/n]:" % opts.outfile)
        if res not in ('Y', 'y', 'yes'):
            print '>>> Abort!'
            sys.exit(-1)
        
    return opts, args


def load_config():
    opts, args = parse_args()
    with open(opts.cfg, 'r') as f:
        config = yaml.load(f)
        
    config['outfile'] = opts.outfile
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

    def on_declared(name, messages, consumers):
        # print 'declared:', name, messages, consumers
        pass

    exchange = Exchange(exchange_name, type=exchange_type)
    queue = MqQueue(queue_name, exchange,
                    routing_key=routing_key, on_declared=on_declared)
    print '''Information:
  MQ:
    mq_url        = %s
    exchange_name = %s
    exchange_type = %s
    routing_key   = %s
    queue_name    = %s
    
  Other:
    csv_file      = %s
    ''' % (mq_url, exchange_name, exchange_type, routing_key, queue_name,
           cfg['outfile'])
    print '-' * 60
    t1 = time.time()
    try:
        with Connection(mq_url) as conn:
            worker = Cleaner(conn, queue, cfg['number'])
            worker.run()
    except KeyboardInterrupt:
        print '>> KeyboardInterrupt'

    if not worker.csvf.closed:
        worker.csvf.flush()
        worker.csvf.close()

    t2 = time.time()
    print '=' * 80
    print '''DONE: < %d > tasks dumpd(requeued),
    Worker: cost = %.2f(s)
    Total : cost = %.2f(s)
    ''' % (worker.done_tasks,
           worker.total_costs, t2-t1)


if __name__ == '__main__':
    main()
