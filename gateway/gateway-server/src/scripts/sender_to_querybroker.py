#coding: utf-8
#/usr/bin/python
# Filename:sender_to_QB.py

from kombu.pools import producers
import time
from kombu import Exchange, Queue
import json
import uuid
from kombu import Connection
import os
import sys

def call_MQ(case_json):
    connection = Connection('amqp://guest:guest@192.168.3.82:5672//')
    task_exchange = Exchange('download_task_exchange')
    task_queues = Queue('download_task_queue', task_exchange, routing_key='download_task_routing_key')

    print "123:%s"%(case_json)
    data=None
    with open(case_json) as f:
            data = json.loads(f.read())
    message = json.dumps(data)
    print type(message)
    print data
    
    with producers[connection].acquire(block=True) as producer: producer.publish(data,serializer='json',compression='bzip2',exchange=task_exchange,declare=[task_exchange],routing_key='download_task_routing_key')

def main():  
    if len(sys.argv) == 1 :  
        print "no input case_json."
    else:  
        LE=sys.argv  
        call_MQ(LE[1])
        #print LE[1]

         
if  __name__ == '__main__':
    main()  
  
