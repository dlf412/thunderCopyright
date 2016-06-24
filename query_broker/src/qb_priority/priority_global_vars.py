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
# global logger
logger = None
module = 'process_task'
log_file = ''
# qb
qb_url = 'amqp://guest:guest@localhost:5672//'
qb_queue = ''
qb_exchange = ''
qb_routing_key = ''

# cas
cas_url = 'amqp://guest:guest@localhost:5672//'
cas_queue = ''
cas_exchange = ''
cas_routing_key = ''
priority = 'low'

cashigh_url = 'amqp://guest:guest@localhost:5672//'
cashigh_queue = ''
cashigh_exchange = ''
cashigh_routing_key = ''


# pushresult
pushresult_url = 'amqp://guest:guest@localhost:5672//'
pushresult_queue = ''
pushresult_exchange = ''
pushresult_routing_key = ''

# dbpc
dp = None
dbpc_host = ''
dbpc_port = 0
dppc_service = ''
component = ''
interval = 0
try_times_limit = 0


# number
task_number = 0

# pushresult
pushresult_url = 'amqp://guest:guest@localhost:5672//'
pushresult_queue = ''
pushresult_exchange = ''
pushresult_routing_key = ''


RESULT_COPYWRITED = 1
RESULT_WORKING = 2
RESULT_NONE = 3


st_auth = ''
st_user = ''
st_key = ''
swith_path = "./"

# vddb async
mediawise_url = 'http://192.168.1.34/service/mediawise'
mediawise_host = "192.168.1.34"
mediawise_user = 'test2'
mediawise_passwd = '123456'
meidawise_port = 8081


# mysql con
mysql_conn_pool = None
databases = ''
# file_ext_list
file_ext_list = []
min_file_size = 0
max_file_size = 100000
suspicious_mime_types = []


# taskprioritymq
taskpriorit_url = 'amqp://guest:guest@localhost:5672//'
taskpriorit_queue = ''
taskpriorit_exchange = ''
taskpriorit_routing_key = ''


# statsdserver
statsdhost = ''
statsdport = 8125
statsd_conn = None

#video rating
strkey = ''
keyword_trie = None
black_keyword_trie = None

rds_url_hot = ''
rds_cas_high = ''
rds_cas_low = ''
rds_cas_black = ''

rds_url_hot_conn = None
rds_cas_black_conn =  None
rds_cas_high_conn = None
rds_cas_low_conn = None

ttl = 2
special_char = []




