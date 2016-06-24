from kombu import  Producer, Exchange
import kombu
try:
    import json
except:
    import simplejson as json
import time
from utils import trans2json
from cas_utils import g_logger, g_logger_info, connect_rabbitmq
from task_container import TaskContainer
from cas_config import gconf


ERR_DOWNLOAD = 121509

def gen_error_msg(task):
    try:
        j_task_info = json.loads(task)

        j_task_info['params']['error_code'] =  ERR_DOWNLOAD
        j_task_info['params']['message'] = 'download failed'
        j_task_info['method'] = 'finish_task'
        js = json.dumps(j_task_info)
        return js
    except Exception, msg:
        g_logger.error(trans2json('create error msg failed [%s]' % (msg)))
        return None


class watch_task_status(object):

    def __init__(self):
        try:
            self.mq_url = gconf.mq_dict['server']

            self.finish_queue_name = gconf.mq_dict['task_finish']['queue_name']
            self.finish_routing_key = gconf.mq_dict[
                'task_finish']['routing_key']
            self.finish_exchange = Exchange(gconf.mq_dict['task_finish']['exchange_name'],
                                            gconf.mq_dict['task_finish']['exchange_type'])
            self.finish_queue = kombu.Queue(
                self.finish_queue_name, self.finish_exchange, self.finish_routing_key)

            self.download_queue_name = gconf.mq_dict[
                'task_download']['queue_name']
            self.download_routing_key = gconf.mq_dict[
                'task_download']['routing_key']
            self.download_exchange = Exchange(gconf.mq_dict['task_download']['exchange_name'],
                                              gconf.mq_dict['task_download']['exchange_type'])
            self.download_queue = kombu.Queue(
                self.download_queue_name, self.download_exchange, self.download_routing_key)

            self.high_download_queue_name = gconf.mq_dict[
                'task_download_high']['queue_name']
            self.high_download_routing_key = gconf.mq_dict[
                'task_download_high']['routing_key']
            self.high_download_exchange = Exchange(gconf.mq_dict['task_download_high']['exchange_name'],
                                                   gconf.mq_dict['task_download_high']['exchange_type'])
            self.high_download_queue = kombu.Queue(
                self.high_download_queue_name, self.high_download_exchange, self.high_download_routing_key)

            self.heartbeat_interval = 2 * \
                gconf.conf_dict['warden']['heartbeat_interval']
            self.timeout = gconf.conf_dict['warden']['timeout']
            self.tc = TaskContainer(url=gconf.conf_dict['redis'])
        except Exception, msg:
            g_logger.error(trans2json('watch task status failed [%s]' % (msg)))
            raise

    def run(self):
        while True:
            try:
                g_logger_info.info(
                    trans2json('strat to watch redis...', 'watch'))

                connection = connect_rabbitmq(
                    self.mq_url, self.finish_queue_name, self.finish_routing_key)
                self.producer = Producer(connection)

                while True:
                    try:
                        tasks = self.tc.get_all_tasks()
                        if not tasks:
                            g_logger.debug(trans2json('No any task, continue'))
                            time.sleep(gconf.conf_dict['watch_interval'])
                            continue
                        g_logger.debug(
                            trans2json('I get tasks size is %d, start watching these tasks' % len(tasks)))
                        for tid in tasks:
                            self.check_work_status(tid)
                        time.sleep(gconf.conf_dict['watch_interval'])
                    except Exception, msg:
                        g_logger.error(
                            trans2json('run watch task status error [%s]' % (msg)))
                        raise
            except Exception, msg:
                import traceback
                traceback.print_exc()
                g_logger.error(
                    trans2json('run watch work status failed [%s]' % (msg)))
                time.sleep(gconf.conf_dict['watch_interval'])
                continue

    def check_work_status(self, tid):
        '''
        task_all_info reference:
        {'status': 'processing', 'update_time': '1415584616', 'worker': 'Downloader#192.168.3.233:25478', 'tries': '1', 'duplicate': '0', 'task_info': '{"params": {"is_duplicated": false}}', 'create_time': '1415584614', 'execute_time': '100'}
        '''
        try:
            t_infos = self.tc.get_task_all_info(tid)
            if t_infos['status'] == 'processing':
                self.process_status_handler(tid, t_infos)
            elif t_infos['status'] == 'error':
                self.error_status_handler(tid, t_infos)
            else:
                g_logger.debug('digest[%s] status is %s, I will do nothing' %(tid, t_infos['status']))
        except Exception, msg:
            g_logger.error(trans2json('check work flow failed [%s]' % (msg)))

    def check_timeout(self, infos, interval):
        try:
            return (self.tc.now() - int(infos['update_time'])) > interval
        except Exception, msg:
            g_logger.error(trans2json('check timeout failed [%s]' % (msg)))

    def send_error_msg2mq(self, tid, task):
        try:
            error_msg = gen_error_msg(task)
            if error_msg is None:
                return
            g_logger.debug('send error task[%s] to finish message queue' % tid)
            self.producer.publish(error_msg, exchange=self.finish_exchange, routing_key=self.finish_routing_key,
                                  declare=[self.finish_queue], serializer='json', compression='zlib')
        except Exception, msg:
            g_logger.error(
                trans2json('send error msg to mq failed [%s]' % (msg)))

    def send_task2mq(self, task):
        try:
            j_task = json.loads(task)
            g_logger.debug(trans2json('redispatch task[%s] into  %s download mq' % (
                task, j_task['params']['priority'])))
            if j_task['params']['priority'] == 'high':
                self.producer.publish(task, exchange=self.high_download_exchange, routing_key=self.high_download_routing_key,
                                      declare=[self.high_download_queue], serializer='json', compression='zlib')
            else:
                self.producer.publish(task, exchange=self.download_exchange, routing_key=self.download_routing_key,
                                      declare=[self.download_queue], serializer='json', compression='zlib')
        except Exception, msg:
            g_logger.error(
                trans2json('send task to download mq failed [%s]' % (msg)))

    def process_status_handler(self, tid, infos):
        try:
            g_logger.debug(trans2json('digest[%s] In process status handler, check the worker is running or down' % tid))
            ret = self.check_timeout(infos, self.heartbeat_interval)
            # maybe worker down, need retry
            if ret:
                if int(infos['tries']) >= gconf.conf_dict['retry_times']:
                    g_logger.error(trans2json(
                        "I delete this task, reason: tries too many times in process status handler"))
                    self.send_error_msg2mq(tid, infos['task_info'])
                    self.tc.delete_task(tid)
                else:
                    g_logger.debug(trans2json("worker may be down, I will retry it"))
                    self.send_task2mq(infos['task_info'])
                    self.tc.set_task_status(tid, 'init')
            else:
                g_logger.debug(trans2json('this worker is running now, no problem'))
                # do nothing
                pass
        except Exception, msg:
            g_logger.error(
                trans2json('handle process status failed [%s]' % (msg)))

    def error_status_handler(self, tid, infos):
        '''
        only set error status to init for worker and send task into mq 
        '''
        try:
            g_logger.debug(trans2json('digest[%s] In error status handler' % tid))
            g_logger.debug(trans2json("the task execute failed, tries is %d, time is %d, I will retry it" % (
                int(infos['tries']), int(infos['execute_time']))))
            self.send_task2mq(infos['task_info'])
            self.tc.set_task_status(tid, 'init')
        except Exception, msg:
            g_logger.error(
                trans2json('handle error status failed [%s]' % (msg)))

