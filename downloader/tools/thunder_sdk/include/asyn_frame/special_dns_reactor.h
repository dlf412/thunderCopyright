#ifndef _SD_SPECIAL_DNS_REACTOR_H
#define _SD_SPECIAL_DNS_REACTOR_H

#ifdef __cplusplus
extern "C" 
{
#endif

#include "utility/define.h"
#include "asyn_frame/msg.h"
/*
note:使用同步dns解析，即调用系统getaddrinfo接口，可能出现调用后卡住的现象。
特别是在迅雷域名被封杀的情况下，卡住概率很大。
为保证部分重要域名的解析不受影响，多开这个special_dns线程进行dns解析。
目前使用special_dns线程解析的有(共1个):
1.原始资源
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

