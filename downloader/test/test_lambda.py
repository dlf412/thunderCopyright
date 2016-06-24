import json

key_data = lambda info_data, key: info_data[key] if info_data.has_key(key) else None
keys_data = lambda info_data, key1, key2: info_data[key1][key2] if key_data(info_data, key1) is not None and key_data(key_data(info_data, key1), key2) is not None else None

with open("../input.json") as f:
    data = json.loads(f.read())['params']
    thunder_hash = key_data(data, 'thunder_hash')
    print thunder_hash
    url_hash = keys_data(data, 'url', 'hash1')
    print url_hash


