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


# thunderserver
thunder_server = ''

# statsdserver
statsdhost = ''
statsdport = 8125
statsd_conn = None

is_push = False
