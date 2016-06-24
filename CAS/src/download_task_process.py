import time
try:
    import json
except:
    import simplejson as json
from kombu import Exchange, Connection, Producer
import kombu
from cas_utils import SUBMIT_TASKS, DOWNLOAD_TASKS
import cas_utils
import utils
from utils import trans2json
from hot_url_queue import HotUrlQueue
from task_container import TaskContainer
from cas_config import gconf

TASK_COEFFICIENT  = 2

def check_task(task):
    return 'params' in task and \
        'digest' in task['params'] and len(task['params']['digest']) != 0

class download_task_process(object):

    def __init__(self):
        try:
            self.hot_url_queue = HotUrlQueue(url=gconf.conf_dict['hot_queue'])
            self.task_container = TaskContainer(gconf.conf_dict['redis'])
            self.cur_workers_cnt = gconf.conf_dict.get('downloader_cnt', 100)

            self.mq_conn = Connection(gconf.mq_dict['server'])
            self.producer = Producer(self.mq_conn)

            self.download_exchange = Exchange(gconf.mq_dict['task_download'][
                                              'exchange_name'], gconf.mq_dict['task_download']['exchange_type'])
            self.download_queue_name = gconf.mq_dict['task_download']['queue_name']
            self.download_routing_key = gconf.mq_dict['task_download']['routing_key']
            self.download_queue = kombu.Queue(
                self.download_queue_name, self.download_exchange, self.download_routing_key)

            self.high_download_queue_name = gconf.mq_dict[
                'task_download_high']['queue_name']
            self.high_download_routing_key = gconf.mq_dict[
                'task_download_high']['routing_key']
            self.high_download_exchange = Exchange(gconf.mq_dict['task_download_high'][
                                                   'exchange_name'], gconf.mq_dict['task_download_high']['exchange_type'])
            self.high_download_queue = kombu.Queue(
                self.high_download_queue_name, self.high_download_exchange, self.high_download_routing_key)

            self.finish_queue_name = gconf.mq_dict['task_finish']['queue_name']
            self.finish_routing_key = gconf.mq_dict[
                'task_finish']['routing_key']
            self.finish_exchange = Exchange(gconf.mq_dict['task_finish'][
                                            'exchange_name'], gconf.mq_dict['task_finish']['exchange_type'])
            self.finish_queue = kombu.Queue(
                self.finish_queue_name, self.finish_exchange, self.finish_routing_key)
        except Exception, msg:
            print "__init__ error"
            cas_utils.g_logger.error(
                trans2json('download task process init failed [%s]' % (msg)))

    def run(self):
        cas_utils.g_logger_info.info(
            trans2json('download task process start...', 'start dispatcher'))
        while True:
            try:
                utils.digest = None
                task_cnt = self.task_container.get_task_size()
                hot_cnt = TASK_COEFFICIENT * self.cur_workers_cnt - task_cnt
                if hot_cnt <= 0:
                    cas_utils.g_logger.debug(trans2json("System is full now, do not fetch any task"))
                while hot_cnt > 0:
                    tasks = self.hot_url_queue.get_highest_hots(hot_cnt, withhots=True)
                    if len(tasks) == 0:
                        break
                    cas_utils.g_logger.debug(trans2json("I get highest hot task count is %d" % len(tasks)))
                    for t_with_hot in tasks:
                        cas_utils.g_statsd.incr(SUBMIT_TASKS, 1)
                        j_t = json.loads(t_with_hot[0])
                        if not check_task(j_t):
                            cas_utils.g_logger.error(
                                trans2json('invalid task, ignore it'))
                            self.hot_url_queue.remove_by_urls(t_with_hot[0])
                            continue
                        j_t['params']['hot'] = int(t_with_hot[1])
                        utils.digest = j_t['params']['digest']
                        duplicate = int('is_duplicated' in j_t['params'])
                        cas_utils.g_logger.debug('get task[%s] and send to download mq' % utils.digest)
                        if self.task_container.add_task(utils.digest, j_t, expire_time=gconf.conf_dict['task_expire_time'], duplicate=duplicate):
                            cas_utils.g_logger_info.info(
                                trans2json('get task %s, hot is %s' % (t_with_hot[0], t_with_hot[1]), 'get_task', utils.digest))
                            self.send2queue(json.dumps(j_t))
                            hot_cnt -= 1
                        else:
                            cas_utils.g_logger.debug(
                                trans2json('task[%s] is exists, ignore it' % utils.digest)
                                    )
                        self.hot_url_queue.remove_by_urls(t_with_hot[0])
                time.sleep(gconf.conf_dict['dispatcher_interval'])
                self.cur_workers_cnt = max(self.cur_workers_cnt, len(
                     self.task_container.get_all_workers()))
            except:
                import traceback
                cas_utils.g_logger.error(trans2json(traceback.format_exc()))
                time.sleep(10)
                self.mq_conn = kombu.Connection(gconf.mq_dict['server'])
                self.producer = Producer(self.mq_conn)

    def send2queue(self, task):
        try:
            j_task = json.loads(task)
            digest = j_task['params']['digest']
            cas_utils.g_logger_info.info(trans2json('dispatch task [%s] to download task queue, type is %s'
                                          % (task, type(task)), 'dispatch task', digest))
            cas_utils.g_statsd.incr(DOWNLOAD_TASKS, 1)
            if j_task['params']['priority'] == 'low':
                self.producer.publish(task, exchange=self.download_exchange, routing_key=self.download_routing_key,
                                      declare=[self.download_queue], serializer='json', compression='zlib')
            else:
                self.producer.publish(task, exchange=self.high_download_exchange, routing_key=self.high_download_routing_key,
                                      declare=[self.high_download_queue], serializer='json', compression='zlib')
        except Exception, msg:
            cas_utils.g_logger.error(trans2json('send to queue failed [%s]' % (msg)))
            raise

