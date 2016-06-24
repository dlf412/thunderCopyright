#!/usr/bin/python
#!encoding:utf-8
'''
Usage:
  offline_downloader.py <url/seed_file> <filename> <config_file> --save_dir=SAVE_DIR [--digest=DIGEST] [--tmp_dir=TMP_DIR] [--log=LOG_FILE] [--poll_interval=POLL_INTERVAL] [--poll_timeout=POLL_TIMEOUT] [--max_speed=MAX_SPEED] [--download_seedfile_timeout=DOWNLOAD_SEEDFILE_TIMEOUT] [--download_timeout=DOWNLOAD_TIMEOUT]
  offline_downloader.py (--version|--help)

Arguments:
  url/seed_file   url for ed2k, http, https, ftp, thunder magnet, seed_file location
  filename        filename to download
  config_file     config file for partially downloading
  
Options:
  -h --help                 show this help message and exit
  --version                 show version  and exit
  -g --digest DIGEST        set the download url's digest
  -p --tmp_dir TMP_DIR      set saving seed_file tmp dir [default: /tmp/]
  -i --poll_interval POLL_INTERVAL  set poll interval [default: 60]
  -t --poll_timeout POLL_TIMEOUT    set poll timeout [default: 3600]
  -d --save_dir SAVE_DIR      set download file save dir
  -m --max_speed MAX_SPEED   set download max speed [default: 4096000]
  -s --download_seedfile_timeout DOWNLOAD_SEEDFILE_TIMEOUT  set download seedfile timeout [default: 600]
  -T --download_timeout DOWNLOAD_TIMEOUT  set download file timeout [default: 10800]
  -l --log=LOG_FILE         set log_file [default: syslog]
'''

import time
import base64
import commands
import request
import sys
import charade
import os
import urllib
import traceback
from docopt import docopt
import pipes
from logging.handlers import SysLogHandler
import json
import subprocess
import uuid
import re

from downloader_util import Retry
from common.mylogger import *
from const import CREATE_SERVER, CREATE_BT_SERVER, CREATE_ED2K_SERVER, \
    QUERY_SERVER, NEW_URL_SERVER, HTTP, ED2K, BT, OFFLINE_UNKNOWN_ERROR
from my_exceptions import MyException, HttpError, StatusError, DownloadError, GenUrlError, \
    UnknownError, PollTimeout
from gen_url import gen_new_url
from request_flow import task_request, upload_bt, query_bt
from partial_downloader import PartialDownloader

tools_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../tools')

resource = ""
cfg = None

g_logger = None


def debug(msg):
    if g_logger:
        g_logger.debug(msg)


def info(msg):
    if g_logger:
        g_logger.debug(msg)


def error(msg):
    if g_logger:
        g_logger.error(msg)


def trans_url_to_utf8(url):

    debug('trans url to utf-8 encoding')
    if isinstance(url, unicode):
        url = url.encode('utf-8')
    encoding = charade.detect(url)['encoding']
    if encoding.lower() in ('gb2312', 'gbk'):
        encoding = 'gb18030'
    url = url.decode(encoding).encode('utf-8')
    return url


def parse_url_type(url):
    debug('parse url type')

    def get_protocol(protocol):
        if "ED2K" == protocol.upper():
            return ED2K
        elif protocol.upper() in ('HTTP', 'HTTPS', 'FTP'):
            return HTTP
        elif "MAGNET" == protocol.upper():
            return BT
        else:  # maybe a path or other protocol, others as BT
            return BT

    protocol = url.split(':')[0]
    if "THUNDER" == protocol.upper():
        t_url = url.split(':')[1].lstrip('//')
        t_url = base64.urlsafe_b64decode(t_url)
        url = t_url.lstrip("AA").rstrip("ZZ")
        protocol = url.split(':')[0]

    url = trans_url_to_utf8(url)
    return get_protocol(protocol), url


def loop_query(crq, res, poll_timeout, poll_interval):
    debug('start polling query...')
    start = time.time()
    while res['data']['status'] in (0, 1):
        if time.time() - start > poll_timeout:
            raise PollTimeout("query poll timeout")
        tid = res['data']['tid']
        tindex = res['data']['tindex']
        ck = crq.ck
        qrq = request.QueryRequestData(tid, tindex, ck)
        try:
            res = task_request(QUERY_SERVER, qrq)
        except:
            pass
        if res['data']['status'] == 3:
            raise StatusError("thunder offline download failed")
        if res['data']['status'] == 2:
            break
        time.sleep(poll_interval)
        debug('polling......')

    resobj = res['data']
    fid = resobj["fid"]
    if len(fid) == 0:
        raise HttpError("empty fid. exit!!!")
    info("polling end, get fid successfully, fid=%s" % fid)
    return fid


def get_bt_hash(bt_file):
    cmd = "aria2c -S %s | grep 'Info Hash'" % pipes.quote(bt_file)
    hash_info = commands.getoutput(cmd)
    if len(hash_info) > 0:
        return hash_info.split(':')[1].strip()
    else:
        return None


def get_new_urls(args):
    '''
    return [(new_url, filename, header) .....]
    '''
    max_speed = int(args['--max_speed'])
    poll_interval = int(args['--poll_interval'])
    poll_timeout = int(args['--poll_timeout'])
    bt_save_dir = args['--tmp_dir']
    filename = args['<filename>']
    global resource
    resource = args['<url/seed_file>']
    download_seedfile_timeout = int(args['--download_seedfile_timeout'])

    urls = []
    url = urllib.unquote(resource)

    protocol, url = parse_url_type(url)
    info(
        "parse url: protocol is %s, url is %s" % (protocol, url))
    if protocol == HTTP:
        #filename = url.split('/')[-1]
        crq = request.CreateRequestData(url, filename)
        res = task_request(CREATE_SERVER, crq)

    if protocol == ED2K:
        #filename = url.split('|')[2]
        crq = request.CreateRequestData(url, filename, protocol=ED2K)
        res = task_request(CREATE_ED2K_SERVER, crq)

    if protocol == BT:
        '''magnet:?xt=urn:btih:2f78da8d0a1c21a12a15097b2db35578f2ed2b38&dn=Predestination'''
        bt_hash = url.split(
            'btih:')[1][:40] if "magnet" in url else get_bt_hash(url)
        if bt_hash:
            debug('query bt hash....')
            fileinfos, hashinfo = query_bt(bt_hash)
        else:
            raise UnknownError("Invalid seed_file or magnet[%s]" % url)

        if fileinfos is None:
            if "magnet" in url:
                dl_bt_cmd = 'timeout %d aria2c %s --dir=%s --bt-save-metadata=true  --bt-metadata-only=true >/dev/null 2>&1' % (
                    download_seedfile_timeout, pipes.quote(url), bt_save_dir)
                debug('download seed_file from magnet, cmd is %s' % dl_bt_cmd)
                ret = os.system(dl_bt_cmd)
                if ret != 0:
                    raise DownloadError("aria2c download bt_file failed")
                bt_files = [f for f in os.listdir(bt_save_dir) if f.upper() == ('%s.TORRENT' % bt_hash).upper()]
                if not bt_files:
                    raise DownloadError("aria2c download bt_file failed")
                bt_file =  os.path.join(bt_save_dir, bt_files[0])
            else:
                bt_file = url
            info("upload bt file:%s" % bt_file)
            fileinfos, hashinfo = upload_bt(bt_file)

    debug("create task end...")

    if protocol in (ED2K, HTTP):
        fid = loop_query(crq, res, poll_timeout, poll_interval)
        try:
            new_url = gen_new_url(
                NEW_URL_SERVER, fid, crq.ck, filename, max_speed)
            info(
                'gen new url successfully, new url is %s' % new_url)
        except:
            raise GenUrlError("generate url error")
        header = "--header='cookie:gdriveid:%s'" % crq.ck
        urls.append((new_url, header, filename))

    elif protocol == BT:
        if fileinfos is not None:
            debug("bt files len is %d" % len(fileinfos))
        for f in fileinfos:
            bt_url = "bt://{hashinfo}/{index}".format(
                hashinfo=hashinfo, index=f['index'])
            if isinstance(f['name'], unicode):
                f['name'] = f['name'].encode('utf-8')
            crq = request.CreateRequestData(bt_url, f['name'], protocol=BT)
            res = task_request(CREATE_BT_SERVER, crq)
            fid = loop_query(crq, res, poll_timeout, poll_interval)
            try:
                new_url = gen_new_url(
                    NEW_URL_SERVER, fid, crq.ck, f['name'], max_speed)
                info('gen new url successfully, new url is %s' % new_url)
            except:
                raise GenUrlError("generate url error")

            header = "--header='cookie:gdriveid:%s'" % crq.ck
            urls.append((new_url, header, f['name']))
    else:
        error("unknown protocol:%s" % url.split(':')[0])
        raise UnknownError("unknown protocol:%s" % url.split(':')[0])

    return urls


def gen_dna_files(save_dir, file_path):
    try:
        temp_path = save_dir + '/' + str(uuid.uuid1())
        far_path, dna_path, stats_path = temp_path + \
            '.far', temp_path + '.dna', temp_path + '.stats'
        gen_far(file_path, far_path)
        gen_dna_stat(far_path, dna_path, stats_path)
        return dna_path, stats_path
    except:
        raise


def calc_need_dl_size(dna_path, file_path):
    try:
        dna_length_thresh = cfg.get('dna_length', 600)
        dna_length = get_dna_len(dna_path)
        debug("dna_length is %d" % dna_length)
        if dna_length >= dna_length_thresh:
            return 0
        need_dl_size = calc_dl_size(file_path, dna_length_thresh)
        return need_dl_size
    except:
        raise


def get_dna_len(dna_path):
    args = "%s/dna_status -i %s 2>&1 | grep LENGTH | awk -F= '{print $2}'" % (
        tools_dir, pipes.quote(dna_path))
    length = commands.getoutput(args).strip()
    try:
        return int(length)
    except ValueError:
        raise Exception(
            "invalid dna or dna_status tool is not exists")


def calc_dl_size(file_path, dl_length):
    '''
    ffmpeg -i file_path to get video and audio bitrate
    '''
    vbitrate = abitrate = 0
    args = "ffmpeg -i %s 2>&1 | grep Video" % pipes.quote(file_path)
    out = commands.getoutput(args).strip()
    m = re.match('.*, (\d+) *kb/s', out)
    if not m:
        raise Exception("not Video")

    vbitrate = int(m.groups()[0])

    args = "ffmpeg -i %s 2>&1 | grep Audio" % pipes.quote(file_path)
    out = commands.getoutput(args).strip()
    if out:
        m = re.match('.*, (\d+) *kb/s', out)
        if m:
            abitrate = int(m.groups()[0])
    bitrate = vbitrate + abitrate

    debug("bitrate is %d kb/s" % bitrate)

    if bitrate == 0:
        raise Exception("get bitrate failed")
    dl_size = bitrate * dl_length / 8. * 1.2 * 1024
    return dl_size 


def gen_dna_stat(far_path, dna_path, stats_path):
    args = "%s/far_split -i %s -d %s  -s %s" % (
        tools_dir,
        pipes.quote(far_path),
        pipes.quote(dna_path),
        pipes.quote(stats_path)
    )
    debug(args)
    ret, output = commands.getstatusoutput(args)
    if ret != 0:
        raise Exception("gen dna stat failed, errmsg is %s" % output)


def gen_far(video_path, far_path):
    args = "VDNAGen -o %s %s" % (
        pipes.quote(far_path), pipes.quote(video_path))
    debug(args)
    output = commands.getoutput(args)
    if output.find("Unsupported file format:") is not -1:
        raise Exception("gen dna failed:Unsupported file format")
    elif output.find("<ErrorCode>0</ErrorCode>") is -1 \
            and output.find("<error_code>0</error_code>") is -1:
        raise Exception("gen dna failed: error is %s" % output)


def download_all(dl, tid, header, timeout):
    if timeout <= 0:
        raise DownloadError("partial download timeout")

    dl.start(tid, timeout=timeout, header=header)
    dl_status, file_path, _ = dl.wait_finished(tid)
    if dl_status not in (0, 7):
        raise DownloadError(
            "partial download failed: aria2c run failed, errcode is %d" % dl_status)
    if dl_status == 7:
        raise DownloadError("partial download timeout")

    debug('download file all size ok')
    return file_path


def download_special_size(dl, tid, header, size, timeout=0):
    dl.start(tid, size=size, timeout=timeout, header=header)
    dl_status, file_path, real_dl_size = dl.wait_finished(tid)
    if dl_status not in (0, 7):
        raise DownloadError(
            "partial download failed: aria2c run failed, errcode is %d" % dl_status)
    if not os.path.exists(file_path):
        raise DownloadError(
            "partial download failed: %s not exists, errcode is %d" % (file_path, dl_status))
    return dl_status, file_path, real_dl_size


@Retry(2, delay=2)
def invoke_vdna_query(dna_path):
    vddb_cfg = cfg.get('vddb')
    args = "vdna_query -s%s -p%d -u%s -w%s -TDNA --timeout=%d -i%s" % (vddb_cfg.get('server'),
                                                                       vddb_cfg.get('port'), 
                                                                       vddb_cfg.get('user'),
                                                                       vddb_cfg.get('password'),
                                                                       vddb_cfg.get('timeout'), dna_path) 
    debug("query vdna commands: %s" % args)
    ret, output = commands.getstatusoutput(args)
    ret = ret >> 8
    if ret != 0:
        raise Exception(
            "invoke vdna_query failed, ret=%d, reason=%s" % (ret, output))
    return parse_match(output)


def parse_match(output):
    '''
    <vddb>
    <query>
    <return_code>0</return_code>
    <extra_info>Success</extra_info>
    </query>
    <matches size="0" status="0">
    </matches>
    </vddb>
    '''
    m = re.match('.*<matches size="(\d+)"', output, re.S)
    if m is None:
        return False
    match_size = int(m.groups()[0])
    return match_size > 0


def partial_download(url, header, filename, save_dir, dl_timeout):
    '''
    start
    '''
    start = time.time()
    dl = PartialDownloader(save_dir, cfg)
    tid = dl.create_task(True, url, filename, 0)

    dl_status, file_path, real_dl_size = download_special_size(
        dl, tid, header, cfg.get('size'), cfg.get('timeout'))
    
    debug("partially download size[%d] OK or timeout" % cfg.get('size'))

    if dl_status == 0:
        return file_path
    has_cost =  int(time.time() - start) 

    try:
        dna_path, stats_path = gen_dna_files(save_dir, file_path)
    except:
        error("gen dna files failed, start download all, reason is %s" % traceback.format_exc())
        return download_all(dl, tid, header, dl_timeout - has_cost) 
    try:
        dl_size = calc_need_dl_size(dna_path, file_path)
        debug("partially download size is %d" % dl_size)
    except:
        error("calc partially download size failed, start download all, reason is %s" % traceback.format_exc())
        return download_all(dl, tid, header, dl_timeout - has_cost)

    if dl_size > 0:
        dl_status, file_path, real_dl_size = download_special_size(
            dl, tid, header, dl_size, dl_timeout - has_cost)
        if dl_status == 0:
            return file_path
        has_cost = int(time.time() - start)
        try:
            dna_path, stats_path = gen_dna_files(save_dir, file_path)
        except:
            error("gen dna files failed, start download all, reason is %s" % traceback.format_exc())
            return download_all(dl, tid, header, dl_timeout - has_cost)

    try:
        vddb_cfg = cfg.get('vddb')
        if  vddb_cfg.get('query', True):
            ismatch = invoke_vdna_query(dna_path)
        else:
            info("vddb query configure is ignore")
            return file_path
    except:
        error("vdna query failed, start download all, reason is %s" % traceback.format_exc())
        return download_all(dl, tid, header, dl_timeout - has_cost)
    if ismatch:
        info("vdna query match, start download all")
        return download_all(dl, tid, header, dl_timeout - has_cost)
    else:
        info("vdna query not match")
        return file_path

    return file_path


def download(url, header, filename, save_dir, log_dir, timeout):
    cmd = "wget -c -T%d %s %s -O %s/%s -o %s" % (timeout, pipes.quote(url), header,
                                                 pipes.quote(save_dir), pipes.quote(
                                                     filename),
                                                 os.path.join(log_dir, "wget.log"))
    debug("download cmd is %s" % cmd)
    ret, _ = commands.getstatusoutput(cmd)
    ret = ret >> 8
    if ret != 0:
        raise DownloadError(
            "download new url[%s] failed: wget run failed, errcode is %d" % (url, ret))
    return os.path.join(save_dir, filename)


def handle_exception(err):
    print >> sys.stderr, str(err)
    error(traceback.format_exc())
    exit(err.errors)


def main():
    args = docopt(__doc__, version='v1.0.0')
    '''
{'--help': False,
 '--log': 'syslog',
 '--digest': None,
 '--max_speed': '200',
 '--poll_interval': '10',
 '--poll_timeout': '60',
 '--save_dir': '/tmp/',
 '--tmp_dir': '/tmp/',
 '--download_seedfile_timeout': '600',
 '--download_timeout': '10800'
 '--version': False,
 '<filename>': 467,
 '<url/seed_file>': '123'
 '<config_file>': '../etc/downloader.conf'}
    '''
    save_dir = args['--save_dir']
    log = args['--log']
    download_timeout = int(args['--download_timeout'])
    digest = '' if args['--digest'] is None else args['--digest']
    wget_log_dir = args['--tmp_dir']

    cfg_file = args['<config_file>']
    with open(cfg_file) as fp:
        global cfg
        gl_cfg = json.load(fp)
        cfg = gl_cfg.get('offline').get('partial')
        log = gl_cfg.get('log').get('log_file', 'syslog')
        log_level = gl_cfg.get('log').get('log_level', 'DEBUG')
    global g_logger
    g_logger = mylogger()
    g_logger.init_logger(
        'offline_downloader', log_level, log, SysLogHandler.LOG_LOCAL0, digest)

    try:
        url_list = get_new_urls(args)
        for url in url_list:
            if cfg.get('enable', True):
                print partial_download(url[0], url[1], url[2], save_dir, download_timeout)
            else:
                print download(url[0], url[1], url[2], save_dir, wget_log_dir, download_timeout)
    except MyException, err:
        handle_exception(err)
    except Exception, err:
        print >> sys.stderr, str(err)
        error(traceback.format_exc())
        exit(OFFLINE_UNKNOWN_ERROR)


if __name__ == '__main__':
    main()
