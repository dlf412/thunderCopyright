#if !defined(__URL_H_20080805)
#define __URL_H_20080805

#ifdef __cplusplus
extern "C" 
{
#endif


#include "utility/define.h"


enum SCHEMA_TYPE { HTTP=0, FTP , MMS, HTTPS, MMST, PEER, RTSP, RTSPT, FTPS, SFTP, UNKNOWN };

/* Encode mode  for url  path and file_name    */
enum URL_ENCODE_MODE
{ 
	UEM_ASCII=0,  			/* ASCII �����ʽ */ 
	UEM_ENCODED,    		/* ����'%' �ı����ʽ */ 
	UEM_GBK,    				/* GBK �����ʽ */ 
	UEM_GBK_ENCODED,  	/* ����'%' ��GBK �����ʽ */ 
	UEM_BIG5,    			/* BIG5 �����ʽ */ 
	UEM_BIG5_ENCODED,   	/* ����'%' ��BIG5 �����ʽ */ 
	UEM_UTF8,     			/* UTF8 �����ʽ */ 
	UEM_UTF8_ENCODED,  	/* ����'%' ��UTF8 �����ʽ */ 
	UEM_UNKNOW = 127          /* δ֪����*/
};

/*  steps  for retry sending request      */
enum URL_CONVERT_STEP
{ 
	UCS_ORIGIN=0,  			/* ֱ����src_string */ 
	UCS_DECODE,    			/* src_string ȥ��'%' --- decode */ 
	UCS_ENCODE,    			/* src_string ��'%' --- encode */ 
	UCS_GBK2UTF8_ENCODE,  /* src_string ȥ��'%'������GBKתUTF8���ټ�'%' --- decode->gbk_2_utf8->encode */ 
	UCS_GBK2UTF8,    		/* src_string ȥ��'%'������GBKתUTF8  --- decode->gbk_2_utf8  */ 
	UCS_UTF82GBK_ENCODE,  /* src_string ȥ��'%'������UTF8תGBK���ټ�'%' --- decode->utf8_2_gbk->encode */ 
	UCS_UTF82GBK,     		/* src_string ȥ��'%'������UTF8תGBK  --- decode->utf8_2_gbk  */ 
	UCS_BIG52UTF8_ENCODE,   /* src_string ȥ��'%'������BIG5תUTF8���ټ�'%' --- decode->big5_2_utf8->encode */ 
	UCS_BIG52UTF8,    		/* src_string ȥ��'%'������BIG5תUTF8  --- decode->big5_2_utf8  */ 
	UCS_END    		
};


typedef struct url_object
{	
  enum	SCHEMA_TYPE _schema_type;

	//�û����ǽ�����ֵ
	char _user[MAX_USER_NAME_LEN];
	
	//�����ǽ�����ֵ
	char _password[MAX_PASSWORD_LEN];
	char _host[MAX_HOST_NAME_LEN];
	_u32 _port;
	char _full_path[MAX_FULL_PATH_BUFFER_LEN];
	char* _path;									//ָ��_full_path������Ϊ_path_len
	char* _file_name;							//ָ��_full_path�е��ļ����Ŀ�ʼ��ַ������Ϊ_file_name_len
	_u32 _path_len;
	_u32 _file_name_len;
	char _file_suffix[MAX_SUFFIX_LEN];
 	enum URL_ENCODE_MODE  _path_encode_mode;		// ·�� �����ֱ����ʽ
	enum URL_ENCODE_MODE  _filename_encode_mode;	// �ļ��� �����ֱ����ʽ
 	enum URL_CONVERT_STEP  _path_valid_step;			// ·�� ����Ч����ת������
	enum URL_CONVERT_STEP  _filename_valid_step;		// �ļ��� ����Ч����ת������,��http�У�_path_valid_stepҪ��_filename_valid_step���
	BOOL _is_dynamic_url;
	BOOL _is_binary_file;
}URL_OBJECT;

 /* @Simple Function@
 * Return : TRUE or FALSE
 */
BOOL sd_is_dynamic_url(char* _url);


 /* Change URL from char* to URL_OBJECT
 * Return : 0: success; other:error
 */
  _int32 sd_url_to_object(const char* _url,_u32 url_length,URL_OBJECT* _url_o);
 
 /* Change URL_OBJECT to char* 
 * Return : 0: success; other:error
 */
 _int32 sd_url_object_to_string(URL_OBJECT  *url_o,char* url);
 
 /* Change URL_OBJECT to ref_url,without file name 
 * Return : 0: success; other:error
 * Notice: Make sure the length of the buffer:char* _url is larger than MAX_URL_LEN
 */
 _int32 sd_url_object_to_ref_url(URL_OBJECT  *url_o,char* url);

 /* Change the full path of URL_OBJECT  
 * Return : 0: success; other:error
 */
 _int32 sd_url_object_set_path(URL_OBJECT  *url_o,char* full_path,_u32 full_path_len);
 
 /* @Simple Function@
 * Return : TRUE or FALSE
* Notice: Just for HTTP_RESOURCE and FTP_RESOURCE!
 */
//BOOL sd_is_server_res_equal(RESOURCE * _p_res1,RESOURCE *  _p_res2);

 /* Get the schema type of URL
 * Return :SCHEMA_TYPE{ HTTP=0, FTP , MMS, HTTPS, MMST, PEER, RTSP, RTSPT, FTPS, SFTP, UNKNOWN}
 * Notice: Just for http,https and ftp now!
 */
 enum SCHEMA_TYPE sd_get_url_type(char* _url,_u32 url_length);

  /* @Simple Function@
 * Return : TRUE or FALSE
 * Notice: Just for HTTP_RESOURCE and FTP_RESOURCE!
 */
BOOL sd_is_url_object_equal(URL_OBJECT * _url_o1,URL_OBJECT * _url_o2);

 /* Get the hash value of URL
 */
 _int32 sd_get_url_hash_value(char* _url,_u32 _url_size,_u32 * _p_hash_value);

 void sd_string_to_low_case(char* str);

 void sd_string_to_uppercase(char* str);

 /* Check if the suffix is binary file 
 */
 BOOL sd_is_binary_file(char* _suffix,char * _ext_buffer);

 /* Get the file suffix from URL object
 */
 _int32 sd_get_file_suffix(URL_OBJECT *_url_o);
 
 /* Decode file name: remove all the '%'
 */
BOOL sd_decode_file_name(char * _file_name,char * _file_suffix, _u32 file_name_buf_len);
 /* Get file from URL
 */
_int32 sd_get_file_name_from_url(char * _url,_u32 url_length,char * _file_name, _u32 _file_name_buf_len);

  /* @Simple Function@
 * Return : TRUE or FALSE
 * Notice: Just for HTTP_RESOURCE and FTP_RESOURCE!
 */
BOOL sd_is_url_has_user_name(char * _url);

 /* Change URL_OBJECT to url string without user name and password 
 */
_int32 url_object_to_noauth_string(const char* src_str,  char * str_buffer ,_u32 buffer_len);

 BOOL url_object_need_escape( char c );
 BOOL url_object_is_reserved( char c );

 //�������ַ�'/','?','@',':'... �⣬�����еĴ���'%' ���ַ�ȥ��'%'
_int32 url_object_decode(const char* src_str, char * str_buffer ,_u32 buffer_len);

//�����еĴ���'%' ���ַ�ȥ��'%'�����������ַ�'/','?','@',':'...
_int32 url_object_decode_ex(const char* src_str, char * str_buffer ,_u32 buffer_len);

// �ѳ������ַ�(';'��'/'��'?'��':'��'@'��'&'��'='��'+'��'$'��',')��������������ַ�ת����%XX
_int32 url_object_encode(const char* src_str, char * str_buffer ,_u32 buffer_len);

// ���������ַ�ת����%XX,���������ַ�(';'��'/'��'?'��':'��'@'��'&'��'='��'+'��'$'��',')
_int32 url_object_encode_ex(const char* src_str, char * str_buffer ,_u32 buffer_len);


_int32  sd_parse_kankan_vod_url(char* url, _int32 length ,_u8 *p_gcid,_u8 * p_cid, _u64 * p_file_size,char * file_name);
_int32 sd_parse_lixian_url(char *url, _int32 len, _u8* p_gcid, _u8* p_cid, _u64* p_filesize, char* filename);
 /* Change the url from  unicode format(with '%') to utf8 format 
 * Return : 0: success; other:error
 * Notice: Make sure the length of the buffer:char* _url_utf8 is larger than MAX_URL_LEN
 */
// _int32 sd_url_unicode_to_utf8(char* _url_unicode,char* _url_utf8);


_int32 url_convert_format( const char* src_str ,_int32 src_str_len,char* str_buffer ,_int32 buffer_len ,enum URL_CONVERT_STEP * convert_step);
_int32 url_convert_format_to_step( const char* src_str ,_int32 src_str_len,char* str_buffer ,_int32 buffer_len,enum URL_CONVERT_STEP  convert_step );
enum URL_ENCODE_MODE url_get_encode_mode( const char* src_str ,_int32 src_str_len );
  _int32 sd_get_url_sum(char* _url,_u32 _url_size,_u32 * _p_sum);

 _int32 sd_get_valid_name(char * _file_name,char * file_suffix);
 
BOOL sd_check_if_in_nat_url(char * url);
BOOL sd_check_if_in_nat_host(const char * host);
/* �Ӿ�����URL�н�����cid��file_size */
_int32 sd_get_cid_filesize_from_lan_url( char * url,_u8 cid[CID_SIZE], _u64  * file_size);
_int32 sd_get_filesize_from_emule_url(char *ed2k_link, _u64 *p_file_size);
#ifdef __cplusplus
}
#endif

#endif /* __URL_H_20080805 */
