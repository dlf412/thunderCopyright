from kombu import Connection
import datetime
from kombu import Exchange, Queue
from kombu.pools import producers
import json
import time
data = {
     "jsonrpc": "2.0",
    "params": {
        "extra_info": "{'client':4}",
        "extra_info_url": "seed_hash_swift_path",
        "dna": "dna_20131217/merge.dna",
        "site_asset_ids":
        [u"url_hash#11111111111111111111111",u"dna_hash#555555555555555",
            u"4444444444444"],
        "priority":0,
        "company" :11,
        "profile": "default",
        "seed_hash":["aaaaaaaaa", "bbbbbb"],
        "query_scope": [],
		"external_id":"11111111111111111111"
    },
    "id": 1
}
da =json.dumps(data)
connection = Connection('amqp://guest:guest@192.168.3.82:5672//')
message ={"haha":"hhe"}
exchange = Exchange('query_exchange')
print type(da)
with producers[connection].acquire() as producer:
    for x in xrange(1):
        producer.publish(da, serializer='json', compression='bzip2',exchange=exchange,declare=[exchange], routing_key='query_routing_key')
        time.sleep(1)
        print '1'
print type(da)
