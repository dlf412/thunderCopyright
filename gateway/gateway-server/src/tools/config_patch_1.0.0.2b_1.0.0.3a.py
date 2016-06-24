#!/usr/bin/env python

import os
import json

LAST_VERSION = '1.0.0.2b'
CUR_VERSION = '1.0.0.3a'

processing_retry_default = False 

def patch_config(path):
    with open(path, 'r') as f:
        cfg = json.load(f)

    if 'processing_retry' not in cfg:
        cfg['processing_retry'] = processing_retry_default
        
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
    cfg_path = os.path.join(opts.etc, 'gateway.conf')
    
    patch_config(cfg_path)
    print '    Patch successfully!'


if __name__ == '__main__':
    main()
