#!/usr/bin/python
#coding: utf-8

from interface_gateway import Gateway

import unittest
import json
 
class TestGateWay(unittest.TestCase):
   def test_gateway_req(self):
       #read template
       template_json = None
       with open('template.json') as f:
            template_json = json.loads(f.read())
       
       #read case
       cases = []
       with open('cases1.json') as b:
            cases = json.loads(b.read())
       
       num=0
       handler=Gateway()
       for case in cases:
           use_case= handler.set_value(template_json,case)
           num+=1
           print 'case %d:'%(num)
           print use_case
           if case['method'] == 'GET':
              resp= handler.gateway_get(use_case)
           else:
              resp= handler.gateway_post(use_case)
           
           expect_result=use_case['result']
           actual_result=json.loads(resp.text)
           expect_code=expect_result['status_code']
           expect_result=expect_result['info']

           self.assertEqual(expect_code,resp.status_code)

           print
           print expect_result
           print actual_result
           for k,v in expect_result.iteritems():
              self.assertEqual(expect_result[k],actual_result[k])

if __name__ == '__main__':
   unittest.main()

