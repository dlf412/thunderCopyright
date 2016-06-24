#!/usr/bin/python
#!encoding:utf-8

import requests
import json
import time
import request
import traceback

from const import CREATE_SERVER, CREATE_BT_SERVER, CREATE_ED2K_SERVER, \
    QUERY_SERVER, NEW_URL_SERVER, HTTP, ED2K, BT, UPLOAD_BT_SERVER, QUERY_BT_SERVER

from gen_url import gen_new_url
from my_exceptions import HttpError


def task_request(host, rq):
    '''
    input: host, create_request_data
    output: requests response, json format:
{"data":{"speed":0,"tid":33038834023,"status":0,"fid":"","progress":0,"tindex":100001}}
    '''

    if not isinstance(rq, request.QueryRequestData) and not isinstance(rq, request.CreateRequestData):
        raise HttpError("request data invalid!")
    if not isinstance(host, str):
        raise HttpError("host error!")
    try:
        r = requests.post(host, data=json.dumps(rq.body), headers=rq.headers)
    except:
        raise HttpError("task request post error:%s" % traceback.format_exc())

    if r.status_code != 200:
        raise HttpError("create task request error, error_code=%d, reason=%s" % (
            r.status_code, r.reason))

    return json.loads(r.text)


def query_bt(bt_hash):
    '''
    input: host, query_bt_data
    output1: fileinfos, infohash 
    output2: None, None 
    json format: {u'fileinfo': [{u'path': u'', u'length': 1074722816, u'name': u'Predestination.avi', u'index': 0}], u'infohash': u'2f78da8d0a1c21a12a15097b2db35578f2ed2b38'} 
    '''
    qbd = request.QueryBtData(bt_hash)
    try:
        r = requests.post(QUERY_BT_SERVER, data=json.dumps(qbd.body),
                          headers=qbd.headers)
    except:
        raise HttpError("query bt post error:%s" % traceback.format_exc())

    if r.status_code == 404:
        return None, None
    elif r.status_code != 200:
        raise HttpError(
            "Query bt hash error, errcode=%d, reason=%s" % (r.status_code, r.reason))
    r.encoding = 'utf-8'
    res_obj = json.loads(r.text)['data']
    fileinfos = res_obj['fileinfo']
    infohash = res_obj['infohash']
    return fileinfos, infohash


def upload_bt(bt_file):
    ubd = request.UploadBtData(bt_file)
    url = UPLOAD_BT_SERVER + '?' + ubd.params
    try:
        r = requests.post(url, data=ubd.bt_file_content, headers=ubd.headers)
    except:
        raise HttpError("upload bt post error:%s" % traceback.format_exc())

    if r.status_code != 200:
        raise HttpError(
            "Upload bt file error, errcode = %d, reason=%s" % (r.status_code, r.reason))
    r.encoding = 'utf-8'
    res_obj = json.loads(r.text)['data']
    fileinfos = res_obj['fileinfo']
    infohash = res_obj['infohash']

    return fileinfos, infohash


if __name__ == '__main__':

    interval = 3
    url = "http://dlc2.pconline.com.cn/filedown3_52509_16841482/IkUOPeO9/flashget.3.7.0_5100000525096841482.exe"
    protocol = HTTP
    filename = "flashget.3.7.0_5100000525096841482.exe"
    #url = "http://v.snagfilms.com/films/aol/us/aoltruestories/2012/autlookfilmsales/thearrangement/THEARRANGEMEN1.mp4"
    crq = request.CreateRequestData(url, "QQ6.7.exe")

    print "=========Create HTTP Task==========="
    res = task_request(CREATE_SERVER, crq)
    print "=========Query Task ================"
    while res['data']['status'] in (0, 1):
        tid = res['data']['tid']
        tindex = res['data']['tindex']
        ck = crq.ck
        qrq = request.QueryRequestData(tid, tindex, ck)
        res = task_request(QUERY_SERVER, qrq)
        if res['data']['status'] in (2, 3):
            break
        time.sleep(interval)

    resobj = res['data']
    fid = resobj["fid"]
    if len(fid) == 0:
        exit("empty fid. exit!!!")

    print gen_new_url(NEW_URL_SERVER, fid, crq.ck, filename, 2345678)

    """
    print "========Create BT Task============"
    
    print "=======upload bt file=============="
    bt_file = "/home/deng_lingfei/The.Interview.2014.720p.WEB-DL.XviD.MP3-RARBG.torrent"
    ubd = request.UploadBtData(bt_file)
    url = UPLOAD_BT_SERVER + '?' + ubd.params

    r = requests.post(url, data=ubd.bt_file_content, headers=ubd.headers) 
    '''
    response format: {u'data': {u'fileinfo': [{u'path': u'', u'length': 208879708, u'name': u'\u795e\u76fe\u5c40\u7279\u5de5.Marvels.Agents.of.S.H.I.E.L.D.S02E01.\u4e2d\u82f1\u5b57\u5e55.HDTVrip.720X400.mp4', u'index': 0}], u'infohash': u'9CB2F0558CC8C10E07F514C7E9C1856BD9B901F5'}}
    '''
    if r.status_code != 200:
        raise RuntimeError("Upload bt file error, errcode = %d, reason=%s" % (r.status_code, r.reason))
    r.encoding = 'utf-8'

    res_obj = json.loads(r.text)['data']

    fileinfos = res_obj['fileinfo']
    infohash = res_obj['infohash']

    for f in fileinfos:
        f['name'] = f['name'].encode('utf-8') if isinstance(f['name'], unicode) else f['name']
        print f['path'], f['length'], type(f['name']), f['index']


    print "========== end upload bt file ========="

    print "creat bt task............."

    for f in fileinfos:
        bt_url = "bt://{infohash}/{index}".format(infohash=infohash, index=f['index'])
        print bt_url
        crq = request.CreateRequestData(bt_url, f['name'], protocol=BT)
        res = task_request(CREATE_BT_SERVER, crq)
        print res
        while res['data']['status'] in (0, 1):
            tid = res['data']['tid']
            tindex = res['data']['tindex']
            ck = crq.ck
            qrq = request.QueryRequestData(tid, tindex, ck)
            res = task_request(QUERY_SERVER, qrq)
            if res['data']['status'] in (2, 3):
                break
            time.sleep(interval)

        resobj = res['data']
        fid = resobj["fid"]
        if len(fid) == 0:
            exit("empty fid. exit!!!")

        print gen_new_url(NEW_URL_SERVER, fid, crq.ck, f['name'])
    """

    print "=============Create ed2k Task ================"
    ed2k_url = "ed2k://|file|%E5%B1%B1%E6%B5%B7%E7%BB%8F[www.ed2kers.com].pdf|55486308|dbd852b4d0cc4a794d873480dbcee253|h=stqay2agcpgnpdd3bk5plevq7dhk7lim|/"
    ed2k_url = "ed2k://|file|%5B%E5%B7%A5%E5%8E%82%E7%B2%BE%E7%BB%86%E5%8C%96%E7%AE%A1%E7%90%86%E5%88%B6%E5%BA%A6%E8%8C%83%E6%9C%AC.%E5%AE%9E%E6%88%98%E7%B2%BE%E5%8D%8E%E7%89%88%5D.%E5%90%B4%E6%97%A5%E8%8D%A3.%E6%89%AB%E6%8F%8F%E7%89%88[www.ed2kers.com].pdf|17106363|8f9b86059969be9c4cd40c4d264ad030|h=ong52fcg3ozngypgb3nfybngy6hgl7fe|/"
    #ed2k_url = "ed2k://|file|earth-7.1.1.1888-veket[www.ed2kers.com].pet|68466957|12448691c3a3a49320e9b32aa665b9b5|h=uakjnuht74et2uztftwheefgnpj424f7|/"
    filename = "earth-7.1.1.1888-veket.pet"

    crq = request.CreateRequestData(ed2k_url, filename, protocol=ED2K)
    res = task_request(CREATE_ED2K_SERVER, crq)

    print res
    while res['data']['status'] in (0, 1):
        tid = res['data']['tid']
        tindex = res['data']['tindex']
        ck = crq.ck
        qrq = request.QueryRequestData(tid, tindex, ck)
        res = task_request(QUERY_SERVER, qrq)
        print res
        if res['data']['status'] in (2, 3):
            break
        time.sleep(interval)

    resobj = res['data']
    fid = resobj["fid"]
    if len(fid) == 0:
        exit("empty fid. exit!!!")

    print gen_new_url(NEW_URL_SERVER, fid, crq.ck, filename, 2345678)

    print "============end ed2k Task ============="
