#!/usr/bin/python
#coding: utf-8

from interface_gateway import Gateway

import unittest
import json
 
class gateway_TestCase(unittest.TestCase):
   template_json=None
   case_json=None

   def runTest(self):
       handler=Gateway()
       print gateway_TestCase.template_json
       print 111
       print gateway_TestCase.case_json
       use_case= handler.set_value(gateway_TestCase.template_json,gateway_TestCase.case_json)

       print use_case
       if gateway_TestCase.case_json['method'] == 'GET':
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

   def suite():
      """
        Gather all the tests from this module in a test suite.
      """
      test_suite = unittest.TestSuite()
      test_suite.addTest(gateway_TestCase('runTest'))
      return test_suite

if __name__ == '__main__':
   unittest.main()

