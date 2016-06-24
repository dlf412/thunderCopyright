#!/usr/bin/python
# coding=utf-8

import json
import time
import os
import sys
import subprocess
import traceback
import uuid
import urllib
import base64
import redis
import statsd
import chardet
import threading
import commands
import shlex
import signal
import pipes

from const import OFFLINE_TIMEOUT, OFFLINE_STATUS_ERROR, OFFLINE_HTTP_ERROR, OFFLINE_GENURL_ERROR
from logging.handlers import SysLogHandler
from subprocess import PIPE
from datetime import datetime


from dt_err import *
from common.mylogger import *
from downloader_util import *
from partial_downloader import PartialDownloader

from common.task_container import TaskContainer

# worker is a module execute the download/far generate/upload dna file and return the result message to the downloader,
# downloader put the message to the finish queue
# load the result template as dict data

reload(sys)
sys.setdefaultencoding('utf-8')

ARIA_SUCC, ARIA_INT = 0, 7

NO_ERROR = 0
PARTIAL_DOWN_ERROR = -1
GEN_DNA_FAR_ERROR = -2
GEN_DNA_STAT_ERROR = -3
GET_DNA_LEN_ERROR = -4
CALC_DL_SIZE_ERROR = -5
PARTIAL_DOWN_EXCEPTION = -6
PARTIAL_DOWN_TIMEOUT = -7

PARTIAL_DISABLE_IGNORE = 1
URL_TYPE_UNSUPPORT_IGNORE = 2
BT_UNSUPPORT_IGNORE = 3
EXT_UNSUPPORT_IGNORE = 4
MULTI_FILE_UNSUPPORT_IGNORE = 5
FILE_SIZE_SMALL_IGNORE = 6


down_fd = None
vdnagen_fd = None
NORMAL_MODE = 1
OFFLINE_MODE = 2

UNCOPYRIGHT = 1
UN_DETECTED = 2
NO_MATCH_FILTER = 3

def signal_handler(signal, frame):
    if down_fd and down_fd.poll() is None:
        down_fd.terminate()
        down_fd.poll()
    if vdnagen_fd and vdnagen_fd.poll() is None:
        vdnagen_fd.terminate()
        vdnagen_fd.poll()
    sys.exit(1)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

class worker_temp:

    def __init__(self, info_logger, logger, path, config_file, task_info):
        # init redis connector, input_data, result_data and so on
        self.logger = logger
        self.info_logger = info_logger
        self.config_file = config_file
        with open(config_file) as fp:
            self.worker_config = json.load(fp)
        self.download_mode = self.worker_config.get('download_mode', OFFLINE_MODE)
        self.dirs = []
        self.task_info = task_info
        self.result_data = task_info
        self.torrent_info = []

        self.tool_path = path + '/tools'
        self.lib_path = path + '/lib'
        self.bin_path = path + '/bin'


        self.priority = None
        self.task_path = self.created_temp_dir()

        self.external_id = None

        self.parse_input(task_info)
        

        self.logger.info('init worker sucess, hash_data is: [%s], priority is: [%s]'
                         % (self.input_data.hash_data, self.priority))

        self.log_path = self.worker_config.get(
            'thunder_log_path', '/tmp/downloader/log')

    def created_temp_dir(self, clean=True):
        download_dir = self.worker_config.get(
            'download_dir',
            "/tmp/downloader"
        )
        tmp_path = os.path.join(
            download_dir,
            datetime.now().strftime("%Y-%m-%d"),
            datetime.now().strftime("%H"),
            str(uuid.uuid1())
        )
        create_dir(tmp_path)
        if clean:
            self.dirs.append(tmp_path)
        return tmp_path

    def created_log_path(self, clean=True):
        tmp_path = os.path.join(
            self.log_path,
            datetime.now().strftime("%Y-%m-%d"),
            datetime.now().strftime("%H"),
            str(uuid.uuid1())
        )
        create_dir(tmp_path)
        return tmp_path

    def processing_timer(self, interval):
        self.tc.set_task_status(self.digest, 'processing')
        self.timer = threading.Timer(
            interval, self.processing_timer, (interval,))
        self.timer.setDaemon(True)
        self.timer.start()

    def cancel_processing_timer(self):
        self.timer.cancel()
        del self.timer

    def upload_task_flow(self, message):
        try:
            if self.redis_op.redis_info_exists(
                    self.input_data.hash_data,
                    self.priority
            ):
                self.redis_op.update_work_flow(
                    self.input_data.hash_data,
                    message,
                    self.priority
                )
            else:
                if self.task_type is URL_FILE:
                    self.redis_op.init_redis_info(
                        self.input_data.hash_data,
                        "url",
                        self.priority,
                        json.dumps(self.task_info)
                    )
                else:
                    self.redis_op.init_redis_info(
                        self.input_data.hash_data,
                        "seed_file",
                        self.priority,
                        json.dumps(self.task_info)
                    )
                self.redis_op.update_work_flow(
                    self.input_data.hash_data,
                    message,
                    self.priority
                )
        except Exception, reason:
            self.logger.error(
                "update or init_redis_info occur error: [%s]" % str(reason))

    def parse_input(self, task_info):
        
        self.digest = self.result_data['params'].get('digest', "")
        if len(self.digest) == 0:
            self.logger.error('parse input task failed, reason: no any digest')
            raise dt_error(ERR_INPUT, "no digest")
        self.priority = self.result_data['params'].get('priority', "low")
        self.downloader_time = self.result_data[
            'params'].get('downloader_time', 0)
        self.downloader_retry = self.result_data[
            'params'].get('downloader_retry', 0)
        self.external_id = self.result_data['params'].get('external_id', None)

        self.file_name = self.result_data['params'].get('file_name', '')
        if self.file_name is None:
            self.file_name = ''
        if isinstance(self.file_name, unicode):
            self.file_name = self.file_name.encode('utf8')

        self.file_ext = self.result_data['params'].get('file_ext', '')
        if isinstance(self.file_ext, str):
            self.file_ext = self.file_ext.lower().strip()
        else:
            self.file_ext = ''

        self.file_size = self.result_data['params'].get('file_size', 0)

        self.statsd_host = self.worker_config.get('statsd').get('host')
        self.statsd_port = self.worker_config.get('statsd').get('port')
        self.statsd_con = statsd.client.StatsClient(
            self.statsd_host, self.statsd_port)
        self.redis_conn = redis.from_url(
            self.worker_config.get('redis_url'),
            socket_timeout=60
        )
        # using task_container
        self.tc = TaskContainer(self.worker_config.get('redis_url'))
        # registe myself
        self.tc.registe_worker(self.digest, "%s:%d" %(socket.gethostname(), os.getpid()))
        self.redis_op = redis_operater(self.redis_conn)
        # default 10G
        self.max_download_size = self.worker_config.get(
            'max_download_size',
            10737418240
        )
        # default 1hour
        self.extract_timeout = self.worker_config.get(
            "extrac_timeout",
            1800
        )
        # default 10k
        self.min_file_size = self.worker_config.get(
            'min_file_size',
            10000
        )

        if not self.external_id:
            msg = 'external_id is None'
            self.logger.error(msg)
            raise dt_error(ERR_INPUT, msg)

        if keys_value(task_info, 'params', 'seed_file') is not None:
            location = keys_value(
                task_info['params'],
                'seed_file',
                'path'
            )
            self.task_type, self.input_data = SEED_FILE\
                , InputData(
                    location,
                    keys_value(task_info['params'], 'seed_file', 'hash')
                )
        elif keys_value(task_info, 'params', 'url') is not None:
            location = keys_value(
                task_info['params'],
                'url',
                'location'
            )
            if isinstance(location, unicode):
                location = location.encode('utf8')
            self.task_type, self.input_data = URL_FILE\
                , InputData(
                    location,
                    keys_value(task_info['params'], 'url', 'hash')
                )
        else:
            msg = "can not find url or seed_file data"
            self.logger.error(msg)
            raise dt_error(ERR_INPUT, msg)
        if not self.input_data.location:
            msg = 'input seed_file path is None or url location is None'
            raise dt_error(ERR_INPUT, msg)

    def parse_torrent_info(self, bt_path):
        output = judge_torrent(bt_path)
        if output.find(invalid_torrent) is not -1:
            self.logger.error(output)
            raise dt_error(ERR_INVALID_TORRENT, invalid_torrent)

        group = re.findall(re_torrent_file_number, output)
        # self.logger.debug("parse torrent output is: [%s]" % output)
        # the following may not happen, otherwise aria2c changed is output
        # format
        if not group:
            self.logger.error("parse torrent error")
            raise dt_error(
                ERR_INVALID_TORRENT,
                "torrent parse error"
            )
        u'''
        file_info is structure about: file_number, file_name, file_size
        eg: 1, ./我是歌手.rmvb, 123456
        '''
        bt_file_size = 0
        for k, s, v in group:
            file_info = int(k), s, int(v.replace(',', '').replace(' ', ''))
            bt_file_size += file_info[2]
            self.torrent_info.append(file_info)
        if self.max_download_size < bt_file_size:
            raise dt_error(
                ERR_FILTER_PASS,
                "torrent file too big [%d], filter" % bt_file_size
            )

    def get_file_number(self, bt_name):
        number = None
        for number, filename, filesize in self.torrent_info:
            if filename == bt_name:
                return number

    def offline_download(self, remote_path):
        resource = self.input_data.location
        if self.task_type is SEED_FILE:
            torrent_path = os.path.join(
                self.task_path,
                os.path.basename(resource)
            )
            download_swift_file(
                self.tool_path,
                self.input_data.location,
                torrent_path
            )
            self.parse_torrent_info(torrent_path)
            resource = torrent_path

        offline_download_path = self.created_temp_dir()
        file_list = []
        try:
            offline_cfg = self.worker_config.get('offline')
            poll_interval = offline_cfg.get('poll_interval', 600)
            poll_timeout = offline_cfg.get('poll_timeout', 3600)
            max_speed = offline_cfg.get('max_speed', 4096000)
            download_seedfile_timeout = download_seedfile_timeout = offline_cfg.get('download_seedfile_timeout', 600)

            poll_interval = poll_interval if poll_interval > 0 else 600
            poll_timeout = poll_timeout if poll_timeout > 0 else 3600
            max_speed = max_speed if max_speed > 0 else 4096000
            download_seedfile_timeout = download_seedfile_timeout if download_seedfile_timeout > 0 else 600
            download_timeout = self.worker_config.get('download_task_timeout', 10800)
            
            escaped_res = pipes.quote(resource)
            escaped_filename = pipes.quote(self.file_name)
            cmd = "python %s/offline_downloader.py %s %s %s --digest=%s --save_dir=%s --tmp_dir=%s --poll_interval=%d \
                --poll_timeout=%d --max_speed=%d --download_seedfile_timeout=%d --download_timeout=%d" % (
                        self.bin_path, escaped_res, escaped_filename, self.config_file,
                        self.digest, offline_download_path, self.task_path, poll_interval, 
                        poll_timeout, max_speed, download_seedfile_timeout, download_timeout)
            self.logger.info("offline download command is %s" % cmd)
            ret, output = commands.getstatusoutput(cmd)
            if ret != 0:
                self.logger.error("offline download failed: reason is %s" % output.strip())
                real_ret = ret >> 8
                ret = real_ret if real_ret <= 128 else real_ret - 256
            else:
                self.logger.debug('offline download success, files is %s' % output.strip())
                file_list = output.strip().split('\n')
        except:
            #os.system("rm -rf %s/*" % offline_download_path)
            self.logger.error(
                'offline download exception:%s' % traceback.format_exc())
            raise dt_error(ERR_DOWNLOAD, "offline download maybe interrupted!")

        self.record_offline_download(ret, resource)

        if ret == OFFLINE_TIMEOUT:
            raise dt_error(ERR_OFFLINE_TIMEOUT, "offline download poll timeout")
        if ret == OFFLINE_HTTP_ERROR:
            raise dt_error(ERR_OFFLINE_HTTP, "offline download http error")
        if ret == OFFLINE_GENURL_ERROR:
            raise dt_error(ERR_OFFLINE_GENURL, "offline download gen url error")
        if ret == OFFLINE_STATUS_ERROR:
            # TODO: using ERR_UNSUPPORTED_DOWNLOAD replacing OFFLINE_STATUS_ERROR as query_broker
            raise dt_error(ERR_UNSUPPORTED_DOWNLOAD, "offline download status error")

        if not file_list \
                or not len(file_list):
            raise dt_error(ERR_DOWNLOAD,
                           "downloader error, directory has no file"
                           )
        return offline_download_path, file_list

    def download_file(self):
        remote_path = datetime.now().strftime("%Y-%m-%d_%H")
        file_list = []

        if self.download_mode == NORMAL_MODE:
            if self.task_type is URL_FILE:
                file_list = self.url_download_process(remote_path)
                download_path = self.task_path
            else:
                download_path, file_list = self.seed_download_process(remote_path)
        elif self.download_mode == OFFLINE_MODE: 
            download_path, file_list = self.offline_download(remote_path)
        else:
            self.logger.info("unsupport download mode, default offline mode")
            download_path, file_list = self.offline_download(remote_path)
	
        self.logger.info("download file list is %s" % str(file_list))
        if len(file_list) is 1 and self.task_type is URL_FILE:
            file_path = file_list[0]
            
            output = judge_torrent(file_path)
            if output.find(invalid_torrent) is -1:
                # swift bug: chinese character will raise exception, so rename bt file 
                dir_name = os.path.dirname(file_path)
                base_name = os.path.basename(file_path)
                new_bt_name = os.path.join(dir_name, "swift_bug.torrent")
                os.rename(file_path, new_bt_name)
                file_path = new_bt_name
                file_list[0] = file_path
                # end fix as swift bug
                self.upload_file(
                    remote_path,
                    file_path
                )
                self.record_file_list(
                    file_list,
                    download_path
                )
                self.result_data['params'].update\
                    ({"seed_file": {
                     "path": remote_path + file_path, "hash": ""}})
                self.logger.info(
                    'file is torrent, need qb compute hash and re-download seed-file')
                raise dt_error(SUCCESS, "success")

        file_list = self.extract_list(file_list)
        self.record_file_list(file_list, download_path)

        '''
        if self.worker_config.get('is_audio_filter'):
            file_list = self.audio_filter(file_list)
        file_list = self.filesize_filter(file_list)
        '''

        a_filter = self.worker_config.get("is_audio_filter", False)
        c_size = self.worker_config.get('min_file_size', 100 * 100)

        '''
        to do:
        judge file use ffmpeg, if not video file ,need use 7z extrac, or directly call vdnagen
        '''

        files = list()
        for video_path in file_list:
            file_data = None
            try:
                local_path = video_path.replace(download_path, '.')
                #number      = self.get_file_number(local_path)

                if c_size > os.path.getsize(video_path)\
                        or (a_filter and self.ffmpeg_check(video_path) is AUDIO)\
                        or self.ffmpeg_check(video_path) is OTHER_FILE:
                    file_data = {"path": "", "cal_size": 0, "code": NO_MATCH_FILTER, "file_path":
                                 local_path, "hash": "file_hash#" + str(uuid.uuid1())}
                    continue

                temp_path = self.task_path + '/' + str(uuid.uuid1())
                far_path, dna_path, stats_path = temp_path + \
                    '.far', temp_path + '.dna', temp_path + '.stats'

                if not self.gen_far(video_path, far_path):
                    if self.ffmpeg_check(video_path) is VIDEO:
                        file_data = {"path": "", "cal_size": 0, "code": UN_DETECTED, "file_path":
                                     local_path, "hash": "file_hash#" + str(uuid.uuid1())}
                    else:
                        file_data = {"path": "", "cal_size": 0, "code": UNCOPYRIGHT, "file_path":
                                     local_path, "hash": "file_hash#" + str(uuid.uuid1())}
                    continue

                file_hash, file_size = gethash_filesize(video_path)
                file_hash = 'file_hash#' + file_hash

                self.gen_dna_stat(far_path, dna_path, stats_path)
                self.upload_file(remote_path, dna_path)

                self.upload_file(remote_path, stats_path)

                file_data = {"path": remote_path + dna_path, "hash": file_hash,
                             "cal_size": file_size, "file_path": local_path, "code": SUCCESS}
            finally:
                files.append(file_data)
        if not len(files):
            # need record file_number
            raise dt_error(ERR_DOWNLOAD, "no files found")
        # this part record success
        self.result_data['params'].update({"files": files})

    def extract_file(self, c_file, target_path):
        args = "%s/7z x %s -o%s -p123456 " % (
            self.tool_path, pipes.quote(c_file), target_path)
        self.logger.debug('extract file: [%s]' % args)

        os.environ["LD_LIBRARY_PATH"] = self.tool_path
        fd = subprocess.Popen(
            args, stdout=PIPE, stderr=PIPE, shell=True, env=os.environ)
        start = time.time()
        while fd.poll() is None:
            if (time.time() - start) > self.extract_timeout:
                self.logger.error(
                    'extract file timeout failed: [%s]' % self.input_data.location)
                fd.terminate()
                return
            time.sleep(20)
        output, err = fd.communicate()
        if fd.poll():
            self.logger.debug(
                'extract failed, not compress file: [%s]' % str(output))
            return
        else:
            self.logger.debug('extract success')
            c_files = traverse_folder(target_path)
            # create pathname as samename of compressed file
            original_path = os.path.dirname(c_file)

            file_name = os.path.basename(c_file) if self.task_type is SEED_FILE\
                else (self.file_name if self.file_name else os.path.basename(c_file))

            original_file = os.path.join(original_path, file_name)
            mv_file(
                c_file, os.path.join(target_path, os.path.basename(c_file)))
            create_dir(original_file)

            new_c_files = []
            for file_ in c_files:
                new_file = os.path.join(original_file, os.path.basename(file_))
                mv_file(file_, new_file)
                new_c_files.append(new_file)
            return new_c_files

    def extract_list(self, file_list):
        c_files = self.worker_config.get('compressed_file')
        c_sets = tuple(c_files if not ',' in c_files else c_files.split(','))
        new_list = []
        for file_ in file_list:
            info_data = judge_file(file_)
            self.logger.debug('jugde extract output is: [%s], file is %s' % (str(info_data), file_))
            if judge_compressed_file(info_data, c_sets):
                c_path = self.created_temp_dir()
                c_list = self.extract_file(file_, c_path)
                if c_list:
                    new_list += c_list
                else:
                    new_list.append(file_)
            else:
                new_list.append(file_)
        return new_list

    def ffmpeg_check(self, file_path):
        args = "ffmpeg -i %s" % pipes.quote(file_path)
        output = commands.getoutput(args)
        if output.find('ffmpeg: not found') is not -1:
            raise Exception("ffmpeg not installed")
        return judge_audio_video(output)

    def filesize_filter(self, file_list):
        new_list = []
        configure_size = self.worker_config.get('min_file_size', 1000 * 1000)
        for file_path in file_list:
            file_size = os.path.getsize(file_path)
            if file_size > configure_size:
                new_list.append(file_path)
            else:
                self.logger.info(
                    'file: [%s] size [%d] is small than configure size: [%d]'
                    % (file_path, file_size, configure_size)
                )
        return new_list

    def audio_filter(self, files_list):
        new_list = []
        for file_path in files_list:
            file_type = self.ffmpeg_check(file_path)
            if file_type is not AUDIO:
                new_list.append(file_path)
            else:
                self.logger.info(
                    'file: [%s] ffmpeg check file is Audio, filter' % (file_path))
        return new_list

    def gen_far(self, video_path, far_path):
        args = "timeout %d VDNAGen -o %s %s %s" % (self.worker_config.get("vdnagen_timeout", 10800), 
                pipes.quote(far_path), pipes.quote(video_path), self.worker_config.get("vdangen_para", " "))
        self.logger.debug('gen_far commands is: [%s]' % args)

        global vdnagen_fd
        vdnagen_fd = subprocess.Popen(args, stdout=PIPE, stderr=PIPE, shell=True)
        ret = vdnagen_fd.wait()
        output, err = vdnagen_fd.communicate()
        vdnagen_fd = None

        if output.find("Unsupported file format:") is not -1:
            self.logger.info('unsupported file format: [%s]' % str(output))
            return False
        elif output.find("<ErrorCode>0</ErrorCode>") is -1\
                and output.find("<error_code>0</error_code>") is -1:
            self.logger.error("vdangen failed: [%s]" % str(output))
            raise Exception("vdnagen failed:%s" % str(output + err))
        else:
            return True

    def gen_dna_stat(self, far_path, dna_path, stats_path):
        args = "%s/far_split -i %s -d %s  -s %s" % (
            self.tool_path,
            pipes.quote(far_path),
            pipes.quote(dna_path),
            pipes.quote(stats_path)
        )
        self.logger.debug('gen_dna_stat commands is: [%s]' % args)

        ret, output, err = call_subprocess(args)
        if ret != 0:
            self.logger.error("split far failed: [%s]" % str(err))
            raise dt_error(ERR_FAR, "split far to dna and stats")

        self.logger.debug("far_split success")
        return

    def get_dna_len(self, dna_path):
        args = "%s/dna_status -i %s 2>&1 | grep LENGTH | awk -F= '{print $2}'" % (
            self.tool_path, pipes.quote(dna_path))
        length = commands.getoutput(args).strip()
        try:
            return int(length)
        except ValueError:
            self.logger.error(
                "invalid dna or dna_status tool is not in %s" % self.tool_path)
            return -1

    def calc_dl_size(self, stats_path, dl_length):
        '''
        Note: far_split tool maybe has a bug: VideoBirate is FileBitrate
        if the dna is audio, can't find VideoBitrate, will raise ValueError exception
        '''
        args = "grep 'VideoBitrate' '%s' | grep -o '[0-9]*'" % stats_path
        bitrate = commands.getoutput(args).strip()
        try:
            bitrate = int(bitrate)
        except ValueError:
            self.logger.error(
                "can't find VideoBitrate in far_stats file[%s], maybe dna is only audio" % stats_path)
            return -1
        return int((bitrate * dl_length / 8.0) * 1.1)

    def get_download_size(self, url):
        default_size = self.worker_config.get(
            'download_size',
            10485760
        )
        url_type = get_urlfiletype(url)
        if not url_type:
            return self.max_download_size, None
        else:
            self.logger.info(
                'url_type is: [%s]' % url_type
            )
            for pd in self.worker_config.get(
                    'partly_download',
                    'flv'
            ).split(','):
                if pd in url_type:
                    return default_size, url_type
            else:
                return self.max_download_size, url_type

    def get_ext_name(self, output):
        if not output:
            return ".casd"
        else:
            return "." + output

    def update_time(self, start, end):
        self.tc.incr_task_execute_time(self.digest, int(end - start))

    def download_url(self, url):
        self.url_checker(url)
        download_size, output = self.get_download_size(url)
        ext_name = self.get_ext_name(output)
        if '.' == self.file_name:
            download_name = 'download' + ext_name
        else:
            download_name = self.file_name
        file_name = os.path.join(
            self.task_path,
            download_name
        )

        '''
        call download_url.sh example
        ./download_url.sh  -m 10241024 "http://vr.tudou.com/v2proxy/v2?it=201179196&st=52&pw="  test/1.flv  1.log
        '''

        args = "%s/download_url.sh -m %d '%s' '%s' '%s' " % (
            self.tool_path,
            download_size,
            url,
            file_name,
            file_name + '.download.log'
        )
        self.logger.info("wget command: [%s]" % args)
        fd = subprocess.Popen(args, stdout=PIPE, stderr=PIPE, shell=True)

        while fd.poll() is None:
            time.sleep(1)

        output, err = fd.communicate()
        if fd.poll() is not 0:
            self.logger.error(
                'download output: [%s], error: [%s]' % (str(output), str(err)))
            raise dt_error(ERR_DOWNLOAD, "download failed")
        self.logger.debug("download success")
        return [file_name]

    def upload_file(self, upload_path, file_path):
        args = "%s/swift upload %s %s " % (
            self.tool_path, upload_path, pipes.quote(file_path))
        self.logger.debug('upload file command is: [%s]' % args)
        fd = subprocess.Popen(args, stdout=PIPE, stderr=PIPE, shell=True)
        while fd.poll() is None:
            time.sleep(10)
        output, err = fd.communicate()
        if err or fd.poll():
            self.logger.error(
                "upload output is: [%s], find error: [%s]" % (str(output), str(err)))
            raise dt_error(ERR_UPLOAD, str(err))
        else:
            self.logger.debug('upload file success')
            return

    def url_checker(self, url):
        code = 0
        # set socket timeout
        urllib.socket.setdefaulttimeout(200)
        try:
            code = urllib.urlopen(url).getcode()
        except:
            # traceback.print_exc()
            pass
        self.logger.debug("http code is: [%d]" % code)
        if code / 100 is 4:
            raise dt_error(ERR_UNSUPPORTED_DOWNLOAD, "http_code: %d, unsupported download"
                           % code)

    def url_download_process(self, remote_path):
        self.logger.debug('begin download url')

        url_data = self.input_data.location
        if re.match("thunder://", url_data):
            url_data = url_data[
                10:-1] if url_data.endswith('/') else url_data[10:]
            url_data = base64.b64decode(url_data)
            url_data = url_data[
                2:-2] if (url_data.startswith('AA') and url_data.endswith('ZZ')) else url_data

        encoding = chardet.detect(url_data)
        charset = encoding.get('encoding')
        if charset:
            url_data = url_data.decode(charset).encode('utf8')

        if isinstance(url_data, unicode):
            url_data = url_data.encode('utf8')
        # partial_download
        try:
            ret, need_thunder, file_list = self.partial_download(
                url_data.strip(), self.task_path)
        except:
            ret, need_thunder, file_list = PARTIAL_DOWN_EXCEPTION, True, []
            if os.path.isdir(self.task_path):
                os.system("rm -rf %s/*" % self.task_path)
            self.logger.error(
                'partial download exception:%s' % traceback.format_exc())
        self.record_partial_download(ret, url_data)
        if need_thunder:
            file_list = self.thunder_download(url_data.strip(), self.task_path)

        '''
        if re.match(r'http', url_data):
            file_list = self.download_url(url_data)
        else:
            file_list = self.thunder_download(url_data, self.task_path)
        '''

        if not file_list\
                or not len(file_list):
            raise dt_error(
                ERR_DOWNLOAD, "downloader error, directory has no file")
        return file_list

    def partial_download(self, protocol, task_path, is_url=True):
        self.logger.info('start partial download: hash_data=%s, file=%s' % (
            self.input_data.hash_data, self.file_name))
        need_thunder_retry = True
        errcode = NO_ERROR
        file_list = []

        errcode = self._check_partial_download(protocol, is_url)
        # ignore the partial download, return
        if errcode != NO_ERROR:
            return errcode, True, []

        partial_cfg = self.worker_config.get('partial')
        # begin download
        dl_size = partial_cfg.get('size')

        downloader = PartialDownloader(task_path, partial_cfg)
        task_id = downloader.create_task(
            is_url, protocol, self.file_name, self.file_size, task_id=self.input_data.hash_data)
        downloader.start(
            task_id, size=dl_size, timeout=partial_cfg.get('timeout', 0))
        dl_status, file_path, real_dl_size = downloader.wait_finished(task_id)

        if dl_status not in (ARIA_SUCC, ARIA_INT):
            self.logger.error("[%s]Partial download failed, retcode=%d" % (
                self.input_data.hash_data, dl_status))
            errcode = PARTIAL_DOWN_ERROR
        elif not os.path.exists(file_path):
            self.logger.error("[%s]Partial download failed, download file[%s] is not exists" % (
                self.input_data.hash_data, file_path))
            errcode = PARTIAL_DOWN_ERROR
        elif real_dl_size <= dl_size and dl_status == ARIA_INT:
            self.logger.error("[%s]partial download real size is %d <= expected size[%d], maybe timeout" % (
                self.input_data.hash_data, real_dl_size, dl_size))
            errcode = PARTIAL_DOWN_TIMEOUT
        else:
            self.logger.info("partial download OK , start generate dna far")
            temp_path = task_path + '/' + str(uuid.uuid1())
            far_path, dna_path, stats_path = temp_path + \
                '.far', temp_path + '.dna', temp_path + '.stats'
            try:
                gen_far_ok = self.gen_far(file_path, far_path)
            except:
                gen_far_ok = False
            if gen_far_ok:
                dna_length_thresh = partial_cfg.get('dna_length', 600)
                try:
                    self.gen_dna_stat(far_path, dna_path, stats_path)
                except dt_error:
                    self.logger.error(
                        '[%s]gen dna stat error' % self.input_data.hash_data)
                    errcode = GEN_DNA_STAT_ERROR
                else:
                    dna_length = self.get_dna_len(dna_path)
                    self.logger.debug(
                        "[%s]get dna length is %d" % (self.input_data.hash_data, dna_length))
                    if dna_length >= dna_length_thresh:
                        self.logger.info(
                            "[%s]dna length is enough already, Partial download successfully" % self.input_data.hash_data)
                    elif dna_length < 0:
                        errcode = GET_DNA_LEN_ERROR
                        self.logger.error(
                            '[%s]get dna length error' % self.input_data.hash_data)
                    else:
                        self.logger.info(
                            '[%s]dna is too short, need continue partial download' % self.input_data.hash_data)
                        need_dl_size = self.calc_dl_size(
                            stats_path, dna_length_thresh)
                        if need_dl_size < 0:
                            self.logger.error(
                                '[%s]calc download size error' % self.input_data.hash_data)
                            errcode = CALC_DL_SIZE_ERROR
                        else:
                            self.logger.info('[%s]need download size is %d, continue download...' % (
                                self.input_data.hash_data, need_dl_size))
                            # Should add timeout
                            l_speed = partial_cfg.get('lowest_speed', 0)
                            timeout = 0
                            if l_speed > 0:
                                timeout = int(need_dl_size / float(l_speed) * 1.1)
                        
                            downloader.start(task_id, size=need_dl_size, timeout=timeout)
                            dl_status, file_path, real_dl_size = downloader.wait_finished(
                                task_id)
                            if dl_status not in (0, 7):
                                self.logger.error("[%s]Partial download failed, retcode=%d" % (
                                    self.input_data.hash_data, dl_status))
                                errcode = PARTIAL_DOWN_ERROR
                            elif real_dl_size <= need_dl_size and dl_status == 7:
                                self.logger.error("[%s]partial download real size is %d <= expected size[%d], maybe timeout" % (
                                    self.input_data.hash_data, real_dl_size, dl_size))
                                errcode = PARTIAL_DOWN_TIMEOUT
                            else:
                                self.logger.info(
                                    "[%s]Partial download successfully" % self.input_data.hash_data)
            else:
                self.logger.error('[%s]Gen dna far error' %
                                  self.input_data.hash_data)
                errcode = GEN_DNA_FAR_ERROR

        if errcode < NO_ERROR:
            need_thunder_down = partial_cfg.get('thunder_retry', True)
            # save bt_file or url to facilitate the investigation of problem
            save_err_dir = os.path.join(partial_cfg.get(
                'save_err_dir', '/tmp/partial_download_error'), datetime.now().strftime("%Y-%m-%d"), self.input_data.hash_data)
            self.logger.info(
                "save the bt_file or url to dir:'%s' to facilitate the investigation of problem" % save_err_dir)
            if not os.path.exists(save_err_dir):
                os.makedirs(save_err_dir)
            self.save_error_protocol(protocol, save_err_dir, errcode, is_url)
            downloader.remove(task_id, clean=True)
            file_list = []
        elif errcode > NO_ERROR:
            need_thunder_down = True
            file_list = []
        else:
            if os.path.isdir(file_path):
                file_list = traverse_folder(file_path)
            else:
                file_list.append(file_path)
            need_thunder_down = False
            downloader.remove(task_id)

        return errcode, need_thunder_down, file_list

    def save_error_protocol(self, protocol, save_dir, errcode, is_url=True):
        if is_url:
            with open(os.path.join(save_dir, str(errcode)), 'a+') as f:
                f.write(protocol)
                f.write('\n')
        else:
            os.system("cp %s %s" % (protocol, save_dir))
            os.system("touch %s/%s" % (save_dir, errcode))

    def _check_partial_download(self, protocol, is_url):
        errcode = NO_ERROR
        while True:
            partial_cfg = self.worker_config.get('partial', {})
            if not isinstance(partial_cfg, dict) \
                    or len(partial_cfg) == 0 \
                    or not partial_cfg.get('enable', False):
                self.logger.info(
                    '[%s]partial download is disable, ignore' % self.input_data.hash_data)
                errcode = PARTIAL_DISABLE_IGNORE
                break
            # check protocal
            if is_url:
                url_type = protocol.split(":")[0].strip().lower()
                self.logger.debug(
                    "partial_download: protocol is: %s, url_type is:%s" % (protocol, url_type))
                if url_type not in partial_cfg.get("url_protocols", []):
                    self.logger.info(
                        '[%s]url type is not support, ignore' % self.input_data.hash_data)
                    errcode = URL_TYPE_UNSUPPORT_IGNORE
                    break
            else:
                if not partial_cfg.get("bt_support", True):
                    self.logger.info(
                        '[%s]bt file is not support, ignore' % self.input_data.hash_data)
                    errcode = BT_UNSUPPORT_IGNORE
                    break
            # check extensions
            if is_url:
                if len(self.file_name.strip()) == 0:
                    self.file_name = os.path.basename(protocol)
                ext = self.file_ext
                if not ext:
                    ext = os.path.splitext(self.file_name)[-1]
                    ext = ext.split('.')[-1].strip().lower()
                self.logger.debug("partial_downloader, ext:%s" % ext)
                if ext not in partial_cfg.get("extensions", []):
                    self.logger.info(
                        '[%s]file extension is not support, ignore' % self.input_data.hash_data)
                    errcode = EXT_UNSUPPORT_IGNORE
                    break
            else:
                # replace file name from protocol
                cmd = 'aria2c -S %s | grep "^Name:"' % pipes.quote(protocol)
                
                self.file_name = commands.getoutput(cmd).split(':', 2)[-1].strip()

                # file size should be reset from protocol
                # Total Length: 1.6GiB (1,787,479,165)
                cmd = 'aria2c -S %s | grep "^Total Length:" | grep -o "([0-9,]*)"' % pipes.quote(protocol)
                self.file_size = int(
                    commands.getoutput(cmd).strip()[1:-1].replace(',', ''))

                # bt file maybe a dir
                cmd = "aria2c -S %s | grep '^Mode:.*multi'" % pipes.quote(protocol)

                ret = os.system(cmd)
                if ret != 0:  # is not dir
                    # seed file ext should be from protocol
                    ext = os.path.splitext(self.file_name)[-1]
                    ext = ext.split('.')[-1].strip().lower()
                    if ext not in partial_cfg.get("extensions", []):
                        self.logger.info(
                            '[%s]file extension is not support, ignore' % self.input_data.hash_data)
                        errcode = EXT_UNSUPPORT_IGNORE
                        break
                else:
                    # check bt file invalid
                    # if file count> 1: unsupport
                    # if file count= 0: invalid bt file
                    cmd = "aria2c -S %s | grep -cE  '^[ ]*[0-9]+\|'" % pipes.quote(protocol)
                    file_cnt = int(commands.getoutput(cmd).strip())
                    if file_cnt != 1:
                        self.logger.info(
                            '[%s]multi files is not support, ignore' % self.input_data.hash_data)
                        errcode = MULTI_FILE_UNSUPPORT_IGNORE
                        break
                    '''
                      1|./【变形金刚4：绝迹重生(变形金刚：歼灭世纪)】【TS-RMVB】【2014美国科幻动作冒险大片】/【变形金刚4：绝迹重生.Transformers Age of Extinction】【TS-RMVB】.rmvb
                    '''
                    cmd = 'aria2c -S %s | grep -E "^[ ]+1\|.+"' % pipes.quote(protocol)
                    ext = self.file_ext
                    if not ext:
                        filename = commands.getoutput(cmd).split(
                            '|', 2)[-1].strip()
                        ext = os.path.splitext(filename)[-1]
                        ext = ext.split('.')[-1].strip().lower()
                    if ext not in partial_cfg.get("extensions", []):
                        self.logger.info(
                            '[%s]file extension is not support, ignore' % self.input_data.hash_data)
                        errcode = EXT_UNSUPPORT_IGNORE
                        break

            # check file_size
            partial_size = partial_cfg.get('size', self.file_size)
            if self.file_size <= partial_size:
                self.logger.info(
                    '[%s]file size is <= partial_size of configure, ignore' % self.input_data.hash_data)
                errcode = FILE_SIZE_SMALL_IGNORE

            break

        return errcode

    def record_file_list(self, file_list, path):
        for file_path in file_list:
            file_size = os.path.getsize(file_path)
            file_type = re.search(
                r':\s+.*/([^;]+);\s+',
                judge_file(file_path)).group(1)
            _path = file_path.replace(path, '.')

            file_info = 'file_size:%d, file_type:%s, file_name:'\
                % (file_size, file_type)

            if isinstance(_path, unicode):
                _path = _path.encode('utf8')
            file_info += _path
            # sys.stdout.write(_path)
            self.info_logger.info(trans2json(
                self.external_id,
                "record_file",
                "file_info", file_info)
            )

    def check_inputdata(self, task_info):
        if True:
            return
        else:
            raise Exception

    def thunder_download(self, protocol, download_path):
        log_path = self.created_log_path()
        log_file = log_path + '/' + 'thunder_download.log'
        
        args = 'timeout %d %s/Downloader "%s" "%s" %d %d %d' % (
            self.worker_config.get('download_task_timeout', 10800),
            self.tool_path,
            protocol,
            download_path,
            self.max_download_size / (1024 * 1024),
            self.worker_config.get('download_task_timeout', 10800),
            self.worker_config.get('check_progress_time', 600))

        self.logger.debug('args is: [%s]' % args)
        self.logger.info("logfile is %s" % log_file)

        os.environ["LD_LIBRARY_PATH"] = self.tool_path

        args = shlex.split(args)

        global down_fd
        down_fd = subprocess.Popen(
            args, stdout=open(log_file, 'w'), stderr=PIPE, env=os.environ)

        ret = down_fd.wait()
        _, err = down_fd.communicate()
        down_fd = None
        self.logger.debug('ret: %d, err is: %s' %
                          (ret, str(err)))
        if ret != 0:
            raise dt_error(ERR_DOWNLOAD, "thunder sdk download file failed")
        else:
            return self.remove_thunder_temp_file(traverse_folder(download_path))

    def remove_thunder_temp_file(self, file_list):
        new_file_list = []
        for file_ in file_list:
            if os.path.basename(file_) in ("kad.cfg", "dht.cfg"):
                pass
            else:
                new_file_list.append(file_)
        return new_file_list

    def seed_download_process(self, remote_path):
        torrent_path = os.path.join(
            self.task_path,
            os.path.basename(self.input_data.location)
        )
        download_swift_file(
            self.tool_path,
            self.input_data.location,
            torrent_path
        )

        self.parse_torrent_info(torrent_path)
        seed_download_path = self.created_temp_dir()
        try:
            ret, need_thunder, file_list = self.partial_download(
                torrent_path.strip(), seed_download_path, is_url=False)
        except:
            ret, need_thunder, file_list = PARTIAL_DOWN_EXCEPTION, True, []
            if os.path.isdir(seed_download_path):
                os.system("rm -rf %s/*" % seed_download_path)
            self.logger.error(
                'partial download exception:%s' % traceback.format_exc())
        self.record_partial_download(ret, torrent_path)
        if need_thunder:
            file_list = self.thunder_download(
                torrent_path.strip(),
                seed_download_path
            )

        if not file_list\
                or not len(file_list):
            raise dt_error(ERR_DOWNLOAD,
                           "downloader error, directory has no file"
                           )
        return seed_download_path, file_list

    def record_partial_download(self, ret, protocol):
        key = 'info'
        status = {-1: 'failed', 0: 'success', 1: 'ignore'}
        f = lambda ret: -1 if ret < 0 else (0 if ret == 0 else 1)
        value = 'hash_data:{0}, protocol:{1}, status:{2}, errcode:{3}'.format(
                self.input_data.hash_data, protocol, status[f(ret)], ret)
        self.info_logger.info(
            trans2json(self.external_id, 'partial_download', key, value))
        self.result_data['params']['partial_errcode'] = ret

    def record_offline_download(self, ret, protocol):
        key = 'info'
        status = {-1: 'failed', 0: 'success', 1: 'ignore'}
        f = lambda ret: -1 if ret < 0 else (0 if ret == 0 else 1)
        value = 'hash_data:{0}, protocol:{1}, status:{2}, errcode:{3}'.format(
                self.input_data.hash_data, protocol, status[f(ret)], ret)
        self.info_logger.info(
            trans2json(self.external_id, 'offline_download', key, value))
        self.result_data['params']['offline_errcode'] = ret

    def __del__(self):
        if self.worker_config.get('clean_tmp_dir', True):
            self.dirs.append(self.task_path)
            for temp_dir in self.dirs:
                delete_path(temp_dir)


def finish_task(result, code, msg):
    try:
        result['method'] = 'finish_task'
        result['params']['error_code'] = code
        result['params']['message'] = msg
        result['params']['host_name'] = socket.gethostname()
        result = json.dumps(result)
        return result
    except:
        traceback.print_exc()


def downloader_worker(config_file, task_info, path, log_path):
    try:
        with open(config_file) as fp:
            etc_data = json.load(fp)
        worker_config = etc_data

        info_logger = mylogger()
        info_logger.init_logger(
            "downloader",
            etc_data['log']['log_level'],
            log_path,
            SysLogHandler.LOG_LOCAL1
        )

        logger = mylogger()
        logger.init_logger(
            "downloader",
            etc_data['log']['log_level'],
            log_path,
            SysLogHandler.LOG_LOCAL2
        )

        logger.debug('download worker start')
        worker = None
    except Exception, reason:
        traceback.print_exc()
        sys.exit(1)

    try:
        logger.debug('task is: [%s]' % task_info)
        task_info = json.loads(task_info)
        worker = worker_temp(
            info_logger,
            logger,
            path,
            config_file,
            task_info
        )
    except dt_error, dt:
        traceback.print_exc()
        logger.error('init failed: [%s]' % str())
        return finish_task(task_info, dt.code(), dt.msg())

    except Exception, reason:
        logger.error('fetal error, worker class init failed')
        traceback.print_exc()
        return finish_task(task_info, ERR_UNKNOW, str(reason))

    try:
        start = time.time()
        worker.processing_timer(worker_config.get('heartbeat_interval', 60))
        worker.download_file()
        end = time.time()
        worker.update_time(start, end)
        return finish_task(worker.result_data, SUCCESS, 'success')

    except dt_error, dt:
        if dt.code() == SUCCESS:
            logger.info('worker executor: %s' % dt.msg())
        else:
            logger.error('worker executor: %s' % dt.msg())
        end = time.time()
        worker.update_time(start, end)
        return finish_task(worker.result_data, dt.code(), dt.msg())

    except Exception, reason:
        logger.error('find unkwon error: %s' % str(reason))
        traceback.print_exc()
        end = time.time()
        worker.update_time(start, end)
        return finish_task(worker.result_data, ERR_UNKNOW, str(reason))

    finally:
        worker.cancel_processing_timer()


'''
    def load_result_template(self):
        self.result_data['params'].update({"dna": [ { "path": "", "hash": "", "cal_size": 0, "etc_version": "1.0" } ]})
        self.result_data['params'].update({"error_code": 0, "message": ""})
        if self.task_type is URL_FILE:
            self.result_data['params'].update({"seed_file": { "path": "", "hash": "" }})
        else:
            self.result_data['params'].update({"url":{ "location": "", "hash": "" }})
        #self.result_data['params'] = result_data
'''
