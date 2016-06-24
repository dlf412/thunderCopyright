#ifndef SD_FS_H_00138F8F2E70_200806111928
#define SD_FS_H_00138F8F2E70_200806111928

#ifdef __cplusplus
extern "C" 
{
#endif

#include "utility/define.h"

/* ------------------------------------------------------ */

#define SD_MAX_PATH	(1024)

#define INVALID_FILE_ID	(0xFFFFFFFF)

/* whether if create file while it not exist. */
#define O_FS_CREATE		(0x1)
/* read and write (default) */
#define O_FS_RDWR		(0x0)
/* read only. */
#define O_FS_RDONLY		(0x2)
/* write only. */
#define O_FS_WRONLY		(0x4)
#define O_FS_MASK       (0xFF)

#if defined(LINUX)
#if defined(_ANDROID_LINUX)
#define FILE_ENLARGE_UNIT	(1024 * 1024)
#define FILE_ENLARGE_WRITE_UNIT	(1024 * 1024) 
#else
#define FILE_ENLARGE_UNIT	(1024 * 1024)
#endif
#elif defined(WINCE)
#define FILE_ENLARGE_UNIT	(1024 * 1024)
#else
#define FILE_ENLARGE_UNIT	(1024 * 1024)
#endif

/* ��ǰϵͳ֧�ֵ�Ŀ¼�ָ��� */
#if defined(WINCE) 
#define DIR_SPLIT_CHAR   '\\'
#define DIR_SPLIT_STRING "\\"
#else
#define DIR_SPLIT_CHAR   '/'
#define DIR_SPLIT_STRING "/"
#endif

char format_dir_split_char(char c);

/* ------------------------------------------------------ */

#define FILE_ATTRIB_READABLE (0x0001)
#define FILE_ATTRIB_WRITEABLE (0x0002)
#define FILE_ATTRIB_EXECABLE (0x0004)

typedef struct tag_file_attrib
{
	char _name[MAX_LONG_FILE_NAME_BUFFER_LEN];	
	BOOL _is_dir;
	_u32 _attrib;
#ifdef LINUX
	_u32 _is_lnk:1;
#endif	
} FILE_ATTRIB;

/* ------------------------------------------------------ */

_int32 sd_filepos(_u32 file_id, _u64 *filepos);
_int32 sd_setfilepos(_u32 file_id, _u64 filepos);
_int32 sd_filesize(_u32 file_id, _u64 *filesize);
_int32 sd_open_ex(const char *filepath, _int32 flag, _u32 *file_id);

/* sd_enlarge_file
 * ֻ���������ļ������ô˺�����fileposλ�ò�ȷ���������ã�
 * �����sd_pread/sd_pwriteʹ�ã��������ȱ���filepos��
 */
_int32 sd_enlarge_file(_u32 file_id, _u64 expect_filesize, _u64 *cur_filesize);
_int32 sd_close_ex(_u32 file_id);
_int32 sd_read(_u32 file_id, char *buffer, _int32 size, _u32 *readsize);
_int32 sd_write(_u32 file_id, char *buffer, _int32 size, _u32 *writesize);
_int32 sd_pread(_u32 file_id, char *buffer, _int32 size, _u64 filepos, _u32 *readsize);
_int32 sd_pwrite(_u32 file_id, char *buffer, _int32 size, _u64 filepos, _u32 *writesize);
_int32 sd_append(const char *filepath, char *buffer, _u32 size);
_int32 sd_copy_file(const char *filepath, const char *new_filepath);
_int32 sd_move_file(const char *filepath, const char *new_filepath);
_int32 sd_rename_file(const char *filepath, const char *new_filepath);
_int32 sd_delete_file(const char *filepath);
/* ɾ������Ŀ¼ */
_int32 sd_delete_dir(const char *path);
_int32 sd_copy_dir(const char *src_path, const char *dest_path);

/* sd_file_exist
 * Return : whether if filepath exist
 */
BOOL sd_file_exist(const char *filepath);

/* sd_dir_exist
 * Return : whether if dirpath is a exist dir 
 */
BOOL sd_dir_exist(const char *dirpath);

_int32 sd_is_path_exist(const char* path);
_int32 sd_ensure_path_exist(const char* path);

_int32 recursive_mkdir(const char *dirpath);

/* create directory recursively */
_int32 sd_mkdir(const char *dirpath);

/* failed if the directory is not empty */
_int32 sd_rmdir(const char *dirpath);

/* failed if the file or directory in directory is in use */
_int32 sd_recursive_rmdir(const char *dirpath);

/* ��ȡ��Ŀ¼/�ļ��ĸ��������ơ� 
 * ���sub_filesΪNULL����sub_files_size=0����������Ŀ¼�ĸ�����
 */
_int32 sd_get_sub_files(const char *dirpath, FILE_ATTRIB sub_files[], _u32 sub_files_size, _u32 *p_sub_files_count);


/* ��ȡĿ¼���������ļ�(���������ļ���)���ܴ�С 
 */
_int32 sd_get_sub_files_total_size(const char *dirpath,  _u64 * total_size);

/* Get file size and last modified time without opening the file */
_int32 sd_get_file_size_and_modified_time(const char * filepath,_u64 * p_file_size,_u32 * p_last_modified_time);

/* get free disk-space about path 
 *  unit of free_size : K (1024 bytes)
 */
_int32 sd_get_free_disk(const char *path, _u64 *free_size);

/* get total disk-space about path 
 *  unit of total_size : K (1024 bytes)
 */
_int32 sd_get_disk_space(const char *path, _u32 *total_size);

/* Check if the file is readable */
BOOL sd_is_file_readable(const char * filepath);
_int32 sd_test_path_writable(const char *path);

BOOL sd_is_file_name_valid(const char * filename);



/* Save the being writen data to buffer for reducing sd_write operations  */
_int32 sd_write_save_to_buffer(_u32 file_id, char *buffer, _u32 buffer_len,_u32 *buffer_pos, char * p_data,_u32 data_len);

/* ��ʽ���ļ�·���е�\��/
 * ����path����������ASCII,����GBK
**/
_int32 sd_format_filepath(const char *path, char *formated_path,
						  _u32 formated_path_size, _u32 *p_formated_path_len);

/* ��ʽ��Ŀ¼·���е�\��/������Էָ�����β
* ����path����������ASCII,����GBK
**/
_int32 sd_format_dirpath(const char *path, char *formated_path,
						 _u32 formated_path_size, _u32 *p_formated_path_len);

/* ��path����ת�룬��Ӧ��ͬ��ƽ̨
 * ����symbian  -> GBK; WINCE ->Unicode; Android ->UTF8 , ����������
**/
_int32 sd_conv_path(const char *input,_u32 input_len, char* output,_u32 *output_len);

/*��ʽ���ļ�·���е�\��/������Բ�ͬƽ̨����ת��
**/
_int32 sd_format_conv_filepath(const char *path, char *formated_path,
						  _u32 formated_path_size, _u32 *p_formated_path_len);

/* ��ʽ��Ŀ¼·���е�\��/������Բ�ͬƽ̨����ת��
**/
_int32 sd_format_conv_dirpath(const char *path, char *formated_path,
						 _u32 formated_path_size, _u32 *p_formated_path_len);

_int32 sd_append_path(char *path, _u32 buff_len, const char *append);
/* ------------------------------------------------------ */
/* �ļ�����·��
 * ��·����ʽ: DIR_SPLIT_CHAR + ʵ·��, ��: "/a/b/c", "\c:\a\b\"��
 */

/* �Ƿ���ʵ�ļ�·�� */
BOOL is_realdir(const char *dir);

BOOL sd_realpath(const char *path, char *resolved_path);

/* �ļ���·��תΪʵ·�� */
_int32 vdir2realdir(const char *vdir, char *realdir, _u32 realdir_size, _u32 *p_realdir_len);

/* �ļ�ʵ·��תΪ��·��,��֧�����·�� */
_int32 realdir2vdir(const char *realdir, char *vdir, _u32 vdir_size, _u32 *p_vdir_len);

/* ------------------------------------------------------ */
/*	�ض��ļ� 
*/
_int32 sd_truncate(const char *filepath, _u64 length);

/* ���·�����Ƿ����㹻��ʣ��ռ�,need_size�ĵ�λ��KB */
_int32 sd_check_enough_free_disk(char * path, _u64 need_size);

/* ------------------------------------------------------ */
#ifdef LINUX
#include <stdio.h>
typedef FILE		_FILE;
#else
typedef FILE		_FILE;
#endif

/* ------------------------------------------------------ */
/*	mode : r,r+,w,w+,a,a+  or with 'b'
*/
_int32 sd_fopen(const char *filepath, const char * mode,_FILE ** fp);
_int32 sd_fclose(_FILE *fp);

/* ��ȡһ�л�n-1���ַ� */
_int32 sd_fgets(char *buf, _int32 n, _FILE *fp);

/* д���ַ��� */
_int32 sd_fputs(const char *str, _FILE *fp);

_int32 sd_is_support_create_big_file(const char* path, BOOL* result);
BOOL sd_is_path_writable(const char* path);

_int32 sd_get_total_disk(const char *path, _u64 *total_size);

_int32 sd_recursive_rm_empty_dir(const char* dirpath);
#ifdef __cplusplus
}
#endif

#endif
