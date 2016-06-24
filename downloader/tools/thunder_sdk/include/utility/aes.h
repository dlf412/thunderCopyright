/*----------------------------------------------------------------------------------------------------------
author:		ZHANGSHAOHAN
created:	2008/08/20
-----------------------------------------------------------------------------------------------------------*/
#ifndef _AES_H_
#define _AES_H_

#ifdef __cplusplus
extern "C" 
{
#endif

#include "utility/define.h"

#define Bits128				16  /*��Կ����*/
#define Bits192				24
#define Bits256				32
#define ENCRYPT_BLOCK_SIZE	16

typedef struct  
{
	_int32 Nb;         /* block size in 32-bit words.  Always 4 for AES.  (128 bits). */
	_int32 Nk;         /* key size in 32-bit words.  4, 6, 8.  (128, 192, 256 bits). */
	_int32 Nr;         /* number of rounds. 10, 12, 14. */
	_u8	   State[4][4];/* State matrix */
	_u8	   key[32];    /* the seed key. size will be 4 *keySize from ctor. */
	_u8    w[16*15];   /* key schedule array. (Nb*(Nr+1))*4 */
}ctx_aes;

void xl_aes_init(ctx_aes* aes, int keySize, _u8* keyBytes);
void xl_aes_cipher(ctx_aes* aes, _u8* input, _u8* output);  /* encipher 16-bit input */
void xl_aes_invcipher(ctx_aes* aes, _u8* input, _u8* output);
//
// ���º���û�б������������ã���ʱ�������������Ҫ��������Ѻ������ּ���ǰ׺�������ϵͳ���ͻ
// void SetNbNkNr(ctx_aes* aes, _int32 keyS);
// void AddRoundKey(ctx_aes* aes, _int32 round);
// void SubBytes(ctx_aes* aes);
// void InvSubBytes(ctx_aes* aes);
// void ShiftRows(ctx_aes* aes);
// void InvShiftRows(ctx_aes* aes);
// void MixColumns(ctx_aes* aes);
// void InvMixColumns(ctx_aes* aes);
// _u8  gfmultby01(_u8 b);
// _u8 gfmultby02(_u8 b);
// _u8 gfmultby03(_u8 b);
// unsigned char gfmultby09(unsigned char b);
// unsigned char gfmultby0b(unsigned char b);
// unsigned char gfmultby0d(unsigned char b);
// unsigned char gfmultby0e(unsigned char b);
// void KeyExpansion(ctx_aes* aes);
// void SubWord(_u8 *word, _u8 *result);
// void RotWord(_u8 *word, _u8 *result);

_int32 xl_gen_aes_key_by_ptr(const void *ptr, _u8 *p_aeskey);
_int32 xl_aes_encrypt_with_known_key(char* buffer,_u32* len, _u8 *key);
_int32 xl_aes_decrypt_with_known_key(char* p_data_buff, _u32* p_data_buff_len, _u8 *key);

//////////////////////////////////
//��src�е����ݽ���AES(128Bytes)���ܣ����ܺ����ݱ�����des��
//aes_key:���ڼ��ܵ�key,����ע�⣬���key����Ҫ����MD5���㣬�������MD5ֵ��Ϊ���ܽ��ܵ���Կ!
//src:����������
//src_len:���������ݳ���
//des:���ܺ������
//des_len:�����������������ȥ�ĵ���des���ڴ���󳤶�,���������Ǽ��ܺ�����ݳ���
_int32 sd_aes_encrypt( const char* aes_key,const _u8 * src, _u32 src_len,_u8 * des, _u32 * des_len);

//////////////////////////////////
//��src�е����ݽ���AES(128Bytes)���ܣ����ܺ����ݱ�����des��
//aes_key:���ڽ��ܵ�key,����ע�⣬���key����Ҫ����MD5���㣬�������MD5ֵ��Ϊ���ܽ��ܵ���Կ!
//src:����������
//src_len:���������ݳ���
//des:���ܺ������
//des_len:�����������������ȥ�ĵ���des���ڴ���󳤶�,���������ǽ��ܺ�����ݳ���
_int32 sd_aes_decrypt(const  char* aes_key,const _u8 * src, _u32 src_len,_u8 * des, _u32 * des_len);

//////////////////////////////////
//�������ļ�����AES(128Bytes)���ܣ����ý��ܺ���ļ��滻����ǰ���ļ�
//aes_key:���ڽ��ܵ�key,����ע�⣬���key����Ҫ����MD5���㣬�������MD5ֵ��Ϊ���ܽ��ܵ���Կ!
//file_name:�������ļ�ȫ��
_int32 sd_aes_decrypt_file(const  char* aes_key,const char * file_name);


int32_t em_aes_encrypt(char* in_buffer ,uint32_t in_len, char* out_buffer, uint32_t* out_len, uint8_t key[16]);
int32_t em_aes_decrypt(char* in_buffer ,uint32_t in_len, char* out_buffer, uint32_t* out_len, uint8_t key[16]);

#ifdef __cplusplus
}
#endif

#endif

