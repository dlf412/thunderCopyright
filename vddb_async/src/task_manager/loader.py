from server import catch_and_die
from tm_sqls import *

from db_txn import db_query, db_result, db_txn

from collections import defaultdict, namedtuple
from functools import partial
import logging
from time import sleep


def do_load(logger):
    # there are 2 things to load from db: account and backends
    # accounts also point to backends associated with them
    # accounts also have rules about filtering matches
    c, rs = yield db_query(LOAD_ACCOUNTS)
    _, rs2 = yield db_query(ACCOUNT_BACKENDS)
    _, rs3 = yield db_query(LOAD_RULES)

    acc_backs = defaultdict(lambda: [])
    for r in rs2:               # associate backends with accounts
        acc_backs[r.account].append(r)
    acc_rules = defaultdict(lambda: set())
    for r in rs3:               # parse rules, and collect into dict
        if r.k == 'VIDEO_ONLY' and r.value == '0':
            acc_rules[r.account].add('drop-video')
        elif r.k == 'AUDIO_ONLY' and r.value == '0':
            acc_rules[r.account].add('drop-audio')
        elif r.k == 'AUDIO_VIDEO_ONLY' and r.value == '0':
            acc_rules[r.account].add('drop-both')
        elif r.k == 'ONLY_THE_BEST_RESULT' and r.value == '1':
            # r.value is compared with 0 here, because the rule is the reverse
            # of the key
            acc_rules[r.account].add('best-match')

    _, rs4 = yield db_query(LOAD_BACKENDS)
    backends = {}
    for r in rs4:
        backends[r.id] = r

    accounts = {}
    if c > 0:
        a = namedtuple('_', rs[0]._fields + ('backends', 'rules'))
    for r in rs:
        good = True
        for be in acc_backs[r.id]:
            if not be.backend in backends:
                logger.error('backend %s not found for working account %s',
                             be.backend, r.id)
                good = False
                break
        if r.user_deleted == 'true':
            logger.error('backend user \'%s\' deleted for working account %s',
                         r.backend_user, r.id)
            good = False
        if r.hot == 'true' and r.hot_user_deleted == 'true':
            logger.error('hot backend user \'%s\' deleted for working ' +
                         'account %s', r.hot_user, r.id)
            good = False
        if r.hot == 'true' and r.hot_user == None:
            logger.error('hot backend user not set for account with hot query ' +
                         'enabled %s', r.id)
            good = False
        if good:
            accounts[r.id] = a(*(list(r) + [acc_backs[r.id], acc_rules[r.id]]))

    yield db_result(accounts, backends)

@catch_and_die('mwtm_loader')
def load_database(config, pool, lev, observers):
    logger = logging.getLogger('mwtm_loader')
    acc_ids = set()
    be_ids = set()
    while True:
        logger.info('to load system config from database')
        try:
            accounts, backends = db_txn(pool, partial(do_load, logger))
        except:
            logger.error('failed to load system config from database',
                         exc_info=True)
        else:
            # make sure all settings are not null
            # use default in config if necessary
            accs = {}
            for a, p in accounts.iteritems():
                p_ = p._asdict()
                # sanity check, some settings are new and not on web page,
                # so they may be missing
                if p.max_conc == None:
                    logger.warning('bad setting for account %s, ' +
                                  'max_query_thread_num is null', a)
                    p_['max_conc'] = int(config['default_max_query_thread_num'])
                if p.min_conc == None:
                    logger.warning('bad setting for account %s, ' +
                                  'min_query_thread_num is null', a)
                    p_['min_conc'] = int(config['default_min_query_thread_num'])
                if p_['min_conc'] > p_['max_conc']:
                    logger.warning('bad setting for account %s, ' +
                                   'min_query_thread_num %s is greater than ' +
                                   'max_query_thread_num %s, using max as min',
                                   a, p_['min_conc'], p_['max_conc'])
                    p_['min_conc'] = p_['max_conc']
                if p.max_buf == None or p.max_buf == 0:
                    logger.warning('bad setting for account %s, ' +
                                  'max_pending_queue_size is null/0', a)
                    p_['max_buf'] = int(config['default_max_pending_queue_size'])
                if p.min_buf == None or p.min_buf == 0:
                    logger.warning('bad setting for account %s, ' +
                                  'min_pending_queue_size is null/0', a)
                    p_['min_buf'] = int(config['default_min_pending_queue_size'])
                if p.slicing == 'true' and p.slice_duration == None or \
                   p.slice_duration == 0:
                    logger.warning('bad setting for account %s, '
                                   'slice_duration is null/0, turning off ' +
                                   'slice for account', a)
                    p_['slicing'] = 'false'
                accs[a] = p.__class__(**p_)

            nacc_ids = set(accs.iterkeys())
            deled = acc_ids - nacc_ids
            if len(deled) != 0:
                logger.info('newly deleted accounts: %s', list(deled))
            added = nacc_ids - acc_ids
            if len(added) != 0:
                logger.info('newly added accounts: %s', list(added))
            acc_ids = nacc_ids

            nbe_ids = set(backends.iterkeys())
            deled = be_ids - nbe_ids
            if len(deled) != 0:
                logger.info('newly deleted backends: %s', list(deled))
            added = nbe_ids - be_ids
            if len(added) != 0:
                logger.info('newly added backends: %s', list(added))
            be_ids = nbe_ids

            for o in observers:
                o.update_accounts(accs)
                o.update_backends(backends)

            lev.set()
        sleep(int(config['ck_db_interval']))
