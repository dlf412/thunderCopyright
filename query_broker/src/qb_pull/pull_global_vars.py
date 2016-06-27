import os
import sys
import threading

# the major dirs
bin_dir = os.path.dirname(os.path.abspath(__file__))
if os.path.islink(os.getenv('PWD')):
    bin_dir = os.getenv('PWD')
run_dir = os.getenv('PWD')
os.chdir(bin_dir)

base_dir = os.path.dirname(bin_dir)
lib_dir = os.path.join(base_dir, 'lib')

if lib_dir not in sys.path:
    sys.path.insert(0, lib_dir)

version = '1.2.1.0'
status = ['idle', 'recovering', 'working', 'down']
cons = [threading.Condition() for s in status]
con_map = dict(zip(status, cons))
# global logger
logger = None
module = 'process_task'
log_file = ''

# finsh
finsh_url = ''
finsh_queue = ''
finsh_exchange = ''
finsh_routing_key = ''

# vddb query
vddb_queryurl = ''
vddb_queryqueue = ''
vddb_queryexchange = ''
vddb_queryrouting_key = ''

# vddb result
vddb_resulturl = ''
vddb_resultqueue = ''
vddb_resultexchange = ''
vddb_resultrouting_key = ''

# swift
st_auth = ''
st_user = ''
st_key = ''
swith_path = "."

# dbpc
dp = None
dbpc_host = ''
dbpc_port = 0
dppc_service = ''
component = ''
interval = 0
try_times_limit = 0

# redis
redis_url = 'redis://127.0.0.1:6379/1'
rds_conn = None

# vddb async
mysystem_url = 'http://192.168.1.34/service/mysystem'
mysystem_host = "192.168.1.34"
mysystem_user = 'test2'
mysystem_passwd = '123456'
mysystem_port = 8081


# file dir
file_tmpdir = ''


# cas
cas_url = 'amqp://guest:guest@localhost:5672//'
cas_queue = ''
cas_exchange = ''
cas_routing_key = ''

# error_code
PARSE_INPUT_ERROR = 121500
GEN_DNA_ERROR = 121511
DOWNLOAD_SUCCESS = 0
DOWNLOAD_ERROR = 121509
DOWNLOAD_UNSPORTTYPE = 121508
DOWNLOAD_INVALIDTORRENT = 121512
SPLIT_FAR_ERROR = 121502
SWIFT_ERROR = 121503
UNKNOWN_ERROR = 121510

VIDEO_DNA_ERROR = 2
NOT_VIDEO = 1
NO_MATCH_FILTER = 3

# pushresult
pushresult_url = 'amqp://guest:guest@localhost:5672//'
pushresult_queue = ''
pushresult_exchange = ''
pushresult_routing_key = ''


# company
company = 0


RESULT_COPYWRITED = 0
RESULT_WORKING = 3
RESULT_NONE = 2


RESULT_WAIT = 0
RESULT_PUSH = 1


downloader_time = 0
downloader_retry = 0


ZIP_EXTENSIONS = []
# 0 no copy right 1 copy right 2 unkown 3 can not check
#statsd
statsdhost = ''
statsdport = 8125
statsd_conn = None
UNRECOGNIZED_ERROR_LIST = [VIDEO_DNA_ERROR,PARSE_INPUT_ERROR,SPLIT_FAR_ERROR,SWIFT_ERROR,DOWNLOAD_UNSPORTTYPE,DOWNLOAD_ERROR,UNKNOWN_ERROR,DOWNLOAD_INVALIDTORRENT]
NOMATCH_ERROR_LIST = [NOT_VIDEO,NO_MATCH_FILTER,GEN_DNA_ERROR]



rds_url_hot = ''
rds_cas_high = ''
rds_cas_low = ''
rds_cas_black = ''

rds_cas_black_conn =  None
rds_cas_high_conn = None
rds_cas_low_conn = None


