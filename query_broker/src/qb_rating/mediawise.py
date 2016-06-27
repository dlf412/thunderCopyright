#!/usr/bin/env python
#coding: utf-8


import os
import json
from datetime import datetime

import requests



# ==============================================================================
#  mysystem
# ==============================================================================
def http_request(url, data=None, params=None, timeout=15, retry=1):
    """ Send a GET or POST request, default will retry 2 times. """

    resp = None
    times = 1
    logs = []
    while times <= retry:
        try:
            if data is None:
                resp = requests.get(url, params=params, timeout=timeout)
            else:
                resp = requests.post(url, params=params, data=data, timeout=timeout)
            break
        except requests.ConnectionError as e:
            logs.append({
                'level': 'error',
                'action': 'http-request',
                'error': str(e),
                'info': {
                    'url': url,
                    'times': times,
                }
            })
            times += 1
        except requests.Timeout as e:
            logs.append({
                'level': 'error',
                'action': 'http-request',
                'error': str(e),
                'info': {
                    'url': url,
                    'times': times,
                }
            })
            times += 1
    return resp, logs

    
class mysystemError(Exception): pass
class mysystem(object):
    """
    Usage:
    =======
        >>> from common.mysystem import mysystem
        >>> mw = mysystem(MEDIA_WISE_USER, MEDIA_WISE_PASSWD,
                           MEDIA_WISE_URL, MEDIA_WISE_REQ_TIMEOUT,
                           logger)
        >>> print mw.query("url_hash#SOME-HASH-STRING")
        (False, False)
    """

    def __init__(self, user, passwd, query_url, all_matches, req_timeout, logger=None):
        self.logger = logger
        self.USER = user
        self.PASSWD = passwd
        self.QUERY_URL = query_url
        self.ALL_MATCHES = all_matches
        self.REQ_TIMEOUT = req_timeout


    def query(self, req_hash, uuid=None):
        """
        ::Reference: http://seals.mysite.cn/trac/vdna/wiki/thunder_mysystem
        """
        all_matches = 'True' if self.ALL_MATCHES else 'False'
        params = {
            'site_asset_id' : req_hash,
            'all_matches': all_matches
        }
        resp, logs = http_request(self.QUERY_URL, params=params, timeout=self.REQ_TIMEOUT)

        if self.logger:
            for log in logs:
                level = log.pop('level')
                _logger = getattr(self.logger, level)
                _logger("query-vddb-async#%s" % json.dumps(log))

        if resp is None:
            raise  mysystemError('Request mysystem failed!')

        # return: None or what self.result() need
        listing = []
        has_fake = False
        fake_status = None
        tasks_count = None

        if self.logger:
            self.logger.info("query-vddb-async#%s" % json.dumps({
                'action': 'show-response-info',
                'uuid': uuid,
                'info': {
                    'params': params,
                    'resp': resp.text
                }
            }))
        ret_data = resp.json()
        error = ret_data.get('error', None)
        if error:
            if self.logger:
                self.logger.warning("query-vddb-async#%s" % json.dumps({
                    'action': 'mysystem-result-error.',
                    'uuid': uuid,
                    'info': {
                        'error': error,
                        'hash': req_hash
                    }
                }))
            return None, []
        else:
            result = ret_data.get('result', {})
            tasks = result.get('tasks', [])
            tasks_count = result.get('tasks_count')
            if tasks_count == 1:
                task = tasks[0]
                fake_status = task['status']
            elif tasks_count > 1:
                for task in tasks:
                    status = task.get('status', None)
                    extra_info = task.get('extra_info', [{}])
                    extra_info = extra_info[0] if extra_info else {}
                    path = extra_info.get('path', None)
                    listing.append({
                        'status': status,
                        'path': path
                    })


        overall = None
        lst_len = len(listing)
            
        # 1. Only has fake result
        if tasks_count == 1:
            overall = fake_status
        # 2. Sub tasks is working
        elif lst_len < tasks_count - 1:
            overall = 3
        # 3. <fake + real> results
        # 4. All real results
        elif lst_len > 0:
            copyrighted_cnt = 0
            uncopyrighted_cnt = 0
            undetected_cnt = 0
            working_cnt = 0
            
            for item in listing:
                status = item['status']
                if status == 3:
                    working_cnt += 1
                elif status == 0:
                    copyrighted_cnt += 1
                elif status == 1:
                    uncopyrighted_cnt += 1
                elif status == 2:
                    undetected_cnt += 1

            if working_cnt > 0:
                overall = 3
            elif copyrighted_cnt > 0:
                overall = 0
            elif lst_len == undetected_cnt:
                overall = 2
            elif lst_len == undetected_cnt + uncopyrighted_cnt:
                overall = 1
        
        if self.logger:
            self.logger.info("query-vddb-async#%s" % json.dumps({
                'action': 'mysystem-result-summary',
                'uuid': uuid,
                'info': {
                    'has_fake': has_fake,
                    'fake_status': fake_status,
                    'tasks_count': tasks_count,
                    'overall': overall,
                    'listing': listing
                }
            }))
        return overall, listing



# ==============================================================================
#  Swift (upload/)
# ==============================================================================        
