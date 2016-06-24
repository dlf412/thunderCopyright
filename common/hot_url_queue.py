#! /usr/bin/env python
#coding: utf-8

import redis
import time
try:
    import json
except:
    import simplejson as json


class ConnectionError(Exception):
    pass
class HotKeyError(Exception):
    pass
class FullError(Exception):
    pass
class TimeoutError(Exception):
    pass
class OperateError(Exception):
    pass

def catch_exceptions(f):
    def fn(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except redis.TimeoutError, err:
            raise TimeoutError(str(err))
        except redis.ResponseError, err:
            if "OOM command not allowed" in str(err):
                raise FullError(str(err))
            else:
                raise OperateError(str(err))
        except redis.RedisError, err:
            raise OperateError(str(err))
    return fn
    
class HotUrlQueue(object):
    '''
    using redis impl hot_url_queue
    hot_key: the sortedset key, default is hot
    url: redis format url, like: 'redis://host:port/db'
    db: redis db, 
    '''

    def __init__(self, hot_key='hot', url="redis://127.0.0.1", db=None, **kwargs):
        self._conn = None
        self._conn = redis.from_url(url, db=db, **kwargs)
        try:
            self._conn.ping()
        except redis.ConnectionError, err:
            raise ConnectionError(str(err))
        self._hot_key = hot_key
        if self._conn.exists(self._hot_key) and self._conn.type(self._hot_key) != 'zset':
            raise HotKeyError('hot key in redis but not zset type')

    @catch_exceptions
    def set_hot(self, *args, **kwargs):
        '''
          set_hot(self, *args, **kwargs)
          Set any url_task of hot, element-name pairs to the hot_key. Pairs
          can be specified in two ways:
          
          As *args, in the form of: url_task1, hot1, url_task2, hot2, ...

          or as **kwargs, in the form of: url_task1=hot1, url_task2=hot2, ...
          
          The following example would set four values to the hot_key:
          hot_url_queue.set_hot('url_task1', 1.1, 'url_task2', 2.2, url_task3=3.3, url_task4=4.4)
        '''
        return self._conn.zadd(self._hot_key, *args, **kwargs)
    
    @catch_exceptions
    def incr_hot(self, url_task, count=1):
        return self._conn.zincrby(self._hot_key, url_task, count)
    
    @catch_exceptions
    def get_lowest_hots(self, count=1, withhots=False):
        if count <= 0:
            return []
        else:
            return self._conn.zrange(self._hot_key, 0, count-1, withscores=withhots)
    
    @catch_exceptions
    def get_highest_hots(self, count=1, withhots=False):
        if count <= 0:
            return []
        else:
            return self._conn.zrevrange(self._hot_key, 0, count-1, withscores=withhots)

    @catch_exceptions
    def remove_highest_hots(self, count=1):
        if count <= 0:
            return 0
        else:
            return self._conn.zremrangebyrank(self._hot_key, -1, 0-count)

    @catch_exceptions
    def remove_lowest_hots(self, count=1):
        if count <= 0:
            return 0
        else:
            return self._conn.zremrangebyrank(self._hot_key, 0, count-1)

    @catch_exceptions
    def remove_by_urls(self, *url_tasks):
        return self._conn.zrem(self._hot_key, *url_tasks)

    @catch_exceptions
    def pop_highest_hots(self, count=1):
        url_tasks = self.get_highest_hots(count)
        if url_tasks:
            self.remove_by_urls(*url_tasks)
        return url_tasks

    @catch_exceptions
    def pop_lowest_hots(self, count=1):
        url_tasks = self.get_lowest_hots(count)
        if url_tasks:
            self.remove_by_urls(*url_tasks)
        return url_tasks

    @catch_exceptions
    def get_size(self):
        return self._conn.zcard(self._hot_key)

    @catch_exceptions
    def get_hot_by_url(self, url_task):
        return self._conn.zscore(self._hot_key, url_task)

    @catch_exceptions
    def get_url_count_by_hot(self, min_hot, max_hot):
        return self._conn.zcount(self._hot_key, min_hot, max_hot)


    @catch_exceptions
    def get_url_tasks_by_hot(self, min_hot, max_hot, withhots=False):
        return self._conn.zrangebyscore(self._hot_key, min_hot, max_hot, withscores=withhots)

    @catch_exceptions
    def remove_url_tasks_by_hot(self, min_hot, max_hot):
        return self._conn.zremrangebyscore(self._hot_key, min_hot, max_hot)

    @catch_exceptions
    def get_used_memory(self):
        return int(self._conn.info()['used_memory'])

    @catch_exceptions
    def get_max_memory(self):
        return int(self._conn.config_get()['maxmemory'])

    def __del__(self):
        if self._conn:
            del self._conn



if __name__ == '__main__':
    huq = HotUrlQueue()
    huq.set_hot('aaa', 1)
    huq.set_hot('bbb', 2)
    huq.set_hot('ccc', 3)
    huq.set_hot('ddd', 2)
    huq.set_hot('eee', 5)
    huq.set_hot('fff', 15)
    huq.set_hot('ggg', 8)

    huq.set_hot('hhh', 100)
    
    print "lowest:", huq.get_lowest_hots(10)
    print "highest:", huq.get_highest_hots(10)
    print "size:", huq.get_size()
    print "aaa's hot:", huq.get_hot_by_url('aaa')
    huq.incr_hot('aaa', 10)
    print "aaa's hot:", huq.get_hot_by_url('aaa')
    print "get url count by hot:", huq.get_url_count_by_hot(1, 2)
    print "get urls by hot:", huq.get_url_tasks_by_hot(1, 2)

    huq.remove_highest_hots()
    print "highest:", huq.get_highest_hots()
    huq.remove_lowest_hots()
    print "lowest:", huq.get_lowest_hots()
    print "size:", huq.get_size()

    print 'pop highest_hots:', huq.pop_highest_hots()
    print 'pop lowest_hots:', huq.pop_lowest_hots()

    
    print 'remove size:', huq.remove_by_urls('ccc')
    print "size:", huq.get_size()

    print 'test end ============'

