/*----------------------------------------------------------------------------------------------------------
author:		ZHANGSHAOHAN
created:	2008/11/28
-----------------------------------------------------------------------------------------------------------*/
#ifndef _BITMAP_H_
#define _BITMAP_H_

#ifdef __cplusplus
extern "C" 
{
#endif

#include "utility/define.h"

//���ǵ�Ƕ��ʽ�����ܵ�Ҫ�󣬸�bitmap��ʵ��ʹ�ù̶���8�ֽ���Ϊ���洢����,Ŀǰ��������bit_countΪ161
#define		MAX_BITMAP_SIZE		100

typedef struct tagBITMAP
{
	_u8*	_bit;
	_u32	_bit_count; //λ��
	_u32	_mem_size;	//�ڴ��С
}BITMAP;

_int32 bitmap_init(BITMAP* bitmap);

_int32 bitmap_uninit(BITMAP* bitmap);

_int32 bitmap_resize(BITMAP* bitmap, _u32 bit_count);	//�����С

_int32 bitmap_init_with_bit_count( BITMAP* bitmap, _u32 bit_count );	

_int32 bitmap_set(BITMAP* bitmap, _u32 pos, BOOL val);	// ��ָ��λ��ֵ

_u32 bitmap_bit_count(const BITMAP* bitmap);	//�õ�λ��

BOOL bitmap_at(const BITMAP* bitmap, _u32 pos);	//ָ��λ�Ƿ�Ϊ1

BOOL bitmap_all_none(BITMAP* bitmap);	//�Ƿ�����λ��Ϊ0

_int32 bitmap_from_bits(BITMAP* bitmap, char* data, _u32 data_len, _u32 bit_count);

_int32 bitmap_adjust(BITMAP* left, BITMAP* right);

void bitmap_print(const BITMAP* bitmap);

BOOL bitmap_range_is_all_set(BITMAP* bitmap, _u32 start_pos, _u32 end_pos);

_int32 bitmap_xor( const BITMAP* bitmap1, const BITMAP* bitmap2, BITMAP* ret );

BOOL bitmap_is_equal( const BITMAP* bitmap1, const BITMAP* bitmap2, _u32 pos );

//Ϊ���Ч��,bitmap_dest�����Ѿ���ʼ������_bit_count��_mem_size��С�ڶ�Ӧbitmap_src��ֵ.
_int32 bitmap_copy( const BITMAP* bitmap_src, BITMAP* bitmap_dest );

_u8 *bitmap_get_bits( BITMAP* bitmap );

_int32 bitmap_compare( BITMAP *p_bitmap_1, BITMAP *p_bitmap_2, _int32 *p_result );

#ifdef ENABLE_EMULE
//emule��bitmap������һ���ֽڴ��������˳����һ��Ĳ�һ�������ԼӶ�����������
_int32 bitmap_emule_at(BITMAP* bitmap, _u32 pos);

_int32 bitmap_emule_set(BITMAP* bitmap, _u32 pos, BOOL val);
#endif

#ifdef __cplusplus
}
#endif

#endif
