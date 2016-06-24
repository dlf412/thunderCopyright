#!/usr/bin/python
import json
import httplib
import logging
from httplib import HTTPException


class AuthError(Exception):pass
class GetMetaError(Exception):pass

class meta(object):

    def __init__(self, host, port, user, password, meta_uuid):
        self.host = host
        self.port = int(port)
        self.user = user
        self.password = password
        self.meta_uuid = meta_uuid
        self.conn = httplib.HTTPSConnection(self.host, self.port)
        self.logger = logging.getLogger("mw_" + self.__class__.__name__)

    def auth(self):
        request = {"protocols":["5.1"], "user":self.user,
                   "password":self.password}
        self.conn.request ('POST', '/mediawise/auth', json.dumps(request))
        response = self.conn.getresponse()
        response.read()
        if response.status == 200:
            return response.getheader('set-cookie')
        else:
            raise AuthError("host:%s, port:%s, user:%s, password:%s" %
                    (self.host, self.port, self.user, self.password))

    def get(self):
        token = self.auth()
        header =  {'Content-type':'application/x-www-form-urlencoded',
                   'Cookie':token}
        self.conn.request("GET", '/mediawise/contents/%s/meta' %
                          self.meta_uuid, None, header)
        response = self.conn.getresponse()
        results = response.read()
        if response.status == 200:
            results = json.loads(results)
            return results["body"][0]
        elif response.status == 404:
            try:
                json.loads(results)
            except:
                raise GetMetaError("get meta info failed, address:%s, port:%s, "
                                   "username:%s, password:%s, code:%s, msg:%s"
                                   % (self.host, self.port, self.user,
                                      self.password, response.status, results))
            return {}
        else:
            raise GetMetaError("get meta info failed, address:%s, port:%s, "
                               "username:%s, password:%s, code:%s, msg:%s"
                               % (self.host, self.port, self.user,
                                  self.password, response.status, results))


if __name__ == '__main__':
    m = meta("192.168.3.68", 443, "admin", "admin123",
            "7f0f1e26-3346-11e4-b2f8-0800272cb2e1")
    print m.get()
