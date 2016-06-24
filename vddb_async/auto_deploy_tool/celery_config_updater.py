#!/usr/bin/env python

import os
import json
import sys

def config_updater (standard_conf, target_conf):
    default_conf = json.loads (open (standard_conf, 'r').read ())
    celery_conf = default_conf['vddb_async']['celery']

    conf = dict ()
    #update celery config in task_manager.py
    conf['BROKER_URL'] = celery_conf['broker']
    conf['CELERY_RESULT_BACKEND'] = celery_conf['backend']

    for key in conf:
        value = ""
        if type (conf[key]) == list or type (conf[key]) == tuple:
            value = ",".join (conf[key])
        else:
            value = str (conf[key])
        os.system ("sed -i 's#^[[:space:]]*%s[[:space:]]*=.*#%s=\"%s\"#g' %s"
                % (key, key, value, target_conf))

def main ():
    if (len (sys.argv) != 3):
        print 'Usage: %s standard_conf target_conf' % (sys.argv[0], )
        sys.exit ()
    standard_conf = sys.argv[1]
    target_conf = sys.argv[2]
    config_updater (standard_conf, target_conf)

if __name__ == "__main__":
    main ()
