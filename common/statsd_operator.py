import statsd
import time

#con = statsd.client.StatsClient(host='192.168.1.', port=8125)
class statsd_operator(object):
    def __init__(self, host, port):
        try:
            self.host = host
            self.port = port
            self.conn = statsd.client.StatsClient(host= self.host, port = self.port)
        except Exception, msg:
            #g_logger.debug(trans2json('init statsd failed [%s]' %(msg)))
            pass

    def get_connection(self):
        try:
            self.conn = statsd.client.StatsClient(host= self.host, port = self.port)
        except Exception, msg:
            #g_logger.debug(trans2json('get connection from statsd failed [%s]' %(msg)))
            pass

    def incr(self, stat, count=1, rate=1):
        try:
            self.conn.incr(stat, count, rate)
        except Exception, msg:
            #g_logger.debug(trans2json('incr stat count failed [%s]' %(msg)))
            self.get_connection()

    def decr(self, stat, count=1, rate=1):
        try:
            self.conn.decr(stat, count, rate)
        except Exception, msg:
            #g_logger.debug(trans2json('decr stat count failed [%s]' %(msg)))
            self.get_connection()


    def timing(self, stat, delta, rate=1):
        try:
            self.conn.timing(stat, delta, rate)
        except Exception, msg:
            #g_logger.debug(trans2json('record stat time failed [%s]' %(msg)))
            self.get_connection()
    

        
