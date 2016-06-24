#!/usr/bin/python
# coding=utf-8


import os
import sys
import subprocess
import shlex
import re
import time
import signal
import uuid
from datetime import datetime
import commands
import pipes

reload(sys)
sys.setdefaultencoding('utf-8')

bytes_trans = {
    'B': 1, 'KiB': 1024, 'MiB': 1024 * 1024, 'GiB': 1024 * 1024 * 1024}

EEXIST = 17

class PartialDownloader(object):

    '''
    partial downloader class: using aria2c tool
    '''

    def __init__(self, task_path, cfg):
        '''
        init partial download task
        parameters: task_path, config
        '''
        if not os.path.exists(task_path):
            os.makedirs(task_path)
        self.task_path = task_path

        self.cfg = cfg
        self.dl_tool = cfg.get('tools', 'ariac2')
        args = cfg.get('args', {})
        if not isinstance(args, dict) or len(args) == 0:
            self.http_args = self.bt_args = ''
        else:
            self.http_args = args.get('http', '')
            self.bt_args = args.get('bt', '')
        self.process_dir = cfg.get('process_dir', '/tmp/')
        if not os.path.exists(self.process_dir):
            try:
                os.makedirs(self.process_dir)
            except OSError, err:
                if err.errno == EEXIST:
                    pass
                else:
                    raise
        self.tasks = {}

    def create_task(self, is_url, protocol, filename, filesize, task_id='', ):
        # if bt and dir ignore the task
        '''
aria2c -S output format:
Creation Date: Sat, 28 Jun 2014 17:02:16 GMT
Created By: BitComet/1.37
Mode: multi
Total Length: 836MiB (877,504,082)
Files:
idx|path/length
===+===========================================================================
  1|./【变形金刚4：绝迹重生(变形金刚：歼灭世纪)】【TS-RMVB】【2014美国科幻动作冒险大片】/【变形金刚4：绝迹重生.Transformers Age of Extinction】【TS-RMVB】.rmvb
   |836MiB (877,504,082)
---+---------------------------------------------------------------------------
        '''
        if len(task_id.strip()) == 0:
            t_id = uuid.uuid1()
        else:
            t_id = task_id
        task = self.tasks[t_id] = {}
        if not is_url:
            cmd = 'aria2c -S %s | grep "^Name:"' % pipes.quote(protocol)
            task['filename'] = commands.getoutput(cmd).split(':', 2)[-1].strip()
        else:
            if len(filename.strip()) != 0:
                task['filename'] = filename
            else:
                task['filename'] = os.path.basename(protocol)

        task['args'] = self.http_args if is_url else self.bt_args
        task['is_url'] = is_url
        task['tool'] = self.dl_tool
        task['protocol'] = protocol
        task['filesize'] = filesize
        return t_id

    def start(self, task_id, size=0, timeout=0, header=''):
        task = self.tasks[task_id]
        args = task['args']
        tool = task['tool']
        is_url = task['is_url']
        filename = task['filename']
        protocol = task['protocol']

        if len(filename.strip()) != 0 and is_url:
            args = args + ' -o "%s"' % filename
        args = args + " --dir=%s" % self.task_path
        if size > 0:
            if not is_url:
                tail = self.cfg.get('bt_tail_size', 0)
                args = args + \
                    " --bt-prioritize-piece=head=%d,tail=%d" % (size, tail)
        args = args + " --stop=%d" % timeout

        if is_url:
            args = args + " --lowest-speed-limit=%d" % self.cfg.get('lowest_speed', 0)
        else:
            args = args + " --bt-request-peer-speed-limit=%d" % self.cfg.get('lowest_speed', 0)

        if len(header) > 0:
            args = args + " %s" % header

        args = args + ' %s' % pipes.quote(protocol)

        #print >> sys.stderr, "partial download args is %s" % args

        now = datetime.now().strftime("%Y-%m-%d_%H")
        process_dir = os.path.join(self.process_dir, now)
        if not os.path.exists(process_dir):
            try:
                os.makedirs(process_dir)
            except OSError, err:
                if err.errno == EEXIST:
                    pass
                else:
                    raise
        process = os.path.join(process_dir, '%s_process' % task_id)

        cmd = shlex.split('%s %s' % (tool, args))
        self.tasks[task_id]['cmd'] = cmd
        self.tasks[task_id]['dl_size'] = size if size > 0 else self.tasks[
            task_id]['filesize']
        self.tasks[task_id]['process'] = process
        self.tasks[task_id]['dl_sub'] = subprocess.Popen(
            cmd, stdout=open(process, 'a+'), stderr=None)

    def wait_finished(self, task_id):
        task = self.tasks[task_id]
        sub = task['dl_sub']
        process = task['process']
        filepath = os.path.join(self.task_path, task['filename'])

        dl_size = task['dl_size']
        if not task['is_url']:
            # bt file download size should be larger than config value
            dl_size = task['dl_size'] + self.cfg.get(
                'bt_tail_size', 819200) + self.cfg.get('bt_over_size', 1024 * 1024 * 10)

        Bytes = 0

        retry = 0
        while retry < 3:
            while sub.poll() is None:
                if os.path.isdir(filepath):
                    if len(os.listdir(filepath)) > 1:
                        sub.send_signal(signal.SIGUSR1)  # returncode will be -10
                cur = commands.getoutput('tail -n4 "%s" | head -n1' % process).strip()
                m = re.match('^\S+ ([.\d]+)([^/]+)/([^(]+)\(([^)]+).*', cur)
                if m:
                    (down_size, unit, total_size, percent) = m.groups()
                    Bytes = float(down_size) * bytes_trans[unit]
                    
                    if dl_size > 0 and Bytes > dl_size:
                        sub.terminate()
                time.sleep(1)
            retcode = sub.returncode
            if retcode not in (0, 7):
                retry += 1
                #print >> sys.stderr, "aria2c tool return code is %d, retry %d" % (retcode, retry)
                time.sleep(3)
                sub = task['dl_sub'] = subprocess.Popen(
                    task['cmd'], stdout=open(process, 'a+'), stderr=None)
            else:
                break
                
        return retcode, filepath, Bytes

    def pause(self, task_id):
        if task_id not in self.tasks:
            pass
        else:
            sub = self.tasks[task_id].get('dl_sub', None)
            if sub:
                while sub.poll() is None:
                    sub.terminate()

    def resume(self, task_id):
        if task_id not in self.tasks:
            pass
        else:
            sub = self.tasks[task_id].get('dl_sub', None)
            if sub:
                if sub.poll() is None:
                    pass
                else:
                    cmd = self.tasks[task_id]['cmd']
                    self.tasks[task_id]['dl_sub'] = subprocess.Popen(
                        cmd, stdout=open(self.tasks[task_id]['process'], 'a+'), stderr=None)

    def remove(self, task_id, clean=False):
        if task_id in self.tasks:
            task = self.tasks.pop(task_id)
            if clean:
                # print 'rm -rf %s* >/dev/null 2>&1' %
                # os.path.join(self.task_path, task['filename'])
                file_path = os.path.join(self.task_path, task['filename'])
                if os.path.exists(file_path):
                    os.system("rm -rf '%s' >/dev/null 2>&1" % file_path)
                    os.system("rm -f '%s' >/dev/null 2>&1" % (file_path + '.aria2'))
            del task

    def show_process(self, task_id, show_line_cnt):
        pass


if __name__ == '__main__':

    import json
    fp = open('../etc/downloader.conf', 'r')
    cfg = json.load(fp).get('partial')
    dl = PartialDownloader('/home/deng_lingfei/partial_tmp', cfg)

    url = "http://v.snagfilms.com/films/aol/us/aoltruestories/2012/filmfatale/warzone/WARZONE_DSL1.mp4"
    bt_file = "/home/deng_lingfei/partial_tmp/dummy.torrent"
    #tid = dl.create_task(False, bt_file, "", 1024*1024*300)
    tid = dl.create_task(True, url, "", 1024 * 1024 * 300)
    dl_size = cfg.get('size')
    dl.start(tid, size=100 * 1024 * 1024, timeout=1200)
    dl_status, file_path, real_dl_size = dl.wait_finished(tid)
    print dl_status, file_path
    dl.remove(tid, clean=False)
