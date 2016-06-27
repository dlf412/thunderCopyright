#! /usr/bin/env python
# coding:utf-8

# Author: xu_xiaorong
# Mail: xu_xiaorong@mysite.cn
# Created: 2013-09-17

'''
    use for send dbpc

'''
import sys
import time
import socket
import getopt
import traceback
import threading
import logging
import logging.handlers as hd

class dbpc(threading.Thread):
    def __init__(self, dbpc_host, dbpc_port, service, component, send_interval=5, log_obj=None):
        super(dbpc, self).__init__()
        '''
            Constructor for dbpc
            `dbpc_host`:
                DBPC server hostname or ipaddress.
            `dbpc_port`:
                DBPC server port ,PORT  must be a valid interger
            `dbpc_service`:
                send DBPC service, SERVICE must in DB service_name(enum)
            `component`:
                send DBPC component.
            `send_interval`:
                send DBPC time interval (minute)
        '''
        self.dbpc_host = dbpc_host
        self.dbpc_port = dbpc_port
        self.service = service
        self.component = component
        self.send_interval = send_interval
        self.pause_flag = False
        self.setDaemon(True)
        self.log_obj = log_obj
        self.log_init()


    def pause(self):
        self.pause_flag = True

    def resume(self):
        self.pause_flag = False

    def log_init(self):
        self.logger = logging.getLogger('dbpc module - service:%s - component:%s' % (self.service, self.component))
        sh = None
        if self.log_obj is None:
            sh = hd.SysLogHandler(address='/dev/log', facility=hd.SysLogHandler.LOG_LOCAL3)
        else:
            sh = logging.StreamHandler(self.log_obj)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        sh.setFormatter(formatter)
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(sh)

    def send(self):
        '''
            Use sock send localhost, service, component to dbpc
            Server
        '''
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connect_value = (self.dbpc_host, self.dbpc_port)
        s.connect(connect_value)
        s.sendall('{"status":[{"service":"%s", component:"%s"}]}' % (self.service,
            self.component))
        # `ret` whill successful when dbpc server receive current dbpc message from client
        #  other will block
        ret =  s.recv(1024)
        s.close()
        return ret

    def run(self):
        while True:
            try:
                if not self.pause_flag:
                    if self.send() != "successful":
                        self.logger.error("send dbpc failed")
                    else:
                        self.logger.info("send dbpc successful")
                else:
                    self.logger.info("dbpc paused")
            except Exception, e:
                self.logger.error("send dbpc catch exception")
                self.logger.error(traceback.format_exc())
            finally:
                time.sleep(int(self.send_interval))

if __name__=='__main__':
    d = dbpc("192.168.1.146",5800, "vddb123", "warmup", 0)
    d.start()
    d.join()
