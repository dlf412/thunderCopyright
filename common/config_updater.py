#!/usr/bin/env python
#coding: utf-8

import json


def merge(mapping, global_cfg):
    '''
    mapping.json:
    =============
    [
        []                             , ["gateway"],
        ["log", "level"]               , ["general", "log", "log_level"],
        ["log", "file"]                , ["general", "log", "log_file"],
        ["query_broker", "zip", "type"], ["query_broker", "zip_extensions", 4],
        ["query_broker", "zip", "value1"], "abcdef",
        ["query_broker", "zip", "value2"], 4,
        ["query_broker", "zip", "value2"], {"abc": "def"}
    ]
    '''
    module_cfg = {}

    mapping_len = len(mapping)
    if mapping_len % 2 == 1:
        raise ValueError('Invalid mapping count: %d, which should be even number!' % mapping_len)

    def check_accessor(accessor):
        for k in accessor:
            if not isinstance(k, (str, unicode, int)):
                raise KeyError('Invalid key type (%r): %r' % (k, accessor))

    for i in range(0, mapping_len, 2):
        target_accessor, source_accessor = mapping[i], mapping[i+1]

        if isinstance(source_accessor, list):
            check_accessor(source_accessor)
            source = global_cfg
            for key in source_accessor:
                source = source[key]
        else:
            source = source_accessor

        check_accessor(target_accessor)
        target = module_cfg
        for i in range(len(target_accessor)):
            key = target_accessor[i]
            if i == len(target_accessor) - 1:
                target[key] = source
            else:
                key_next = target_accessor[i+1]
                try:
                    target[key]
                except (IndexError, KeyError):
                    target[key] = [] if isinstance(key_next, int) else {}
                target = target[key]

        if len(target_accessor) == 0:
            for k, v in source.iteritems():
                target[k] = v

    return module_cfg


def merge_file(mapping_file, global_cfg_file):
    with open(mapping_file, 'r') as f:
        mapping = json.load(f)
    with open(global_cfg_file, 'r') as f:
        global_cfg = json.load(f)
        
    return merge(mapping, global_cfg)


def diff_key_tree(cfg_a, cfg_b):
    if type(cfg_a) != type(cfg_b):
        print cfg_a, cfg_b
        return False
        
    elif isinstance(cfg_a, dict):
        for ka, va in cfg_a.iteritems():
            if ka not in cfg_b:
                print cfg_a.keys(), cfg_b.keys()
                return False
            same = diff_key_tree(va, cfg_b[ka])
            if not same:
                return False
    return True


def diff_key_tree_file(cfg_a_file, cfg_b_file):
    with open(cfg_a_file, 'r') as f:
        cfg_a = json.load(f)
    with open(cfg_b_file, 'r') as f:
        cfg_b = json.load(f)

    same = diff_key_tree(cfg_a, cfg_b) and diff_key_tree(cfg_b, cfg_a)
    return {'same': same}


if __name__ == '__main__':
    import sys
    
    USAGE = '''
    Usage:
    =====
      python %(prog)s merge [mapping-file] [global-config-file]
      python %(prog)s diff   [conf-file-A]  [config-file-B]
    ''' % {'prog': sys.argv[0]}

    func_dict = {'merge': merge_file, 'diff': diff_key_tree_file}
    try:
        action = sys.argv[1]
        if action not in func_dict:
            raise KeyError('Invalid action: %s' % action)
        func = func_dict.get(action)
        print json.dumps(func(*sys.argv[2:]), indent=4)
    except Exception as e:
        import traceback
        print >> sys.stderr, traceback.format_exc()
        print '-' * 68
        print USAGE
        sys.exit(-1)
