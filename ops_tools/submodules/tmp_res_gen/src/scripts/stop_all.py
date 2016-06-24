#!/usr/bin/env python
#coding: utf-8


import os
import signal
import commands

cmd = 'ps aux | grep worker.yaml'
output = commands.getoutput(cmd)
for line in output.splitlines():
    pid = int(line.split()[1])
    try:
        os.kill(pid, signal.SIGKILL)
    except OSError:
        pass

output = commands.getoutput(cmd)
print output
