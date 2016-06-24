#coding: utf-8
#/usr/bin/python
# Filename:sender_to_vddb.py
 
from kombu.pools import producers
import time
from kombu import Exchange, Queue
import json
import uuid
from kombu import Connection
import os
import sys
import random
 
connection = Connection('amqp://guest:guest@182.92.154.107:5672//')
task_exchange = Exchange('query_queue')
#task_queues = Queue('submit_task', exchange, routing_key='submit_task')


data= {
    "jsonrpc": "2.0",
    "method" : "query",
    "params": {
         "extra_info": "{'client_id':'client_id123456'}",
         "extra_info_url": "",
         "files":
         "2014-08-04_13/kexbsn.flv.far.dna",
         "site_asset_id": [
             "url_hash#1asdf12312safd12",
             "file_hash#123456567"
         ],
         "priority": 0,
         "company": 2,
         "profile": "default",
         "query_scope": [],
         "external_id":"1234"
         },
         "id": 1
}

'''

-------------------url-----------------
Aug  4 16:50:11 slave1 slave1#2014-08-04 16:50:11,718#3644#vddbasync-stastistic#
consumer.py#66#INFO#normal#{"action": "fetchTask", "message": "get task from broker 
:{\"params\": {\"files\": \"2014-08-04_16/opt/thunder/downloader/bin/../
var/tmp/39d66cd2-1bb4-11e4-a73e-00163e001022/3ba35bc4-1bb4-11e4-a73e-00163e001022.dna\",
 \"profile\": \"default\", \"extra_info_url\": \"\", \"company\": 11, \"query_scope\": []
 , \"priority\": 0, \"site_asset_ids\": [\"url_hash#9a2662c968a0c78e56b1d4eefba639cacefe78f6\"
 , \"file_hash#2da33808c63cd83a4aae134e0cd09ca419f2f6fa\"], \"external_id\": 
 \"3987f3b81bb411e49fc600163e001180\", \"extra_info\": 
 {\"url\": \"http://10.162.207.221/sample/Wishyouwerehere.f4v\", 
 \"file_path\": \"./Wishyouwerehere.f4v\", \"client_id\": \"client_id123456\", 
 \"file_number\": null}}, \"jsonrpc\": \"2.0\", \"method\": \"query\", \"id\": 1}"}

------------------seed-----------------
{
    "params": {
        "files": "2014-08-06_15/opt/thunder/downloader/bin/../var/tmp/9ee4ff3a-1d3a-11e4-93b6-00163e001022/a90fd39a-1d3a-11e4-93b6-00163e001022.dna",
        "profile": "default",
        "extra_info_url": "2014-08-06_15/opt/thunder/downloader/bin/../var/tmp/8f61eb9a-1d3a-11e4-9ebe-00163e001022/65-018wmv.torrent",
        "company": 2,
        "query_scope": [],
        "priority": 0,
        "site_asset_ids": [
            "seed_hash#2466cba90f1a27b63b6d1088b167e5c94c3787e7-file_hash#9b1321db84cdbe93927ec74e3ae289f5a0b805a3",
            "url_hash#gatewayabcdefg873535377-file_hash#9b1321db84cdbe93927ec74e3ae289f5a0b805a3",
            "file_hash#9b1321db84cdbe93927ec74e3ae289f5a0b805a3"
        ],
        "external_id": "8ebdd3ac1d3a11e48bda00163e001180",
        "extra_info": {
            "url": "http://www.amtb.tw/bt/haerbin/torrent/65/65-018wmv.torrent",
            "seed_file": "2014-08-06_15/opt/thunder/downloader/bin/../var/tmp/8f61eb9a-1d3a-11e4-9ebe-00163e001022/65-018wmv.torrent",
            "file_path": "./65-018wmv/65-018-0001.wmv.td",
            "client_id": "client_id123456"
        }
    },
    "jsonrpc": "2.0",
    "method": "query",
    "id": 1
}


 match_size>0          "2014-08-04_13/cappella.merged.dna",(2 video/audio)
 match_size=1          "2014-08-04_13/Wish.f4v.far.dna"  (video/audio)
 match_size=1          "2014-08-04_13/Wish_You_Were_Here.1.adna" (audio)
 match_size>0          "2014-08-04_13/cappella_1.1.flv.1.adna" (2 audio)
 match_size=0          "2014-08-04_13/kexbsn.flv.far.dna"(video/audio)
 match_size=0          "2014-08-04_13/kexbsn.flv.far.dna.1.adna"(audio)
 match_size>0          "2014-08-04_13/cappella_1.1.flv.0.dna"(video)
 match_size=0          "2014-08-04_13/kexbsn.flv.far.dna.0.dna"(video)
'''


#print type(data)
site_asset_list=[]
temp_hash=random.randint(0,1000000000)


'''
-----------------seed_hash-----------------------
'''
#temp2="file_hash#abcdefg%s"%(temp_hash)
#site_asset_list.append(temp2)

#temp1="url_hash#abcdefg%s-%s"%(temp_hash,temp2)
#temp1="url_hash#a2cd80b4f94ffb6b91f82bbf96d6bba721383bbb"
#site_asset_list.append("url_hash#b52c2226-2106-11e4-a573-00163e001022")

#seed hash
#temp5="seed_hash#sabcdefg%s-%s"%(temp_hash,temp2)
#temp1="url_hash#a2cd80b4f94ffb6b91f82bbf96d6bba721383bbb"
#site_asset_list.append(temp5)

#data["params"]["extra_info_url"]="2014-08-06_15/opt/thunder/downloader/bin/../var/tmp/8f61eb9a-1d3a-11e4-9ebe-00163e001022/65-018wmv.torrent"
#data["params"]["extra_info"]={
#            "url": "http://www.amtb.tw/bt/haerbin/torrent/65/65-018wmv.torrent",
#            "seed_file": "2014-08-06_15/opt/thunder/downloader/bin/../var/tmp/8f61eb9a-1d3a-11e4-9ebe-00163e001022/65-018wmv.torrent",
#            "file_path": "./65-018wmv/65-018-0001.wmv.td",
#            "client_id": "client_id123456"
#        }

''' ------------url-----------------   '''
data["params"]["files"]="2014-08-04_13/cappella.merged.dna"
temp="file_hash#manualfileabcdefg%s"%(temp_hash)
site_asset_list.append(temp)

temp="url_hash#manualurlabcde%s"%(temp_hash)
site_asset_list.append(temp)

#temp4="thunder_hash#xabcdefg%s"%(temp_hash)
#site_asset_list.append(temp4)

''' 
 match=0
 url_hash#manualurlabcde717155788

   '''


#task_id
temp3="abc%s-bcd%s-efg%s"%(random.randint(0,1000),random.randint(0,1000),random.randint(0,1000))

data["params"]["external_id"]=temp3
data["params"]["site_asset_id"]=site_asset_list
#print data["params"]["site_asset_ids"]
print data
message = json.dumps(data)
#print type(message)
with producers[connection].acquire(block=True) as producer: \
        producer.publish(message,serializer='json',compression='zlib',\
            exchange=task_exchange,declare=[task_exchange],routing_key='query_queue')

print "end time:%s"%(time.strftime('%Y%m%d-%H%M%S'))
