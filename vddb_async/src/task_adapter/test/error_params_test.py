from kombu import Connection
import datetime
from kombu import Exchange, Queue
from kombu.pools import producers
import json
import time
data = {
     "jsonrpc": "2.0",
    "params": {
        "extra_info": "",
        "extra_info_url": "seed_hash_swift_path",
        "dna": "swift_url",
        "site_asset_ids": [
            "url_hash#asdf12312safd12",
            "seed_hash#123123asdfasdf"
        ],
        "priority":0,
        "user" :3,
        "profile": "default",
        "query_scope": []
    },
    "id": 1
}

not_jsonrpc = {
        "priority":0,
        "user" :3, 
        "profile": "default",
        "query_scope": []
}
params_error = { 
     "jsonrpc": "2.0",
      "params": {
        "extra_info": "", 
        "dna": "swift_url",
        "site_asset_ids": [
            "url_hash#asdf12312safd12",
            "seed_hash#123123asdfasdf"
        ],  
        "user" :3, 
        "profile": "default",
        "query_scope": []
    },  
    "id": 1
}


connection = Connection('amqp://guest:guest@localhost:5672//')
message ={"haha":"hhe"}
exchange = Exchange('tasks')
def produce(producer, data):
    producer.publish(data, serializer='json',
            compression='bzip2',exchange=exchange,declare=[exchange],
            routing_key='message_queue')

#begin test
with producers[connection].acquire(block=True) as producer:
    # message is not jsonrpc
    for x in xrange(10):
        produce(producer, not_jsonrpc)
        time.sleep(1)
    # params is error
    for x in xrange(10):
        produce(producer, params_error)
        time.sleep(1)
    # right message
    for x in xrange(10):
        produce(producer, data)
        time.sleep(1)


