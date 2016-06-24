#! /usr/bin/python

import sys
import os
import httplib
import json
import urllib

if len (sys.argv) < 4:
    print "useage: %s host port site_asset_id [true|false] " % sys.argv[0]
    sys.exit (-1)

prefix_search = False
if len(sys.argv) >= 5:
    prefix_search = True

host = sys.argv[1]
port = int(sys.argv[2])
site_asset_id = sys.argv[3]

print prefix_search


args = urllib.urlencode(
        {
            "site_asset_id":site_asset_id,
            "prefix_search":str(prefix_search)
        }
        )
# conn is HTTPConnection
conn = httplib.HTTPConnection (host, port)
conn.request ('GET', "/vddb-async/matches?%s" % args)

# res is HTTPResponse
res = conn.getresponse ()

status = res.status
reason = res.reason

results = res.read ()
r_headers = res.getheaders ()


print status
print reason
print results
print r_headers
