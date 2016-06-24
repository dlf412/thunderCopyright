#!/usr/bin/python


ERR_INPUT = 121500
ERR_JSON = 121501
ERR_FAR = 121502
ERR_UPLOAD = 121503
ERR_ECF = 121504
ERR_OS = 121505
ERR_PARSE = 121506
ERR_FILESIZE = 121507
ERR_UNSUPPORTED_DOWNLOAD = 121508
ERR_DOWNLOAD = 121509
ERR_UNKNOW = 121510
ERR_FILTER_PASS = 121511
ERR_INVALID_TORRENT = 121512
# add at 1.2.0.0 version
ERR_OFFLINE_TIMEOUT = 121521
# add at 1.2.0.1b version
ERR_OFFLINE_HTTP = 121522
ERR_OFFLINE_GENURL = 121523

SUCCESS = 0

DOWNLOAD_FIN = 1

class dt_error (Exception):
    def __init__ (self, code, msg):
        self._code = code
        self._msg = msg

    def code (self):
        return self._code

    def msg (self):
        return self._msg

    def __str__ (self):
        return repr (self._msg)

class dt_fin (Exception):
    def __init__ (self, code, msg):
        self._code = code
        self._msg = msg

    def code (self):
        return self._code

    def msg (self):
        return self._msg

    def __str__ (self):
        return repr (self._msg)
