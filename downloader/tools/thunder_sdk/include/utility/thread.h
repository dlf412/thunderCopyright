#ifndef SD_THREAD_H_00138F8F2E70_200808231422
#define SD_THREAD_H_00138F8F2E70_200808231422

#ifdef __cplusplus
extern "C" 
{
#endif

#include "utility/define.h"

/* Very Simple Thread Crontrol */

typedef struct 
{
    _int32 _thread_idx;
    void *_user_param;
}THREADS_PARAM;

typedef enum 
{
    INIT = 0,
    RUNNING, 
    STOP, 
    STOPPING, 
    STOPPED,
} THREAD_STATUS;

#ifdef LINUX
#include<pthread.h>
#include <stddef.h>

typedef enum
{
	THREAD_RUNNING = 0, // �߳�������
	THREAD_SUSPENDING, // �߳̽�Ҫ����
	THREAD_SUSPENDED, // �߳��Ѿ�����
} THREAD_SUSPEND_FLAG;

typedef struct 
{
    pthread_mutex_t mutex;
    pthread_cond_t cond;
    THREAD_SUSPEND_FLAG flag;	// �Ƿ�֪ͨ�߳̽�������״̬,�̵߳�ǰ�Ĺ���״̬

	THREAD_SUSPEND_FLAG should_suspend_flag; // �߳�������Ӧ�õĹ���״̬��һ���flag��һ���ģ��йؼ���Ϣ��Ҫ����ʱ�����ܻ��flag��һ��
	void* p_critical_msg;
 }SUSPEND_DATA;

#endif


#define THREAD_IDX(arglist) (((THREADS_PARAM*)(arglist))->_thread_idx)
#define USER_PARAM(arglist) (((THREADS_PARAM*)(arglist))->_user_param)

#define RUN_THREAD(status)	((status) = RUNNING)
#define IS_THREAD_RUN(status) ((status) == RUNNING)

#define STOP_THREAD(status)	((status) = STOP)
#define BEGIN_STOP(status) ((status) = STOPPING)

_int32 finished_thread(THREAD_STATUS *status);

/* maybe use notice in future */
_int32 wait_thread(THREAD_STATUS *status, _int32 notice_handle);

_int32 thread_suspend_init(SUSPEND_DATA *data);
_int32 thread_suspend_uninit(SUSPEND_DATA *data);
BOOL thread_is_suspend(SUSPEND_DATA *data);
_int32 thread_do_suspend(SUSPEND_DATA *data); // ���������Ϊthread_suspend����ϵͳ�Դ�������ͻ
_int32 thread_do_resume(SUSPEND_DATA *data); // ���������Ϊthread_resume����ϵͳ�Դ�������ͻ
void thread_check_suspend(SUSPEND_DATA *data);

// Ϊִ�� һ�� �ؼ�����Ϣ ��ʱresume �߳�ֱ������ ��Ϣִ����(thread_signal_for_critical_msg_end)
// ע��: 
// 1.����̱߳�������resume״̬��ҲӦ�õ���thread_signal_for_critical_msg_beginȷ������Ϣ��ִ�У�
//    ��ֹ��Ϣ��û�б�ִ�У����̵߳�����thread_do_suspend�������̣߳�
// 2.����thread_signal_for_critical_msg_end���߳̽��ָ�����ǰ״̬����������Ϣ������ʱ��״̬��
// 3.���ͬʱ�����˶��thread_signal_for_critical_msg_begin������¼���һ��p_msg����Ϊ���е���Ϣ
//    �����Ŷ�˳��ִ�еģ����һ����Ϣִ�����ˣ�����ζ��ǰ�����Ϣ��ִ�����ˣ�
//    ���⣬���ʱ����ǰ���p_msg(�������һ��)����thread_signal_for_critical_msg_end��ֱ�ӷ��أ�
// 4.�������������thread_signal_for_critical_msg_beginʱ������thread_to_suspend��thread_to_resume��ֻ����
//    ��־�������κ�ʵ���ϵĴ�������Ϣ������ϵ���thread_signal_for_critical_msg_endʱ���ݸ�
//    ��־�ָ��߳�״̬
_int32 thread_signal_for_critical_msg_begin(SUSPEND_DATA *data, void* p_msg);
_int32 thread_signal_for_critical_msg_end(SUSPEND_DATA *data, void* p_msg);

#define BEGIN_THREAD_LOOP(status)\
       while(IS_THREAD_RUN(status)) {

#define END_THREAD_LOOP(status) } BEGIN_STOP(status);

#ifdef __cplusplus
}
#endif

#endif
