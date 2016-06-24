import time
import json
import sys
sys.path.append('../')
from cas_utils import *

def message_handler(body, message):
    print body
    #js = json.loads(body)
    #print js.items()
    time.sleep(1)
    message.ack()


def test1():
    exchange = Exchange('test', type='fanout')
    queue = kombu.Queue('test', exchange, routing_key='test')

    with Connection('amqp://guest:guest@localhost:5672//') as connection:
        with Consumer(connection, queue, callbacks=[message_handler]) as consumer:
            while True:
                print 'start ....'
                connection.drain_events()
                print 'end...'

def test2():
    exchange = Exchange('download_task')
    queue = kombu.Queue('download_task', exchange, routing_key='download_task')

    with Connection('amqp://guest:guest@localhost:5672//') as connection:
        with Consumer(connection, queue, callbacks=[message_handler]) as consumer:
            while True:
                print 'start ....'
                connection.drain_events()
                print 'end...'


def test3():
    exchange = Exchange('finish_task')
    queue = kombu.Queue('finish_task', exchange, routing_key='finish_task')
    
    download_exchange = Exchange('download_task_high')
    download_queue = kombu.Queue('download_task_high', download_exchange, routing_key='download_task_high')
    
    download_exchange_low = Exchange('download_task')
    download_queue_low = kombu.Queue('download_task', download_exchange_low, routing_key='download_task')

    with Connection('amqp://guest:guest@192.168.3.82:5672//') as connection:
        with Consumer(connection, [download_queue, download_queue_low], callbacks=[message_handler]) as consumer:
            #consumer.add_queue(download_queue)
            #onsumer.consume()
            while True:
                print 'start ....'
                connection.drain_events()
                print 'end...'

def test4():
    
    download_exchange = Exchange('download_task')
    download_queue = kombu.Queue('download_task', download_exchange, routing_key='download_task')

    with Connection('amqp://guest:guest@localhost:5672//') as connection:
        with Consumer(connection, [download_queue], callbacks=[message_handler]) as consumer:
            #consumer.add_queue(download_queue)
            #onsumer.consume()
            while True:
                print 'start ....'
                connection.drain_events()
                print 'end...'

if __name__ == '__main__':
    test3()
