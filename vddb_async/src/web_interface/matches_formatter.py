#! /usr/bin/python

import logging
from collections import defaultdict

class matches_formatter():
    def __init__(self, tasks_count=1, filter_cids=None):
        self.logger = logging.getLogger('mwtm_matches_formatter')
        self.task = {"uuid":"", "site_asset_id":"", "extra_info":""}
        self.matches = []
        self.crr = ""
        self.filter_cids = filter_cids
        self.processing = False
        self.recognize = True
        self.extra_info = ""
        self.result = {
                    "jsonrpc":"2.0",
                    "result":{"tasks_count":tasks_count, "tasks":[]},
                    "id":"null"
        }

    def add_task(self, task, matches=[], crr="", extra_info="",
                 processing=False, recognize=True):
        legal_matches = []
        self.logger.debug("filter_cids:%s", self.filter_cids)
        if self.filter_cids:
            legal_matches = filter(lambda a:int(a.get('company_id',-1)) not in
                    self.filter_cids, matches)
        else:
            legal_matches = matches

        self.task = task
        self.matches = self._group_matches(legal_matches)
        self.crr = crr
        self.processing = processing
        self.recognize = recognize
        if task.has_key("extra_info"):
            self.extra_info = self.task["extra_info"]
        else:
            self.extra_info = extra_info
        self.logger.debug("task:%s, matches:%s, extra_info:%s",
                          self.task, self.matches, self.extra_info)
        self._format()

    def _group_matches(self, matches):
        '''
            group matches by meta_uuid
            some match info may have same meta_uuid
        '''
        t = defaultdict(list)
        for m in matches:
            t[m["meta_uuid"]].append(m)
        return t

    def _format(self):
        '''
            one task may match some meta, or match more than
            one segments in one meta
        '''
        task_matches = {"task_id":"", "matches":[], "status":2}
        for meta_uuid, matches in self.matches.iteritems():
            audio = {"segments":[]}.copy()
            video = {"segments":[]}.copy()
            media_type = matches[0]["media_type"]
            for m in matches:
                if m["match_type"] == 'audio':
                    audio["segments"].append(dict(sample_offset=m["audio_sample_offset"],
                        ref_offset=m["audio_ref_offset"],duration=m["audio_duration"]))
                elif m["match_type"] == "video":
                    video["segments"].append(dict(sample_offset=m["video_sample_offset"],
                        ref_offset = m["video_ref_offset"],duration=m["video_duration"]))
                elif m["match_type"] == "both":
                    audio["segments"].append(dict(sample_offset=m["audio_sample_offset"],
                        ref_offset = m["audio_ref_offset"],duration=m["audio_duration"]))
                    video["segments"].append(dict(sample_offset=m["video_sample_offset"],
                        ref_offset = m["video_ref_offset"],duration=m["video_duration"]))
            task_matches["matches"].append(dict(vobile_ref_id=meta_uuid,
                title=m["meta_name"], type=media_type, audio=audio, video=video))
        if self.recognize:
            if self.processing:
                task_matches["status"] = 3
            else:
                if task_matches["matches"] == []:
                    task_matches["status"] = 1
                else:
                    task_matches["status"] = 0
        else:
            task_matches["status"] = 2
        #TODO, add nofitication
        task_matches["notification"] = ""
        task_matches["task_id"] = self.task["uuid"]
        task_matches["extra_info"] = self.extra_info
        task_matches["site_asset_id"] = self.task["site_asset_id"]
        self.result["result"]["tasks"].append(task_matches)

