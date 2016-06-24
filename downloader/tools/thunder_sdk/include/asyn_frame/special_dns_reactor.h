#ifndef _SD_SPECIAL_DNS_REACTOR_H
#define _SD_SPECIAL_DNS_REACTOR_H

#ifdef __cplusplus
extern "C" 
{
#endif

#include "utility/define.h"
#include "asyn_frame/msg.h"
/*
note:ʹ��ͬ��dns������������ϵͳgetaddrinfo�ӿڣ����ܳ��ֵ��ú�ס������
�ر�����Ѹ����������ɱ������£���ס���ʺܴ�
Ϊ��֤������Ҫ�����Ľ�������Ӱ�죬�࿪���special_dns�߳̽���dns������
Ŀǰʹ��special_dns�߳̽�������(��1��):
1.ԭʼ��Դ
*/

_int32 init_special_dns_reactor(_int32 *waitable_handle);
_int32 uninit_special_dns_reactor(void);

_int32 register_special_dns_event(MSG *msg);
_int32 unregister_special_dns(MSG *msg, _int32 reason);

_int32 get_complete_special_dns_msg(MSG **msg);


#ifdef __cplusplus
}
#endif

#endif //_SD_SPECIAL_DNS_REACTOR_H

