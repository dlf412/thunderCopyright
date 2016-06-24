#! /usr/bin/python

import os
import sys
import web
import logging
try:
    import samplejson as json
except:
    import json

work_dir = os.getenv("MW_HOME")

bin_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, bin_dir)

logger = logging.getLogger("va-interface-")
config = None
try:
    config_file = os.path.join(work_dir, 'etc', 'web_config.json')
    with open(config_file, 'r') as f:
        config = json.load(f)
except Exception as e:
    web.debug("parse config failed, message:%s" % e)
    sys.exit(-1)


logger.debug(config)
