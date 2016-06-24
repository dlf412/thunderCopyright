import os
import base64
import json
import hashlib


class Hash(object):

    u"""
    ::Reference: http://seals.vobile.cn/trac/vdna/wiki/vobile_thunder/thunder_hash

    Usage:
    ======
        >>> print Hash(url="http://www.baidu.com/dl/some.mp4").value
        76709133b1bcd884611186bdefcdbe2e235ef104
        >>> print Hash(url="http://www.baidu.com/dl/some.mp4").protocol
        http

        >>> print Hash(filename="some.torrent", content="TEST_SEED_FILE_CONTENT").value
        fda6c4d1938082c32afea756bdaf1e031349c23a
    """

    def __init__(self, url=None, content=None, filename=None):
        if url is None and (filename is None or content is None):
            logger.error(trans2json('URL or filename/content required!'))
            raise ValueError('URL or filename/content required!')

        if url:
            self.arg = url
            self.prefix = 'url_hash'
            self.protocol = url.split('://', 1)[0].lower()
        else:
            self.arg = content
            self.prefix = 'seed_hash'
            self.protocol = filename.rsplit('.', 1)[-1].lower()

        # self.protocol = url.split('://', 1)[0].lower() if url else filename.rsplit('.', 1)[-1].lower()
        # self.prefix = 'url_hash' if url else 'seed_hash'
        self.url = url
        self.filename = filename
        self.content = content

    @property
    def value(self):
        u""" Cached property """

        if hasattr(self, '_value'):
            return self._value

        hash_type_dict = {
            'ftp': Hash.sha1_hex,
            'http': Hash.sha1_hex,
            'ed2k': Hash.hash_ed2k,
            'magnet': Hash.hash_magnet,
            'torrent': Hash.hash_bt,
        }
        func = hash_type_dict.get(self.protocol.lower(), Hash.sha1_hex)
        self._value = '%s#%s' % (self.prefix, func(self.arg))
        return self._value

    @staticmethod
    def sha1_hex(s):
        if type(s) == unicode:
            s = s.encode('utf-8')
        return hashlib.sha1(s).hexdigest()

    @staticmethod
    def hash_bt(b64_content):
        u"""  !!! *tmp* !!! """
        return Hash.sha1_hex(b64_content)

    @staticmethod
    def hash_ed2k(uri):
        return uri.split('|')[4]

    @staticmethod
    def hash_thunder(uri):
        '''
        thunder uri decoded format: "AA" + origin_url + "ZZ"
        '''
        uri = uri.strip('/')
        t_hash = uri[len("thunder://"):]
        origin_uri = base64.b64decode(t_hash)[2:-2]
        return Hash.sha1_hex(origin_uri)

    @staticmethod
    def hash_magnet(uri):
        u"""  !!! *tmp* !!! """
        return Hash.sha1_hex(uri)
