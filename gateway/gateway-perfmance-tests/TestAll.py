#!/usr/bin/env python
#coding: utf-8

import os
import re
import json
import time
import subprocess
import threading
from datetime import datetime

import psutil
import requests


TEST_SERVER_HOSTS = ['192.168.40.215', '192.168.40.91']
TEST_SERVER_PORT = 8999
TEST_REQ_TMPL = 'http://%(host)s:%(port)d/test'
APP_SERVER_IP = '192.168.3.235'
APP_SERVER_PATH_TMPL = 'http://%(ip)s:%(port)d/hello'
TARGET_REQUEST = {
    'path_tmpl': '',
    'headers': {
    },
    'params' : {
    }
}

SECONDS = 10
CONCURRENTS = [400, 600, 800, 1000, 1600]
PROCESSES_LST = [1, 4, 8, 16, 32]

HEADERS = {'Content-type': 'application/json', 'Accept': 'text/plain'}

REGEXPS = {
    'availability(%)' : r'^Availability.*\b(\d+\.\d+)\b.*',
    'transaction-rate(trans/sec)': r'^Transaction rate.*\b(\d+\.\d+)\b.*'
}


SUMMARY = {
    'INFO': {
        'TAG' : 'None',
        'SECONDS': SECONDS,
        'CONCURRENTS': CONCURRENTS,
        'PROCESSES_LST': PROCESSES_LST,
        'TEST_SERVER_HOSTS': TEST_SERVER_HOSTS,
        'APP_SERVER_IP' : APP_SERVER_IP
    },
    'tests': [
        {
            'app': 'test_http.go',
            'cmd_tmpl': './webapps/test_http.bin -port=%(port)d -size=%(processes)d 2>/dev/null 1>/dev/null',
            'port' : 9001,
            'results': []
        },
        {
            'app': 'test_martini.go',
            'cmd_tmpl': './webapps/test_martini.bin -port=%(port)d -size=%(processes)d 2>/dev/null 1>/dev/null',
            'port': 9002,
            'results': []
        },
        {
            'app': 'test_tornado.py',
            'port': 8001,
            'cmd_tmpl': './webapps/test_tornado.py --port=%(port)d --processes=%(processes)d  2>/dev/null 1>/dev/null',
            'results': []
        },
        {
            'app': 'test_webpy_gevent.py',
            'port': 8002,
            'cmd_tmpl': 'cd webapps && gunicorn -k gevent -w %(processes)d -b 0.0.0.0:%(port)d test_webpy_gevent:wsgiapp 2>/dev/null 1>/dev/null',
            'results': []
        }
    ]
}


time_now = lambda: datetime.now().strftime("%m-%d_%H:%M:%S")
results_lock = threading.Lock()

def kill_proc_tree(pid, including_parent=True):
    parent = psutil.Process(pid)
    for child in parent.children(recursive=True):
        try:
            child.kill()
        except psutil.NoSuchProcess:
            pass
    if including_parent:
        try:
            parent.kill()
        except psutil.NoSuchProcess:
            pass


def ping(url):
    status = False
    req = None
    try:
        req = requests.get(url, verify=False, timeout=2)
    except Exception as e:
        print 'Ping failed:', url, e
        time.sleep(30)

    if req and req.status_code == 200:
        status = True
    return status


def extract_test(data):
    output = data['output']
    result = {
        'output': output
    }
    for line in output.split('\n'):
        for name, regexp in REGEXPS.iteritems():
            m = re.match(regexp, line)
            if m:
                match_result = m.groups()[0]
                result[name] = float(match_result)
                break
    return result


def test_request(results, url, data, timeout):
    retry = 3
    resp_data = None
    while retry > 0:
        try:
            req = requests.post(url, headers=HEADERS, data=json.dumps(data), timeout=timeout)
            resp_data = req.json()
            retry = 0           # !!!
        except requests.Timeout as e:
            print (3-retry), e
            retry -= 1

    if resp_data:
        result = extract_test(resp_data)
        results_lock.acquire()
        results.append(result)
        results_lock.release()


def merge_test(datas):
    if len(datas) == 0: return None
    
    result = {}
    outputs = []
    keys = []
    for key in REGEXPS.keys():
        keys.append(key)
        # result[key] = []
        result[key + '_TOTAL'] = 0
        
    for data in datas:
        outputs.append(data['output'])
        for key in keys:
            if key not in data: continue
            # result[key].append(data[key])
            result[key + '_TOTAL'] = result[key + '_TOTAL'] + data[key]

    result['output'] = '\n\n'.join(outputs)
    return result


def do_test(app_url, concurrent, seconds=20):
    data = {
        'url': app_url,
        'concurrent': concurrent,
        'seconds': seconds,
    }
    timeout = seconds + 10

    results = []
    threads = []
    for host in TEST_SERVER_HOSTS:
        port = TEST_SERVER_PORT
        test_req_url = TEST_REQ_TMPL % locals()
        t = threading.Thread(target=test_request, args=(results, test_req_url, data, timeout))
        t.start()
        threads.append(t)

    [t.join() for t in threads]
    return merge_test(results)

    
def gen_server_results(cmd_tmpl, port, app_url):
    for processes in PROCESSES_LST:
        cmd = cmd_tmpl % locals()
        print 'Server:', cmd
        p = subprocess.Popen(cmd, shell=True,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        time.sleep(0.5)
        if not ping(app_url):
            yield {
                'processes': processes,
                'concurrent': -1,
                'output': 'PingError'
            }
            kill_proc_tree(p.pid)
            continue
            
        for concurrent in CONCURRENTS:
            result = do_test(app_url, concurrent, seconds=SECONDS)
            result['processes'] = processes
            result['concurrent'] = concurrent * len(TEST_SERVER_HOSTS)
            yield result

        kill_proc_tree(p.pid)
        time.sleep(3)


def main():
    def cmp_res(a, b):
        c1, c2 = a['concurrent'], b['concurrent']
        if c1 > c2: return 1
        if c1 < c2: return -1
        
        p1, p2 = a['processes'], b['processes']
        if p1 > p2: return 1
        if p1 <= p2: return -1


    for info in SUMMARY['tests']:
        cmd_tmpl = info['cmd_tmpl']
        port = info['port']
        ip = APP_SERVER_IP
        app_url = APP_SERVER_PATH_TMPL % locals()
        results = info['results']
        print 'Section:', info['app'], app_url
        print time_now()
        print '=================='
        
        for result in gen_server_results(cmd_tmpl, port, app_url):
            print 'section: {0}, processes: {1}, concurrent: {2}'.format(info['app'], result['processes'], result['concurrent'])
            output = result.pop('output')
            print '--------------------'
            print output
            print '--------------------'
            print time_now(), info['app']
            print '----------------------------------------\n'
            results.append(result)
            
        results.sort(cmp=cmp_res)
        print '======================================================\n\n'
            
    with open(os.path.join('results', '{0}_summary.json'.format(time_now())), 'w') as f:
        f.write(json.dumps(SUMMARY, indent=4))


if __name__ == '__main__':
    main()
