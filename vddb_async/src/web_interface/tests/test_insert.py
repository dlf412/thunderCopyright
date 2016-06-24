#! /usr/bin/python

import sys
import os
import httplib
import json
import urllib

params = {
    "jsonrpc": "2.0",
    "method" : "insert",
    "params": {
        "site_asset_ids": [
            "seed_hash2222222222",
            "url_hash22222222"
        ],
        "status":"match",
        "matches":[{'video_score': 99, 'meta_uuid':
            '970ae0ba-773b-11e1-a7b2-080027cf46d6', 'video_sample_offset': 0,
            'match_type': 'video', 'meta_name': 'Auto_Rule306_Movie',
            'video_ref_offset': 0, 'audio_duration': 0, 'track_id': 0.0,
            'instance_id': '9752d1cc-773b-11e1-a7b2-080027cf46d6',
            'video_duration': 307, 'instance_name': 'cappella.flv.xfp.0'}]
    },
    "id": "null"
}
# conn is HTTPConnection
header = {"Content-Type": "application/json"}
conn = httplib.HTTPConnection ('182.92.153.94', 8083)
conn.request ('POST', "/vddb-async/matches?is_tmp=true", json.dumps(params), header)

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
