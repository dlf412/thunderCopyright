#!/usr/bin/env python

import os
import json

LAST_VERSION = '1.0.0.3a'
CUR_VERSION = '1.1.0.0'
    
unreg_default = ["gvod://"]
nomatch_default = []
server_flag_default = 0


def patch_config(path):
    with open(path, 'r') as f:
        cfg = json.load(f)
    
    cheating = cfg['cheating']
    if 'no_match' not in cheating:
        cheating['no_match'] = nomatch_default
    if 'unrecognized' not in cheating:
        cheating['unrecognized'] = unreg_default
    if 'server_flag' not in cfg:
        cfg['server_flag'] = server_flag_default

    with open(path, 'w') as f:
        json.dump(cfg, f, indent=4)


def parse_args():
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("-c", "--etc", metavar="DIR", help="Where config directory placed!")
    opts, _ = parser.parse_args()
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
