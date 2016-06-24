from kombu import Connection, Exchange, Queue, Consumer, eventloop
from pprint import pformat
import json
from amqp_util import *
import time


'''
connection = Connection('amqp://guest:guest@localhost:5672//')
channel = connection.channel()

def process_media(body, message):
    print body
    message.ack()

# consume
consumer = Consumer(channel, task_queue)
consumer.register_callback(process_media)
consumer.consume()

while True:
    connection.drain_events()
'''


def handle_message(body, message):
    try:
        print " message is: ", body
        message.ack()
    except Exception, e:
        print 'handle message error'


connection = Connection('amqp://guest:guest@192.168.3.82:5672//')
consumer = connection.Consumer(queue, callbacks=[handle_message])
consumer.qos(prefetch_count=1)
consumer.consume()

for t in range(10000):
    try:
        connection.drain_events()
        #eventloop(connection)
    except Exception ,e:
        print e
        pass


#    with Consumer(connection, queue, callbacks=[handle_message]) as consumer:
#        for i in range(3):
#            print 'consumer start'
#            connection.drain_events(timeout=1)
#            #eventloop(connection)
#            print 'consumer stop'

