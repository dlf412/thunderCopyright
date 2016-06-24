#!/usr/bin/python
# coding=utf-8

import sys
import os
import json
import datetime
import traceback
import time
import re

import getopt


def parse_line_data(line):
    result_data = re.search(r'({.*})', line)
    if result_data:
        result_data = result_data.group(0)
    else:
        print result_data
    try:
        result_data = json.loads(result_data)
        return json_parse(result_data)
    except ValueError:
        return regex_parse(result_data)
    except Exception:
        traceback.print_exc()

def json_parse(task_info):
    downloader_failed = {
            121508:'download_failed', 
            121509:'unsupported_download',
            121500:'parse_input_failed',
            121502:'split_far_failed',
            121503:'swift_opration_faild',
            121510:'unknow_error',
            121512:'invalid_torrent'}
    success           = {121511:"filter_torrent"}
    code              = task_info['params'].get('error_code')
    msg               = task_info['params']['message']

    if code in downloader_failed:
        return 1, 'failed', msg, code, get_location(task_info), task_info
    elif code in success:
        return 0, 'success'
    else:
        files = task_info['params'].get('files', None)
        if not files and code is 0:
            #this means download is torrent file
            return 3, 'success', msg, code, get_location(task_info), task_info
        if not files:
            return 1, 'failed', msg, code, get_location(task_info), task_info
        else:
            for f in files:
                if 2 != f.get('code'):
                    return 0, 'suceess', msg, code, get_location(task_info), task_info
            return 2, 'undected', msg, code, get_location(task_info), task_info


def get_location(task_info):
    if 'seed_file' in task_info['params']:
        seed_path = task_info['params']['seed_file']['path']
        if 'url' in task_info['params']:
            url_location = task_info['params']['url']['location']
            return seed_path, url_location
        else:
            return seed_path, None
    else:
        return None, task_info['params']['url']['location']

def regex_parse(data):
    pass


class Taskinfo():
    def __init__(code, msg, url):
        self.code = code
        self.msg  = msg
        self.url  = url

def main():
    if len(sys.argv) is not 7:
        print " input need, -s:'start_time:2014-08-26 06', -e:'end_time:2014-08-26 23', -f:'log_filename:/var/log/syslog' "
        sys.exit(0)

    global start_time
    global end_time
    options,args = getopt.getopt(sys.argv[1:],"s:e:f:",["start_time", "end_time","log_filename"])
    for opt, arg in options:
        if opt in ('-s', '--start_time'):
            start_time = arg 
        elif opt in ('-e', '--end_time'):
            end_time = arg
        elif opt in ('-f', '--log_filename'):
            log_name = arg

    record_list = []
    '''
    global s_time
    global e_time
    s_time = datetime.datetime.strptime(start_time.strip() + ":00:00")
    e_time = datetime.datatime.strptime(end_time.strip() + ":00:00")
    '''

    success_list      = []
    failed_list       = []
    no_detect_list    = []
    torrent_list      = []

    with open(log_name) as f:
        for line in f.readlines():
            if not re.search(r'new fin task generate', line):
                continue
            d_time = re.search('(\d{4}-\d{2}-\d{2}\s*\d{2}:\d{2}:\d{2})', line).group(0)
            if d_time < start_time:
                continue
            elif d_time > end_time:
                break
            else:
                result = parse_line_data(line)
                if not result:
                    continue
                else:
                    if result[0] is 0:
                        success_list.append(result)
                    elif result[0] is 1:
                        failed_list.append(result)
                    elif result[0] is 2:
                        no_detect_list.append(result)
                    elif result[0] is 3:
                        #url_torrent_file, this need be charged
                        torrent_list.append(result)
                    else:
                        pass
    f_count = open('task_count', "w")
    f_count.write('success task count: %s\n' % str(len(success_list) + len(torrent_list)))
    f_count.write('\tsuccess download_video count: %s\n' % str(len(success_list)))
    f_count.write('\tsuccess download url_seed/magnet count: %s\n' % str(len(torrent_list)))
    f_count.write('failed task count: %s\n' % str(len(failed_list)))
    f_count.write('undtected task count: %s\n' % str(len(no_detect_list)))
    f_count.close()

    f_failed = open('task_failed', "w")
    for failed_task in failed_list:
        _,_, msg, code, location, task = failed_task
        d_time = task['params']['downloader_time']
        f_failed.write('downloader_time:[%d], code: [%d], msg: [%s], location: [%s]\n\n'
                % (d_time, code, msg, json.dumps(location)))
    f_failed.close()

    f_undtected = open('task_undected', "w")
    for no_de_task in no_detect_list:
        _,_, msg, code, location, task = failed_task
        f_failed.write('code: [%s], msg: [%s], location: [%s]\n'
                % (code, msg, json.dumps(location)))

    print 'success data is: ', len(success_list)
    print 'failed data is: ', len(failed_list)
    print 'undeteced data is: ', len(no_detect_list)
    print 'torrent list is: ', len(torrent_list)

if __name__ == '__main__':
    main()

