from server import server, catch_and_die, cluster
from tm_sqls import *
from task_stat import *

from db_txn import db_execute, db_query, db_result, db_txn

from collections import defaultdict
from functools import partial
import logging
from time import time
from datetime import datetime
from collections import defaultdict
try:
    import samplejson as json
except:
    import json
from logger import g_logger
from utils import trans2json

import requests
from requests import RequestException
from stats import stats, QUERY_FAILED, QUERY_SUCCESS

class SendMatchesError(Exception): pass

class cleaner_cluster(cluster):
    def __init__(self, config, db_pool, hbase_pool, clean_cond, manage_cond):
        cleaner_nums = int(config['cleaner_threads_num'])
        super(cleaner_cluster, self).__init__(cleaner, cleaner_nums,
                                              clean_cond, manage_cond)

        self.backoff = int(config['retry_backoff'])
        self.powlim = int(config['max_backoff_power'])
        # backend codes to retry
        # CONFIRM: we're not retrying with other codes
        codes = []
        if config['retry_forever_list'] != '':
            codes += [int(c) for c in config['retry_forever_list'].split(',')]
        if config['retry_sometime_list'] != '':
            codes += [int(c) for c in config['retry_sometime_list'].split(',')]
        self.backend_retry = set(codes)
        # thresholds
        self.thresholds = defaultdict(lambda: {})
        self.thresholds['audio']['score'] = int(config["fp_audio_score"])
        self.thresholds['video']['score'] = int(config["fp_video_score"])
        self.thresholds['audio']['duration'] = int(config["fp_audio_duration"])
        self.thresholds['video']['duration'] = int(config["fp_video_duration"])
        self.matches_server = config['matches_server']

        self.pool = db_pool
        self.hbase_pool = hbase_pool


class cleaner(cluster.member):
    def __init__(self, owner):
        super(cleaner, self).__init__(owner)

    def do_doom(self, t, code, queue_at, deadline):
        logger = logging.getLogger('mwtm_cleaner')
        if queue_at != None and (deadline == None or deadline == 0 or \
                                 deadline > queue_at):
            logger.debug('to retry task %s, queue at %s', t.uuid, queue_at)
            yield db_execute(RETRY_TASK, queue_at, code, t.id)
            #yield db_execute(RENEW_EVENT, t.uuid, 'retry')
            g_logger.info(trans2json(message="task_uuid:%s, "
                          "site_asset_id:%s, deadline:%s, external_id:%s " % (t.uuid,
                          t.site_asset_id, deadline, t.external_id),
                          action="retry task"))
        else:
            logger.debug('to fail task %s', t.uuid)
            g_logger.info(trans2json(message="task_uuid:%s, "
                          "site_asset_id:%s, external_id:%s" % (t.uuid,
                          t.site_asset_id, t.external_id), action="to fail task"))
            rc, _ = yield db_query(CHECK_TASK, t.id)
            if rc <= 0:
                yield db_execute(FAIL_TASK, code, t.id)
                self.send_matches(t, unrecognized=True)
                task_status = db_txn(self.pool, partial(self.load_task_status, t.uuid))
                self.update_hbase_task(task_status)
            stats.incr(QUERY_FAILED, 1)

    @staticmethod
    def update_task(t, code, mc, tr):
        # NOTE: status is always query success here
        if t.from_reverse and mc > 0:
            yield db_execute(FINISH_TASK, 'match', 1000, t.id)
        else:
            yield db_execute(FINISH_TASK, tr, code, t.id)

    def update_hbase_task(self, task):
        billing_time = datetime.utcnow().strftime('%Y%m%dT%H%M%S') \
                if task.billing_time is None \
                else task.billing_time.strftime('%Y%m%dT%H%M%S')
        queued_at = '0' \
                if task.queued_at is None \
                else task.queued_at.strftime('%Y%m%dT%H%M%S')
        end_query_time = datetime.utcnow().strftime('%Y%m%dT%H%M%S') \
                if task.end_query_time is None \
                else task.end_query_time.strftime('%Y%m%dT%H%M%S')
        self.save_hbase("task", task.uuid,
                        {
                            "s:queued_at":queued_at,
                            "s:status":task.status,
                            "s:query_count":str(task.query_count),
                            "s:billing_time":billing_time,
                            "s:error_code":str(task.error_code),
                            "s:task_result":str(task.task_result),
                            "s:start_query_time":task.start_query_time.strftime('%Y%m%dT%H%M%S'),
                            "s:end_query_time":end_query_time,
                            "i:external_id":str(task.external_id),
                            "i:company_id":str(task.company_id),
                            "i:task_priority":str(task.task_priority),
                            "i:user_id":str(task.user_id),
                            "i:clip_duration":str(task.clip_duration),
                            "i:clip_format":str(task.clip_url),
                            "i:dna_type":str(task.dna_type),
                            "i:query_level":str(task.query_level),
                            "i:is_indexed":str(task.is_indexed),
                            "i:is_requery":str(task.is_requery),
                            "i:result_revision":str(task.result_revision),
                            "i:userClientInfo_id":str(task.userClientInfo_id),
                            "i:created_at":task.created_at.strftime('%Y%m%dT%H%M%S'),
                            "i:compressed_file_size":str(task.compressed_file_size),
                            "i:processed_file_size":str(task.processed_file_size),
                            "i:dna_url":str(task.dna_url)
                        }
                       )

    def save_hbase(self, table, key, value):
        with self.hbase_pool.connection() as conn:
            table = conn.table(table)
            table.put(key, value)

    def read_hbase(self, table, row, columns=None):
        with self.hbase_pool.connection() as conn:
            table = conn.table(table)
            return table.row(row, columns)

    def filter_matches(self, matches):
        ms = []
        for m in matches:
            keep = True
            if not 'meta_uuid' in m or m['meta_uuid'] == '':
                # bad match
                self.logger.debug('dropping match with no meta uuid')
                keep = False
            elif not 'meta_name' in m:
                m['meta_name'] = ''
            elif not 'match_type' in m or \
               not m['match_type'] in ('both', 'video', 'audio'):
                # bad match
                self.logger.debug('dropping match with invalid match type',
                                  m['match_type'])
                keep = False
            else:
                mt = m['match_type']
                for typ in ('video', 'audio'):
                    for f in ('duration', 'score', 'ref_offset', \
                              'sample_offset'):
                        if not (typ + '_' + f) in m:
                            if typ != mt and mt != 'both':
                                m[typ + '_' + f] = 0
                            else:
                                # bad match
                                self.logger.debug('dropping match with ' +
                                                  'missing field %s, type %s',
                                                  typ + '_' + f, mt)
                                keep = False

            if m['match_type'] in ('both', 'video'):
                if m['video_score'] <= self.thresholds['video']['score'] or \
                   m['video_duration'] <= self.thresholds['video']['duration']:
                    keep = False
            if m['match_type'] in ('both', 'audio'):
                if m['audio_score'] <= self.thresholds['audio']['score'] or \
                   m['audio_duration'] <= self.thresholds['audio']['duration']:
                    keep = False
            if keep:
                ms.append(m)
        return ms

    @staticmethod
    def store_crr(t, crr):
        # record crr
        if crr != None and crr != '':
            crr = crr.encode('utf8')
            yield db_execute(STORE_CRR, t.uuid, crr, crr)

    @staticmethod
    def store_matches(t, matches):
        for m in matches:
            c, _ = yield db_execute(STORE_MATCH, t.account, m['meta_uuid'],
                                    t.uuid, t.created_at, t.site_asset_id,
                                    m['match_type'], m['video_duration'],
                                    m['video_score'], m['video_sample_offset'],
                                    m['video_ref_offset'], m['audio_duration'],
                                    m['audio_score'], m['audio_sample_offset'],
                                    m['audio_ref_offset'], 'auto_match',
                                    0, t.account, m['match_type'],
                                    m['video_duration'], m['video_score'],
                                    m['video_sample_offset'],
                                    m['video_ref_offset'], m['audio_duration'],
                                    m['audio_score'], m['audio_sample_offset'],
                                    m['audio_ref_offset'], 'auto_match',
                                    0)
            if c > 0:
                # match stored, add meta if not existing
                yield db_execute(ADD_CONTENT, m['meta_uuid'],
                                 m['meta_name'].encode('utf8'))

    @staticmethod
    def record_finish(t, row, code, matches):
        yield db_execute(UPDATE_QUERY, t.uuid, code, matches, row)

    @staticmethod
    def check_matches(t):
        # check for previous matches
        rc, rs = yield db_query(CHECK_MATCHES, t.uuid)
        yield db_result(rc > 0 and rs[0][0] > 1)

    @staticmethod
    def load_task_status(uuid):
        rc, rs = yield db_query(LOAD_TASK_STATUS, uuid)
        yield db_result(rs[0])

    def doom(self, t, code, p, res):
        self.logger.error("to doom task, task_uuid: %s, site_asset_id: %s, "
                          "code: %s, res: %s" % (t.uuid, t.site_asset_id, code, res))
        retry = True
        if code == 0:
            retry = res.code > 0 or (res.code == 0 and \
                                     # backend code == 0 -> finish failed
                                     # query itself can succeed, so retry
                                     (res.backend_code == 0 or \
                                      res.backend_code in self.backend_retry))
        elif code == OPS_KILLED:
            retry = False

        queue_at = None
        if retry and p.retry != 'false':
            power = t.retries if t.retries <= self.powlim else self.powlim
            # NOTE: time() only returns utc timestamp on linux/posix
            queue_at = time() + 2 ** power * self.backoff

        try:
            db_txn(self.pool, partial(self.do_doom, t, code, queue_at,
                                      t.deadline))
        except:
            self.logger.error('failed to doom task:%s, site_asset_id: %s' % (t.uuid,
                              t.site_asset_id), exc_info=True)

    def finish(self, t, p, res):
        self.logger.info('to finish task, task_uuid:%s, site_asset_id:%s',
                         t.uuid, t.site_asset_id)
        self.logger.debug("res:%s " % str(res))
        assert res.matches != None
        code = WITHOUT_MATCH if len(res.matches) == 0 else WITH_MATCH
        if code == WITHOUT_MATCH:
            try:
                if db_txn(self.pool, partial(self.check_matches, t)):
                    code = WITH_MATCH
            except:
                pass

        tr = 'match' if code == WITH_MATCH else 'no_match'
        self.logger.debug('record finished task %s, site_asset_id: %s',
                          t.uuid, t.site_asset_id)
        try:
            ms = self.filter_matches(res.matches)
            for m in ms:
                g_logger.info(trans2json(message="company_id:%s, "
                "meta_uuid:%s, instance_uuid:%s, vddb_company_id:%s" % (t.account, m['meta_uuid'],
                              m['instance_id'], m['company_id']),
                              action='matches info'))
            mc = len(ms)
            #m = match_saver(self.hbase_pool, self.redis_conn, task_status, ms, res.crr)
            #m.save()
            self.send_matches(t, ms, res.crr)
            task_status = db_txn(self.pool, partial(self.load_task_status, t.uuid))
            self.update_hbase_task(task_status)
            db_txn(self.pool, partial(self.update_task, t, code, mc, tr))
        except:
            self.logger.error('failed to finish task: %s, site_asset_id: %s' %
                              (t.uuid, t.site_asset_id), exc_info=True)
            # dooming may succeed, as it touches fewer tables
            self.doom(t, INTERNAL, p, res)
            return
        g_logger.info(trans2json(message="site_asset_id:%s, "
                      "task_uuid:%s, external_id:%s" % (t.site_asset_id, t.uuid,
                      t.external_id), action="task query complete"))
        stats.incr(QUERY_SUCCESS, 1)

    def send_matches(self, task, matches=[], crr="", unrecognized=False):
        match_type = "no_match"
        if unrecognized:
            match_type = "unrecognized"
        elif len(matches):
            match_type = 'match'
        data = dict(id="null", jsonrpc="2.0",
                    method="matches",
                    params=dict(matches=matches,
                    site_asset_id=eval(task.site_asset_id), notification=crr,
                    match_type=match_type))
        params = dict(source="auto_match")
        req = None
        try:
            req = requests.post(self.matches_server, params=params,
                                data=json.dumps(data))
            if req.status_code != 200:
                self.logger.error("send matches failed, code:%s", req.status_code)
                raise SendMatchesError("send matches faild, task_id:%s" % task.uuid)
        except RequestException:
            self.logger.error("send matches failed, %s", task.uuid, exc_info=True)
            raise SendMatchesError("send matches faild")
        self.logger.info("send matches success, task_uuid:%s, site_asset_id:%s,"
                         "external_id:%s", task.uuid, task.site_asset_id,
                         task.external_id)
        g_logger.info(trans2json(message="task_uuid:%s, "
                      "site_asset_id:%s, external_id:%s " % \
                      (task.uuid, task.site_asset_id,
                       task.external_id), action="send matches success"))

    @catch_and_die('mwtm_cleaner')
    def run(self):
        while True:
            self.loop()

    def task_failed(self, res):
        return (res == None or res.code == None or res.backend_code == None or
                res.code != 0 or res.backend_code != 0 or res.matches == None)

    def loop(self):
        reqs = self.requests(True)
        accs = self.accounts()
        for (t, code, res) in reqs:
            if not t.account in accs:
                continue

            self.logger.info('receive task from manager, task_uuid:%s, site_asset_id:%s',
                             t.uuid, t.site_asset_id)

            if code != 0 or self.task_failed(res):
                if code == 0:
                    code = INTERNAL
                self.doom(t, code, accs[t.account], res)
            else:
                self.finish(t, accs[t.account], res)
