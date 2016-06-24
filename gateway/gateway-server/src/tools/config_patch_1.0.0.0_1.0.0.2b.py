#!/usr/bin/env python

import os
import json

LAST_VERSION = '1.0.0.0'
CUR_VERSION = '1.0.0.2b'

publish_timeout = 3


def patch_apikey(path):
    try:
        with open(path, 'r') as f:
            json.load(f)
        print '    API.key file already good.'
    except ValueError:
        with open(path, 'r') as f:
            apikey = f.read()
        with open(path, 'w') as f:
            data = { 'default': apikey }
            json.dump(data, f, indent=4)
        print '    API.key file Updated'


def patch_config(path):
    with open(path, 'r') as f:
        cfg = json.load(f)

    query_broker = cfg['query_broker']
    if 'publish_timeout' not in query_broker:
        query_broker['publish_timeout'] = publish_timeout
        
    with open(path, 'w') as f:
        json.dump(cfg, f, indent=4)


def parse_args():
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("-c", "--etc", metavar="DIR", help="Where config directory placed!")
    opts, args = parser.parse_args()
    if not opts.etc:
        parser.error("Please specific the config directory!")

    return opts


def main():
    opts = parse_args()
    apikey_path = os.path.join(opts.etc, 'API.key')
    cfg_path = os.path.join(opts.etc, 'gateway.conf')
    
    patch_apikey(apikey_path)
    patch_config(cfg_path)
    print '    Patch successfully!'


if __name__ == '__main__':
    main()
