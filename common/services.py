#!/usr/bin/env python
#coding: utf-8


import os
import json
from datetime import datetime

import requests

from .utils import execute

STATUS_COPYRIGHTED = 0
STATUS_UNCOPYRIGHTED = 1
STATUS_UNDETECTED = 2
STATUS_WORKING = 3

OVERALL_WORKING = 3
OVERALL_HAS_COPYRIGHTED = 0
OVERALL_ALL_UNDETECTED = 2
OVERALL_UNDETECTED_UNCOPYRIGHTED = 1

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
        ::Reference: http://seals.mysite.cn/trac/vdna/wiki/thunder_result_management
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
        only1_status = None
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
            tasks_count = result['tasks_count']
            if tasks_count == 1:
                task = tasks[0]
                only1_status = task['status']
            elif tasks_count > 1:
                for task in tasks:
                    site_asset_ids = task.get('site_asset_id', [])
                    is_tmp_case = False
                    for assert_id in site_asset_ids:
                        if assert_id == req_hash:
                            is_tmp_case = True
                            break
                    if is_tmp_case:
                        continue
                    
                    status = task.get('status', None)
                    extra_infos = task.get('extra_info', [])
                    path = None
                    prefix = req_hash.split('#', 1)[0]
                    for extra_info in extra_infos:
                        _hash = extra_info.get(prefix)
                        if req_hash == _hash:
                            path = extra_info.get('file_path')
                    listing.append({
                        'status': status,
                        'path': path
                    })

        overall = None
        lst_len = len(listing)

        # 1. Only one result
        if tasks_count == 1:
            overall = only1_status
        # 2. Sub tasks is working
        elif lst_len < tasks_count:
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
                overall = OVERALL_HAS_COPYRIGHTED
            elif lst_len == undetected_cnt:
                overall = OVERALL_ALL_UNDETECTED
            elif lst_len == undetected_cnt + uncopyrighted_cnt:
                overall = OVERALL_UNDETECTED_UNCOPYRIGHTED
        
        if self.logger:
            self.logger.info("query-vddb-async#%s" % json.dumps({
                'action': 'mysystem-result-summary',
                'uuid': uuid,
                'info': {
                    'only1_status': only1_status,
                    'tasks_count': tasks_count,
                    'overall': overall,
                    'listing': listing
                }
            }))
        return overall, listing



# ==============================================================================
#  Swift (upload/)
# ==============================================================================        
class SwiftInitError(Exception):
    def __str__(self):
        return str(self.__dict__)
        
class SwiftUploadError(Exception): 
    def __str__(self):
        return str(self.__dict__)


class _Swift(object):
    pass


class Swift(object):
    """
    Usage:
    ======
        >>> swift = Swift('tools/swift', 'http://192.168.200.10:8080/auth/v1.0', 'system:root', 'testpass')
    
        >>> swift.upload('container', '/tmp/exists-file.txt')

    
        file_path = '/tmp/new-file.txt'
        try:
            swift.upload(file_path, content='abcdefXYZ')
            # Other code...
        except SwiftUploadError as e:
            logger.error(mk_logmsg({
                'action': 'Upload swift.',
                'uuid': self.uuid,
                'error': {
                    'message': str(e),
                }
            }))
            raise
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)
    """
    
    def __init__(self, path, auth, user, key):
        self.path = path
        self.auth = auth
        self.user = user
        self.key = key


    def container(self):
        return datetime.now().strftime('%Y-%m-%d_%H')
        
        
    def create_container(self):
        """ Create container """

        # Dead code below, because tools/swift will automatic create container.
        args = {
            'path': self.path,
            'auth': self.auth,
            'user': self.user,
            'key': self.key,
            'container': self.container()
        }
        cmd = '%(path)s -A %(auth)s -U %(user)s -K %(key)s post %(container)s' % args
        _, _, err = execute(cmd)
        err = err.strip()
        if err:
            ex = SwiftInitError('Init failed!')
            ex.cmd = cmd
            ex.error = err
            raise ex


    def upload(self, filepath, container=None, content=None, retry=2):
        
        if not os.path.exists(filepath) and content is None:
            raise SwiftUploadError('If you want upload as new file, content required !')

        if isinstance(content, unicode):
            content = content.encode('utf-8')
        if not isinstance(content, str):
            raise SwiftUploadError('`content` must be `str` type!')

        if content is not None:
            with open(filepath, 'w') as f:
                f.write(content)

        if not container:
            container = self.container()
        args = {
            'path': self.path,
            'auth': self.auth,
            'user': self.user,
            'key': self.key,
            'container': container,
            'filepath': filepath,
        }
        cmd = '%(path)s -A %(auth)s -U %(user)s -K %(key)s upload %(container)s "%(filepath)s"' % args

        ok = False
        errors = []
        while retry > 0:
            try:
                _, _, err = execute(cmd)
                err = err.strip()
                if not err:
                    ok = True
                    break
                else:
                    errors.append(err)
                    ok = False
                    retry -= 1
            except OSError as e:
                errors.append(e)
                retry -= 1
                
        if not ok:
            ex = SwiftUploadError('Upload Failed')
            ex.cmd = cmd
            ex.error = errors
            raise ex
        return container
