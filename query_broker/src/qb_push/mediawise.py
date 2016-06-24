#!/usr/bin/env python
#coding: utf-8


import os
import json
from datetime import datetime

import requests

MEDIAWISE_TIMEOUT = 15
MEDIAWISE_RETRY = 1

OVERALL_COPYRIGHTED = 0
OVERALL_UNCOPYRIGHTED = 1
OVERALL_UNDETECTED = 2
OVERALL_WORKING = 3

STATUS_COPYRIGHTED = 0
STATUS_UNCOPYRIGHTED = 1
STATUS_UNDETECTED = 2
STATUS_WORKING = 3

# ==============================================================================
#  MediaWise
# ==============================================================================
def http_request(url, data=None, params=None, timeout=MEDIAWISE_TIMEOUT, retry=MEDIAWISE_RETRY):
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

    
class MediaWiseError(Exception): pass
class MediaWise(object):
    """
    Usage:
    =======
        >>> from common.mediawise import MediaWise
        >>> mw = MediaWise(MEDIA_WISE_USER, MEDIA_WISE_PASSWD,
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
        ::Reference: http://seals.vobile.cn/trac/vdna/wiki/thunder_mediawise
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
            raise  MediaWiseError('Request mediawise failed!')

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
                    'action': 'mediawise-result-error.',
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
            overall = OVERALL_WORKING 
        # 3. <fake + real> results
        # 4. All real results
        elif lst_len > 0:
            copyrighted_cnt = 0
            uncopyrighted_cnt = 0
            undetected_cnt = 0
            working_cnt = 0
            
            for item in listing:
                status = item['status']
                if status == STATUS_WORKING:
                    working_cnt += 1
                elif status == STATUS_COPYRIGHTED:
                    copyrighted_cnt += 1
                elif status == STATUS_UNCOPYRIGHTED:
                    uncopyrighted_cnt += 1
                elif status == STATUS_UNDETECTED:
                    undetected_cnt += 1

            if working_cnt > 0:
                overall = OVERALL_WORKING 
            elif copyrighted_cnt > 0:
                overall = OVERALL_COPYRIGHTED 
            elif lst_len == undetected_cnt:
                overall = OVERALL_UNDETECTED
            elif lst_len == undetected_cnt + uncopyrighted_cnt:
                overall = OVERALL_UNCOPYRIGHTED 
        
        if self.logger:
            self.logger.info("query-vddb-async#%s" % json.dumps({
                'action': 'mediawise-result-summary',
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
