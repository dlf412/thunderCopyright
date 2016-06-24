import os
import sys 
from os import _exit, getenv
from sys import stderr

PROGRAM_INFO = "VDDB Async 1.0"

if len(sys.argv) > 1:
    print PROGRAM_INFO
    sys.exit(0)

path = getenv('MW_HOME')
if path == None:
    stderr.write("MW_HOME not set in environment, program cannot start.")
    _exit(1)
sys.path.append('/'.join([path, 'lib']))
os.environ['PATH'] = ':'.join([os.environ['PATH'], '/'.join([path, 'bin'])])
import logging, logging.config
from parse_config import parse_config
from utils import  make_db_pool, make_hbase_pool
import statsd
logging.config.fileConfig('/'.join([path, 'etc', 'logging.conf']))
logger = logging.getLogger('mw')
try:
    config = parse_config('/'.join([path, 'etc', 'vddb_async.conf']))
    hbpool = make_hbase_pool(config)
    pool = make_db_pool(config, 3)
except :
    logger.error('init task_adapter module failed !', exc_info=True)
    sys.exit(0)

