#!/usr/bin/python
# Filename:testGatewaySuite.py

from GatewayTestCase import gateway_TestCase
import json
import unittest

#read template
#template1_json = None
with open('template.json') as f:
     template1_json = json.loads(f.read())

#read case
cases = []
with open('cases1.json') as b:
     cases = json.loads(b.read())

num=0
testcase=gateway_TestCase()

testSuite = unittest.TestSuite()
testResult = unittest.TestResult()

for case_json in cases:
      num+=1
      print 'case %d:'%(num)
      gateway_TestCase.template_json=template1_json
      gateway_TestCase.case_json=case_json
      suite = unittest.TestLoader().loadTestsFromTestCase(gateway_TestCase)
      unittest.TextTestRunner(verbosity=2).run(suite)

print 'finished.'

