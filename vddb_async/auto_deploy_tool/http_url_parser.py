#! /usr/bin/env python

def parse (url):
    import urllib
    import socket
    http_conf = {};
    start_idx = url.find ('http://');
    if (not (start_idx == 0)):
        raise Exception ("bad http format (%s)" %url);
    start_idx = len ('http://');
    try:
        host, port = urllib.splitport (url[start_idx:])
        #try:
            #socket.inet_aton (host)
        #except socket.error:
        #    raise
        http_conf['host'] = host
        if port is not None:
            http_conf['port'] = int (port)
        else:
            http_conf['port'] = 80
    except Exception, msg:
        raise Exception ("bad http url format (%s), %s" % (url, msg))
    return http_conf

def main ():
    import sys;
    if (len (sys.argv) == 1):
        print 'Usage %s http_url' %sys.argv[0];
        print '  http_url format: http://host:port';
        sys.exit (1);
    print "http conf dict: %s" % parse (sys.argv[1]);

if __name__ == '__main__':
    main ();
