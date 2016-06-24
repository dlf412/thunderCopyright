#ifndef _SD_DNS_PARSER_H_200905221723
#define _SD_DNS_PARSER_H_200905221723

#ifdef __cplusplus
extern "C" 
{
#endif

#include "utility/define.h"

/************************************************************************
 *
 * DNS server ip.
 *
 ************************************************************************/

/* ����(n)�������޷������������nameserver��Ϊ��Ч�� */
#define DNS_SERVER_IP_INVALID_SCORE (3)

/* ���ڼ��nameserver�����ļ���ʱ�䡣 */
#define DNS_SERVER_IP_CHECK_SERVER_IP_INTERVAL (2000)

typedef struct
{
    _int32 _host_name_key[DNS_SERVER_IP_INVALID_SCORE];
    _u32 _count;
} DNS_SERVER_IP_VALIDITY;

typedef struct
{
    _u32 _ip_list[DNS_SERVER_IP_COUNT_MAX];
    DNS_SERVER_IP_VALIDITY _validity[DNS_SERVER_IP_COUNT_MAX];
    _u32 _ip_count;
    _u64 _file_size;
    _u32 _file_last_modified_time;
    _u32 _last_check_file_attrib_time;
} DNS_SERVER_IP;

/************************************************************************
 *
 * DNS content.
 *
 ************************************************************************/

typedef struct
{
    char _host_name[MAX_HOST_NAME_LEN];
    _u32 _host_name_buffer_len;
    _u32 _ip_list[DNS_CONTENT_IP_COUNT_MAX];
    _u32 _ttl[DNS_CONTENT_IP_COUNT_MAX];    /* TTL���������С� */
    _u32 _start_time;   /* ��ȡ��TTLʱ��ʱ����� */
    _u32 _ip_count;
    _u32 _result;
} DNS_CONTENT_PACKAGE;

/************************************************************************
 *
 * DNS code package.
 *
 ************************************************************************/

#define DNS_CODE_SIZE_MAX (1024)

typedef struct
{
    char _dns_code[DNS_CODE_SIZE_MAX];
    _u32 _len;
}DNS_CODE_PACKAGE;

/************************************************************************
 *
 * DNS cache.
 *
 ************************************************************************/

/* cache size. */
#define DNS_CHCHE_SIZE_MAX (29)

/* ���������DNS��CACHE�е�TTL. */
#define DNS_CHCHE_INVAIL_DNS_TTL (5000)

typedef struct
{
    _u32 _index[DNS_CHCHE_SIZE_MAX];
    _u32 _conflict_next_index[DNS_CHCHE_SIZE_MAX];
}DNS_CACHE_HASH_TABLE;

typedef struct
{
    _u32 _prior_index[DNS_CHCHE_SIZE_MAX];
    _u32 _next_index[DNS_CHCHE_SIZE_MAX];
    _u32 _min_index;
    _u32 _max_index;
}DNS_CACHE_PRIORITY_LIST;

typedef struct
{
    DNS_CONTENT_PACKAGE _dns_content[DNS_CHCHE_SIZE_MAX];
    DNS_CACHE_PRIORITY_LIST _pri_lru;
    DNS_CACHE_PRIORITY_LIST _pri_ttl;
    DNS_CACHE_HASH_TABLE _hash_table;
    _u32 _size;
}DNS_CACHE;

/* ��ʼ��
 * @return:
 *	   SUCCESS - �ɹ���
 */
_int32 dns_cache_init(DNS_CACHE *dns_cache);

/* ����ʼ��
 * @return:
 *	   SUCCESS - �ɹ���
 */
_int32 dns_cache_uninit(DNS_CACHE *dns_cache);

/* ���cache
 * @return:
 *	  SUCCESS - �ɹ���
 */
_int32 dns_cache_clear(DNS_CACHE *dns_cache);

/* ��ѯcache
 * @return:
 *	  SUCCESS: �ɹ���
 *	  -1: û�ҵ���
 */
_int32 dns_cache_query(DNS_CACHE *dns_cache, char *host_name, DNS_CONTENT_PACKAGE *dns_content);

/* ������ѯ�����cache
 * @return:
 *	  SUCCESS - �ɹ���
 */
_int32 dns_cache_append(DNS_CACHE *dns_cache, DNS_CONTENT_PACKAGE *dns_content);


/************************************************************************
 *
 * DNS request queue.
 * ���ڱ����ѷ���request����δ�յ�answer��DNS msg��
 *
 ************************************************************************/

/* request queue size. */
#define DNS_REQUEST_QUEUE_SIZE_MAX (29)

/* retry times after request fail or expired. */
#define DNS_REQUEST_RETRY_TIMES (1)

/* request ttl. */
#define DNS_REQUEST_TTL (5000)

typedef struct
{
    _u32 _dns_id;
    char _host_name[MAX_HOST_NAME_LEN];
    _u32 _host_name_len;
    _u32 _request_time;
    _u32 _retry_times;
    _u32 _ttl;
    _u32 _dns_server_ip_index;  /* ��indexֵΪ DNS_SERVER_IP_COUNT_MAX ʱ����ʾ�������nameserver��ʧЧ�� */
    void *_data;
}DNS_REQUEST_RECORD;

typedef struct
{
    _u32 _head;
    _u32 _tail;
    _u32 _prior_index[DNS_REQUEST_QUEUE_SIZE_MAX];
    _u32 _next_index[DNS_REQUEST_QUEUE_SIZE_MAX];
}DNS_REQUEST_EXPIRED_LIST;

typedef struct
{
    DNS_REQUEST_RECORD _record[DNS_REQUEST_QUEUE_SIZE_MAX];
    DNS_REQUEST_EXPIRED_LIST _exp_list;
    DNS_SERVER_IP _dns_server_ip;
    _u32 _cur_dns_id;
    _u32 _size;
}DNS_REQUEST_QUEUE;

/************************************************************************
 *
 * DNS PARSER (platform)
 *
 ************************************************************************/

typedef struct
{   
    DNS_REQUEST_QUEUE _dns_request_queue;
    DNS_CACHE _dns_cache;
    _u32 sock;
}DNS_PARSER;

_int32 dns_parser_init(DNS_PARSER *dns_parser);
_int32 dns_parser_uninit(DNS_PARSER *dns_parser); 

/*
 * ��ǰDNS�������Ƿ������
 *
 * @arguments:
 *  [out]is_ready:
 *      TRUE - ������
 *      FALSE - ��ʱ�޷������µĽ�������
 *
 * @return:
 *      NOT SUCCESS - �쳣��
 */
_int32 dns_parser_is_ready(DNS_PARSER * dns_parser, BOOL *is_ready);

/*
 * ��ѯDNS��
 * ���������δ���سɹ�������� dns_parser_get �����첽��ȡ�����
 *
 * @argments:
 *  [out]query_result:
 *      DNS_QUERY_RESULT_OK - ��ͬ�����ؽ��������
 *      DNS_QUERY_RESULT_ASYNC_REQUEST - δͬ���õ�������������ѷ����첽����
 *  [in]pdata:
 *      �����첽��ȡDNS����ʱ���ɻ�ȡ���˲���ֵ��
 *  [out]content:
 *      ͬ�����صĽ��������
 *
 * @return:
 *      NOT SUCCESS - �쳣��
 */

#define DNS_QUERY_RESULT_OK                 (0)
#define DNS_QUERY_RESULT_ASYNC_REQUEST      (1)

_int32 dns_parser_query(DNS_PARSER *dns_parser, char *host_name, _u32 host_name_len, _int32 *query_result,
    void *pdata, DNS_CONTENT_PACKAGE *content);

/*
 * �첽��ȡDNS���������
 *
 * @argments:
 *  [out]ack_result:
 *      DNS_ACK_RESULT_OK - �ѷ��ؽ��������
 *      DNS_ACK_RESULT_NOT_GET_ANSWER - ���ε���δ��ȡ�����������
 *  [out]ppdata:
 *      ��ѯDNS �����д����ֵ��
 *  [out]content:
 *      ͬ�����صĽ��������
 *
 * @return:
 *      NOT SUCCESS - �쳣��
 */

#define DNS_ACK_RESULT_OK                   (0)
#define DNS_ACK_RESULT_NOT_GET_ANSWER       (1)

_int32 dns_parser_get(DNS_PARSER * dns_parser, _int32 *ack_result, void **ppdata, DNS_CONTENT_PACKAGE *content);

/*
 * ȡ��DNS����
 */
_int32 dns_parser_query_cancel(DNS_PARSER * dns_parser, _u32 index);

/*
 * �Ƿ����е�DNS�����ѽ�����ɡ�
 *
 * @arguments:
 *  [out]is_finished:
 *      TRUE - ���е�DNS�����ѽ�����ɡ�
 *      FALSE - ����DNS����δ������
 *
 * @return:
 *      NOT SUCCESS - �쳣��
 */
_int32 dns_parser_is_finished(DNS_PARSER * dns_parser, BOOL *is_finished);

/*
 * ������δ�����DNS���������
 *
 * @arguments:
 *  [out]count: δ��������������
 *
 * @return:
 *      NOT SUCCESS - �쳣��
 */
_int32 dns_parser_request_count(DNS_PARSER * dns_parser, _u32 *count);

/*
 * ������δ�����DNS������Ϣ��
 *
 * @arguments:
 *  [in]index:   ������ע�⣺��������ָ��Ϣ�����κ�����
 *  [out]record: ������Ϣ��¼��
 *
 * @return:
 *      NOT SUCCESS - �쳣��
 */
_int32 dns_parser_request_record_const(DNS_PARSER * dns_parser, _u32 index, DNS_REQUEST_RECORD **precord);

/*
 * DNS Server ������
 *
 * @arguments:
 *  [out]count: δ��������������
 *
 * @return:
 *      NOT SUCCESS - �쳣��
 */
_int32 dns_parser_dns_server_count(DNS_PARSER * dns_parser, _u32 *count);

/*
 * DNS Server IP ��Ϣ��
 *
 * @arguments:
 *  [in]index:   ������
 *  [out]dns_server_ip: DNS Server IP ��Ϣ��
 *
 * @return:
 *      NOT SUCCESS - �쳣��
 */
_int32 dns_parser_dns_server_info(DNS_PARSER * dns_parser, _u32 index, _u32 *dns_server_ip);

#ifdef __cplusplus
}
#endif

#endif
