import redis
import traceback
import time

ADD_OK    = 1
ADD_ERROR = -1

GET_ERROR     = -2
MEMBER_EXISTS = -3

URL_HOT     = 'hot'
TASK_INFO   = 'task_info'
CREATE_TIME = 'create_time'
UPDATE_TIME = 'update_time'


def connect_redis(url):
    retries = 3
    retry_interval = 5
    while retries:
        try:
            r = redis.from_url(url)
            r.ping()
            return r
        except redis.exceptions.ConnectionError:
            retries -= 1
            if not retries:
                raise
            time.sleep(retry_interval)
            continue

def set_digest_updatetime(rds_conn,key,digest):
    if not rds_conn.sismember(key, digest):
        rds_conn.sadd(key,digest)
        update_time = get_updatime_time(rds_conn,digest)
        update_time_key = update_time[0:8]
        if update_time_key != key:
            if rds_conn.sismember(update_time_key,digest):
                rds_conn.srem(update_time_key,digest)
                if not rds_conn.smembers(key):
                    rds_conn.delete(key)

def set_hot_key(digest):
    return "hot#" + digest

def set_client_id(digest):
    return "client_id#" + digest

def write_crete_time(rds_conn,key,time):
    key = set_hot_key(key)
    if not rds_conn.hget(key,CREATE_TIME):
        rds_conn.hset(key,CREATE_TIME,time)

def write_update_time(rds_conn,key,time):
    key = set_hot_key(key)
    rds_conn.hset(key,UPDATE_TIME,time)

def get_updatime_time(rds_conn,key):
    key = set_hot_key(key)
    return rds_conn.hget(key,UPDATE_TIME)

def write_task_info(rds_conn,key,value):
    key = set_hot_key(key)

    return rds_conn.hset(key,TASK_INFO,value)

def get_task_info(rds_conn,key):
    key = set_hot_key(key)
    return (rds_conn.hget(key,TASK_INFO))

def get_url_hot(rds_conn,key):
    key = set_hot_key(key)
    return int(rds_conn.hget(key,URL_HOT))

def incr_url_hot(rds_conn,key,value=1):
    key = set_hot_key(key)
    rds_conn.hincrby(key,URL_HOT,value)

def client_id_exists(rds_conn,key,member):
    key = set_client_id(key)
    return rds_conn.sismember(key,member)

def write_client_id(rds_conn,key,member,ttl):
    digest = set_client_id(key)
    rds_conn.sadd(digest, member)
    ttl_seconds = rds_conn.ttl(digest)
    if not ttl_seconds:
        rds_conn.expire(digest,int(ttl)*24*3600)
    return ADD_OK

def get_client_id(rds_conn, key):
    key = set_client_id(key)
    return rds_conn.smembers(key)

def set_redis_aof():
    r = connect_redis(gv.redis_url)
    r.config_set('appendonly', 'yes')


