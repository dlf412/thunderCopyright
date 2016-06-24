#!/usr/bin/python
#coding: utf-8

import sys
import json
import base64
import requests
import unittest
import copy
import random
import time

class InterGateway:
    def clear_empty(self,dicts):
        """ 清除空字符串 """
        for d in dicts:
            [d.pop(k)
             for k, v in d.iteritems()
             if (v is None
                 or (isinstance(v, (str, unicode)) and len(v)==0))]

    def gateway_get(self,case):
        ''' gateway get  requests\
            xxx
        '''
        URL = '{}://{}:{}/copyrighted'.format(case['scheme'], case['host'], case['port'])
        headers = {
            'User-Agent':case['user-agent'],
            'X-Progress': case['X-Progress'],
            'X-Client-Address': case['X-Client-Address'],
            'X-Client-ID': case['X-Client-ID'],
            'X-File-Name': case['X-File-Name'].encode('utf-8'),
            'X-File-Size': case['X-File-Size'],
            'X-Mime-Type': case['X-Mime-Type'],
            'Referer':case['Referer'],
            'X-URL': case['url'].encode('utf-8')
        }

        params = {
            'key': case['key'],
            'hash': case['hash'],
            'digest': case['digest'],
            'digest-algorithm': case['digest-algorithm']
        }

        # 清除空字符串
        # clear_empty([headers, params])
        
        resp = requests.get(URL, headers=headers, params=params, verify=False)
        #print resp.status_code
        #print resp.headers
        #print resp.text
        return resp
        

    def gateway_post(self,case):
        URL = '{}://{}:{}/copyrighted'.format(case['scheme'], case['host'], case['port'])
        headers = {
            'User-Agent':case['user-agent'],
            'X-Progress': case['X-Progress'],
            'X-Client-Address': case['X-Client-Address'],
            'X-Client-ID': case['X-Client-ID'],
            'X-File-Name': case['X-File-Name'].encode('utf-8'),
            'X-File-Size': case['X-File-Size'],
            'X-Mime-Type': case['X-Mime-Type'],
            'Referer':case['Referer'],
            'X-URL': case['url'].encode('utf-8')
        }
        
        params = {
            'key': case['key'],
            'hash': case['hash'],
            'digest': case['digest'],
            'digest-algorithm': case['digest-algorithm']
        }

        path = case['seed_file']
        with open(path, 'r') as f:
            content = base64.b64encode(f.read())
            #print 'cotent###############', content
        data = {
            'seed_file': content,
            'seed_encoded': True
        }

        # 清除空字符串
        # clear_empty([headers, params])

        resp = requests.post(URL, headers=headers, params=params, data=json.dumps(data), verify=False)
        #print resp.status_code
        #print resp.headers
        #print resp.text
        return resp

    def req_http_url(self,ssl,host,port,method,site_asset_id):
        #http://host:port/vddb-async/matches?site_asset_id=url_hash#f8fabdde-e0f4-11e3-b471-fa163e4c5cc4
        URL = '{}://{}:{}/vddb-async/matches'.format(ssl, host, port)
        params={
            'site_asset_id':site_asset_id.encode('utf-8')
        }
        resp = requests.get(URL, headers={}, params=params, verify=False)
        #print resp.status_code
        #print resp.headers
        #print resp.text
        return [resp.status_code,resp.text]       

    def set_value(self,template_json,case_json):
        use_json=copy.copy(template_json)
        for k, v in case_json.iteritems():
            use_json[k]=v
        return use_json

    def test_result(self,expect_result,resp):
        print expect_result
        print resp.status_code
        print resp.text
        resp_result=json.dumps(resp.text)

    def req_gateway2(self,template_json,paramsDict):
        '''
        template_json format:
         {"scheme":"http","host":"182.92.9.187","port":8080,"key":"this-is-TMP-apikey",
         "X-Progress": "10","X-Client-Address": "192.168.1.1",
         "X-Client-ID": "client_id123456","X-File-Name":"qa_test",
         "X-File-Size": "123456","X-Mime-Type": "video/mp4","hash": "",
         "digest": "018e206e00bdc68374ff32bb0245d98ea703090e",
         "digest-algorithm": "sha1","method": "GET",
         "url": "http://115.29.36.65/clips/youku_28.flv",
         "seed_file":"123.torrent","seed_encoded":"true"}

         paramsDict format:
            {"url":"http:/xxx/xxx/xxx"}
        '''
        template1_json = json.loads(template_json);
        #print paramsDict
        use_case=self.set_value(template1_json,paramsDict);
        print use_case
        if use_case['method'] == 'post':
           resp= self.gateway_post(use_case)
        else:
           resp= self.gateway_get(use_case)
        d=[]
        d.append(resp.status_code)
        d.append(resp.text)
        return d

if __name__ == '__main__':
    num=random.randint(0,10000000000000)
    x= InterGateway();
    template1_json={"scheme":"http","host":"182.92.9.187","port":8080,"key":"this-is-TMP-apikey",\
         "X-Progress": "10","X-Client-Address": "192.168.1.1",\
         "X-Client-ID": "client_id123456","X-File-Name":"youku_28_1.flv",\
         "X-File-Size": "123456","X-Mime-Type": "video/mp4","hash": "",\
         "digest": "018e206e00bdc68374ff32bb0245d98ea703090e",\
         "digest-algorithm": "sha1","method": "GET",\
         "url": "http://115.29.36.65/clips/youku_28_1.flv","Referer":"http://www.test.net",\
         "seed_file":"123.torrent","seed_encoded":"true","user-agent":"Thunder Win 7.0"}
    template1_json=json.dumps(template1_json);          
    
    paramsDisct={"1":"1"}

    #torrent file
    #url="http://10.162.207.221/sample/low_audio_BT-Skylarking_[Remixes]_[EP]_[Muzic4all].torrent"
    #paramsDisct["X-File-Name"]="low_audio_BT-Skylarking_[Remixes]_[EP]_[Muzic4all].torrent"
    #paramsDisct["X-Mime-Type"]="application/x-bittorrent"
    #paramsDisct["url"]=url

    temp_hash=random.randint(0,1000000000)
    temp1="gatewayabcdefg%s"%(temp_hash)


    #post request
    #paramsDisct["method"]="post"
    #paramsDisct["seed_file"]="low_audio.torrent"
    #paramsDisct["seed_encoded"]="true"
    #paramsDisct["url"]="file://low_audio.torrent"
    #paramsDisct["X-Mime-Type"]="application/x-bittorrent"
    #paramsDisct["digest"]=temp1
    
    #http seed request
    paramsDisct["url"]="http://10.162.207.221/sample/low_audiotest01.torrent"
    paramsDisct["X-Mime-Type"]="application/x-bittorrent"
    paramsDisct["digest"]=temp1
    paramsDisct["X-File-Name"]="low_audiotest01.torrent"

    #
    #paramsDisct["X-File-Name"]=""
    #paramsDisct["X-File-Size"]=""
 
    #seed request
    #paramsDisct["X-File-Name"]=""
    #paramsDisct["X-File-Size"]=""

    # result=0
    # match_size=1 ['url_hash#abcdefg513792066', 'file_hash#abcdefg513792066']
    #match_size>1 ['url_hash#abcdefg513792066', 'file_hash#abcdefg513792066']

    #paramsDisct["digest"]="abcdefg824397263"
    #url="http://10.162.207.221/sample/xxx.mp3"
    #paramsDisct["X-File-Name"]="xxx.mp3"
    #paramsDisct["X-Mime-Type"]="audio/mpeg"
    #paramsDisct["url"]=url

    #result=1
    #paramsDisct["digest"]="abcdefg548673670"
    #url="http://10.162.207.221/sample/xxx.mp3"
    #paramsDisct["X-File-Name"]="xxx.mp3"
    #paramsDisct["X-Mime-Type"]="audio/mpeg"
    #paramsDisct["url"]=url


    print "---------------start time:%s\n"%(time.strftime('%Y%m%d-%H%M%S'))
    result=x.req_gateway2(template1_json,paramsDisct);
    print result
    print "\n---------------end time:%s"%(time.strftime('%Y%m%d-%H%M%S'))
