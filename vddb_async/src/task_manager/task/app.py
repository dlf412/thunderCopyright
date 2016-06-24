from __future__ import absolute_import
import os
import sys
from celery import Celery
from parse_config import parse_config

#app read config from celeryconfig in etc/celeryconfig.py
app = Celery('spawner', include=['task'])

app.config_from_object('celeryconfig')

if __name__ == '__main__':
    app.start()
