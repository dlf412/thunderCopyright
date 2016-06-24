#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <time.h>
#include "../include/embed_thunder.h"
#include "../include/utility/url.h"
#include "../include/platform/sd_fs.h"


#define  BT_MAX_FILES   1000
#define  CHECK_PROGRESS_TIME  60

static int xl_strnicmp(const char* pStr1, const char* pStr2, int n)
{
	int i = 0;
	int result = 0;
	
	for (; pStr1[i] != '\0' && pStr2[i] != '\0' && i < n; i++)
	{
		result = tolower(pStr1[i]) - tolower(pStr2[i]);
		if (result != 0)
		{
			return result;
		}
	}
	
	if (i == n)
	{
		return 0;
	}
	
	// 执行到这里一定是有一个字符为'\0'了，不用再tolower进行比较了
	return pStr1[i] - pStr2[i];
}

static char to_hex(int in)
{
	if (in >= 0 && in < 10)
	{
		return '0' + in;
	}
	else
	{
		return 'A' + in - 10;
	}
}

void xl_bin_to_hex(char* hex, const unsigned char* in, int inlen)
{
	int i = 0;
	for (; i < inlen; i++)
	{
		hex[i * 2] = to_hex(in[i] >> 4);
		hex[i * 2 + 1] = to_hex(in[i] & 0xF);
	}

	hex[inlen * 2] = '\0';
}

int32 get_task_file_name(u32 task_id, char* file_name, int* p_file_name_length)
{
	char* suffix_pos = NULL;
	int32 result = 0;
	
	*file_name = '\0';
	result = et_get_task_file_name(task_id, file_name, p_file_name_length);
	suffix_pos = strrchr(file_name, '.');
	if((suffix_pos!=NULL)&&(xl_strnicmp(suffix_pos, ".td", *p_file_name_length)==0))
	{
		*suffix_pos = '\0';
		*p_file_name_length -= 3;
	}
	return result;
}

static int download_emule(const char* ed2k_link, const char* download_path);
static int download_bt_torrent(const char* torrent_path, const char* download_path);
static int download_bt_magnet(const char* magnet_link, const char* download_path);
static int download_p2sp(const char* url, const char* download_path);

int timeout = 0;
int max_size = 0;
int check_progress_time = 300;

int main(int argc, char *argv[]){
	if (argc < 5)
	{
		printf("usage:\r\nDownloader <http/ftp-url>|<BT torrent path>|<ED2K link> <download-path> <max_download_size> <time_out> [check_progress_time=300]\n");
	}
	else
	{
		int i = 0;
		int ret_code = 0;
		printf("download Start:\n");
		
		for(; i < argc; i++)
		{
			printf("%s\t", argv[i]);
		}
		printf("\n");
        max_size = atoi(argv[3]);
        timeout  = atoi(argv[4]);

        if(argc >= 6) 
        {
            check_progress_time = atoi(argv[5]);
        }


		et_set_partner_id(10171);
		printf("et_set_partner_id\n");
		
		et_init(NULL);
		printf("et_init\n");
		
		et_set_system_path(argv[2]);
		printf("et_set_system_path");
		
		if (xl_strnicmp(argv[1], "ed2k", 4) == 0)
		{
			ret_code = download_emule(argv[1], argv[2]);
		}
		else if (xl_strnicmp(argv[1], "magnet", 6) == 0)
		{
			ret_code = download_bt_magnet(argv[1], argv[2]);
		}
		else if (xl_strnicmp(argv[1], "http", 4) == 0 ||
			xl_strnicmp(argv[1], "ftp", 3) == 0)
		{
			ret_code = download_p2sp(argv[1], argv[2]);
		}
		else // 其他认为是本地BT种子路径
		{
			ret_code = download_bt_torrent(argv[1], argv[2]);
		}
		
		et_uninit();
		return ret_code;
	}
}

static bool jduge_down_continue(const ET_TASK& task_info, const time_t& start, const int& start_progress)
{
    time_t end;
    time(&end);
    time_t cost = end - start;
    float expect_time = 0.0;

    if (check_progress_time > 0 && cost > check_progress_time) {
        if (task_info._progress == start_progress)
            return false;
        expect_time = ((100.0 - start_progress) / (float)(task_info._progress - start_progress))
            * (float)cost * 1.1;
    }
    
    return task_info._task_status != ET_TASK_SUCCESS 
        && task_info._task_status != ET_TASK_FAILED
        && task_info._downloaded_data_size < max_size * 1024 * 1024 
        && expect_time < timeout;
}

static void printf_task_info(ET_TASK* task_info)
{
	static int count = 1;
	
	printf("printf_task_info[%d]: task_info->\n", count++);
	printf("\t_task_id = %d\n", task_info->_task_id);
	printf("\t_speed = %d\n", task_info->_speed);
	printf("\t_ul_speed = %d\n", task_info->_ul_speed);
	printf("\t_progress = %d\n", task_info->_progress);
	printf("\t_file_size = %lld\n", task_info->_file_size);
	printf("\t_task_status = %d\n", task_info->_task_status);
	printf("\t_failed_code = %d\n", task_info->_failed_code);
	printf("\t_file_create_status = %d\n", task_info->_file_create_status);
	printf("\t_downloaded_data_size = %lld\n", task_info->_downloaded_data_size);
	printf("\t_written_data_size = %lld\n", task_info->_written_data_size);
    fflush(stdout);
}

static int download_emule(const char* ed2k_link, const char* download_path)
{
	ET_ED2K_LINK_INFO ed2k_link_info;
	ET_TASK task_info;
	u32 task_id = 0;
	int32 result = 0;
	BOOL file_created = FALSE;
	char file_name[1024] = {'\0'};
	int32 file_name_length = 1024;
	
	// 解析URL
	memset(&ed2k_link_info, 0, sizeof(ed2k_link_info));
	et_extract_ed2k_url((char*)ed2k_link, &ed2k_link_info);
	
	printf("download_emule:\n\ted2k_link = %s, \n\tdownload_path = %s, \n\tfile_name = %s\n", ed2k_link, download_path, ed2k_link_info._file_name);
	result = et_create_emule_task(ed2k_link, strlen(ed2k_link),
		(char*)download_path, strlen(download_path),
		ed2k_link_info._file_name, strlen(ed2k_link_info._file_name),
		&task_id);
	
	printf("et_create_emule_task result = %d, task_id = %u\n", result, task_id);
	
	if (result != 0)
	{
		printf("create task failed!");
		return result;
	}
	
	result = et_start_task(task_id);
	printf("et_start_task result = %d\n", result);
	if (result != 0)
	{
		printf("start task failed!");
		return result;
	}
	
	memset(&task_info, 0, sizeof(task_info));
    time_t start_time;
    time(&start_time);

    result = et_get_task_info(task_id, &task_info);
    if (result != 0)
    {
        printf("et_get_task_info failed!, result=%d, I exit with -1\n", result);
        return -1;
    }
    int start_progress = task_info._progress;
	do
	{
		result = et_get_task_info(task_id, &task_info);
		printf("et_get_task_info: result = %d\n", result);
		if (result != 0)
		{
			printf("et_get_task_info failed!\n");
			break;
		}
		
        start_progress = task_info._progress;
		printf_task_info(&task_info);
		
		if (!file_created && task_info._file_create_status == ET_FILE_CREATED_SUCCESS)
		{
			printf("target file created\n");
			file_name_length = 1024;
			result = get_task_file_name(task_id, file_name, &file_name_length);
			printf("get_task_file_name: result = %d, file name is %s\n", result, file_name);
			if (result != 0)
			{
				printf("get_task_file_name failed!\n");
			}
			else
			{
                time(&start_time);
				file_created = TRUE;
			}
		}
		sleep(1);
	} while(jduge_down_continue(task_info, start_time, start_progress));

	printf("download loop break, task_status=%d\n", task_info._task_status);
    if (task_info._task_status == ET_TASK_RUNNING)
        printf("speed too slow, downloader may be timeout, so I exit now\n");
	
	result = et_stop_task(task_id);
	printf("et_stop_task: result = %d", result);
	
    if(task_info._task_status == ET_TASK_FAILED)
    {
        printf("download task failed! \n");
        et_delete_task(task_id);
        return -1;

    }

	// 再次获取任务状态
	result = et_get_task_info(task_id, &task_info);

	printf("et_get_task_info: result = %d\n", result);
	if (result != 0)
	{
		printf("et_get_task_info failed!\n");

	}
	printf_task_info(&task_info);
	
	if (!file_created && task_info._file_create_status == ET_FILE_CREATED_SUCCESS)
	{
		printf("target file created\n");
		file_name_length = 1024;
		result = get_task_file_name(task_id, file_name, &file_name_length);
		printf("get_task_file_name: result = %d, file name is %s\n", result, file_name);
		if (result != 0)
		{
			printf("get_task_file_name failed!\n");
		}
		else
		{
			file_created = TRUE;
		}
	}
	
	result = et_delete_task(task_id);
	printf("et_delete_task: result = %d\n", result);
    return task_info._task_status == ET_TASK_SUCCESS ? 0:-1;
	
	// 删除下载文件
	/*if (task_info._task_status == ET_TASK_SUCCESS)
	{
		char file_full_path[1024] = {'\0'};
		
		strcpy(file_full_path, download_path);
		strcat(file_full_path, file_name);
		unlink(file_full_path);
	}
	else
	{
		result = et_remove_tmp_file((char*)download_path, file_name);
		printf("et_remove_tmp_file: result = %d", result);
	}*/

}

static void printf_bt_file_info(ET_BT_FILE* file_info)
{

}

static void delete_bt_download_file(const char* torrent_path, const char* download_path)
{
	ET_TORRENT_SEED_INFO* p_torrent_info = NULL;
	int32 result = 0;
	char full_path[1024] = {'\0'};
	char* p_download_path_end = NULL;
	int32 len = 0;

	result = et_get_torrent_seed_info((char*)torrent_path, &p_torrent_info);
	if (p_torrent_info == NULL)
	{
		return;
	}
	
	strcpy(full_path, download_path);
	len = strlen(full_path); 
	if( full_path[len-1] != '/')
	{
		strcat(full_path, "/");
		len += 1;
	}
	
	p_download_path_end = full_path + len;
	
	// 1.如果BT种子中有多个文件，下载文件存储在以title命名的目录下
	//   直接递归删除目录就可以删除该任务下载过程中产生的所有文件
	//	 sd_delete_dir封装了递归删除一个目录的逻辑
	// 2.如果BT种子中只有一个文件，则title以该文件名命名，直接删除可以删除已完成的下载文件
	strcat(full_path, p_torrent_info->_title_name);
	sd_delete_dir(full_path);

	// 3.如果BT种子中只有一个文件，且没有完成，需要删除该文件同名的".td"和".td.cfg"文件
	//   另外要删除以该任务info_hash命名的".tmp"和".tmp.cfg"文件，这两个文件用于存放下载
	//	 BT任务过程中产生的分块边界内容，校验的时候需要用到
	// 注意：下面的逻辑是删除第一个文件，等价于，删除单文件BT任务的所有文件（只有一个文件）
	if( p_torrent_info->file_info_array_ptr[0]->_file_path_len == 0 )
	{
		char info_hash[INFO_HASH_LEN * 2 + 1] = {'\0'};
	
		strcat(full_path, ".td");
		sd_delete_dir(full_path);
		
		strcat(full_path, ".cfg");
		sd_delete_dir(full_path);				

		xl_bin_to_hex(info_hash, p_torrent_info->_info_hash, INFO_HASH_LEN);
		info_hash[INFO_HASH_LEN * 2] = '\0';
		
		strcpy(p_download_path_end, info_hash);
		strcat(full_path, ".tmp");

		sd_delete_dir(full_path);				

		strcat(full_path, ".cfg");

		sd_delete_dir(full_path);				
	}

	et_release_torrent_seed_info(p_torrent_info);
}

static int download_bt_torrent(const char* torrent_path, const char* download_path)
{
	ET_TORRENT_SEED_INFO* p_torrent_info = NULL;
	ET_TASK task_info;
	u32 task_id = 0;
	int32 result = 0;
	BOOL file_created = FALSE;
	char file_name[1024] = {'\0'};
	int32 file_name_length = 1024;
	// u32 file_index_array[3] = {0, 1, 2}; // 只下载前三个
	// ET_BT_FILE file_info[3];
	u32 file_num = 3;
	int i = 0;
	
	// 解析种子文件
	result = et_get_torrent_seed_info((char*)torrent_path, &p_torrent_info);
	printf("download_bt_torrent:\n\torrent_path = %s, \n\tdownload_path = %s, \n\tp_torrent_info = 0x%x\n", torrent_path, download_path, p_torrent_info);
	if (p_torrent_info == NULL)
	{
		printf("parse torrent failed!");
		return result;
	}
    

    ET_BT_FILE file_info[BT_MAX_FILES];
    u32 file_index_array[BT_MAX_FILES] = {0} ; // max download BT_MAX_FILES files

    printf("***************\nfile_count is: [%d]\n", BT_MAX_FILES);

	file_num = 0;
	for (i = 0; i < p_torrent_info->_file_num && file_num < BT_MAX_FILES; i++)
	{
		if (xl_strnicmp(p_torrent_info->file_info_array_ptr[i]->_file_name, "_____padding_file", 16) != 0) // 剔除填充文件
		{
			file_index_array[file_num++] = i;
		}
	}
	
	result = et_create_bt_task((char*)torrent_path, strlen(torrent_path),
		(char*)download_path, strlen(download_path),
		file_index_array, file_num,
		ET_ENCODING_PROTO_MODE,
		&task_id);
	
	printf("et_create_bt_task result = %d, task_id = %u\n", result, task_id);
	
	if (result != 0)
	{
		printf("create task failed!");
		et_release_torrent_seed_info(p_torrent_info);
		return result;
	}
	
	result = et_start_task(task_id);
	printf("et_start_task result = %d\n", result);
	if (result != 0)
	{
		printf("start task failed!");
		et_release_torrent_seed_info(p_torrent_info);
		return result;
	}
	
	memset(&task_info, 0, sizeof(task_info));
	memset(file_info, 0, sizeof(file_info));

    time_t start_time;
    time(&start_time);

    result = et_get_task_info(task_id, &task_info);
    if (result != 0)
    {
        printf("et_get_task_info failed!, result=%d, I exit with -1\n", result);
        return -1;
    }
    int start_progress = task_info._progress;
	do
	{
		result = et_get_task_info(task_id, &task_info);
		printf("et_get_task_info: result = %d\n", result);
		if (result != 0)
		{
			printf("et_get_task_info failed!\n");
			break;
		}
		printf_task_info(&task_info);
        if (task_info._task_status != ET_TASK_FAILED)
        {
            for (i = 0; i < file_num; i++)
            {
                result = et_get_bt_file_info(task_id, file_index_array[i], &file_info[i]);
                printf("et_get_bt_file_info[%d]: result = %d; ", i, result);
                printf_bt_file_info(&file_info[i]);
            }
            printf("\n");
        }
		sleep(1);
	} while(jduge_down_continue(task_info, start_time, start_progress));

	printf("download loop break, task_status=%d\n", task_info._task_status);
    if (task_info._task_status == ET_TASK_RUNNING)
        printf("speed too slow, downloader may be timeout, so I exit now\n");
    
	result = et_stop_task(task_id);
	printf("et_stop_task: result = %d", result);
	if(task_info._task_status == ET_TASK_FAILED)
	{
		printf("download task failed! \n");
		return -1;

	}
	
	// 再次获取任务状态
	result = et_get_task_info(task_id, &task_info);
	printf("et_get_task_info: result = %d\n", result);
	if (result != 0)
	{
		printf("et_get_task_info failed!\n");
	}
	
	printf_task_info(&task_info);
    
    if (task_info._task_status != ET_TASK_FAILED)
    {
        for (i = 0; i < file_num; i++)
        {
            result = et_get_bt_file_info(task_id, file_index_array[i], &file_info[i]);
            printf("et_get_bt_file_info[%d]: result = %d; ", i, result);
            printf_bt_file_info(&file_info[i]);
        }
        printf("\n");
    }
	
	result = et_delete_task(task_id);
	printf("et_delete_task: result = %d\n", result);
	
    return task_info._task_status == ET_TASK_SUCCESS ? 0:-1;

	// 删除下载文件
	/*delete_bt_download_file(torrent_path, download_path);
	
	et_release_torrent_seed_info(p_torrent_info);*/
}

static int download_bt_magnet(const char* magnet_link, const char* download_path)
{
	ET_TASK task_info;
	u32 task_id = 0;
	int32 result = 0;
	char file_name[1024] = "dummy.torrent";
	int32 file_name_length = 1024;
	BOOL seed_download = FALSE;
	
	printf("download_bt_magnet:\n\turl = %s, \n\tdownload_path = %s, \n\tfile_name = %s\n", magnet_link, download_path, file_name);
	result = et_create_bt_magnet_task((char*)magnet_link, strlen(magnet_link),
		(char*)download_path, strlen(download_path),
		file_name, strlen(file_name),
		TRUE, // 只下载种子文件
		ET_ENCODING_PROTO_MODE,
		&task_id);
	
	printf("et_create_bt_magnet_task result = %d, task_id = %u\n", result, task_id);
	
	if (result != 0)
	{
		printf("create task failed!");
		return result;
	}
	
	result = et_start_task(task_id);
	printf("et_start_task result = %d\n", result);
	if (result != 0)
	{
		printf("start task failed!");
		return result;
	}
	
	memset(&task_info, 0, sizeof(task_info));
    time_t start_time;
    time(&start_time);

    result = et_get_task_info(task_id, &task_info);
    if (result != 0)
    {
        printf("et_get_task_info failed!, result=%d, I exit with -1\n", result);
        return -1;
    }
    int start_progress = task_info._progress;

	do
	{
		result = et_get_task_info(task_id, &task_info);
		printf("et_get_task_info: result = %d\n", result);
		if (result != 0)
		{
			printf("et_get_task_info failed!\n");
			break;
		}
		
		printf_task_info(&task_info);
	    
        if (task_info._task_status != ET_TASK_FAILED)
        {
            if (!seed_download)
            {
                result = et_get_bt_magnet_torrent_seed_downloaded(task_id, &seed_download);
                printf("et_get_bt_magnet_torrent_seed_downloaded: result = %d, seed_download = %d\n", result, seed_download);
            }
        }
		sleep(1);

	} while(jduge_down_continue(task_info, start_time, start_progress));
		
	printf("download loop break, task_status=%d\n", task_info._task_status);
    if (task_info._task_status == ET_TASK_RUNNING)
        printf("speed too slow, downloader may be timeout, so I exit now\n");

	result = et_stop_task(task_id);
	printf("et_stop_task: result = %d", result);
    if(task_info._task_status == ET_TASK_FAILED)
    {
        printf("download task failed! \n");
        et_delete_task(task_id);
        return -1;
    }
	
	// 再次获取任务状态
	result = et_get_task_info(task_id, &task_info);
	printf("et_get_task_info: result = %d\n", result);
	if (result != 0)
	{
		printf("et_get_task_info failed!\n");
	}
	
	printf_task_info(&task_info);

	result = et_delete_task(task_id);
	printf("et_delete_task: result = %d\n", result);
	
	// 删除下载文件
	/*if (task_info._task_status == ET_TASK_SUCCESS)
	{
		char file_full_path[1024] = {'\0'};
		
		strcpy(file_full_path, download_path);
		strcat(file_full_path, file_name);
		unlink(file_full_path);
	}
	else
	{
		result = et_remove_tmp_file((char*)download_path, file_name);
		printf("et_remove_tmp_file: result = %d", result);
	}*/
    return task_info._task_status == ET_TASK_SUCCESS ? 0:-1;
}

static int download_p2sp(const char* url, const char* download_path)
{
	URL_OBJECT url_object;
	ET_TASK task_info;
	u32 task_id = 0;
	int32 result = 0;
	BOOL file_created = FALSE;
	char file_name[1024] = {'\0'};
	int32 file_name_length = 1024;
	char unknown_file_name[] = "unknown_file_name";
	char empty_string[] = "";
	
	// 解析URL
	memset(&url_object, 0, sizeof(url_object));
	sd_url_to_object(url, strlen(url), &url_object);
	
	if (url_object._file_name == NULL)
	{
		url_object._file_name = unknown_file_name;
		url_object._file_name_len = sizeof(unknown_file_name);
	}
	
	strncpy(file_name, url_object._file_name, url_object._file_name_len);
	file_name[url_object._file_name_len] = '\0';
	
	printf("download_p2sp:\n\turl = %s, \n\tdownload_path = %s, \n\tfile_name = %s\n", url, download_path, url_object._file_name);
	result = et_create_new_task_by_url((char*)url, strlen(url),
		empty_string, 0,
		empty_string, 0,
		(char*)download_path, strlen(download_path),
		file_name, url_object._file_name_len,
		&task_id);
	
	printf("et_create_new_task_by_url result = %d, task_id = %u\n", result, task_id);
	
	if (result != 0)
	{
		printf("create task failed!\n");
		return result;
	}
	
	result = et_start_task(task_id);
	printf("et_start_task result = %d\n", result);
	if (result != 0)
	{
		printf("start task failed!\n");
		return result;
	}
	
	result = et_set_origin_mode(task_id, FALSE); // 多资源加速
	printf("et_set_origin_mode result = %d\n", result);
	if (result != 0)
	{
		printf("et_set_origin_mode failed!\n");
		return result;
	}
	
	memset(&task_info, 0, sizeof(task_info));
    time_t start_time;
    time(&start_time);

    result = et_get_task_info(task_id, &task_info);
    if (result != 0)
    {
        printf("et_get_task_info failed!, result=%d, I exit with -1\n", result);
        return -1;
    }
    int start_progress = task_info._progress;
	do
	{
		result = et_get_task_info(task_id, &task_info);
		printf("et_get_task_info: result = %d\n", result);
		if (result != 0)
		{
			printf("et_get_task_info failed!\n");
			break;
		}
	    	
		printf_task_info(&task_info);
		
		if (!file_created && task_info._file_create_status == ET_FILE_CREATED_SUCCESS)
		{
			printf("target file created\n");
			file_name_length = 1024;
			result = get_task_file_name(task_id, file_name, &file_name_length);
			printf("get_task_file_name: result = %d, file name is %s\n", result, file_name);
			if (result != 0)
			{
				printf("get_task_file_name failed!\n");
			}
			else
			{
                // create file done, reset start_time
                time(&start_time);
				file_created = TRUE;
			}
		}
		sleep(1);
        
	} while(jduge_down_continue(task_info, start_time, start_progress));

	printf("download loop break, task_status=%d\n", task_info._task_status);
    if (task_info._task_status == ET_TASK_RUNNING)
        printf("speed too slow, downloader may be timeout, so I exit now\n");

	result = et_stop_task(task_id);
	printf("et_stop_task: result = %d\n", result);
    if(task_info._task_status == ET_TASK_FAILED)
    {
        printf("download task failed! \n");
        et_delete_task(task_id);
        return -1;
    }
	// 再次获取任务状态
	result = et_get_task_info(task_id, &task_info);
	printf("et_get_task_info: result = %d\n", result);
	if (result != 0)
	{
		printf("et_get_task_info failed!\n");
	}
	
	printf_task_info(&task_info);
	
	if (!file_created && task_info._file_create_status == ET_FILE_CREATED_SUCCESS)
	{
		char* suffix_pos = NULL;
		printf("target file created\n");
		file_name_length = 1024;
		result = get_task_file_name(task_id, file_name, &file_name_length);
		printf("get_task_file_name: result = %d, file name is %s\n", result, file_name);
		if (result != 0)
		{
			printf("get_task_file_name failed!\n");
		}
		else
		{
			file_created = TRUE;
		}
	}
	
	result = et_delete_task(task_id);
	printf("et_delete_task: result = %d\n", result);
	
	// 删除下载文件
	/*if (task_info._task_status == ET_TASK_SUCCESS)
	{
		char file_full_path[1024] = {'\0'};
		
		strcpy(file_full_path, download_path);
		strcat(file_full_path, file_name);
		unlink(file_full_path);
	}
	else
	{
		result = et_remove_tmp_file((char*)download_path, file_name);
		printf("et_remove_tmp_file: result = %d", result);
	}*/

    return task_info._task_status == ET_TASK_SUCCESS ? 0:-1;
}
