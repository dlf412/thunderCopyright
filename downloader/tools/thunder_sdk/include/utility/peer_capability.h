/*----------------------------------------------------------------------------------------------------------
author:		ZHANGSHAOHAN
created:	2008/08/14
-----------------------------------------------------------------------------------------------------------*/
#ifndef _PEER_CAPABILITY_H_
#define _PEER_CAPABILITY_H_
#ifdef __cplusplus
extern "C" 
{
#endif
#include "utility/define.h"

_u32	get_peer_capability(void);

/*
Peer���߱��Ĺ��ܱ�־������P2P����㣺
��0λ���Ƿ�������
��1λ���Ƿ�֧������ֱ��
��2λ���Ƿ��뱾��Peerλ����ͬ��������������Դ��ѯ���أ�
��3λ���Ƿ�֧�ֱ��±ߴ�
��4λ���Ƿ�Ϊ����server
��5λ���Ƿ�֧��P2P�����
��6λ���Ƿ�֧����udt��426�濪ʼ��
��7λ��ΪUDTЭ�鱣��
*/
void set_peer_capability(_u32* peer_capability, BOOL nated, BOOL support_intranet , BOOL same_nat, BOOL support_new_p2p, BOOL is_cdn,
						 BOOL support_ptl, BOOL support_new_udt);

BOOL is_nated(_u32 peer_capability);

BOOL is_support_intranet(_u32 peer_capability);

BOOL is_same_nat(_u32 peer_capability);

BOOL is_support_new_p2p(_u32 peer_capability);

BOOL is_cdn(_u32 peer_capability);

BOOL is_support_ptl(_u32 peer_capability);

BOOL is_support_new_udt(_u32 peer_capability);

BOOL is_support_mhxy_version1(_u32 peer_capability);
#ifdef __cplusplus
}
#endif
#endif
