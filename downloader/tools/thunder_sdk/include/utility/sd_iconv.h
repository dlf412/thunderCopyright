#ifndef SD_ICONV_H_20081229
#define SD_ICONV_H_20081229

#include "utility/define.h"

#ifdef __cplusplus
extern "C" 
{
#endif

enum CODE_PAGE { _CP_ACP = 0, _CP_GBK , _CP_UTF8 ,_CP_BIG5 };

enum GBK_CHAR_TYPE
{
    _STAND_COMMON_CHAR=1,
    _STAND_CHAR=3,
    _STAND_CHAR_EXTEND_1=4,
    _STAND_CHAR_EXTEND_2=8,
    _STAND_FLAG=16,
    STAND_FLAG_EXTEND=32,
    _UNKNOWN_TYPE = 0x80
};
    
/*	�²��ַ����ı����ʽ:CP_ACP=0, CP_GBK , CP_UTF8
 
Notice:
   �ú������ڲ²��ַ����ı����ʽ��ֻ�ܲ²��������ֱ�����ַ�����
	��ASCII���뷵��CP_ACP�����ļ���GBK���뷵��CP_GBK��UTF8���뷵��CP_UTF8�����ķ���BIG5����CP_BIG5��
   ���ڸú�����һ��100%�ܲ���ȷ�����ԣ����ݲ�ͬ�ķ���ֵ�������������Ҫע�⣺
	1.�������ֵΪCP_ACP������ַ���һ���Ǵ�ASCII���룬������������ʽ�ı��룻
	2.�������ֵΪUTF8������ַ���һ����UTF8���룬������������ʽ�ı��룻
	3.�������ֵΪCP_BIG5������ַ���Ҳ�п�����UTF8���룬����������CP_ACP��CP_GBK��ʽ�ı��룻���������Ҫ���ע�⡣
	4.�������ֵΪCP_GBK������ַ���Ҳ�п�����CP_BIG5��UTF8���룬���������Ǵ�ASCII���룻�������Ҳ��Ҫ���ע�⡣

*/
enum CODE_PAGE sd_conjecture_code_page( const char* src_str );

enum GBK_CHAR_TYPE sd_get_gbk_type( _u16  char_value );
BOOL sd_is_gbk_type(enum GBK_CHAR_TYPE src, enum GBK_CHAR_TYPE dst);
    
_int32 sd_utf8_2_gbk(const char *p_input, _u32 input_len, char *p_output, _u32 *output_len);
_int32  sd_gbk_2_utf8(const char *p_input, _u32 input_len, char *p_output, _u32 *output_len);
_int32 sd_utf8_2_big5(const char *p_input, _u32 input_len, char *p_output, _u32 *output_len);
_int32  sd_big5_2_utf8(const char *p_input, _u32 input_len, char *p_output, _u32 *output_len);

_int32 sd_big5_2_gbk(const char *p_input, _u32 input_len, char *p_output, _u32 *output_len);

_int32 sd_unicode_2_gbk(const _u16 *p_input, _u32 input_len, char *p_output, _u32 *output_len);
_int32  sd_gbk_2_unicode(const char *p_input, _u32 input_len, _u16 *p_output, _u32 *output_len);

_int32 sd_utf8_2_unicode(_u8* utf8, _u32 input_len, _u16* unicode,_u32 *output_len);
_int32 sd_unicode_2_utf8(_u16* unicode,_u32 input_len, _u8* utf8,_u32 *output_len);

/* ����ɹ�, *output_len����ռ���ڴ泤��(byte)*/
_int32 sd_any_format_to_gbk( const char *input,_u32 input_len, _u8* gbk,_u32 *output_len);
/* ����ɹ�, *output_len����ռ���ڴ泤��(byte)*/
_int32 sd_any_format_to_utf8( const char *input,_u32 input_len, char * p_utf8,_u32 *output_len);
/* ����ɹ�, *output_len����unicode�ַ�(���ֽ�)����*/
_int32 sd_any_format_to_unicode( const char *input,_u32 input_len, _u16* p_unicode,_u32 *output_len);

BOOL sd_is_acp_page_code(const char* str, _int32 len);
#ifdef __cplusplus
}
#endif


#endif  /* SD_ICONV_H_20081229 */

