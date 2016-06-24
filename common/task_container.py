#! /usr/bin/env python
# coding: utf-8

'''
Reference:
    TaskContainer impl using redis
    the data struct is hashtable
    data format is:
    hash key is digest
    status: init, processing, error#errno_msg, finish 
    duplicated: 0/1
    task_info: json rpc格式
    create_time：任务的创建时间，由dispatcher创建
    update_time: cas dispatcher模块初始化，downloader更新。用于判断downloader是否存活(downloader 心跳)
    tries: 此任务的执行次数
    execute_time: 总的执行时间, 单位秒
    worker: 当前执行的机器，格式：worker_prefix#host:pid
'''

import redis
try:
    import json
except ImportError:
    import simplejson as json


ONE_DAY = 24 * 3600
ONE_HOUR = 3600

class TaskContainerError(Exception):
    pass


class ConnectionError(TaskContainerError):
    pass


class FullError(TaskContainerError):
    pass


class TimeoutError(TaskContainerError):
    pass


class OperateError(TaskContainerError):
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


class TaskContainer(object):

    def __init__(self, url="redis://127.0.0.1:6379/0", finish_expire=ONE_HOUR, worker_prefix='Downloader', **kwargs):
        self._conn = None
        self._conn = redis.from_url(url, db=None, **kwargs)
        self._finish_expire = finish_expire
        self.worker_prefix = worker_prefix
        try:
            self._conn.ping()
        except redis.ConnectionError, err:
            raise ConnectionError(str(err))
        try:
            self.maindb = int(url.strip().split('/')[-1])
        except ValueError:
            self.maindb = 0
        self.finishdb = self.maindb + 1

    @catch_exceptions
    def add_task(self, tid, task_info, expire_time=ONE_DAY, duplicate=0):
        if self.task_exists(tid, duplicate=duplicate):
            return
        task = {}
        if isinstance(task_info, dict):
            task_info = json.dumps(task_info)
        task["task_info"] = task_info
        task["status"] = "init"
        task["create_time"] = task["update_time"] = self._conn.time()[0]
        task["tries"] = 0
        task["worker"] = ""
        task["duplicate"] = duplicate
        task['execute_time'] = 0

        ret = self._conn.hmset(tid, task)
        self._conn.expire(tid, expire_time)

        return ret

    @catch_exceptions
    def set_task_status(self, tid, status):
        '''
        status: init, processing, error, finish 
        if set finish the task will be moved to other db
        '''
        key, value = 'status', status
        if not self._conn.hexists(tid, key):
            return None
        self._conn.hset(tid, key, value)
        self._update_task(tid)
        if 'finish' == value:
            if 0 == self._conn.move(tid, self.finishdb):
                self._conn.execute_command('select', self.finishdb)
                self._conn.delete(tid)
                self._conn.execute_command('select', self.maindb)
                self._conn.move(tid, self.finishdb)
            self._conn.execute_command('select', self.finishdb)
            self._conn.expire(tid, self._finish_expire)
            self._conn.execute_command('select', self.maindb)
        return 1

    @catch_exceptions
    def set_finish_task_expire(self, expire_time):
        self._finish_expire = expire_time

    @catch_exceptions
    def _update_task(self, tid):
        '''
        using redis server time as update_time 
        '''
        key, value = 'update_time', self._conn.time()[0]
        return self._conn.hset(tid, key, value)

    @catch_exceptions
    def get_task_update_time(self, tid):
        return self._conn.hget(tid, 'update_time')

    @catch_exceptions
    def get_task_create_time(self, tid):
        return self._conn.hget(tid, 'create_time')

    @catch_exceptions
    def registe_worker(self, tid, worker_info):
        if self.worker_prefix not in worker_info:
            worker_info = self.worker_prefix + '#' + worker_info
        self._conn.client_setname(worker_info)
        key, value = 'worker', worker_info
        if self._conn.hexists(tid, key):
            self._update_task(tid)
            return self._conn.hset(tid, key, value)

    @catch_exceptions
    def get_task_status(self, tid):
        return self._conn.hget(tid, 'status')

    @catch_exceptions
    def delete_task(self, tid):
        return self._conn.delete(tid)

    @catch_exceptions
    def task_exists(self, tid, duplicate=0):
        flag1 = self._conn.exists(tid)
        self._conn.execute_command('select', self.finishdb)
        dup = self._conn.hget(tid, 'duplicate')
        self._conn.execute_command('select', self.maindb)
        if dup is None:
            flag2 = False
        else:
            dup = int(dup)
            if dup == 1:
                flag2 = True
            elif dup == 0 and duplicate == 0:
                flag2 = True
            else:
                flag2 = False
        return flag1 or flag2

    @catch_exceptions
    def get_all_workers(self):
        return [cli for cli in self._conn.client_list()
                if self.worker_prefix in cli['name']]

    @catch_exceptions
    def get_all_tasks(self):
        '''
        return task id: digest
        '''
        # using scan should be better, but version required > 2.8. Now redis2.6
        # using
        return self._conn.keys()

    def get_task_size(self):
        return self._conn.dbsize()

    @catch_exceptions
    def get_task_tries(self, tid):
        return int(self._conn.hget(tid, 'tries'))

    @catch_exceptions
    def get_task_execute_time(self, tid):
        return int(self._conn.hget(tid, 'execute_time'))

    @catch_exceptions
    def incr_task_execute_time(self, tid, etime):
        if not self._conn.exists(tid):
            return None
        ret = self._conn.hincrby(tid, 'execute_time', etime)
        self._update_task(tid)
        return ret

    @catch_exceptions
    def incr_task_tries(self, tid, count=1):
        if not self._conn.exists(tid):
            return None
        ret = self._conn.hincrby(tid, 'tries', count)
        self._update_task(tid)
        return ret

    @catch_exceptions
    def get_task_info(self, tid):
        return self._conn.hget(tid, 'task_info')

    @catch_exceptions
    def get_task_all_info(self, tid):
        return self._conn.hgetall(tid)

    @catch_exceptions
    def set_task_info(self, tid, task_info):
        if self.task_exists(tid):
            self._conn.hset(tid, 'task_info', task_info)

    @catch_exceptions
    def now(self):
        return self._conn.time()[0]

    def __del__(self):
        if self._conn:
            del self._conn


if __name__ == '__main__':

    import time
    import os
    tc = TaskContainer()
    tc.set_finish_task_expire(3)
    assert 1 == tc.add_task('digest001', {"params": {"name": "digest001"}})
    assert None == tc.add_task('digest001', '{task001}')
    assert 1 == tc.set_task_status('digest001', 'processing')
    assert None == tc.set_task_status('digest002', 'processing')

    time.sleep(1)
    assert 1 == tc.add_task('digest002', {"params": {"is_duplicated": False}})
    assert 1 == tc.set_task_status('digest002', 'processing')
    assert 'processing' == tc.get_task_status('digest002')

    assert 1 == tc.add_task(
        'digest003', {"params": {"is_duplicated": True}}, duplicate=1)

    assert 1 == tc.set_task_status('digest002', 'finish')
    assert 1 == tc.set_task_status('digest003', 'finish')

    assert 'digest001' in (tc.get_all_tasks())
    assert 'digest002' not in (tc.get_all_tasks())
    assert 'digest003' not in (tc.get_all_tasks())

    assert tc.task_exists('digest001')
    assert not tc.task_exists('digest002', duplicate=1)
    assert tc.task_exists('digest003', duplicate=1)
    assert tc.task_exists('digest003', duplicate=0)

    assert 1 == tc.add_task(
        'digest002', {"params": {"is_duplicated": True}}, duplicate=1)
    assert 1 == tc.set_task_status('digest002', "finish")

    assert None == tc.get_task_info('digest002')

    time.sleep(3)

    assert 1 == tc.add_task('digest002', {"params": {"is_duplicated": False}})
    assert 1 == tc.set_task_status('digest002', 'processing')
    assert ['digest001', 'digest002'] == tc.get_all_tasks()
    time.sleep(2)
    assert 1 == tc.incr_task_tries('digest002')
    assert 1 == tc.get_task_tries('digest002')

    assert 100 == tc.incr_task_execute_time('digest002', 100)
    assert 300 == tc.incr_task_execute_time('digest002', 200)

    assert 300 == tc.get_task_execute_time('digest002')

    assert int(tc.get_task_update_time('digest002')) > int(
        tc.get_task_create_time('digest002'))

    tc.registe_worker('digest002', "192.168.3.233:%d" % os.getpid())

    print tc.get_all_workers()

    print tc.get_task_info('digest001')
    print tc.get_task_all_info('digest002')

    #assert 1 == tc.delete_task('digest001')
    #assert 1 == tc.delete_task('digest002')

    print "===========test end=============="
