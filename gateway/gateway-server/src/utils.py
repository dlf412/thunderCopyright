#coding: utf-8

import json


#### Logging ####
LOG_DEBUG = 'debug'
LOG_INFO = 'info'
LOG_WARN = 'warning'
LOG_WARNING = 'warning'
LOG_ERROR = 'error'
LOG_CRITICAL = 'critical'

def log_normal(logger, data, level, uuid=None):
    if not isinstance(uuid, str): uuid = '<None>'
    log = getattr(logger, level)
    log('%s#%s' % (uuid, json.dumps(data)))

def log_bill(logger, data, uuid=None):
    if not isinstance(uuid, str): uuid = '<None>'
    logger.info('%s#%s' % (uuid, json.dumps(data)))

def log_info(logger, data, uuid=None):
    if not isinstance(uuid, str): uuid = '<None>'
    logger.info('%s#%s' % (uuid, json.dumps(data)))

