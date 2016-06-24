#!/usr/bin/env python

import MySQLdb;
import os;
import socket;
import sys;

import mysql_url_parser;
import http_url_parser;

def check_folder (folder):
    if (not os.path.exists (folder)):
        ret = os.system ("mkdir -p %s >/dev/null 2>&1" %folder);
        if (ret != 0):
            return False;
    return True;

def check_mysql (mysql_url):
    db_conf = mysql_url_parser.parse (mysql_url);
    try:
        dbconn = MySQLdb.connect(host = db_conf['host'],
                                 port = db_conf['port'],
                                 user = db_conf['user'],
                                 passwd = db_conf['pass'],
                                 db = db_conf['db'],
                                 charset='utf8');
        dbconn.ping ();
    except:
        return False;
    return True;

def check_http (http_url):
    http_conf = http_url_parser.parse (http_url);
    sock = socket.socket ();
    sock.settimeout (0.5);
    ret = sock.connect_ex ((http_conf['host'], http_conf['port']));
    sock.close ();
    if (ret != 0):
        return False;
    return True;

def folder_checker (folder):
    folder_raw = folder.encode ('ascii', 'ignore')
    if not check_folder (folder_raw):
        print "folder %s check failed" % (folder_raw, )
        sys.exit (1)

def mysql_url_checker (url):
    url_raw = url.encode ('ascii', 'ignore')
    if not check_mysql (url_raw):
        print "mysql url %s check failed" % (url_raw, )
        sys.exit (1)

def http_url_checker (url):
    url_raw = url.encode ('ascii', 'ignore')
    if not check_http (url_raw):
        print "http url %s check failed" % (url_raw, )
        sys.exit (1)

if __name__ == '__main__':
    if (len (sys.argv) != 3):
        print "Usage: %s opt arg" %sys.argv[0];
        print "  opt = folder/mysql/http";
        sys.exit (1);
    opt = sys.argv[1];
    arg = sys.argv[2];
    ret = False;
    if (opt == 'folder'):
        ret = check_folder (arg);
    elif (opt == 'mysql'):
        ret = check_mysql (arg);
    elif (opt == 'http'):
        ret = check_http (arg);
    if (ret):
        print "succeed";
    else:
        print "failed";
