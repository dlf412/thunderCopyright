#!/usr/bin/python
from global_var import config, logger
from utils import check_kingship, start_dbpc
import threading
def run():
    from kombu import Connection, Exchange, Queue
    from consumer import consumer
    with Connection(config['mq_connection']) as conn:
        ex = Exchange(config['query_exchange'])
        queue = Queue(config['query_queue'], exchange=ex,
                routing_key=config['query_routing_key'])
        worker = consumer(conn, queue, ex)
        worker.run()


def main():
    start_dbpc(config, 'task_adapter')
    processList = []
    for i in xrange(int(config['task_thread_number'])):
        t = threading.Thread(target=run)
        t.start()
        processList.append(t)


if __name__ == '__main__':
    try:
        main()
    except Exception, ex:
        logger.error('Error:', exc_info=True)
