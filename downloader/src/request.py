#/usr/bin/env python
#! encoding=utf-8

import os
import sys

import json
import base64
from hashlib import md5
import requests
import time
import platform

from const import PK, PUSH, SK, HTTP, ED2K, BT

from const import UPLOAD_BT_SERVER, QUERY_BT_SERVER


class CreateRequestData(object):

    '''
    protocol is in (HTTP, ED2K, BT)
    BT url format: bt://<infohash>/<file_index>
    '''

    def __init__(self, url, name, protocol=HTTP, http_referer="", http_cookie=""):

        self.protocol = protocol
        self._sk = SK
        self._pk = PK
        self._timestamp = int(time.time())
        self._url = url
        self._name = base64.b64encode(name)
        ac_keys = ['_sk', '_pk', '_timestamp', '_url', '_name']
        if self.protocol == HTTP:
            self._referer = http_referer
            self._cookie = http_cookie
            ac_keys.append('_referer')
            ac_keys.append('_cookie')
        ac = ''.join([str(getattr(self, key)) for key in ac_keys])
        self._access_token = md5(ac).hexdigest()
        self._push = PUSH
        body_keys = [
            e for e in dir(self) if e.startswith('_') and not e.endswith('_')]
        self.body = {key[1:]: getattr(self, key)
                     for key in body_keys if key != '_sk'}

        self.ck = md5(
            self._pk + time.strftime("%Y%m%d", time.localtime())).hexdigest().upper()
        self.headers = {'content-type': 'application/octet-stream',
                        'Connection:': 'Keep-Alive',
                        'Accept:': '*/*',
                        'User-Agent': platform.system(),
                        'Host': platform.node(),
                        'Cookie': self.ck,
                        'Content-Length': len(json.dumps(self.body))}


'''
pk
string
生成access_token字段的密钥别名
必填
timestamp
int
unix时间戳，相差5分钟则认为请求非法
必填
tid
uint64
创建时返回的任务ID
必填
tindex
Uint32
创建时返回任务ID索引
必填
access_token
string
用pk对应的sk将url请求对应的字符串加密得到的结果, md5sum(sk+ pk+ timestamp + tid+tindex)
必填

'''


class QueryRequestData(object):

    def __init__(self, tid, tindex, ck=None):
        self._sk = SK
        self._pk = PK
        self._timestamp = int(time.time())
        self._tid = tid
        self._tindex = tindex

        ac_keys = ['_sk', '_pk', '_timestamp', '_tid', '_tindex']
        ac = ''.join([str(getattr(self, key)) for key in ac_keys])
        self._access_token = md5(ac).hexdigest()
        body_keys = [
            e for e in dir(self) if e.startswith('_') and not e.endswith('_')]
        self.body = {key[1:]: getattr(self, key)
                     for key in body_keys if key != '_sk'}
        if ck is None:
            self.ck = md5(
                self._pk + time.strftime("%Y%m%d", time.localtime())).hexdigest()
        else:
            self.ck = ck
        self.headers = {'content-type': 'application/octet-stream',
                        'Connection:': 'Keep-Alive',
                        'Accept:': '*/*',
                        'User-Agent': platform.system(),
                        'Host': platform.node(),
                        'Cookie': self.ck,
                        'Content-Length': len(json.dumps(self.body))}


class UploadBtData(object):

    def __init__(self, bt_file_path):
        self._bt_file_path = bt_file_path
        with open(bt_file_path) as fp:
            self.bt_file_content = fp.read()
        # download_to_clouds/upload_torrent?pk=xxx&timestamp=yyy&access_token=zzz
        params_format = "pk={pk}&timestamp={ts}&access_token={at}"
        ts = str(int(time.time()))
        at = md5(SK + PK + ts).hexdigest().upper()
        self.params = params_format.format(pk=PK, ts=ts, at=at)
        #self.ck = md5(PK + time.strftime("%Y%m%d", time.localtime())).hexdigest()

        self.headers = {'content-type': 'application/octet-stream',
                        'Connection:': 'Keep-Alive',
                        'Accept:': '*/*',
                        'User-Agent': platform.system(),
                        'Host': platform.node(),
                        #'Cookie': self.ck,
                        'Content-Length': len(self.bt_file_content)}


class QueryBtData(object):

    '''
    pk
    string
    生成access_token字段的密钥别名
    必填
    timestamp
    Int
    unix时间戳，相差5分钟则认为请求非法
    必填
    infohash
    String
    种子infohash
    必填
    access_token
    string
    用pk对应的sk将url请求对应的字符串加密得到的结果, md5sum(sk+ pk+ timestamp+infohash )
    必填
    '''

    def __init__(self, bt_hash):
        self._sk = SK
        self._pk = PK
        self._timestamp = int(time.time())
        self._infohash = bt_hash

        ac_keys = ['_sk', '_pk', '_timestamp', '_infohash']
        ac = ''.join([str(getattr(self, key)) for key in ac_keys])
        self._access_token = md5(ac).hexdigest()
        body_keys = [
            e for e in dir(self) if e.startswith('_') and not e.endswith('_')]
        self.body = {key[1:]: getattr(self, key)
                     for key in body_keys if key != '_sk'}
        self.ck = md5(
            self._pk + time.strftime("%Y%m%d", time.localtime())).hexdigest()
        self.headers = {'content-type': 'application/octet-stream',
                        'Connection:': 'Keep-Alive',
                        'Accept:': '*/*',
                        'User-Agent': platform.system(),
                        'Host': platform.node(),
                        'Cookie': self.ck,
                        'Content-Length': len(json.dumps(self.body))}


if __name__ == "__main__":

    qbd = QueryBtData("2f78da8d0a1c21a12a15097b2db35578f2ed2b38")

    #rq = CreateRequestData("123","456","789")

    #ubd = UploadBtData('/home/deng_lingfei/dummy.torrent')

    # print ubd.params

    #url = UPLOAD_BT_SERVER + '?' + ubd.params
    # print url

    import requests

    r = requests.post(
        QUERY_BT_SERVER, data=json.dumps(qbd.body), headers=qbd.headers)

    #r = requests.post(url, data=ubd.bt_file_content, headers=ubd.headers)

    '''
    response format: {u'data': {u'fileinfo': [{u'path': u'', u'length': 208879708, u'name': u'\u795e\u76fe\u5c40\u7279\u5de5.Marvels.Agents.of.S.H.I.E.L.D.S02E01.\u4e2d\u82f1\u5b57\u5e55.HDTVrip.720X400.mp4', u'index': 0}], u'infohash': u'9CB2F0558CC8C10E07F514C7E9C1856BD9B901F5'}}
    '''
    if r.status_code != 200:
        raise RuntimeError(
            "Upload bt file error, errcode = %d, reason=%s" % (r.status_code, r.reason))
    r.encoding = 'utf-8'

    '''
    data
    Object


    data.infohash
    String
    种子infohash
    必填
    data.fileinfo
    Array(Object)
    种子子文件信息
    必填
    data.fileinfo.index
    Uint32
    子文件索引
    必填
    data.fileinfo.name
    String
    子文件名
    必填
    data.fileinfo.size
    Uint32
    子文件大小
    必填

    '''
    res_obj = json.loads(r.text)['data']

    print str(res_obj)
    '''
    fileinfos = res_obj['fileinfo']
    infohash = res_obj['infohash']

    for f in fileinfos:
        print f['path'], f['length'], f['name'], f['index']

    print json.loads(r.text)['data']['fileinfo'][0]['name'].encode('utf-8')
    '''
