#!/usr/bin/env python

from os import getenv
import os
import sys
path = getenv('MW_HOME')
sys.path.append('/'.join([path, 'lib']))
os.environ['PATH'] = ':'.join([os.environ['PATH'], '/'.join([path, 'bin'])])

from query import query
from task_stat import *
from task_finish import TaskTerminator
from utils import datestr, popen

from argparse import ArgumentParser
from collections import namedtuple
from datetime import datetime
import logging, logging.config
from os import _exit, getpid, killpg, makedirs, setpgrp, system, abort
import re
from shutil import rmtree
from signal import signal, SIGQUIT, SIGTERM, SIGINT
import simplejson as json
from threading import Thread
import urllib
import logging
from parse_config import parse_config

KILLED = 9
ERROR = 255

class query_state(object):
    State = namedtuple('State', ['slicing', 'hot'])

    @classmethod
    def initial(cls, **setting):
        s = namedtuple('_', setting.keys())
        setting = s(**setting)
        return cls(setting, slicing=setting.slicing, hot=False)

    def __init__(self, setting, **state):
        self.logger = logging.getLogger('mwtm_executor')

        self.setting = setting
        self.state = self.State(**state)

    def update_query(self, q):
        q.update_state(self.state)

    def hot_transition(self, matched):
        if not matched and not self.state.hot and self.setting.hot:
            # continue to do hot query
            self.logger.debug('to transit into hot query, matched: %s, state: ' +
                              '%s, setting: %s', matched, self.state,
                              self.setting)
            return self.__class__(self.setting, slicing=self.setting.slicing,
                                  hot=True)
        else:
            # no hot state to continue into, or no need to do hot, break
            self.logger.debug('to stop querying, matched: %s, state: %s, ' +
                              'setting: %s', matched, self.state, self.setting)
            return None

    def next(self, res):
        matched = 'matches' in res and len(res['matches']) != 0

        if self.state.slicing and matched:
            # continue querying with original dna
            self.logger.debug('tp transit into non-slice, matched: %s, state: ' +
                              '%s, setting: %s', matched, self.state,
                              self.setting)
            return self.__class__(self.setting, slicing=False,
                                  hot=self.state.hot)
        else:
            return self.hot_transition(matched)

class query_runner(Thread):
    def __init__(self, task, account, backend, site_file, timestr, clip_duration):
        super(query_runner, self).__init__()

        can_slice = False
        if account.slicing:
            can_slice = clip_duration > account.slice_duration
        self.state = query_state.initial(slicing=account.slicing and can_slice,
                                         hot=backend.hot_user != None)
        self.query = query(task, account, backend, site_file, timestr)
        self.result = None

    def run(self):
        qs = self.state
        while qs != None:
            qs.update_query(self.query)
            self.query.query()
            self.result = dict(**self.query.result)
            if qs.state.slicing:
                self.result['matches'] = {}
                self.result['crr'] = None
            qs = qs.next(self.query.result)

class task_executor(object):
    def __init__(self, task, account):
        self.path = getenv('MW_HOME')
        assert self.path != None
        self.logger = logging.getLogger('mwtm_executor')

        self.task = task
        self.account = account
        self.timestr = datetime.utcnow().strftime('%Y%m%dT%H%M%S')
        self.config = parse_config('/'.join([path, 'etc',
                                            'vddb_async.conf']))

        self.result = None
        self.dna = None
        self.dna_duration = None
        self.dna_type = None

    def exec_dir(self):
        ds = datestr(self.task.created_at)
        uuid = self.task.uuid
        return '/'.join([self.path, 'var', 'tmp', ds, uuid, self.timestr])

    def task_dir(self):
        ds = datestr(self.task.created_at)
        uuid = self.task.uuid
        return '/'.join([self.path, 'var', 'cache', ds, uuid[6:8], uuid[21:23],
                         uuid])

    def parse_dna_url(self, dna_url):
        d = dna_url.strip(" ").split("/")
        if d[0] == "":
            return "/"+d[1], '/'.join(d[2:])
        else:
            return d[0], '/'.join(d[1:])

    def download(self):
        success = False
        container, remote_path = self.parse_dna_url(self.task.dna_url)
        cmd = "swift download -A {auth} -U {user} -K {key} {container} -o {dna_file} "\
              "{remote_path}".format(auth=self.config['swift_auth'],
                                     user=self.config['swift_user'],
                                     key=self.config['swift_key'],
                                     container=container,
                                     dna_file=self.dna,
                                     remote_path=remote_path
                                     )
        ret, _, err = popen(cmd)
        if ret or err:
            self.logger.error("download falied cmd: %s, url: %s, ret: %s, err: %s"  %
                             (cmd, self.task.dna_url, ret, err))
        else:
            self.logger.info("download success, url:%s " % self.task.dna_url)
            success = True
        return success

    def parse_dna(self):
        cmd = "dna_status -i {dna} 2>&1".format(dna=self.dna)
        ret, out, err = popen(cmd)
        self.logger.debug("parse_dna: cmd: %s out: %s, ret: %s, "
                          "err: %s" % (cmd, out, ret, err))
        try:
            if ret == 0:
                out = out.strip("\n").split("\n")[-1]
                self.dna_duration = int(out.split(" ")[1])
                self.dna_type = out.split(" ")[0].lower()
        except:
            self.looger.error("parse_dna failed", exc_info=True)
            ret = 1
        return ret

    def fill_result(self):
        if 'matches' not in self.result:
            return
        for r in self.result['matches']:
            r['media_type'] = self.dna_type
            r['clip_duration'] = self.dna_duration

    def run(self):
        edir = self.exec_dir()
        wdir = os.path.dirname(edir)
        try:
            makedirs(edir)
        except:
            self.logger.error('failed to mkdir for task %s: %s', self.task.uuid,
                              edir, exc_info=True)
            self.result = dict(code=SYSTEM)
            return self.report_back()
        else:
            self.logger.debug('exec dir for task %s: %s', self.task.uuid, edir)

        #download dna
        self.dna = '/'.join([edir, "merge.dna"])
        self.logger.debug("local save dna_path: %s" % self.dna)
        if not os.path.exists(self.dna):
            success = self.download()
            if not success:
                self.result = dict(code=CANNOT_DOWNLOAD)
                rmtree(wdir, True)
                return self.report_back()

        #parse dna
        ret = self.parse_dna()
        if ret != 0:
            self.result = dict(code=BAD_DNA)
            rmtree(wdir, True)
            return self.report_back()

        # generate site file
        site_file = edir + '/site'
        site_format = '''<SampleInfo>
                             <SiteAssetID>{site_asset_id}</SiteAssetID>
                             <OriginatorID>{domain}</OriginatorID>
                             <SiteDomain>{domain}</SiteDomain>
                         </SampleInfo>'''
        site_info = site_format.format(site_asset_id=self.task.site_asset_id,
                                       domain=self.account.domain)
        try:
            with open(site_file, 'w') as f:
                f.write(site_info)
        except:
            self.logger.error('failed to write site file for task %s: %s',
                              self.task.uuid, edir, exc_info=True)
            self.result = dict(code=SYSTEM)
            rmtree(wdir, True)
            return self.report_back()

        if self.account.slicing and \
           self.dna_duration > self.account.slice_duration:
            # slice dna first
            sliced = edir + '/sliced.dna'
            duration = self.account.slice_duration * 1000
            cmd = '''dna_slice -i {original} -o {sliced} -t {duration}
                               >/dev/null 2>&1'''.format(original=self.dna,
                                                         sliced=sliced,
                                                         duration=duration)
            self.logger.debug('dna slice command for task %s: %s',
                              self.task.uuid, cmd)
            status = system(cmd)
            self.logger.debug('dna slice status for task %s: %s', self.task.uuid,
                              status)
            if status != 0:
                if status == KILLED:
                    self.result = dict(code=-OPS_KILLED)
                elif status > ERROR:
                    self.result = dict(code=-BAD_DNA)
                else:
                    self.result = dict(code=INTERNAL)
                rmtree(wdir, True)
                return self.report_back()

        self.runners = [query_runner(self.task, self.account, b, site_file,
                                     self.timestr, self.dna_duration) \
                        for b in self.account.backends]
        for r in self.runners:
            r.start()
        for r in self.runners:
            r.join()
            self.logger.debug('result for task %s: %s', self.task.uuid, r.result)
            self.merge_result(r.result)

        if self.result['code'] != 0 or not 'backend_code' in self.result or \
           self.result['backend_code'] != 0:
            rmtree(wdir, True)
            return self.report_back()

        if self.result == None:
            self.result = dict(code=INTERNAL)
            rmtree(wdir, True)
            return self.report_back()

        self.logger.debug("remove tmp dir: %s" % os.path.dirname(edir))
        self.logger.debug('result for task %s: %s', self.task.uuid, self.result)
        uuids = self.filter_matches()
        if 'crr' in self.result:
            self.filter_crr(uuids)

        self.fill_result()
        self.generate_raw()
        rmtree(wdir, True)
        self.report_back()

    def generate_raw(self):
        ds = datestr(self.task.created_at)
        uuid = self.task.uuid
        fn = '/'.join([self.exec_dir(), 'raw'])
        with open(fn, 'w') as f:
            f.write('''<vddb>
                         <query>
                           <return_code>0</return_code>
                           <extra_info>Success</extra_info>
                         </query>
                         <matches size="%s" status="0">'''
                    % (len(self.result['matches']),))
            for m in self.result['matches']:
                t = 'audio' if m['video_duration'] == 0 else 'video'
                f.write('''<match>
                             <master_uuid>%s</master_uuid>
                             <master_name>%s</master_name>
                             <instance_id>%s</instance_id>
                             <instance_name>%s</instance_name>
                             <track_type>%s</track_type>
                             <track_id>%s</track_id>
                             <match_duration>%s</match_duration>
                             <score>%s</score>
                             <reference_offset>%s</reference_offset>
                             <sample_offset>%s</sample_offset>
                           </match>''' % (str(m['meta_uuid']), m['meta_name'].encode('utf-8'),
                                          str(m['instance_id']), m['instance_name'].encode('utf-8'),
                                          str(m['match_type']), str(m['track_id']),
                                          str(m[t + '_duration']), str(m[t + '_score']),
                                          str(m[t + '_ref_offset']),
                                          str(m[t + '_sample_offset'])))
            f.write('''  </matches>
                       </vddb>''')

    def merge_result(self, result):
        if self.result == None:
            self.logger.debug('using thread result as result for task %s: %s',
                              self.task.uuid, result)
            self.result = result
            return
        elif self.result['code'] != 0 or self.result['backend_code'] != 0:
            if self.account.allow_partial:
                self.logger.debug('using thread result for task %s: %s',
                                  self.task.uuid, result)
                self.result = result
            else:
                self.logger.debug('keeping error result for task %s',
                                  self.task.uuid)
            return
        elif result['code'] != 0 or result['backend_code'] != 0:
            if not self.account.allow_partial:
                self.logger.debug('using thread result for task %s: %s',
                                  self.task.uuid, result)
                self.result = result
            else:
                self.logger.debug('keeping no error result for task %s',
                                 self.task.uuid)
            return

        assert self.result['matches'] != None
        self.merge_matches(self.result['matches'], result['matches'])
        if result['crr'] != None and result['crr'] != '':
            self.result['crr'] = result['crr']

    def merge_matches(self, into, one):
        for uuid, m in one.iteritems():
            if uuid in into:
                m_ = into[uuid]
                for t in 'video', 'audio':
                    # FIXME: when merging results from multiple backends,
                    #        score takes precedence,
                    #        however when merging results from same backend,
                    #        duration takes precedence
                    #        coerce?
                    score_, score = m_[t + '_score'], m[t + '_score']
                    dur_, dur = m_[t + '_duration'], m[t + '_duration']
                    if score_ < score or (score_ == score and dur_ < dur):
                        m_[t + '_score'] = score
                        m_[t + '_duration'] = dur
                        m_[t + 'ref_offset'] = m[t + 'ref_offset']
                        m_[t + 'sample_offset'] = m[t + 'sample_offset']
            else:
                into[uuid] = m

    def report_back(self):
        if not 'code' in self.result:
            self.result['code'] = INTERNAL
        self.logger.debug('final result for task %s: %s', self.task.uuid,
                          self.result)
        print json.dumps(self.result)

    def filter_matches(self):
        if 'matches' not in self.result:
            return

        matches = []
        uuids = self.result['matches'].keys()
        for _, m in self.result['matches'].iteritems():
            if m['video_duration'] > 0 and m['audio_duration'] > 0:
                if self.account.both_matches:
                    self.logger.debug('keeping both match')
                    m['match_type'] = 'both'
                    matches.append(m)
                else:
                    self.logger.debug('dropping both match')
            elif m['video_duration'] > 0:
                if self.account.video_only:
                    self.logger.debug('keeping video match')
                    m['match_type'] = 'video'
                    matches.append(m)
                else:
                    self.logger.debug('dropping video match')
            else:
                if self.account.audio_only:
                    self.logger.debug('keeping audio match')
                    m['match_type'] = 'audio'
                    matches.append(m)
                else:
                    self.logger.debug('dropping audio match')

        key = lambda r: r['video_duration'] + r['audio_duration']
        if not self.account.all_matches and len(matches) > 1:
            self.logger.debug('selecting best match')
            matches = [max(matches, key=key)]
            uuids = [matches[0]['meta_uuid']]

        self.result['matches'] = matches
        return uuids

    def filter_crr(self, uuids):
        tt = TaskTerminator()
        crr = self.result['crr'] #.encode('utf8')
        self.result['crr'] = tt.sync_crr_with_match_list(crr, uuids)

def parse_backend(url):
    def unescape(s):
        return urllib.unquote(s.replace('+', ' '))

    try:
        proto, u = urllib.splittype(url)
        auth, path = urllib.splithost(u)
        user, host = urllib.splituser(auth)
        user, password = urllib.splitpasswd(user)
        host, _ = urllib.splitport(host)
        _, query = urllib.splitquery(path)

        args = query.split('&')
        hot_user = None
        hot_pass = None
        level = 0
        mode = -1
        for arg in args:
            k, v = arg.split('=', 2)
            v = unescape(v)
            if k == 'hot_user':
                hot_user = v
            elif k == 'hot_pass':
                hot_pass = v
            elif k == 'level':
                level = parse_level(v)
            elif k == 'mode':
                mode = parse_mode(v)
            elif k == 'extra':
                hot_addr, extra = parse_extra(v)
        if hot_user != None and hot_addr == None:
            hot_addr = host

        Backend = namedtuple('Backend', ['address', 'user', 'password',
                                         'hot_addr', 'hot_user', 'hot_pass',
                                         'extra', 'level', 'mode'])
        return Backend(address=host, user=user, password=password,
                       hot_addr=hot_addr, hot_user=hot_user, hot_pass=hot_pass,
                       extra=extra, level=level, mode=mode)
    except Exception:
        logging.getLogger('mwtm_executor').error('bad backend: %s', url,
                                                 exc_info=True)
        _exit(1)

def parse_level(level):
    if level == 'lowest_FN':
        return 1
    elif level == 'low_FN':
        return 2
    elif level == 'normal':
        return 3
    elif level == 'low_FP':
        return 4
    elif level == 'lowest_FP':
        return 5
    else:
        return 0

def parse_mode(mode):
    if mode == 'normal':
        return 0
    elif mode == 'refined':
        return 1
    else:
        return -1

def parse_extra(extra):
    if extra == None:
        return None, ''

    hotp = re.compile('(^|^.* )hotvddb ([^ ]+)($| .*$)')
    m = hotp.match(extra)
    if m != None:
#        print 'match 1', m.group(2), 'match 2', m.group(1), 'match 3', m.group(3)
        return m.group(2), m.group(1) + m.group(3)
    else:
        return None, extra


def kill_and_exit(sig):
    killpg(getpid(), sig)
    _exit(0)


def main():
    setpgrp()                   # kill me and the group will all die
    for sig in SIGINT, SIGTERM, SIGQUIT:
        signal(sig, lambda sig, _: kill_and_exit(sig))

    path = getenv('MW_HOME')
    if path == None:
        stderr.write("MW_HOME not set in environment, program cannot start.")
        _exit(1)
    logging.config.fileConfig('/'.join([path, 'etc', 'logging.conf']),disable_existing_loggers=False)

    logger = logging.getLogger('mwtm_executor')

    parser = ArgumentParser()
    parser.add_argument('--drop-video', action='store_true', default=False)
    parser.add_argument('--drop-audio', action='store_true', default=False)
    parser.add_argument('--drop-both', action='store_true', default=False)
    parser.add_argument('--best-match', action='store_true', default=False)
    parser.add_argument("--task", type=int, default=None)
    parser.add_argument("--timestamp", type=int, default=None)
    parser.add_argument("--account", type=int, default=None)
    parser.add_argument("--site-domain", type=str, default=None)
    parser.add_argument("--site-asset-id", type=str, default=None)
    parser.add_argument("--task-uuid", type=str, default=None)
    parser.add_argument("--clip-format", type=str, default=None)
    parser.add_argument("--slice-duration", type=int, default=None)
    parser.add_argument("--scope", action="append", type=str, default=None)
    parser.add_argument("--backend", action="append", type=str, default=None)
    parser.add_argument('--fail-partial', action='store_true', default=False)
    parser.add_argument('--dna-url', type=str, default=None)

    args = parser.parse_args()
    if args.backend == None:
        logger.error('no backend specified for task %s', args.task_uuid)
        _exit(1)

    Task = namedtuple('Task', ['site_asset_id', 'scope', 'dna_url',
                               'created_at', 'uuid', 'id', 'clip_format'])
    Account = namedtuple('Account', ['video_only', 'audio_only', 'both_matches',
                                     'all_matches', 'domain', 'backends',
                                     'slicing', 'slice_duration',
                                     'allow_partial'])
    backends = [parse_backend(b) for b in args.backend]
    account = Account(domain=args.site_domain, backends=backends,
                      slicing=args.slice_duration != None,
                      slice_duration=args.slice_duration,
                      video_only=not args.drop_video,
                      audio_only=not args.drop_audio,
                      both_matches=not args.drop_both,
                      all_matches=not args.best_match,
                      allow_partial=not args.fail_partial)
    task = Task(site_asset_id=args.site_asset_id,
                clip_format=args.clip_format,
                dna_url=args.dna_url,
                scope=args.scope, created_at=args.timestamp,
                uuid=args.task_uuid, id=args.task)

    logger.debug('args: %s', args)
    logger.debug('task: %s', task)
    logger.debug('account: %s', account)

    task_executor(task, account).run()

main()
