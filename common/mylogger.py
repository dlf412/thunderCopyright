import logging
import socket

class mylogger(object):
    def __init__(self):
        self.name = ""
        self.level = ""
        self.log_file = ""
        self.logger = None

    def init_logger(self, name, log_level, log_file, log_facility, digest=''):
        try:
            self.name = name
            self.log_file = log_file
            self.level = getattr(logging, log_level)
            self.create_logger(self.name, self.level, self.log_file, log_facility, digest)
            self.debug = self.logger.debug
            self.info = self.logger.info
            self.warning = self.logger.warning
            self.error = self.logger.error
            self.critical = self.logger.critical
        except Exception, msg:
            raise Exception('init logger error [%s]' %(msg))

    def create_logger(self, name, log_level, log_file, log_facility, digest=''):
        try:
            self.logger = logging.getLogger(name)
            self.logger.handlers = []
            self.logger.setLevel(log_level)
            if log_file is None or log_file == 'syslog':
                hdlr = logging.handlers.SysLogHandler(address="/dev/log", facility=log_facility)
            else:
                hdlr = logging.FileHandler(log_file)
            
            host_name = socket.gethostname()
            if digest:
                log_format = host_name + '#' + digest + '#%(asctime)s#%(process)d#%(name)s#%(filename)s#%(lineno)d#%(levelname)s#%(message)s'
            else:
                log_format = host_name + '#%(asctime)s#%(process)d#%(name)s#%(filename)s#%(lineno)d#%(levelname)s#%(message)s'
            
            #formatter = logging.Formatter('%(asctime)s#%(process)d#%(name)s#%(filename)s#%(lineno)d#%(levelname)s#%(message)s')
            formatter = logging.Formatter(log_format)
            hdlr.setFormatter(formatter)
            self.logger.addHandler(hdlr)
        except Exception, msg:
            raise Exception("create logger error [%s]" %(msg))

