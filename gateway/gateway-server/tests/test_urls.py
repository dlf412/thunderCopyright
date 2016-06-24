import hashlib
import requests


def query(url):
    digest = hashlib.sha1(url.strip()).hexdigest()
    params = {
        "digest" : digest,
        "digest-algorithm" : "sha1",
        "key" : "this-is-TMP-apikey",
    }
    headers = {
        "X-Client-ID": "test-client-id",
        "X-File-Name": "somefile.flv",
        "X-File-Size" : 234,
        "X-URL" : url,
    }
    resp = requests.get(GATEWAY_URL, params=params, headers=headers)
    print resp.status_code
    print '-' * 10
    print resp.headers
    print '-' * 10
    print resp.text
    print '=' * 60


GATEWAY_URL = 'http://127.0.0.1:8080/identified'

for url in ('http://182.92.9.187:88/sample/cappella.flv'):
    query(url)
