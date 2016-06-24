#!/usr/bin/python
from global_var import config, logger
from utils import check_kingship, start_dbpc, trans2json
from threading import Thread
from hbase import *
import time
from pusher import *
from logger import g_logger
def run(queue):
    pro = producer()
    push = pusher(pro)
    while True:
        t = queue.get(block=True)
        logger.info('get a task to push, task_id: %s', t)
        g_logger.info(trans2json(message ='get a task to push, task_id: %s'%t,
            atcion= 'get task'))
        task = getTask(t)
        logger.info('------task:%s', task)
        try:
            re = push.getMatch(t)
            #logger.info('type:%s, %s', type(re), re)
            push.pushResult(re)
            updateFinished(t, 'success')
            dropUnpush(t)
            logger.info('succeed to push the match result , task_id: %s,'
                    'result: %s', t, re)
            g_logger.info(trans2json(message='succeed to push the match result ,'
                'external_id :%s, task_id: %s'
                %(task['i:external_id'], t, ), action='push result'))
        except resultError:
            logger.error("failed to get the result , task_id: %s", t)
            g_logger.error(trans2json(message ='failed to push result,'
                'external_id: %s, task_id: %s'
                %(task['i:external_id'], t), action='push result'))
            dropUnpush(t)
            updateFinished(t, 'failed')
        except AssertionError:
            logger.error("failed to get matches, task_id: %s", t)
            g_logger.error(trans2json(message ='failed to push result,'
                'external_id: %s, task_id: %s'
                %(task['i:external_id'], t), action='push result'))
            dropUnpush(t)
            updateFinished(t, 'failed')
        except :
            logger.error('failed to push result, rest status to new,'
                    'task_id: %s,  Error:', t,  exc_info=True)
            g_logger.error(trans2json(message ='failed to push result, res status'
                'to new, external_id: %s, task_id: %s '
                %(task['i:external_id'], t), action = 'retry to push'))
            changeStatus(t, 'new')
            logger.error("reset status to new , task_id: %s", t)
            #dropUnpush(t)

def resetStatus():
    res = scanUnpush('processing')
    for k, v in res.items():
        changeStatus(k, 'new')

def loop(queue):
    resetStatus()
    while True:
        logger.info('try to get task to push')
        res = scanUnpush('new', int(config['fetch_number']))
        for k, v in res.items():
            queue.put(k)
            changeStatus(k, 'processing')
        time.sleep(5)

def main():
    start_dbpc(config, 'task_adapter')
    from Queue import Queue
    global queue
    queue = Queue()
    threadList = []
    for i in xrange(int(config['push_thread_number'])):
        t = Thread(target=run, args=(queue,))
        t.start()
        threadList.append(t)

    fetch = Thread(target=loop, args=(queue,))
    fetch.start()
    threadList.append(t)

if __name__ == '__main__':
    try:
        main()
    except Exception, ex:
        logger.error('Error:', exc_info=True)

