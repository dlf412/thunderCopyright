#!/usr/bin/python
# coding=utf-8

import concurrent.futures
import json
import multiprocessing
import time
import sys
import os
import traceback
import threading

if len(sys.argv) != 3:
    print 'thunder 1.2.1.0'
    sys.exit(0)

__filedir__ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, __filedir__ + '/../src')
sys.path.insert(0, __filedir__ + '/../bin')
sys.path.insert(0, __filedir__ + '/../tools')
sys.path.insert(0, __filedir__ )

__filedir__ = __filedir__ + '/..'

from downloader_util import *
from amqp_queue import *
from downloader_worker import *


if __name__ == "__main__":
    config_file = sys.argv[2]
    f = open(config_file)
    etc_data    = f.read()
    config      = json.loads(etc_data)
    NUM_PROCESS = config.get('downloader_worker_num', 4)
    Fin_Q       = multiprocessing.Queue()

    Task_Rec_Q  = multiprocessing.Queue(1)
    Task_Ack_Q  = multiprocessing.Queue(1)
    Task_Done_Q  = multiprocessing.Queue(1)

    dp          = process_dbpc(config)
    dp.start()

    jobs        = []

    log_path = config['log'].get('log_file', '')
    if not log_path:
        log_path = 'syslog'

    recorder    = multiprocessing.Process(
            target=record_fin_task, 
            args=(Fin_Q, etc_data, log_path, )
            )
    recorder.daemon = True
    jobs.append(recorder)
    recorder.start()

    get_task  = multiprocessing.Process(
            target=get_download_task, 
            args=(Task_Rec_Q, Task_Ack_Q, Task_Done_Q, etc_data, log_path,  ), 
            )
    get_task.daemon = True
    jobs.append(get_task)
    get_task.start()

    clean_res = threading.Thread(
            target=cleaner, 
            args=(etc_data, ),
            )
    clean_res.setDaemon(True)
    clean_res.start()

    with concurrent.futures.ProcessPoolExecutor(NUM_PROCESS) as executor:
        task_futures = []
        while True:
            try:
                if len(task_futures) < NUM_PROCESS:
                    if not Task_Rec_Q.empty():
                        task_info   = Task_Rec_Q.get()
                        temp_future = executor.submit(downloader_worker, config_file, task_info, __filedir__, log_path)
                        Task_Ack_Q.put(task_info)
                        task_futures.append(temp_future)
                    else:
                        pass
                for future in task_futures:
                    if future.done():
                        task_result = future.result()
                        Fin_Q.put(task_result)
                        task_futures.remove(future)
                    else:
                        pass
            finally:
                time.sleep(1)
    f.close()


