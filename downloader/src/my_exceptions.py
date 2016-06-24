#!/usr/bin/python
#!encoding:utf-8

from const import OFFLINE_HTTP_ERROR, OFFLINE_GENURL_ERROR, OFFLINE_STATUS_ERROR, \
    OFFLINE_UNKNOWN_ERROR, OFFLINE_DOWNLOAD_ERROR, OFFLINE_TIMEOUT

class MyException(Exception): pass

class HttpError(MyException):

    def __init__(self, message):
        super(HttpError, self).__init__(message)
        self.errors = OFFLINE_HTTP_ERROR


class PollTimeout(MyException):

    def __init__(self, message):
        super(PollTimeout, self).__init__(message)
        self.errors = OFFLINE_TIMEOUT


class StatusError(MyException):

    def __init__(self, message):
        super(StatusError, self).__init__(message)
        self.errors = OFFLINE_STATUS_ERROR


class DownloadError(MyException):

    def __init__(self, message):
        super(DownloadError, self).__init__(message)
        self.errors = OFFLINE_DOWNLOAD_ERROR


class GenUrlError(MyException):

    def __init__(self, message):
        super(GenUrlError, self).__init__(message)
        self.errors = OFFLINE_GENURL_ERROR


class UnknownError(MyException):

    def __init__(self, message):
        super(UnknownError, self).__init__(message)
        self.errors = OFFLINE_UNKNOWN_ERROR
