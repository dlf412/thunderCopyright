from kombu import Connection, Producer, Exchange, Queue

#: By default messages sent to exchanges are persistent (delivery_mode=2),
#: and queues and exchanges are durable.
# send.py


from kombu import Connection
from kombu.messaging import Producer
from entity import task_exchange
from kombu.transport.base import Message
import time
import sys
import uuid
import json

'''
connection = Connection('amqp://guest:guest@192.168.3.82:5672//')
channel = connection.channel()

message=Message(channel,body='Hello Kombu')

# produce
producer = Producer(channel,exchange=task_exchange)
producer.publish(message.body,routing_key='suo_piao')
'''
# submit_task
exchange = Exchange('submit_task')
queue = Queue('submit_task', exchange, routing_key='submit_task')

#f =  open("input_seed.json")
f =  open("input_test1.json")
with Connection('amqp://guest:guest@192.168.3.82:5672//') as connection, f:
    producer = Producer(connection)
    message = json.loads(f.read())
    for i in range(1):
        hash_id = str(uuid.uuid1())
        print hash_id
        message['params']['url']['hash'] = "url_hash#" + hash_id
        message['params']['thunder_hash'] = "thunder_hash#" + hash_id
        message = json.dumps(message)
        producer.publish(message, exchange=exchange, declare=[queue], routing_key='submit_task', serializer='json')
        message = json.loads(message)
