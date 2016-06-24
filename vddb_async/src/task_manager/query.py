from task_stat import *
from utils import datestr

from collections import defaultdict
import logging
from math import isnan
from os import getenv, makedirs, system
from os.path import exists
import re
from shutil import rmtree
from xml.dom import minidom
from show_meta import meta
import xpath

class BackendError(ValueError):
    def __init__(self):
        super(BackendError, self).__init__()

class query(object):
    CMD_FORMAT = '''vdna_query -T DNA -i '{dna}' -s '{backend}' -u '{user}' \
                               -w '{password}' -r '{receipt}' -N '{crr}' \
                               -C '{domain}' -b '{site}' --sample_id={sample}'''

    def __init__(self, task, account, backend, site_file, timestr):
        self.path = getenv('MW_HOME')
        assert self.path != None
        self.logger = logging.getLogger('mwtm_query')

        self.task = task
        self.account = account
        self.backend = backend
        # self.parse_extra(backend.extra)
        self.site_file = site_file
        self.timestr = timestr

        ds = datestr(self.task.created_at)
        uuid = self.task.uuid
        self.dna = '/'.join([self.path, 'var', 'tmp', ds, uuid, timestr, 'merge.dna'])

        self.scope = None
        self.state = None
        self.result = {}

    def pick_backend(self):
        backend = self.backend
        if self.state.hot:
            return (backend.hot_addr, backend.hot_user, backend.hot_pass)
        else:
            return (backend.address, backend.user, backend.password)

    def query_dir(self, backend):
        ds = datestr(self.task.created_at)
        uuid = self.task.uuid
        task_dir = '/'.join([self.path, 'var', 'tmp', ds, uuid])
        return '/'.join([task_dir, backend, self.timestr] +
                        (['hot'] if self.state.hot else []) +
                        (['slicing'] if self.state.slicing else []))

    def dna_file(self):
        if self.state.slicing:
            ds = datestr(self.task.created_at)
            uuid = self.task.uuid
            task_dir = '/'.join([self.path, 'var', 'tmp', ds, uuid])
            # all backends can share the same sliced dna
            return '/'.join([task_dir, self.timestr, 'sliced.dna'])
        else:
            return self.dna

    def piece_cmd(self, qdir):
        be, u, p = self.pick_backend()
        cmd = self.CMD_FORMAT.format(dna=self.dna_file(), backend=be, user=u,
                                     password=p, receipt=qdir + '/receipt',
                                     crr=qdir + '/crr',
                                     domain=self.account.domain,
                                     site=self.site_file, sample=self.task.id)

        if self.backend.level > 0: # 0 for default
            cmd += ' -l ' + str(self.backend.level)
        if self.backend.mode >= 0: # -1 for default
            cmd += ' -m ' + str(self.backend.mode)

        if self.scope != None:
            cmd += ' --scope ' + ','.join(self.scope)
        elif self.task.scope != None:
            cmd += ' --scope ' + ','.join(self.task.scope)

        cmd += ' ' + self.backend.extra
        cmd += ' >/dev/null 2>&1'
        return cmd

    # def parse_extra(self, extra):
    #     if extra == None:
    #         self.extra = ''
    #         return

    #     hotp = re.compile('(^|^.* )abc ([^ ]+)($| .*$)')
    #     m = hotp.match(self.extra)
    #     if m != None:
    #         d = self.hot_backend._asdict()
    #         d['address'] = m.group(2)
    #         self.hot_backend = self.hot_backend._class__(**d, extra)
    #         self.extra = m.group(1) + m.group(3)
    #     else:
    #         self.extra = extra

    def query(self):
        be, _, _ = self.pick_backend()
        qdir = self.query_dir(be)
        try:
            if not exists(qdir):
                makedirs(qdir)
        except:
            self.logger.error('failed to mkdir for task %s: %s', self.task.uuid,
                              qdir, exc_info=True)
            self.result = dict(code=SYSTEM)
            return
        else:
            self.logger.debug('query dir for task %s: %s', self.task.uuid, qdir)

        cmd = self.piece_cmd(qdir)
        self.logger.debug('vdna_query command for task %s: %s', self.task.uuid,
                          cmd)
        system(cmd)

        try:
            self.parse_receipt(qdir + '/receipt')
            self.parse_crr(qdir + '/crr')
        except BackendError:
            self.logger.error('backend reports error for task %s: %s ',
                              self.task.uuid, qdir, exc_info=True)
            self.result['code'] = 0
        except:
            self.logger.error('failed to process backend results for task %s: ' +
                              '%s', self.task.uuid, qdir, exc_info=True)
            self.result = dict(code=BAD_OUTPUT)
        else:
            rmtree(qdir, True)
            self.result['code'] = 0
            self.result['backend_code'] = 0

    def parse_crr(self, fn):
        with open(fn) as f:
            crr = f.read()

        self.logger.debug('crr file for task %s: %s => %s', self.task.uuid,
                          fn, crr)

        if crr == '':
            self.result['crr'] = crr
            return

        doc = minidom.parseString(crr)
        fm = str(xpath.find('string(//Format)', doc))
        if fm == 'dna' or fm == 'DNA':
            fmnode = xpath.find('//Format', doc)[0]
            fmnode.replaceChild(doc.createTextNode(self.task.clip_format),
                                fmnode.firstChild)
            self.result['crr'] = doc.toxml()

            self.logger.debug('updated for task %s: %s', self.task.uuid,
                              self.result['crr'])
        else:
            self.result['crr'] = crr

    def meta_info(self, meta_uuid):
        be, u, p = self.pick_backend()
        mi = meta(host=be, port=443, user=u, password=p,
                  meta_uuid=meta_uuid)
        return mi.get()

    def parse_receipt(self, fn):
        with open(fn) as f:
            rcpt = f.read()

        self.logger.debug('receipt file for task %s: %s => %s', self.task.uuid,
                          fn, rcpt)

        doc = minidom.parseString(rcpt)
        code = xpath.find('number(//query/return_code)', doc)
        if isnan(code):
            raise ValueError('backend code not found in receipt')
        self.result['backend_code'] = int(code + 0.5)
        if self.result['backend_code'] != 0:
            raise BackendError()

        ms = defaultdict(lambda: dict(video_duration=0, audio_duration=0))
        mstags = xpath.find('//matches/match', doc)
        for mtag in mstags:
            uuid = xpath.find('string(master_uuid)', mtag)
            info = self.meta_info(uuid)
            if len(uuid) == 0:
                raise ValueError('no master uuid in match info')
            m = ms[uuid]
            t = str(xpath.find('string(track_type)', mtag))
            if not t in ('video', 'audio'):
                raise ValueError('invalid track type in match info')
            dur = int(xpath.find('number(match_duration)', mtag))
            if m[t + '_duration'] < dur:
                m[t + '_duration'] = dur
                m[t + '_score'] = int(xpath.find('number(score)', mtag))
                roff = int(xpath.find('number(reference_offset)', mtag))
                m[t + '_ref_offset'] = roff
                soff = int(xpath.find('number(sample_offset)', mtag))
                m[t + '_sample_offset'] = soff
                m['meta_uuid'] = uuid
                m['meta_name'] = xpath.find('string(master_name)', mtag)
                m['instance_id'] = xpath.find('string(instance_id)', mtag)
                m['instance_name'] = xpath.find('string(instance_name)', mtag)
                m['track_id'] = xpath.find('number(track_id)', mtag)
                m['company_id'] = str(info['company_id'])
        # for m in ms.itervalues():
        #     if m['video_duration'] > 0 and m['video_duration'] > 0:
        #         m['match_type'] = 'both'
        #     elif m['video_duration'] > 0:
        #         m['match_type'] = 'video'
        #     else:
        #         m['match_type'] = 'audio'
        self.result['matches'] = ms

    def update_state(self, state):
        if (self.state != None and self.state.slicing) and not state.slicing:
            # set scope for query after slicing
            assert self.result['matches'] != None
            self.scope = self.result['matches'].keys()

        self.state = state
        self.scope = None
        self.result = {}
