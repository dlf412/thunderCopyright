#ifndef _SD_ASYN_FRAME_H_00138F8F2E70_200806251344
#define _SD_ASYN_FRAME_H_00138F8F2E70_200806251344

#ifdef __cplusplus
extern "C" 
{
#endif

#include "asyn_frame/msg_list.h"
#include "asyn_frame/device.h"


typedef _int32 (*init_handler)(void*);
typedef _int32 (*uninit_handler)(void*);


_int32 start_asyn_frame(init_handler h_init, void *init_arg, uninit_handler h_uninit, void *uninit_arg);

_int32 stop_asyn_frame(void);

BOOL is_asyn_frame_running(void);

/* only support socket-fd, device_type must be DEVICE_SOCKET_TCP || DEVICE_SOCKET_UDP */
_int32 peek_operation_count_by_device_id(_u32 device_id, _u32 device_type, _u32 *count);

BOOL asyn_frame_is_suspend();
_int32 asyn_frame_suspend();
_int32 asyn_frame_resume();

// 为执行 一条 关键的消息 临时resume 线程直到这条 消息执行完(asyn_frame_signal_for_critical_msg_end)
// 注意: 
// 1.如果线程本来就是resume状态，也应该调用asyn_frame_signal_for_critical_msg_begin确保该消息被执行，
//    防止消息还没有被执行，有线程调用了asyn_frame_suspend而挂起线程；
// 2.调用asyn_frame_signal_for_critical_msg_end，线程将恢复到当前状态，而不是消息被发出时的状态；
// 3.如果同时调用了多次asyn_frame_signal_for_critical_msg_begin，将记录最后一个p_msg，因为所有的消息
//    都是排队顺序执行的，最后一个消息执行完了，就意味着前面的消息都执行完了，
//    另外，这个时候用前面的p_msg(不是最后一个)调用asyn_frame_signal_for_critical_msg_end将直接返回；
// 4.当有命令调用了asyn_frame_signal_for_critical_msg_begin时，调用asyn_frame_suspend和asyn_frame_resume将只设置
//    标志，不做任何实质上的处理，待消息处理完毕调用asyn_frame_signal_for_critical_msg_end时根据该
//    标志恢复线程状态
#define ASYN_FRAME_BLOCK_CRITICAL_MSG ((void*)1) // 因为阻塞的消息处理不可能会有多个同时进行，直接用固定的msg
_int32 asyn_frame_signal_for_critical_msg_begin(void* p_msg);
_int32 asyn_frame_signal_for_critical_msg_end(void* p_msg);

#ifdef __cplusplus
}
#endif

#endif
