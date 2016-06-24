
import sys
import re
from task_container import TaskContainer

def check_valid(task):
    keys = ["duplicate"
    , "status"
    , "task_info"
    , "create_time"
    , "execute_time"
    , "tries"
    , "update_time"
    , "worker"]
    return task.keys().sort() == keys.sort()

# format redis://host:port/db
redis_url = sys.argv[1]
db = None
m = re.match("redis://([^:/]+):{0,1}(\d+){0,1}/*(\d+){0,1}", redis_url)
if m:
    db = m.groups()[2]

db = 0 if db is None else int(db)
finishdb = db + 1

sys.exit()

task_dict = {'init':{}, 'processing':{}, 'finish':{}}
tc = TaskContainer(url=redis_url, worker_prefix='Display')

tids = tc.get_all_tasks()

for tid in tids:
    task_all_info = tc.get_task_all_info(tid)
    status = task_all_info['status']
    task_dict[status][tid] = task_all_info

def display_st_cnt():
    for key, value in task_dict.items():
        print "%s count: %d" % (key, len(value))

def display_invalid_task():
    for key, value in task_dict.items():
        for tid, task in value.items():
            if check_valid(task) is False:
                print "digest: %s is invalid, status is %s" % (tid, key)

def display_all_tasks():
    for key, value in task_dict.items():
        for tid, task in value.items():
            print "digest: %s, status: %s, task: %s" % (tid, key, str(task))


display_st_cnt()
display_all_tasks()
display_invalid_task()

