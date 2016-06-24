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
	THREAD_RUNNING = 0, // 线程运行中
	THREAD_SUSPENDING, // 线程将要挂起
	THREAD_SUSPENDED, // 线程已经挂起
} THREAD_SUSPEND_FLAG;

typedef struct 
{
    pthread_mutex_t mutex;
    pthread_cond_t cond;
    THREAD_SUSPEND_FLAG flag;	// 是否通知线程进入休眠状态,线程当前的挂起状态

	THREAD_SUSPEND_FLAG should_suspend_flag; // 线程理论上应该的挂起状态，一般和flag是一样的，有关键消息需要处理时，可能会和flag不一样
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
_int32 thread_do_suspend(SUSPEND_DATA *data); // 如果命名成为thread_suspend则与系统自带函数冲突
_int32 thread_do_resume(SUSPEND_DATA *data); // 如果命名成为thread_resume则与系统自带函数冲突
void thread_check_suspend(SUSPEND_DATA *data);

// 为执行 一条 关键的消息 临时resume 线程直到这条 消息执行完(thread_signal_for_critical_msg_end)
// 注意: 
// 1.如果线程本来就是resume状态，也应该调用thread_signal_for_critical_msg_begin确保该消息被执行，
//    防止消息还没有被执行，有线程调用了thread_do_suspend而挂起线程；
// 2.调用thread_signal_for_critical_msg_end，线程将恢复到当前状态，而不是消息被发出时的状态；
// 3.如果同时调用了多次thread_signal_for_critical_msg_begin，将记录最后一个p_msg，因为所有的消息
//    都是排队顺序执行的，最后一个消息执行完了，就意味着前面的消息都执行完了，
//    另外，这个时候用前面的p_msg(不是最后一个)调用thread_signal_for_critical_msg_end将直接返回；
// 4.当有命令调用了thread_signal_for_critical_msg_begin时，调用thread_to_suspend和thread_to_resume将只设置
//    标志，不做任何实质上的处理，待消息处理完毕调用thread_signal_for_critical_msg_end时根据该
//    标志恢复线程状态
_int32 thread_signal_for_critical_msg_begin(SUSPEND_DATA *data, void* p_msg);
_int32 thread_signal_for_critical_msg_end(SUSPEND_DATA *data, void* p_msg);

#define BEGIN_THREAD_LOOP(status)\
       while(IS_THREAD_RUN(status)) {

#define END_THREAD_LOOP(status) } BEGIN_STOP(status);

#ifdef __cplusplus
}
#endif

#endif
