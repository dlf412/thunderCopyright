#! /usr/bin/env python

def parse (url):
    import urllib
    import socket

    db_conf = {};
    start_idx = url.find ('mysql://');
    if start_idx != 0:
        raise Exception ("bad mysql format (%s)" %url);
    try:
        start_idx = len ('mysql://');
        end_idx = url.find ('/', start_idx);
        if end_idx >= 0:
            tidx = url.find ('/', end_idx+1);
            if tidx < 0:
                db_conf['db'] = url[end_idx+1:];
                db_conf['tbl'] = None;
            else:
                db_conf['db'] = url[end_idx+1:tidx];
                db_conf['tbl'] = url[tidx+1:]
        else:
            db_conf['db'] = None;
            db_conf['tbl'] = None;
        passwd, port = urllib.splituser (url[start_idx:end_idx]);
        db_conf['user'], db_conf['pass'] = urllib.splitpasswd (passwd);
        host, db_port = urllib.splitport (port);
        #try:
        #    socket.inet_aton (host)
        #except socket.error:
        #    raise
        db_conf['host'] = host
        if db_port is not None:
            db_conf['port'] = int (db_port);
        else:
            db_conf['port'] = 3306
    except Exception, msg:
        raise Exception ("bad mysql format (%s), %s" % (url, msg));
    return db_conf;

def url_escape_table (url):
    conf = parse (url);
    new_url = "mysql://%s:%s@%s:%d/%s/%s" %(conf['user'], conf['pass'], \
                                conf['host'], conf['port'], conf['db'], \
                                conf['tbl']);
    return new_url;

def main ():
    import sys;
    if (len (sys.argv) == 1):
        print 'Usage %s db_url' %sys.argv[0];
        print '  db_url format: mysql://user:pass@host:port/db/tbl';
        sys.exit (1);
    print "DB conf dict: %s" % parse (sys.argv[1]);
    print "Escape table name: %s" % url_escape_table (sys.argv[1]);

if __name__ == '__main__':
    main ();
