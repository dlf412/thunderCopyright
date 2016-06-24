# the following for unit test
#this unittest for load_result_template as a dict data, then update
import os
import sys
import concurrent.futures


__filedir__ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, __filedir__ + '/../src/')
sys.path.insert(0, __filedir__ )
#path = os.path.dirname(__filedir__)


from worker import *

#this is unitest for parseinput and load_result_tp
if __name__ == "__main__":
    try:
        path = "/home/wu_guifeng/work/vddb/trunk/downloader"
#        logging.config.fileConfig('/'.join([path, 'downloader_log.conf']))
#        logger = logging.getLogger("download_worker")

        with concurrent.futures.ProcessPoolExecutor(1) as executor:
            with open("input_test1.json") as f:
                task_info = f.read()
                future = executor.submit(worker, task_info, path)
                worker(task_info, path)
    except Exception, reason:
        print 'error', reason


# test download_file, this time doesn't support timeout and other settings 
'''
if __name__ == "__main__":
    try:
        download_file("http://qd.cache.baidupcs.com/file/9fde0db5ed098f079dc8b36d34f0a5ea?xcode=bc9b8b287b524618520b60ef8da13535fb472fdda0f193f1&fid=2584621796-250528-894668746102053&time=1405070142&sign=FDTAXER-DCb740ccc5511e5e8fedcff06b081203-1zq2UfAIcmWt8gxOxJyuTdSzqzs%3D&to=sc,qc&fm=N,Q,U,c&sta_dx=2&sta_cs=11120&sta_ft=mp4&sta_ct=5&newver=1&expires=8h&rt=pr&r=742660034&logid=3124366643&vuk=2584621796", "./test/tianyu.mp4", 100)
    except Exception, reason:
        print 'error', reason
'''

# test far_gen and upload_file function
'''
if __name__ == "__main__":
    try:
        video_path = "/home/wu_guifeng/work/vddb/trunk/downloader/2.mp4"
        path = "/home/wu_guifeng/work/vddb/trunk/downloader/" + str(uuid.uuid1()) 
        far_path, dna_path, stats_path = path + '.far', path + '.dna' , path + '.stats'
        far_gen(video_path, far_path)
        generate_dna_stat(far_path, dna_path, stats_path)
        upload_file(dna_path)
        upload_file(stats_path)
    except Exception, reason:
        print 'error', reason
'''

'''
if __name__ == "__main__":
    result_data = load_result_tp()
    result_data["params"]["dna"]["hash"] = "aabbccddeedd"
    print result_data
    print type(result_data)
    result = json.dumps(result_data)
    print result
'''
