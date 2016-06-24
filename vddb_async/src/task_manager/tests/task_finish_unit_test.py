'''
Created on Aug 28, 2013

@author: hpp
'''
import unittest
from task_finish import TaskTerminator
from xml.etree import ElementTree


class match_result_t(object):
    '''
    a match result struct
    this is for testing
    '''
    meta_uuid = None
    meta_name = None
    instance_name = None
    instance_id = None
    match_type = None
    track_id = None
    video_duration = None
    audio_duration = None
    video_likelihood = None
    audio_likelihood = None
    video_ref_offset = None
    audio_ref_offset = None
    video_sample_offset = None
    audio_sample_offset = None

    def __init__(self, video_duration=None, audio_duration=None,
                 meta_uuid=None):
        self.video_duration = video_duration
        self.audio_duration = audio_duration
        self.meta_uuid = meta_uuid


class fp_thres_t(object):
    '''
        fp thres struct
    '''
    audio_score = None
    audio_duration = None
    video_score = None
    video_duration = None


class Test(unittest.TestCase):
    '''
        a test
    '''
    def test_fp_thres_t(self):
        fp = fp_thres_t()
        fp.audio_duration = 0
        fp.audio_score = 1
        fp.video_duration = 2
        fp.video_score = 3
        _fp = fp
        assert(_fp.audio_duration == 0)
        assert(_fp.audio_score == 1)
        assert(_fp.video_duration == 2)
        assert(_fp.video_score == 3)

    def test_filter_match_list_first_three_logic(self):
        ms = {}
        ms['08e35d26-abca-11e1-b804-080027b5f79a'] = (match_result_t(
                        meta_uuid='08e35d26-abca-11e1-b804-080027b5f79a',
                        video_duration=1, audio_duration=0))
        ms['08e35d26-abca-11e1-b804-080027b5f79b'] = (match_result_t(
                        meta_uuid='08e35d26-abca-11e1-b804-080027b5f79a',
                        video_duration=0, audio_duration=1))
        ms['08e35d26-abca-11e1-b804-080027b5f79c'] = (match_result_t(
                        meta_uuid='08e35d26-abca-11e1-b804-080027b5f79a',
                        video_duration=1, audio_duration=1))

        tt = TaskTerminator()
        fm1 = tt.filter_match_list(False, True, True, True, ms)
        for fm in fm1.items():
            assert(not (fm[1].video_duration > 0
                        and fm[1].audio_duration == 0))
        fm2 = tt.filter_match_list(True, False, True, True, ms)
        for fm in fm2.items():
            assert(not (fm[1].video_duration == 0
                        and fm[1].audio_duration > 0))
        fm3 = tt.filter_match_list(True, True, False, True, ms)
        for fm in fm3.items():
            assert(not (fm[1].video_duration > 0 and fm[1].audio_duration > 0))

    def test_filter_match_list_last_logic(self):
        ms = {}
        ms['08e35d26-abca-11e1-b804-080027b5f79a'] = (match_result_t(
                        meta_uuid='08e35d26-abca-11e1-b804-080027b5f79a',
                        video_duration=2, audio_duration=3))
        ms['08e35d26-abca-11e1-b804-080027b5f79b'] = (match_result_t(
                        meta_uuid='08e35d26-abca-11e1-b804-080027b5f79a',
                        video_duration=1, audio_duration=3))
        ms['08e35d26-abca-11e1-b804-080027b5f79c'] = (match_result_t(
                        meta_uuid='08e35d26-abca-11e1-b804-080027b5f79a',
                        video_duration=5, audio_duration=9))

        tt = TaskTerminator()
        fm1 = tt.filter_match_list(True, True, True, False, ms)

        for fm in fm1.items():
            assert(fm[1].video_duration == 5 and fm[1].audio_duration == 9)

    def test_sync_crr_with_match_list(self):
        ms = {}
        ms['08e35d26-abca-11e1-b804-080027b5f79a'] = (match_result_t(
                        meta_uuid='08e35d26-abca-11e1-b804-080027b5f79a',
                        video_duration=2, audio_duration=3))
        ms['08e35d26-abca-11e1-b804-080027b5f79b'] = (match_result_t(
                        meta_uuid='08e35d26-abca-11e1-b804-080027b5f79a',
                        video_duration=1, audio_duration=3))
        ms['08e35d26-abca-11e1-b804-080027b5f79c'] = (match_result_t(
                        meta_uuid='08e35d26-abca-11e1-b804-080027b5f79a',
                        video_duration=5, audio_duration=9))

        tt = TaskTerminator()
        notifications = file('task_finish_test.xml').read()

        crr = tt.sync_crr_with_match_list(ms, notifications)
        flag = False
        root = ElementTree.fromstring(crr)
        for n in root:
            ast = n.find('Asset')
            if ast == None:
                flag = True
                continue
            oastid = ast.find('OriginalAssetID')
            if oastid == None:
                continue
            uuid = oastid.text
            assert(uuid == '08e35d26-abca-11e1-b804-080027b5f79b')
        assert(flag == True)

if __name__ == "__main__":
    import sys
    sys.argv = ['', 'Test.test_fp_thres_t',
                'Test.test_filter_match_list_last_logic',
                'Test.test_sync_crr_with_match_list']
    unittest.main()
