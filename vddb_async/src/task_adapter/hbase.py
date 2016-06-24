#!/usr/bin/python
from global_var import config, hbpool
import json
def storeHbaseImpl(table, row, data):
    with hbpool.connection() as conn:
        t = conn.table(table)
        t.put(row, data)

def getHbaseImpl(table, row , columns=None):
    with hbpool.connection() as conn:
        t = conn.table(table)
        res = t.row(row, columns=columns)
        #logger.info("re")
        return res

def dropHbaseImpl(table, row, columns=None):
    with hbpool.connection() as conn:
        t = conn.table(table)
        t.delete(row)

def scanHbaseImpl(table, row_prefix=None, filt=None, columns=None, limit=None):
    with hbpool.connection() as conn:
        t = conn.table(table)
        res = t.scan(row_prefix=row_prefix, filter=filt, columns=columns,
                limit=limit)
        re = {}
        for i in res:
            #print i[0] , i[1]
            re[str(i[0])]=i[1]
        return re


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
                'dna_url':'i:dna_url',
                'external_id':'i:external_id',
                'seed_hash':'i:seed_hash'
        }
        value = {}
        for k , v in task.items():
            if not data.has_key(k):
                continue
            value[data[k]] = str(v)
        row = task['task_uuid']
        batch.put(str(row), value)
        batch.send()

def checkSids(site_asset_ids):
    for i in  site_asset_ids:
        res = getHbaseImpl('sid_tid', i, columns =['t:task_uuid','t:source'])
        print res
        if res !={} and res.get('t:source', '')!='manual_tmp':
            return res['t:task_uuid']
    return None
def storeSid(task_id, site_ids):
    for i in site_ids:
        if i =='':
            continue
        storeHbaseImpl('sid_tid', str(i),{'t:task_uuid': str(task_id)})

def storeSeedHash(ha, task_id):
    for i in ha:
        if i =='':
            continue
        res = getHbaseImpl('sid_tid', i, columns=['t:task_uuid'])
        if res == {}:
            lis = [task_id]
            storeHbaseImpl('sid_tid', str(i),{'t:task_uuid': str(lis)})
            logger.info('eeeeeeeeeee')
            #batch.put(str(i), {'t:task_uuids': str(lis)})
        else:
            try:
                r = eval(res['t:task_uuid'])
                r.append(task_id)
                storeHbaseImpl('sid_tid', str(i),{'t:task_uuid': str(r)})
                #atch.put(str(i), {'t:task_uuids': str(r)})
            except :
                logger.error('strore site_asset_id error, site_asset_id')

def getMatches(t):
    #filt = "PrefixFilter (%s)"%t
    res = scanHbaseImpl('matches', row_prefix=t)
    return res

def getCrr(t):
     res = getHbaseImpl('crr', t)

def getTask(t):
    res = getHbaseImpl('task', t)
    return res

def scanUnpush(status,  limit=None):
    filt = "SingleColumnValueFilter('u', 'status', =, 'binary:%s')"% status
    columns = ['u:status']
    res = scanHbaseImpl('unpush', columns =columns, limit=limit, filt =filt)
    return res

def dropUnpush(t):
    dropHbaseImpl('unpush', t)

def updateFinished(t, status):
    storeHbaseImpl('finished', t , {'f:push_status':status})

def changeStatus(t, status):
    storeHbaseImpl('unpush', t, {'u:status':status})

def updateTid(task_id, site_sids):
    res = scanHbaseImpl('tid_sid', row_prefix=task_id)
    lis = [v for k,v in  res.items()]
    n = len(lis)
    for i in  site_sids:
        if not i in lis:
            n+=1
            storeHbaseImpl('task_info', '-'.join([str(task_id), str(n)]),
                        {'t:site_asset_id':str(i)})
def updateTaskInfo(task_id, extra, url):
    res = scanHbaseImpl('task_info', row_prefix=task_id)
    storeHbaseImpl('task_info', '-'.join([task_id, str(len(res)+1)]),
                {'t:extra_info':str(extra), 't:extra_info_url':str(url)})

def storeTid(task_id, site_ids):
    if site_ids:
        n = 1
        for i in site_ids:
            storeHbaseImpl('tid_sid', '-'.join([task_id, str(n)]),
                        {'t:site_asset_id':str(i)})
            n += 1
def storeTaskInfo(task_id, extra_info, url):
    if extra_info:
        storeHbaseImpl('task_info', '-'.join([task_id, '1']),
                    {'t:extra_info':str(extra_info),
                     't:extra_info_url':str(url)})

def get_tid_sid(task_id):
    res = scanHbaseImpl('tid_sid', row_prefix=task_id)
    print '-------------res%s'%res
    lis = [v['t:site_asset_id'] for k,v in res.items()]
    return lis 

def get_extra_info(task_id):
    res = scanHbaseImpl('task_info', row_prefix=task_id)
    print '-------------res%s'%res
    lis = [json.loads(v['t:extra_info']) for k,v in res.items()]
    return lis

