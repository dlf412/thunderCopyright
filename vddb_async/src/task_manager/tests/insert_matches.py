#! /usr/bin/python


import happybase
pool = happybase.ConnectionPool(1, host='localhost',port=9090)


from collections import defaultdict, namedtuple
import happybase


TaskContent = namedtuple('TaskContent', ['submit_at', 'from_reverse', 'site_asset_id',
                           'deadline', 'id', 'retries', 'account',
                           'uuid', 'created_at', 'format', 'priority', 'scope',
                           'queued_at', 'dna_url'])

matches=[{'video_score': 99, 'meta_uuid': '970ae0ba-773b-11e1-a7b2-080027cf46d6', 'video_sample_offset': 0, 'match_type': 'video', 'meta_name': 'Auto_Rule306_Movie', 'video_ref_offset': 0, 'audio_sample_offset': 0, 'audio_score': 0, 'audio_duration': 0, 'track_id': 0.0, 'instance_id': '9752d1cc-773b-11e1-a7b2-080027cf46d6', 'audio_ref_offset': 0, 'clip_duration': 307, 'media_type': 'video', 'video_duration': 307, 'instance_name': 'cappella.flv.xfp.0'}, {'video_score': 99, 'meta_uuid': '3f5b54da-15c5-11e1-9808-080027cf46d6', 'video_sample_offset': 0, 'match_type': 'video', 'meta_name': 'Auto_Rule307_Movie', 'video_ref_offset': 0, 'audio_sample_offset': 0, 'audio_score': 0, 'audio_duration': 0, 'track_id': 0.0, 'instance_id': '3f817b10-15c5-11e1-9808-080027cf46d6', 'audio_ref_offset': 0, 'clip_duration': 307, 'media_type': 'video', 'video_duration': 307, 'instance_name': 'cappella'}, {'video_score': 99, 'meta_uuid': '6ed1e476-df00-11e2-97f6-fa163e45e250', 'video_sample_offset': 0, 'match_type': 'video', 'meta_name': 'cappella.flv.xfp.merge', 'video_ref_offset': 0, 'audio_sample_offset': 0, 'audio_score': 0, 'audio_duration': 0, 'track_id': 0.0, 'instance_id': '6ed6d044-df00-11e2-97f6-fa163e45e250', 'audio_ref_offset': 0, 'clip_duration': 307, 'media_type': 'video', 'video_duration': 307, 'instance_name': 'cappella.flv.xfp.merge'}]

import uuid

task_uuid = str(uuid.uuid1())
task=TaskContent(submit_at=1401426654L, from_reverse='false', site_asset_id='a',
        deadline=1401606654L, id=1085942L, retries=10466, account=11,
        uuid=task_uuid, created_at=1401426654L, format='dna', priority=10, scope=[], queued_at=1401426654L, dna_url='dna_20131217/merge.dna')

print "task_uuid", task_uuid
hash_id = str(uuid.uuid1())
print "hash", hash_id

class match_saver():
    def __init__(self, task, matches):
        #self.logger = logging.getLogger('mwtm_matches_save')
        self.matches = matches
        self.task = task
        self.is_match = True if self.matches!=[] else False

    match_table = 'matches'
    match_data = {
         'meta_uuid':'m:meta_uuid',
         'video_score':'m:video_score',
         'audio_sample_offset':"m:audio_sample_offset",
         'audio_score':'m:audio_score',
         'audio_ref_offset':'m:audio_ref_offset',
         'video_sample_offset':'m:video_sample_offset',
         'match_type':'m:match_type',
         'meta_name':'m:meta_name',
         'video_ref_offset':'m:video_ref_offset',
         'audio_duration':'m:audio_duration',
         'track_id':'m:track_id',
         'instance_id':'m:instance_id',
         'video_duration':'m:video_duration',
         'instance_name':'m:instance_name',
         'media_type':'m:media_type',
         'clip_duration':'m:clip_duration',
         'meta_name':'m:meta_name',
     }

    unpush_table = "unpush"
    finish_table = "finished"
    sid_tid = "sid_tid"

    def save(self):
        #self.logger.debug("matches:%s, task:%s" % (self.matches, self.task))
        self.save_hbase()
        #self.save_redis()


    def save_hbase(self):
        self.save_sid_tid()
        self.save_crr()
        self.save_matches()
        self.save_finished()
        self.save_unpush()
        self.save_task_info()
        print "finished"

    def save_task_info(self):
        self.save_hbase_impl("task_info", task_uuid, {"t:site_asset_id":"['123', '124']",
                             "t:extra_info":"{'id':123}"})

    def save_crr(self):
        self.save_hbase_impl("crr", task_uuid, {"c:notification":"crr_test"})

    def save_sid_tid(self):
        self.save_hbase_impl("sid_tid", hash_id, {"t:task_uuid":task_uuid})

    def save_hbase_impl(self, table, key, value):
        with pool.connection() as conn:
            table = conn.table(table)
            table.put(key, value)

    def save_unpush(self):
        self.save_hbase_impl(match_saver.unpush_table, self.task.uuid,
                            {"u:is_match":str(self.is_match)})

    def save_finished(self):
        self.save_hbase_impl(match_saver.finish_table, self.task.uuid,
                            {"f:is_match":str(self.is_match),
                             "f:query_status":"success"})

    def save_matches(self):
        with pool.connection() as conn:
            table = conn.table(match_saver.match_table)
            batch = table.batch(transaction=True)
            n = 0
            for m in self.matches:
                value = {}
                for k, v in m.iteritems():
                    value[match_saver.match_data[k]]=str(m[k])
                row = "-".join([self.task.uuid, m['match_type'], str(n)])
                batch.put(row, value)
                n = n + 1
            batch.send()

    def save_redis(self):
        pass

#matches = []
m = match_saver(task, matches)
m.save()
