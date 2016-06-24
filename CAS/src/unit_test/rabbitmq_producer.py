import kombu
from kombu import Connection, Producer, Exchange
import time
import json
import random
import time

def gen_hash():
    seed = '123456789abcdefghijklmnopqrstuvwxyz'
    sa = []
    for i in range(6):
        sa.append(random.choice(seed))
    salt = ''.join(sa)
    return salt


def create_tasks(priority, flag, htype):
    s = {}
    s['jsonrpc'] = '2.0'
    s['id'] = 1
    s['method'] = 'submit_task'
    s['params'] = {}
    s['params']['priority'] = priority
    if flag == 1:
        s['params']['is_duplicated'] = 0
    s['params']['client_id'] = 1
    s['params']['host_name'] = 'aliyun001'
    
    if htype == 'url':
        s['params']['url'] = {}
        s['params']['url']['location'] = 'http://video.mp4'
        #s['params']['url']['hash'] = 'url_hash#123456'
        s['params']['url']['hash'] = str(gen_hash())
    elif htype == 'seed':
        s['params']['seed_file'] = {}
        s['params']['seed_file']['path'] = 'http://video.mp4'
        #s['params']['seed_file']['hash'] = 'seed_file#abcdef'
        s['params']['seed_file']['hash'] = str(gen_hash())
    elif htype == 'all':
        s['params']['url'] = {}
        s['params']['url']['location'] = 'http://video.mp4'
        #s['params']['url']['hash'] = 'url_hash#123456'
        s['params']['url']['hash'] = 'url_hash#' + str(gen_hash())
        s['params']['seed_file'] = {}
        s['params']['seed_file']['path'] = 'http://video.mp4'
        #s['params']['seed_file']['hash'] = 'seed_file#abcdef'
        s['params']['seed_file']['hash'] = 'seed_file#' + str(gen_hash())
    
    #s['params']['thunder_hash'] = 'thunder#' + '123#le#df'
    s['params']['thunder_hash'] = "thunder#" + str(gen_hash())
    #s['params']['thunder_hash'] = ''
    s['params']['protocol'] = 'http'
    s['params']['external_id'] = 'UUID-1234567890'
    return s

def test1():
    #exchange = Exchange('test', type='fanout')
    #queue = kombu.Queue('test', exchange, routing_key='test')
    
    exchange = Exchange('submit_task')
    queue = kombu.Queue('submit_task', exchange, routing_key='submit_task')
    with Connection('amqp://guest:guest@localhost:5672//') as connection:
        producer = Producer(connection)
        now_time = time.time()
        while True:
            #if time.time() - now_time >= 100:
            #    break
            print 'create tasks'
            s = create_tasks('high', 0, 'all') 
            js = json.dumps(s)
            print 'type s is %s' %(type(s))
            print 'length s is %s' %(len(js))
            producer.publish(js, exchange=exchange, routing_key='submit_task', declare=[queue], serializer='json', compression='zlib')
            #print '======='
            #time.sleep(0.1)
            break

def test2():
    #exchange = Exchange('test', type='fanout')
    #queue = kombu.Queue('test', exchange, routing_key='test')
    
    exchange = Exchange('submit_task')
    queue = kombu.Queue('submit_task', exchange, routing_key='submit_task')
    with Connection('amqp://guest:guest@localhost:5672//') as connection:
        producer = Producer(connection)
        while True:
            s = create_specified_tasks('123456', 'url') 
            js = json.dumps(s)
            producer.publish(js, exchange=exchange, routing_key='submit_task', declare=[queue], serializer='json', compression='zlib')
            time.sleep(5)
            s = create_specified_tasks('123456', 'seed_file') 
            js = json.dumps(s)
            producer.publish(js, exchange=exchange, routing_key='submit_task', declare=[queue], serializer='json', compression='zlib')
            break

def test3():
    #exchange = Exchange('test', type='fanout')
    #queue = kombu.Queue('test', exchange, routing_key='test')
    
    exchange = Exchange('submit_task', 'direct')
    queue = kombu.Queue('submit_task', exchange, routing_key='submit_task')
    
    high_exchange = Exchange('submit_task', 'direct')
    high_queue = kombu.Queue('submit_task_high', high_exchange, routing_key='submit_task_high')
    with Connection('amqp://guest:guest@localhost:5672//') as connection:
        producer = Producer(connection)
        while True:
            s = create_tasks('low', 0) 
            js = json.dumps(s)
            producer.publish(js, exchange=exchange, routing_key='submit_task', declare=[queue], serializer='json', compression='zlib')
            print "=====1===="
            time.sleep(5)
            #s = create_tasks('high') 
            #js = json.dumps(s)
            #producer.publish(js, exchange=high_exchange, routing_key='submit_task_high', declare=[high_queue], serializer='json', compression='zlib')
            #print '====2==='

def test4():
    #exchange = Exchange('test', type='fanout')
    #queue = kombu.Queue('test', exchange, routing_key='test')
    
    exchange = Exchange('download_task', 'direct')
    queue = kombu.Queue('download_task', exchange, routing_key='download_task')
    
    high_exchange = Exchange('download_task', 'direct')
    high_queue = kombu.Queue('download_task_high', high_exchange, routing_key='download_task_high')
    with Connection('amqp://guest:guest@192.168.3.82:5672//') as connection:
        producer = Producer(connection)
        while True:
            s = create_tasks('low', 0) 
            js = json.dumps(s)
            producer.publish(js, exchange=exchange, routing_key='download_task', declare=[queue], serializer='json', compression='zlib')
            print "=====1===="
            time.sleep(5)
            #s = create_tasks('high') 
            #js = json.dumps(s)
            #producer.publish(js, exchange=high_exchange, routing_key='download_task_high', declare=[high_queue], serializer='json', compression='zlib')
            #print '===2==='

if __name__ == '__main__':
    test1()
