from collections import defaultdict
from functools import partial
import logging
from time import time
from collections import defaultdict
try:
    import samplejson as json
except:
    import json

class result_formatter():
    def __init__(self, task, matches, crr, extra_info):
        # all task uuids has same matches result
        self.logger = logging.getLogger('mwtm_cache_formatter')
        self.template = {
                    "jsonrpc":"2.0",
                    "results":[],
                    "id":"null"
                }
        self.task = task
        self.matches = matches
        self.crr = crr
        self.extra_info = extra_info
        self.results = {}
        self.logger.info("site:%s, type%s", self.task.site_asset_id,
                                        type(self.task.site_asset_id))


    def serialize(self):
        '''
            :param meta_match {meta_uuid:[matches], meta_uuid2:[matches]}
        '''
        meta_match = defaultdict(list)
        for m in self.matches:
            meta_match[m["meta_uuid"]].append(m)

        matches_detail = {"matches":[], "task_id":""}
        for meta_uuid, matches in meta_match.iteritems():
            audio = {"segments":[]}.copy()
            video = {"segments":[]}.copy()
            if matches == []:
                continue
            media_type = matches[0]["media_type"]
            #get segments info
            for m in matches:
                if m["match_type"] == 'audio':
                    audio["segments"].append(dict(sample_offset=m["audio_sample_offset"],
                        ref_offset=m["audio_ref_offset"],duration=m["audio_duration"]))
                elif m["match_type"] == "video":
                    video["segments"].append(dict(sample_offset=m["video_sample_offset"],
                        ref_offset=m["video_ref_offset"],duration=m["video_duration"]))
                elif m["match_type"] == "both":
                    audio["segments"].append(dict(sample_offset=m["audio_sample_offset"],
                        ref_offset=m["audio_ref_offset"],duration=m["audio_duration"]))
                    video["segments"].append(dict(sample_offset=m["video_sample_offset"],
                        ref_offset=m["video_ref_offset"],duration=m["video_duration"]))
            matches_detail["matches"].append(dict(vobile_ref_id=meta_uuid, title=m["meta_name"],
                                                    type=media_type, audio=audio,
                                                    video=video))
        #TODO, add nofitication
        matches_detail["notifications"] = ""
        matches_detail["task_id"] = self.task.uuid
        matches_detail["extra_info"] = self.extra_info
        matches_detail["site_asset_ids"] = self.task.site_asset_id
        t = self.template.copy()
        t["results"].append( matches_detail)
        return t 

