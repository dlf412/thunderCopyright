#!/usr/bin/python
#!encoding:utf-8

import time
from hashlib import md5, sha512
import base64
import struct
import numpy

from const import MID, THRESHOLD, THRESHOLD, SRCID, \
    VERNO, UI, PK, AK, SK, UI, PK, AK, FID_DECODED_LEN, FID_LEN


def hex_string(to_hex):
    out = ""
    hex_digit = "0123456789ABCDEF"

    out_list = [hex_digit[(ord(c) >> 4) & 0x0F] + hex_digit[ord(c) & 0x0F]
                for c in to_hex]

    return ''.join(out_list)


def calc_tid(threshold, filesize):
    trailings = [chr(e) for e in [47, 13, 94, 118, 39, 71, 156, 59]]
    trailings = ''.join(trailings)
    vid = numpy.uint32(~threshold)
    lower_filesize = numpy.uint32(filesize & 0xFFFFFFFF)
    values = struct.pack("II", vid, lower_filesize) + trailings
    return md5(values).hexdigest().upper()


def parse_fid(fid):
    '''
    return thundermd5 and filesize
    '''
    if len(fid) != FID_LEN:
        raise RuntimeError('Parse fid error, reason: fid len is invaild')

    # replace '*' with '+', replace '-' with '/'
    fid = fid.replace('*', '+').replace('-', '/')
    fid_decoded = base64.b64decode(fid)
    if len(fid_decoded) < FID_DECODED_LEN:
        raise RuntimeError(
            'Parse fid error, reason: fid decoded len is invalid')

    filesize = struct.unpack_from('Q', fid_decoded, 20)[0]
    thundermd5 = hex_string(fid_decoded[28:])

    return thundermd5, filesize


def sha512_string(In):
    return hex_string(sha512(In).digest())


def calc_at(*args):
    access_token = '{0}{1}{2}{3}{4}{5}{6}{7}'.format(*args)
    sha512_output = sha512_string(access_token)
    return md5(args[0] + sha512_output).hexdigest().upper()


def gen_new_url(host, fid, ck, filename, max_speed):
    info = {}
    info['host'] = host
    info['filename'] = base64.b64encode(filename)
    info['fid'] = fid
    info['mid'] = MID
    info['threshold'] = THRESHOLD
    thundmd5, filesize = parse_fid(fid)
    info['tid'] = calc_tid(THRESHOLD, filesize)
    info['srcid'] = SRCID
    info['verno'] = VERNO
    info['g'] = thundmd5
    info['ui'] = UI
    info['s'] = filesize
    info['pk'] = PK
    info['ak'] = AK
    info['e'] = int(time.time()) + 36000
    info['ms'] = max_speed
    info['ck'] = ck
    info['at'] = calc_at(SK, UI, thundmd5, PK, AK, info['e'], max_speed, ck)
    '''http://host/filename?fid=xxx&mid=xxx&threshold=xxx&tid=xxx&srcid=xxx&verno=xxx&g=xxx&ui=xxx&s=xxx&pk=xxx&ak=xxx&e=xxx&ms=xxx&ci=xxx&ck=xxx&at=xxx'''

    url_format = "{host}/{filename}?fid={fid}&mid={mid}&threshold={threshold}&tid={tid}&\
srcid={srcid}&verno={verno}&g={g}&ui={ui}&s={s}&pk={pk}&ak={ak}&e={e}&ms={ms}&ck={ck}&at={at}"
    return url_format.format(**info)

if __name__ == '__main__':
    fid = "VLLBeyQeripnKphJA6LKIFOhYG0CnxqMTAAAAAD3xPd20/fDZTcuMhms4XcpQj++"
    thundermd5, filesize = parse_fid(fid)
    e = 1419404613
    max_speed = 4096000
    at = calc_at(SK, UI, thundermd5, PK, AK, e, "", max_speed, "")
    assert '14C14CCD70220933E4FA544A7EAA4C73' == at
