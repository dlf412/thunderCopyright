#!/usr/bin/python
import happybase
import MySQLdb
from MySQLdb import escape_string
import uuid

hbpool = happybase.ConnectionPool(1,host="master",port=9090)
task_uuid = str(uuid.uuid1())
site_asset_id = ['url_hash#'+str(uuid.uuid1()), 'seed_hash#'+str(uuid.uuid1())]
store_data = {
    'site_asset_id': site_asset_id,
    'task_uuid': task_uuid,
    'dna_url': 'dna_20131217/merge.dna',
    'created_at': 1405647635.235882,
    'task_priority': 0,
    'company_id': 11,
    'query_scope': [
    ],
    'extra_info_path': 'seed_hash_swift_path',
    'clip_format': 'dna',
    'site_asset_ids': [
    ],
    'extra_info': 'sdfssdfsdf'
}


def storeTask(task):
    with hbpool.connection() as connection:
        table = connection.table("task")
        batch = table.batch(transaction=True)
        data = {
                'task_priority':'i:task_priority',
                'user_id':'i:user_id',
                'company_id':'i:company_id',
                'dna':'i:dna',
                'site_asset_id':'i:site_asset_id',
                'created_at':'i:created_at',
                'extra_info':'i:extra_info',
                'extra_info_path':'i:extra_info_path',
                'dna_url':'i:dna_url'
        }
        value = {}
        for k ,v in task.items():
            if not data.has_key(k):
                continue
            value[data[k]]=str(v)
        row = task['task_uuid']
        batch.put(row, value)
        batch.send()

def storeMysql(task_uuid, site_asset_id):
    conn = MySQLdb.connect(host="192.168.1.34",user="root", passwd="123", db="media_wise")
    cur = conn.cursor()
    cmd = ("insert into task(task_identification, task_priority,"
                 "created_at, dna_url, user_id, company_id, clip_format, site_asset_id) "
                 "values('%s', 1, now(), 'dna_20131217/merge.dna', 1, 11, 'dna','%s')"
                 % (task_uuid, escape_string(str(site_asset_id))))
    print cmd
    cur.execute(cmd)
    conn.commit()
    cur.close()
    conn.close()

def store_sid_tids():
    with hbpool.connection() as connection:
        table = connection.table("sid_tids")
        batch = table.batch(transaction=True)
        for sid in store_data['site_asset_id']:
            row = sid
            value = {"t:task_uuids":"%s" % task_uuid}
            batch.put(row, value)
        batch.send()

print "begin store task"
print "task_uuid: %s" % task_uuid
print "site_asset_id: %s" % site_asset_id
print store_data
storeTask(store_data)
store_sid_tids()
storeMysql(task_uuid, site_asset_id)
print "store task success"
