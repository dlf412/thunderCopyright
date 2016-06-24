#! -*- coding:cp936 -*-
# entity.py
from kombu import Exchange, Queue

task_exchange = Exchange('tasks', type='direct')
task_queue = Queue('finish_task', task_exchange, routing_key='suo_piao')

