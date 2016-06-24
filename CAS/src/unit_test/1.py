from high2low import *
import sys
sys.path.append('../')
from cas_utils import *

def message_handler(body, message):
    js = json.loads(body)
    message.ack()
    print js
    t = high2low("redis://127.0.0.1:6379/2")
    t.trans_high2low(js)


if __name__ == '__main__':
    download_exchange = Exchange('download_task_high')
    download_queue = kombu.Queue('download_task_high', download_exchange, routing_key='download_task_high')

    with Connection('amqp://guest:guest@localhost:5672//') as connection:
        with Consumer(connection, [download_queue], callbacks=[message_handler]) as consumer:
            while True:
                print 'start ....'
                connection.drain_events()
                print 'end...'

