/*
 ============================================================================
 Name		 : sd_gz.h
 Author	  	 : xueren
 Copyright   : copyright xunlei 2010
 Description : Static lib header file
 ============================================================================
 */

#ifndef __SD_GZ_H_20100908__
#define __SD_GZ_H_20100908__

//  Include Files

//#include <e32base.h>
#include "utility/define.h"

//  Function Prototypes
#ifdef __cplusplus
extern "C" 
{
#endif
#ifdef ENABLE_ZIP
/**
 * ʹ��gz��ѹ�ļ�
 * @para:	filename-�����ļ���, newname-����ļ���
 * @return: 0-SUCCESS else-FAIL
 */
_u32 sd_gz_uncompress_file(char * filename, char * newname);

/**
 * ʹ��gz��buffer���룬ע�⣬�������buffer_out�������ȣ�sd_gzip_decode_buffer���ڲ����·��䳤��Ϊbuffer_out_len���ڴ�
 * @para: 	buffer_in-����buffer, buffer_in_len-����buffer�ĳ���
 * 		  	buffer_out-���buffer, buffer_out_len-���buffer���ܳ���
 * 			encode_len-��ѹ����Ч���ݵĳ���
 * @return: 0-SUCCESS else-FAIL
 */
_int32 sd_gz_decode_buffer(_u8* buffer_in, _u32 buffer_in_len, _u8** buffer_out, _u32* buffer_out_len,  _u32* decode_len);

/**
 * ʹ��gz��buffer����
 * @para: 	buffer_in-����buffer, buffer_in_len-����buffer�ĳ���
 * 		  	buffer_out-���buffer, buffer_out_len-���buffer�ĳ���
 * 			encode_len-ѹ����ĳ���
 * @return: 0-SUCCESS else-FAIL
 */
_int32 sd_gz_encode_buffer(_u8* buffer_in, _u32 buffer_in_len, _u8* buffer_out, _u32 buffer_out_len, _u32* encode_len);


//////////////////////////////////
//��src�е����ݽ���gzipѹ����ѹ�������ݱ�����des��
//src:��ѹ������
//src_len:��ѹ�����ݳ���
//des:ѹ���������
//des_len:�����������������ȥ�ĵ���des���ڴ���󳤶�,����������ѹ��������ݳ���
_int32 sd_zip_data( const _u8 * src, _u32 src_len,_u8 * des, _u32 * des_len);

//////////////////////////////////
//��src�е����ݽ���gzip��ѹ����ѹ�����ݱ�����des��
//src:����ѹ����
//src_len:����ѹ���ݳ���
//des:��ѹ�������
//des_len:�����������������ȥ�ĵ���des���ڴ���󳤶�,���������ǽ�ѹ������ݳ���
_int32 sd_unzip_data( const _u8 * src, _u32 src_len,_u8 * des, _u32 * des_len);

//////////////////////////////////
//�������ļ�����gzip��ѹ�����ý�ѹ����ļ��滻��ѹǰ���ļ�
//file_name:����ѹ�ļ�ȫ��
_int32 sd_unzip_file(const char * file_name);


#endif /*  ENABLE_ZIP */
#ifdef __cplusplus
}
#endif

#endif  // __SD_GZ_H_20100908__

