#!/usr/bin/python
import happybase
import uuid
import sys

hbpool = happybase.ConnectionPool(1,host="master",port=9090)

if len(sys.argv) < 2:
    print "usage: python %s table" % sys.argv[0]
    sys.exit(1)
table = sys.argv[1]
print table
with hbpool.connection() as conn:
    if table == 'all':
        for x in ['crr', 'finished', 'matches', 'unpush', 'task', 'sid_tids']:
            t = conn.table(x)
            for row in t.scan():
                t.delete(row[0])
                print row[0] + " deleted"
print "success"

