#! /usr/bin/env python

import json
import os
import sys

from file_utility import load_file_content
import mysql_url_parser
from check_setting import mysql_url_checker


def init_db_impl (db_url, init_data_file):
    db_conf = mysql_url_parser.parse (db_url);
    if (not os.path.exists (init_data_file)):
        raise Exception ("%s is not exist" %init_data_file);
    cmd = "mysql -u%s -p%s -h%s %s < %s" %(db_conf['user'], db_conf['pass'],
            db_conf['host'], db_conf['db'], init_data_file);
    ret = os.system (cmd);
    if (ret != 0):
        print "initialize %s failed" %db_url;
        sys.exit (1);

def install_database (conf, init_data):
    standard_content = load_file_content (conf);
    standard_dict = json.loads (standard_content);

    mysql_url_checker (standard_dict[u'mysql'][u'media_wise']);

    init_file = "%s/dbinit.sql" %(init_data);
    init_db_impl (standard_dict[u'mysql'][u'media_wise'], init_file);

def main ():
    if (len (sys.argv) != 3):
        print 'Usage: %s standard_conf init_data' %sys.argv[0];
        sys.exit ();
    conf = sys.argv[1];
    init_data = sys.argv[2];
    install_database (conf, init_data);

if __name__ == '__main__':
    main ();
