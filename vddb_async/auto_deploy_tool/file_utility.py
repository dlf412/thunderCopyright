#! /usr/bin/env python

import os;
import sys;

def load_file_content (file):
    if (not os.path.exists (file)):
        raise Exception ("%s is not exist" %file);
    fp = open (file, 'r');
    content = fp.read ();
    fp.close ();
    return content;
def save_file_content (file, content):
    fp = open (file, 'w');
    fp.write (content);
    fp.close ();
    return ;

def main ():
    if (len (sys.argv) == 1):
        print "Usage %s file" %sys.argv[0];
        sys.exit (1);
    file = sys.argv[1];
    content = load_file_content (file);
    print "file (%s)'s content is \n%s" %(file, content);

if __name__ == '__main__':
    main ();
