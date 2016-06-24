#ifndef SD_EMBEDTHUNDER_H_00138F8F2E70_200809081558
#define SD_EMBEDTHUNDER_H_00138F8F2E70_200809081558
/*--------------------------------------------------------------------------*/
/*                               IDENTIFICATION                             */
/*--------------------------------------------------------------------------*/
/*                  Shenzhen XunLei Networks			                    */
/*--------------------------------------------------------------------------*/
/*                  - C (copyright) - www.xunlei.com -		     		    */
/*                                                                          */
/*      This document is the proprietary of XunLei                          */
/*                                                                          */
/*      All rights reserved. Integral or partial reproduction               */
/*      prohibited without a written authorization from the                 */
/*      permanent of the author rights.                                     */
/*                                                                          */
/*--------------------------------------------------------------------------*/
/*--------------------------------------------------------------------------*/
/*                         FUNCTIONAL DESCRIPTION                           */
/*--------------------------------------------------------------------------*/
/* This file contains the platforms of EmbedThunder                         */
/*--------------------------------------------------------------------------*/

#ifdef __cplusplus
extern "C" 
{
#endif

#ifdef WIN32
  #ifdef WINCE
	#define ETDLL_API
  #else
	#ifdef ETDLL_EXPORTS
	#define ETDLL_API __declspec(dllexport)
	#else
	#define ETDLL_API __declspec(dllimport)
	#endif
  #endif
#else
	#define ETDLL_API
#endif

/************************************************************************/
/*                    TYPE DEFINE                                       */
/************************************************************************/
typedef unsigned char		u8;
typedef unsigned short		u16;
typedef unsigned int		u32;
typedef char				int8;
typedef short				int16;
typedef int					int32;
#if defined(LINUX) 
	typedef unsigned long long	uint64;
	typedef long long			int64;
#else
	#ifdef  NOT_SUPPORT_LARGE_INT_64
		typedef unsigned int	uint64;
		typedef int			__int64;
	#else
        #if defined(WINCE)
		typedef unsigned __int64 uint64;
		typedef unsigned __int64 u64;
		//typedef long long			__int64;
         #else
		typedef unsigned long	long uint64;
		typedef long long			__int64;
         #endif
	#endif
#endif

#if defined(LINUX) 
#ifndef NULL
#define NULL	((void*)(0))
#endif
#endif

#ifndef TRUE
typedef int32 BOOL;
typedef int32 _BOOL;
#define TRUE	(1)
#define FALSE	(0)
#else
typedef int32 _BOOL;
#endif

/************************************************************************/
/*                    STRUCT DEFINE                                     */
/************************************************************************/

// 任务状态
enum ET_TASK_STATUS
{
	ET_TASK_IDLE = 0, // 初始状态
	ET_TASK_RUNNING, // 运行状态，正在下载
	ET_TASK_VOD, // 点播状态，暂不支持
	ET_TASK_SUCCESS, // 完成状态
	ET_TASK_FAILED, // 失败状态
	ET_TASK_STOPPED // 暂停状态
};

// 文件状态
enum ET_TASK_FILE_CREATE_STATUS
{
	ET_FILE_NOT_CREATED = 0, // 文件还没有创建
	ET_FILE_CREATED_SUCCESS, // 文件已经成功创建
	ET_FILE_CREATED_FAILED // 文件创建失败
};

// 解析种子时，其中的非ASCII码（如：中文）返回编码格式
enum ET_ENCODING_SWITCH_MODE 
{ 
	ET_ENCODING_PROTO_MODE = 0, /* 返回原始字段 */
	ET_ENCODING_GBK_SWITCH = 1,/*  返回GBK格式编码 */
	ET_ENCODING_UTF8_SWITCH = 2,/* 返回UTF-8格式编码 */
	ET_ENCODING_BIG5_SWITCH = 3,/* 返回BIG5格式编码  */
	
	ET_ENCODING_UTF8_PROTO_MODE = 4,/* 返回种子文件中的utf-8字段  */
	ET_ENCODING_DEFAULT_SWITCH = 5/* 未设置输出格式(使用et_set_seed_switch_type的全局输出设置)  */
};

// 下载文件命名规则
typedef enum _tag_et_filename_policy
{
    ET_FILENAME_POLICY_DEFAULT_SMART = 0,        // 默认智能命名文件名
    ET_FILENAME_POLICY_SIMPLE_USER               //用户命名文件名
}ET_FILENAME_POLICY;

typedef struct t_et_download_task_info
{
	u32  _task_id;
	u32 _speed;    /*任务的下载速度*/
	u32 _server_speed;   /*任务server 资源的下载速度*/  
	u32 _peer_speed;   /*任务peer 资源的下载速度*/  
	u32 _ul_speed;    /*任务的上传速度*/
	u32 _progress;  /*任务进度*/  
	u32 _dowing_server_pipe_num; /*任务server 连接数*/  
	u32 _connecting_server_pipe_num;  /*任务server 正在连接数*/  
	u32 _dowing_peer_pipe_num;  /*任务peer 连接数*/  
	u32 _connecting_peer_pipe_num; /*任务pipe 正在连接数*/  
	uint64 _file_size;  /*任务文件大小*/  

      /*任务状态: 	ET_TASK_IDLE  		空闲
                                	ET_TASK_RUNNING 	正在运行
                                 	ET_TASK_VOD 		数据已下载完成，正在播放中
                                 	ET_TASK_SUCCESS 	任务成功
                                 	ET_TASK_FAILED 		任务失败，失败码为failed_code
                                 	ET_TASK_STOPPED 	任务已停止
	 */  
	enum ET_TASK_STATUS  _task_status;   

	 /*任务失败原因
              102  无法纠错
              103  无法获取cid
              104  无法获取gcid
              105  cid 校验错误
              106  gcid校验错误
              107  创建文件失败
              108  写文件失败
              109  读文件失败
              112  空间不足无法创建文件
              113 校验cid时读文件错误 
              130  无资源下载失败

              15400 子文件下载失败(bt任务)
              
         */  	  
	u32  _failed_code;
	 
	/* Time information  */
	/* 注意：1.这两个时间是获得自1970年1月1日开始的秒数
		 		2.考虑到在获取任务开始时间（_start_time）和完成时间（_finished_time）之间，系统的时间有可能被恶意更改而导致开始时间大于完成时间，
		 		或者完成时间远远大于开始时间（如大于1个月），这种情况下，用这两个时间直接作相减运算没有任何意义。
		 		因此，不能用这两个时间计算任务所用的时间或者计算平均速度
		 		3.对于续传任务，开始时间（_start_time）记录的是续传这个任务的开始时间   */
	u32 _start_time;	
	u32 _finished_time;

	enum ET_TASK_FILE_CREATE_STATUS _file_create_status;
	uint64 _downloaded_data_size; 		 /*已下载的数据大小*/  
	uint64 _written_data_size;  /*已写入磁盘的数据大小*/  

        //下面几个属性是是任务生命周期的统计数据
	/*以下几个值除file_size,first_byte_arrive_time外, 都在stop(或重启)后累计计算,时长单位默认是秒, xxx_recv_size 是未校验过的,xxx_download_size 是已校验过的*/
	uint64 _orisrv_recv_size;	/*原始路径下载字节数*/
	uint64 _orisrv_download_size;

	uint64 _altsrv_recv_size;	/*候选url下载字节数*/
	uint64 _altsrv_download_size;

	uint64 _hsc_recv_size;	/*高速通道下载字节数*/
	uint64 _hsc_download_size;

	uint64 _p2p_recv_size;	/*p2p下载字节数*/
	uint64 _p2p_download_size;

	uint64 _lixian_recv_size;	/*离线下载字节数*/
	uint64 _lixian_download_size;

	uint64 _total_recv_size;      //接收数据大小
	//uint64 total_download_size;  //有效数据下载大小
	
	u32 _download_time;           //下载用时

	u32 _first_byte_arrive_time;//起速时长, 任务开始后收到第一个字节的时长,单位秒	
	u32 _zero_speed_time;	//零速时长,每秒统计一次, 任务开始后(已起速),在该秒内没收任何新数据,则认为该秒属于0速段,将该值+1
	u32 _checksum_time;		//校验时长
    
}ET_TASK;


typedef struct  t_et_bt_file
{
	u32 _file_index; // 文件索引，种子中的第几个文件
	uint64 _file_size;	 // 文件大小
	uint64 _downloaded_data_size; 		 /*已下载的数据大小*/  
	uint64 _written_data_size; 			 /*已写进磁盘的数据大小*/  
	u32 _file_percent;/* 文件下载进度    */	

	/*文件状态:
		0:文件未处理
		1:文件正在下载
		2:文件下载完成
		3:文件下载失败 
	*/
	u32 _file_status;


	/*服务器查询状态:
		0:未查询，
		1:正在查询, 
		2:查询成功，
		3:查询失败 
	*/
	u32 _query_result;

	
	/*子任务失败原因错误码
		 15383  无法纠错
		 15393  cid 校验错误
		 15386  gcid校验错误
		 15394  创建文件失败
		 15395  数据下载成功,等待piece校验(临时状态,piece校验成功后子文件成功)
		 108  写文件失败
		 109  读文件失败
		 112  空间不足无法创建文件
		 113 校验cid时读文件错误
		 130  无资源下载失败
		 131  查询资源失败

		 15389 子文件速度太慢
	*/	   
	u32 _sub_task_err_code;

	BOOL _has_record; /* 为1 表示xunlei资源库中有该文件的记录，可以通过p2sp网络进行加速 */
	
	/*通过p2sp网络进行加速的状态:
		0:未加速，
		1:正在加速, 
		2:加速成功，
		3:加速失败，
		4:加速完成。意思是指不管加速成功或失败，总之这个文件已经被加速过，不会再被加速	*/
	u32 _accelerate_state; 
	
}ET_BT_FILE;

typedef struct  t_et_proxy_info
{
	char _server[32]; // 代理服务器地址
	char _user[32]; // 代理服务器用户名
	char _password[32]; // 代理服务器用户密码

	u32 _port; // 代理服务器端口号

	int32 _proxy_type; /* 0 direct connect type, 1 socks5 proxy type, 	2 http_proxy type, 3 ftp_proxy type */
	int32 _server_len;
	int32 _user_len;
	int32 _password_len;
} ET_PROXY_INFO;

/* Structures for bt downloading */

#define ET_MAX_TD_CFG_SUFFIX_LEN (8)

// BT种子子文件信息
typedef struct t_et_torrent_file_info
{
	u32 _file_index; // 文件索引，第几个文件
	char *_file_name; // 文件名
	u32 _file_name_len; // 
	char *_file_path; // 文件相对路径
	u32 _file_path_len;
	uint64 _file_offset; // 文件偏移量
	uint64 _file_size; // 文件大小
} ET_TORRENT_FILE_INFO;

typedef struct t_et_torrent_seed_info
{
	char _title_name[512-ET_MAX_TD_CFG_SUFFIX_LEN]; // 种子标题
	u32 _title_name_len;
	uint64 _file_total_size; // 所有文件总大小
	u32 _file_num; // 文件个数
	u32 _encoding;//种子文件编码格式，GBK = 0, UTF_8 = 1, BIG5 = 2
	unsigned char _info_hash[20]; // 种子的编号
	ET_TORRENT_FILE_INFO ** file_info_array_ptr; // 子文件列表
} ET_TORRENT_SEED_INFO;

/*--------------------------------------------------------------------------*/
/*                Interfaces provid by EmbedThunder download library				        */
/*--------------------------------------------------------------------------*/

/*
 * 设置合作ID，在init前调用，强烈不建议在et_reporter_set_version中设置，
 * 因为在et_init中就要用到partner_id和服务器交互，而et_reporter_set_version依赖et_init接口中一些初始化数据
*/
ETDLL_API void et_set_partner_id(u32 partner_id);

/*--------------------------------------------------------------------------*/
/*                下载库的初始化和反初始化接口				        */
/*--------------------------------------------------------------------------*/
/*
  * 初始化下载库 
  * 返回值: 0    成功
                      1025  初始分配内存失败
                      3672 下载库已经被初始化过了
                      4112 非法参数
                      其它初始化下载库线程失败错误码 
  * 如果连接hub不需要代理，proxy_for_hub设置成NULL或proxy_type为0
  *
  * 注意：迅雷下载库的所有其他所有接口都必须在这个函数之后才能调用，否则会出错（返回-1）！
  */
ETDLL_API int32 et_init(ET_PROXY_INFO* proxy_for_hub);

/*
  * 反初始化下载库 
  * 返回值: 0    成功       
  * 
  * 注意：1.迅雷下载库的所有其他所有接口（除了et_init）都不能在这个函数之后调用，否则会出错（返回-1）！
 */
ETDLL_API int32 et_uninit(void);

/*--------------------------------------------------------------------------*/
/*              license相关接口			        
----------------------------------------------------------------------------*/
/* 设置此客户端的 license 
  * 返回值: 0    成功       
  			   1925 	获取网卡MAC 出错
  			   
*  注意：请务必在下载库初始化之后启动下载任务（et_start_task）之前调用此函数
*/
ETDLL_API  int32 	et_set_license(char *license, int32 license_size);

/*--------------------------------------------------------------------------*/
/*              下载库全局参数配置相关接口			        
----------------------------------------------------------------------------*/
/*
  * 获取下载库版本号, 返回值是版本号的字符串
  *                   
  */
ETDLL_API const char* et_get_version(void);

/*
  * 设置下载记录文件的路径，这个文件用于记录下载库所有成功下载过并且还没有被删除掉的文件的信息。
  *	注意：1.路径不可为空，长度不能为0且长度不超过255字节，要以'/'符号结束，可以是绝对路径，也可以是相对路径。
  *   			   2.该文件夹一定要存在并且是可写的，因为下载库需要在此文件夹创建文件。
  *                    3.这个函数必须在下载库被初始化后，创建任务之前调用。
  */
ETDLL_API  int32 et_set_download_record_file_path(const char *path,u32  path_len);

/************************************************* 
  Function:    et_set_decision_filename_policy   
  Description: 设置文件命名策略，用于解决MIUI添加后缀名的问题
  Input:       ET_FILENAME_POLICY namepolicy 取值范围:  
                                             ET_FILENAME_POLICY_DEFAULT_SMART:智能命名
                                             ET_FILENAME_POLICY_SIMPLE_USER: 用户命名
  Output:      无
  Return:      成功返回: SUCCESS

  History:     created: chenyangyuan 2013-10-12    
               modified:   
*************************************************/
ETDLL_API int32 et_set_decision_filename_policy(ET_FILENAME_POLICY namepolicy);

/*
  * 设置最大任务数,最少1个，最多16个，否则，返回4112错误
  *                   
  */
ETDLL_API int32 et_set_max_tasks(u32 task_num);

/*
  * 获取最大任务数
  *  
  * 注意：若返回-1，表示下载库还没有被初始化！
  */
ETDLL_API u32 et_get_max_tasks(void);

/*
  * 设置最大下载速度和上传速度,以KB为单位,-1表示不限速
  *                   
  * 注意：1.download_limit_speed和upload_limit_speed为下载库所有接收到和发出去的数据量，包括了与外面服务器的各种通信指令和要下载的文件内容，
  *			因此，这两个值均不能设得太小，因为upload_limit_speed设置得太小会严重影响下载速度，得不偿失!
  *			2.这两个值更不能设为0，否则返回4112 错误！
  *			3.如果没有特殊要求，建议不要调用这个接口，因为下载库会根据资源状况自行选择合适的速度。
  *			4.如果下载库是用root帐户运行的话，下载库还会根据网络状况自行调节下载和上传速度，达到智能限速，
  *			这样就会在保持合理的下载速度的同时又不影响同一局域网内其他电脑的网络速度。
 */
ETDLL_API int32 et_set_limit_speed(u32 download_limit_speed, u32 upload_limit_speed);

/*
  * 获取最大速度,以KB为单位
  *                   
  */
ETDLL_API int32 et_get_limit_speed(u32* download_limit_speed, u32* upload_limit_speed);

/*
  * 设置任务最大连接数
  *                   
  * 注意：connection_num 的取值范围为[1~200]，否则返回4112 错误！如果没有特殊要求，建议不要调用这个
  *       		接口，因为下载库会根据资源状况自行选择合适的连接数。
  */
ETDLL_API int32 et_set_max_task_connection(u32 connection_num);

/*
  * 获取任务最大连接数
  *                   
  * 注意：若返回-1，表示下载库还没有被初始化！
  */
ETDLL_API u32 et_get_max_task_connection(void);

/*
 * 获取底层下行速度
 * 注意：底层下行速度为下载库所有接收到的数据量，包括了与外面服务器的各种通信指令和要下载的文件内容，
 *			因此，这个速度通常是大于或等于所有任务在et_get_task_info的ET_TASK结构体中的下载速度(_speed)之和!                   
 *
 */
ETDLL_API u32 et_get_current_download_speed(void);

/*
 * 获取底层上传速度
  * 注意：底层上传速度为下载库所有发出去的数据量，包括了与外面服务器的各种通信指令和点对点协议里的文件内容上传，
  *			因此，这个速度通常是大于或等于所有任务在et_get_task_info的ET_TASK结构体中的上传速度(_ul_speed)之和!                   
 *
 */
ETDLL_API u32 et_get_current_upload_speed(void);

/*
  * 得到下载库内当前所有的task的id，*buffer_len为task_id_buffer的长度，当*buffer_len不够时，返回4115，并在*buffer_len带回正确的长度。 
  * 返回值: 0    成功
                        4112 参数错误，buffer_len和task_id_buffer不能为空
                        4113 当前没有任何任务
                        4115 buffer不够，需要更长的buffer size
  *
  * 注意：如果返回4115，表示所需的task_id_buffer不够长，需要重新传入更多的buffer！
  *                 
  */
ETDLL_API int32 et_get_all_task_id(  u32 *buffer_len, u32 *task_id_buffer );

/*--------------------------------------------------------------------------*/
/*              task相关接口			        
----------------------------------------------------------------------------*/
/*
  * 创建url下载的新任务
  * 参数说明：
  *		url:	下载目标地址
  *		ref_url: 下载引用页
  *		description:任务描述信息
  *		file_path:	文件存放地址
  *		file_name:	下载文件名
  *		task_id: 创建的任务ID
  * 返回值: 0    成功，task_id 标识成功创建的任务
                        4103 已经超过最大任务数
			   4119 操作冲突。由于迅雷下载库同一时间只能处理一个任务的创建或删除，如果用户想同时创建或/和删除两个或以上的任务，会有冲突！                       
			   4200  非法url
                        4201  非法path
                        4202 非法filename
                        4216 已经有另一个具有相同url的任务存在
                        4222 所要下载的文件已经存在

  *                   
  * 注意：1.参数url和file_path切不可为NULL，相应的url_length和file_path_len也不能为0，并且url_length最大
  *       不能超过511字节，file_path_len不能超过255字节,要确保file_path为已存在的路径(绝对路径和相对路径均可)，而且file_path的末尾要有字符'/'。
  *       参数ref_url和description要是没有的话可等于NULL,相应的ref_url_length和description_len也可为0，有的话ref_url_length和description_len不能大于511；
  *       另外file_name也可为空或file_name_length等于0，这种情况下，迅雷将从url中解析出文件名，如果有的话file_name要符合linux文件名的命名规则，file_name_length不能大于255。
  *       2.目前只能接受"http://","https://","ftp://"和"thunder://"开头的url.
  */
ETDLL_API int32 et_create_new_task_by_url(char* url, u32 url_length, 
							  char* ref_url, u32 ref_url_length,
							  char* description, u32 description_len,
							  char* file_path, u32 file_path_len,
							  char* file_name, u32 file_name_length, 
							  u32* task_id);

/*
  * 创建url下载的断点续传任务，要求cfg配置文件存在，否则创建任务失败
  * 参数参照et_create_new_task_by_url函数说明
  * 返回值: 0    成功，task_id 标识成功创建的任务       
                        4103 已经超过最大任务数
			   4119 操作冲突。由于迅雷下载库同一时间只能处理一个任务的创建或删除，如果用户想同时创建或/和删除两个或以上的任务，会有冲突！                       
                        4199  对应的.cfg文件不存在
                        4200  非法url
                        4201  非法path
                        4202 非法filename
                        4216 已经有另一个具有相同url的任务存在
                        4222 所要下载的文件已经存在，没必要续传
                        6159 cfg文件已经被毁坏，创建断点续传任务失败
  * 
  * 注意：1.参数url,file_path和file_name切不可为NULL，相应的url_length，file_path_len和file_name_length
  *       也不能为0，并且url_length最大不能超过511字节，file_path_len和file_name_length不能超过255字节,要确保file_name要符合linux文件名的命名规则，file_path为已存在的路径(绝对路径和相对路径均可)，而且file_path的末尾要有字符'/'。
  *       参数ref_url和description要是没有的话可等于NULL,相应的ref_url_length和description_len也可为0，有的话ref_url_length和description_len不能大于511；
  *       另外，file_name对应的td文件和td.cfg文件一定要存在。
  *       2.目前只能接受"http://","https://","ftp://"和"thunder://"开头的url.
  *       3.另外需要特别注意的是，参数file_name要与该任务在用et_create_new_task_by_url创建时传入的file_name_for_user的文件名部分一致，但由于文件的扩展名可能被下载库自动修改，
  		因此为了确保下载库在启动该续传任务时能准确地找到与之对应的.td和.td.cfg文件,一个比较保险的方法就是在用et_create_new_task_by_url创建任务的时候，当任务信息中的
  		ET_TASK结构体中的_file_create_status为ET_FILE_CREATED_SUCCESS的时候，调用et_get_task_file_name函数得到任务的最终文件名，再去除后缀.td，则得到启动续传任务时的正确文件名.
  *       4.支持续传用迅雷看看vod专用url创建的任务。
 */
ETDLL_API int32 et_create_continue_task_by_url(char* url, u32 url_length, 
								   char* ref_url, u32 ref_url_length,
								   char* description, u32 description_len,
								   char* file_path, u32 file_path_len,
								   char* file_name, u32 file_name_length,
								   u32* task_id);

/* 
 * 创建bt下载任务的新接口(新任务和断点续传任务均使用此接口，并取代et_create_new_bt_task接口
 *                        多传入一个参数seed_switch_type )
 * 参数说明：
 * 	seed_file_full_path: 种子文件全路径
 *	file_path: 下载文件存储路径
 *	download_file_index_array:要下载的文件索引列表
 *	encoding_switch_mode: 种子文件编码的目标格式
 *	task_id: 创建的任务ID
 
 * 返回值: 0     成功，task_id 标识成功创建的任务
 *		   15361 种子文件不存在
 * 		   15362 种子文件解析失败
 *		   15363 种子文件过大不支持解析(种子文件大小大于2G)
 *		   15364 种子文件下载文件序号非法
 *         15365 bt下载被禁用
 *         15367 种子文件读取错误
 *         15368 不支持的种子文件信息输出类型，只支持gbk和utf-8，big5
 *		   15369 底层不支持gbk转utf-8
 *		   15370 底层不支持gbk转big5
 *		   15371 底层不支持utf-8转gbk
 *		   15372 底层不支持utf-8转big5
 *		   15373 底层不支持big5转gbk
 *		   15374 底层不支持big5转utf-8
 *		   15375 种子文件没有utf-8字段。(仅当编码输出格式设置为ET_ENCODING_UTF8_PROTO_MODE时产生
 *		   15376 重复的文件下载序号
                 15400 子文件下载失败
 *		   4112  非法参数，种子文件全路径或文件下载目录路径为空或太长
                 4201  file_path非法
                4216 已经有另一个相同的任务存在
  *		   2058  该版本的下载库不支持BT下载
 * 注意：1.参数seed_file_full_path是*.torrent文件的完全路径，绝对路径和相对路径均可，不可为NULL, 长度不可大于256+255，
            file_path是文件下载后存放的路径，也不可为NULL, 长度不可大于255
  *         相应的seed_file_full_path_len和file_path_len也不能为0，同时要确保file_path为已存在的路径(绝对路径和相对路径均可)，
  *         而且file_path的末尾要有字符'/'。
  *        2.download_file_index_array是用户选择的需要下载的文件序号数组，file_num为数组内包含的文件个数。文件序号不能超过或等于种子的文件个数。
  *        3.seed_switch_type用来设置单个任务的种子文件编码输出格式
  *                          0 返回原始字段
  *                          1 返回GBK格式编码 
  *                          2 返回UTF-8格式编码
  *                          3 返回BIG5格式编码 
  *				  			 4 返回种子文件中的utf-8字段
  *				  			 5 未设置输出格式(使用et_set_seed_switch_type的全局输出设置)  
  */

ETDLL_API int32 et_create_bt_task(char* seed_file_full_path, u32 seed_file_full_path_len, 
								char* file_path, u32 file_path_len,
								u32* download_file_index_array, u32 file_num,
								enum ET_ENCODING_SWITCH_MODE encoding_switch_mode, u32* task_id);

/*
 * 创建BT磁力链任务
 * 参数说明: 
 *	url：磁力链接
 *	bManual: 是否手动创建BT任务，TRUE则只下载BT种子，FALSE则在下载了BT种子文件后自动下载其中包含的全部文件列表
 *	其他参数及返回值参照et_create_bt_task函数说明
*/
ETDLL_API int32 et_create_bt_magnet_task(char* url, u32 url_len, 
							char* file_path, u32 file_path_len,char * file_name,u32 file_name_len,BOOL bManual,
							enum ET_ENCODING_SWITCH_MODE encoding_switch_mode, u32* task_id);

/*
 * 创建emule下载任务的新接口(新任务和断点续传任务均使用此接口 )
 * 参数说明：
 *	ed2k_link: EMULE链接
 *	path：下载文件存储路径
 *	file_name:下载文件名
 *	task_id：创建的任务ID
 
 * 返回值: 0     成功，task_id 标识成功创建的任务
 *		   4103 已经超过最大任务数
 *         4112  非法参数，emule链接为空或太长,全路径或文件下载目录路径为空或太长
           4201  file_path非法
           4216 已经有另一个相同的任务存在
  *		   2058  该版本的下载库不支持emule下载
 *         20482 非法的ed2k_link
 * 注意：1 ed2k_link是emule下载的链接,不可为NULL,长度不可超过2048
 *       2 path是文件下载后存放的路径，也不可为NULL, 长度不可大于255
  *         相应的seed_file_full_path_len和file_path_len也不能为0，同时要确保file_path为已存在的路径(绝对路径和相对路径均可)，
  *         而且file_path的末尾要有字符'/'。
  *		 3.如果在下载的目标路径下有相同HASH值的的EMULE任务，则自动把原任务断点续传
  */

ETDLL_API int32 et_create_emule_task(const char* ed2k_link, u32 ed2k_link_len, char* path, u32 path_len, 
    char* file_name, u32 file_name_length, u32* task_id );

/*
  * 启动task_id 标识的任务
  * 返回值: 0    成功
                        4107  非法task_id
                        4113 当前没有可运行的任务
			   4117  任务状态不正确，有可能是该任务已经start过了
                        4211  非法GCID,该cid任务无法运行
  *                   
  */
ETDLL_API int32 et_start_task(u32 task_id);


/*
  * 停止task_id 标识的任务
  * 返回值: 0    成功
                        4107  非法task_id
                        4110  task_id标识的任务不是正在运行的任务,无法停止
                        4113  当前没有可停止的任务
  *                   
  * 注意：1.调用et_stop_task停掉task之后不能再调用et_start_task尝试再次启动task，必须在
  *       调用et_delete_task之后通过调用et_create_continue_task_by_xxx启动续传任务！
  *       2.只要是调用et_start_task启动的任务，无论状态是什么（RUNNING，VOD,SUCCESS, FAILED），在调用
  *       et_delete_task之前都必须调用et_stop_task把任务停止掉
*/
ETDLL_API int32 et_stop_task(u32 task_id);

/*
  * 删除task_id 标识的任务
  * 返回值: 0    成功
                        4107  非法task_id
                        4109  task_id标识的任务还没有停止，无法删除
                        4113  当前没有可删除的任务
 			   4119 操作冲突。由于迅雷下载库同一时间只能处理一个任务的创建或删除，如果用户想同时创建或/和删除两个或以上的任务，会有冲突！                       
  *                   
  * 注意：调用et_delete_task之前要确保任务已经用et_stop_task停止掉
 */
ETDLL_API int32 et_delete_task(u32 task_id);


/*
  * 获取task_id 标识的任务的任务信息 
  * 返回值: 0    成功
                        4107  非法task_id
                        4113 当前没有运行的任务
                        4112  无效参数，ET_TASK *info 不能为空
  */
ETDLL_API int32 et_get_task_info(u32 task_id, ET_TASK *info);

/*
  * 获取task_id 标识的任务的文件名 （注意，不适合BT任务）
  * 返回值: 0    成功
                        4107  非法task_id
			   4110  任务还没有运行
 			   4112  非法参数，file_name_buffer不能为空
                        4113 当前没有运行的任务
                        4116 任务类型不对，任务的类型不能为BT任务
                        4202 无法获得任务文件名,有可能是因为文件未创建成功(任务信息中的_file_create_status 不等于ET_FILE_CREATED_SUCCESS)
                        4215 buffer_size过小
  *
  * 注意：1.如果在ET_TASK_RUNNING状态下调用该接口，返回的为临时文件名(*.td)，在任务成功后调用则返回最终文件名。
  *	  		buffer_size为输入输出参数，当输入的buffer size过小时（接口返回4215），此参数返回正确的所需buffer size。
  *	  		2.任务由于意外事件发生中断（如停电，死机等）而需要续传时，为确保续传时传进的文件名是正确的，
  *			建议在用et_create_new_task_by_xxx启动新任务时，当任务信息中的_file_create_status 一旦等于ET_FILE_CREATED_SUCCESS，
  *			调用该接口获得任务的正确文件名，并保存起来以被续传用。注意界面程序要去除文件名后缀.td得到正确的文件名。 
   *	  		3.关于迅雷下载库对任务文件名处理的一点重要说明（注意，不适合BT任务）：当界面程序调用et_create_new_task_by_url或et_create_new_task_by_tcid接口创建一个新的下载任务时（注意，不是BT任务），
  *			如果传进来的文件名（参数file_name_for_user或file_name）是完整且扩展名正确（如my_music.mp3）的，则下载库会把下回来的文件严格按照传进去的名字命名（如my_music.mp3）。
  *			但如果传进来的文件名是空的（file_name_for_user或file_name等于NULL，不建议这样用）或扩展名没有或错误（如my_music或my_music.m3p）,则迅雷下载库会根据网络上找到的正确文件名和扩展名自动对文件进行重命名（如最终文件名为my_music.mp3），
  *			这种情况下，为确保任务由于意外中断而需要续传时传进的文件名正确无误，则需要在用et_create_new_task_by_url或et_create_new_task_by_tcid接口创建新任务时调用et_get_task_file_name来获得正确文件名以备不时之需。
 */
ETDLL_API int32 et_get_task_file_name(u32 task_id, char *file_name_buffer, int32* buffer_size);

/*
 * 获取BT子文件文件名
 * 参数说明：
 *	file_index：BT子文件索引
 *	其他参数及返回值参照et_get_task_file_name函数说明
*/
ETDLL_API int32 et_get_bt_task_sub_file_name(u32 task_id, u32 file_index,char *file_name_buffer, int32* buffer_size);

/*
 * 获取下载文件/BT子文件的CID/GCID
 * 参数说明：
 *	task_id：任务ID
 *	file_index: BT子文件索引
 *	tcid: CID(20字节二进制字节流)
 *	gcid: GCID(20字节二进制字节流)
*/
ETDLL_API int32 et_get_task_tcid(u32 task_id, u8 * tcid);
ETDLL_API int32 et_get_bt_task_sub_file_tcid(u32 task_id, u32 file_index,u8 * tcid);
ETDLL_API int32 et_get_task_gcid(u32 task_id, u8 * gcid);
ETDLL_API int32 et_get_bt_task_sub_file_gcid(u32 task_id, u32 file_index,u8 * gcid);

/*
 * 给任务添加加速资源
 * 参数说明：
 * 	task_id：任务ID
 *	p_resource:加速资源，可通过任务的CID/GCID/FILE_SIZE等信息通过高速通道接口（本模块未提供）查询得到
*/
ETDLL_API int32 et_add_task_resource(u32 task_id, void * p_resource);

/*
  * 删除task_id 标识的任务的相关文件，这些文件有可能是临时文件（任务失败或运行中被中止），也有可能是已经下载到的目标文件（任务成功）。 
  * 返回值: 0    成功
                        4107  非法task_id
                        4109 当前任务正在运行
                        4113 当前没有可执行的任务
  *
  * 注意：如果想要用此函数删除任务的临时文件的话，一定要在et_stop_task之后，et_delete_task之前调用此函数！
  *                  当然，如果你不想删除任务的临时文件，可不调用此函数。
  */
ETDLL_API int32 et_remove_task_tmp_file(u32 task_id);

/*
  * 删除指定的文件所匹配的临时文件，如 file_name.td和file_name.td.cfg文件。 
  * 返回值: 0    成功
  *
  * 注意：这个函数的调用与任务无关。
  */
ETDLL_API int32 et_remove_tmp_file(char* file_path, char* file_name);

//判断磁力连任务种子文件是否下载完成
ETDLL_API int32 et_get_bt_magnet_torrent_seed_downloaded(u32 task_id, BOOL *_seed_download);

/*--------------------------------------------------------------------------*/
/*              BT下载专用接口			
 *
 *              注意：如果这部分的接口函数返回错误码为2058，表示该版本的下载库不支持BT下载！	
 *
----------------------------------------------------------------------------*/
/* 传入种子文件全路径(包括路径和种子文件名，长度最大不能超过256+255字节)，生成种子文件信息: pp_seed_info 
 * 返回值: 0    成功
 *		   15361 种子文件不存在
 * 		   15362 种子文件解析失败
 *		   15363 种子文件过大不支持解析(种子文件大小大于2G)
 *		   15364 种子文件下载文件序号非法
 *         15365 bt下载被禁用
 *         15366 bt下载不支持的转换类型
 *         15367 种子文件读取错误
 *         15368 不支持的种子文件信息输出类型，只支持gbk和utf-8，big5
 *		   15369 底层不支持gbk转utf-8
 *		   15370 底层不支持gbk转big5
 *		   15371 底层不支持utf-8转gbk
 *		   15372 底层不支持utf-8转big5
 *		   15373 底层不支持big5转gbk
 *		   15374 底层不支持big5转utf-8
 *		   15375 种子文件没有utf-8字段。(仅当编码输出格式设置为ET_ENCODING_UTF8_PROTO_MODE时产生
 *         4112  非法参数，种子文件全路径大于256+255字节或传入空字符串
 * 注意：1info_hash为2进值编码，显示需自己转换为hex形式。
 *       2  必须和et_release_torrent_seed_info成对使用。
 *       3  _encoding字段意义: GBK = 0, UTF_8 = 1, BIG5 = 2
 *       4  相当于调用et_get_torrent_seed_info_with_encoding_mode传入encoding_switch_mode=ET_ENCODING_DEFAULT_SWITCH
 */
 
ETDLL_API int32 et_get_torrent_seed_info( char *seed_path, ET_TORRENT_SEED_INFO **pp_seed_info );

/* 在et_get_torrent_seed_info基础上，传入encoding_switch_mode字段，用来控制种子编码输出格式
 * 传入种子文件全路径(包括路径和种子文件名，长度最大不能超过256+255字节)，生成种子文件信息: pp_seed_info 
 * 返回值: 0    成功
 *		   15361 种子文件不存在
 * 		   15362 种子文件解析失败
 *		   15363 种子文件过大不支持解析(种子文件大小大于2G)
 *		   15364 种子文件下载文件序号非法
 *         15365 bt下载被禁用
 *         15366 bt下载不支持的转换类型
 *         15367 种子文件读取错误
 *         15368 不支持的种子文件信息输出类型，只支持gbk和utf-8，big5
 *		   15369 底层不支持gbk转utf-8
 *		   15370 底层不支持gbk转big5
 *		   15371 底层不支持utf-8转gbk
 *		   15372 底层不支持utf-8转big5
 *		   15373 底层不支持big5转gbk
 *		   15374 底层不支持big5转utf-8
 *		   15375 种子文件没有utf-8字段。(仅当编码输出格式设置为ET_ENCODING_UTF8_PROTO_MODE时产生
 *         4112  非法参数，种子文件全路径大于256+255字节或传入空字符串
 * 注意：1)info_hash为2进值编码，显示需自己转换为hex形式。
 *       2)  必须和et_release_torrent_seed_info成对使用。
 *       3)  _encoding字段意义: GBK = 0, UTF_8 = 1, BIG5 = 2
 *       4)  seed_switch_type用来设置单个任务的种子文件编码输出格式?
 * 				0 返回原始字段
 * 				1 返回GBK格式编码 
 * 				2 返回UTF-8格式编码
 * 				3 返回BIG5格式编码 
 * 				4 返回种子文件中的utf-8字段
 * 				5 未设置输出格式(使用et_set_seed_switch_type的全局输出设置)  
*/

ETDLL_API int32 et_get_torrent_seed_info_with_encoding_mode( char *seed_path, enum ET_ENCODING_SWITCH_MODE encoding_switch_mode, ET_TORRENT_SEED_INFO **pp_seed_info );


/* 释放通过et_get_torrent_seed_info接口得到的种子文件信息。
 * 注意：必须和et_get_torrent_seed_info成对使用。
 */
ETDLL_API int32 et_release_torrent_seed_info( ET_TORRENT_SEED_INFO *p_seed_info );


/* torrent文件有GBK,UTF8,BIG5编码方式，默认情况下switch_type=0下载库不对种子编码进行转换，用户可以根据
 * et_get_torrent_seed_info接口得到种子文件编码格式，做相应的文字显示处理。
 * 当用户需要指定编码输出方式时使用此接口，比如若是种子文件格式是UTF8,
 * 用户希望下载库以GBK格式输出，需要调用et_set_enable_utf8_switch(1)
 * switch_type: 
 * 				0 返回原始字段
 * 				1 返回GBK格式编码 
 * 				2 返回UTF-8格式编码
 * 				3 返回BIG5格式编码 
 * 				4 返回种子文件中的utf-8字段
 * 				5 未设置输出格式(使用系统默认输出设置:GBK_SWITCH) 
 * 返回值: 0    成功
 *         15366 操作系统不支持(系统不支持ICONV函数调用)
 *         15368 不支持的编码格式转换，即switch_type不是0，1，2
 */
ETDLL_API int32 et_set_seed_switch_type( enum ET_ENCODING_SWITCH_MODE switch_type );


/*
  * 得到task_id 标识的BT任务的所有需要下载的文件的id，*buffer_len为file_index_buffer的长度，当*buffer_len不够时，返回4115，并在*buffer_len带回正确的长度。 
  * 返回值: 0    成功
                        4107  非法task_id
                        4112 参数错误，buffer_len和file_index_buffer不能为空
                        4113 当前没有可执行的任务
                        4115 buffer不够，需要更长的buffer size
                        4116 错误的任务类型，task_id 标识的任务不是BT任务
  *
  * 注意：如果返回4115，表示所需的file_index_buffer不够长，需要重新传入更多的buffer！
  *                 
  */
ETDLL_API int32 et_get_bt_download_file_index( u32 task_id, u32 *buffer_len, u32 *file_index_buffer );

/*
  * 获取task_id 标识的bt任务中，文件序号为file_index的信息，填充在 ET_BT_FILE结构中。
  * 返回值: 0    成功
                        1174  文件信息正在更新中，暂时不可读，请稍候再试!
                        4107  非法task_id
                        4113 当前没有运行的任务
                        4112  无效参数，ET_BT_FILE *info 不能为空    
                        15364 种子文件序号非法
  */
ETDLL_API int32 et_get_bt_file_info(u32 task_id, u32 file_index, ET_BT_FILE *info);

/*
  * 获取task_id 标识的bt任务中，文件序号为file_index的文件的路径（任务目录内）和文件名。
  * 返回值: 0    成功
                        4107  非法task_id
                        4112  无效参数，file_path_buffer和file_name_buffer 不能为空,*file_path_buffer_size和*file_name_buffer_size 不能小于256    
                        4113 当前没有运行的任务
                        4116 任务类型不对，任务的类型应该为BT任务
                        1424 buffer_size过小
                        15364 种子文件序号非法
  * 注意: 1.两个buffer的长度*buffer_size 均不能小于256。
	  	    2.返回的路径为任务目录内的路径，如该文件在磁盘的路径为c:/tddownload/abc/abc_cd1.avi ,其中用户指定的下载目录为c:/tddownload，则返回的路径为abc/  
          	    3.返回的路径和文件名的编码方式跟用户在创建该任务时传入的encoding_switch_mode相同。
	  	    4.如果函数返回1424，则界面程序需要检查*file_path_buffer_size或*file_name_buffer_size是否小于256，纠正后重新调用该函数即可。
  */
ETDLL_API int32 et_get_bt_file_path_and_name(u32 task_id, u32 file_index,char *file_path_buffer, int32 *file_path_buffer_size, char *file_name_buffer, int32* file_name_buffer_size);

/*
获取BT任务临时文件存储路径
*/
ETDLL_API int32 et_get_bt_tmp_file_path(u32 task_id, char* tmp_file_path, char* tmp_file_name);

/*
 * 获取下载库peerid
 * 返回值: 0     成功
           1925  peerid无效
 */
ETDLL_API int32 et_get_peerid( char *buffer, u32 buffer_size );


/* 
 *  通过路径得到对应的磁盘剩余空间
 *  path:       全路径
 *  free_size : 剩余磁盘空间,单位K (1024 bytes)
 * 返回值: 0     成功
 */

ETDLL_API int32 et_get_free_disk( const char *path, uint64 *free_size );

typedef struct tagET_ED2K_LINK_INFO
{
	char		_file_name[256]; // 文件名
	uint64		_file_size; // 文件大小
	u8		_file_id[16]; // EMULE任务标识（HASH），16字节二进制字节流
	u8		_root_hash[20]; // 根HASH（可能是空）
	char		_http_url[512]; // 文件的HTTP地址（可能是空）
}ET_ED2K_LINK_INFO;

/*
 * 解析EMULE链接
*/
ETDLL_API int32 et_extract_ed2k_url(char* ed2k, ET_ED2K_LINK_INFO* info);

////////////////////////////////////////////////////////////////////////////

/*
	添加CDN-PEER加速资源，可以通过下载文件的CID/GCID/FILE-SIZE等信息通过高速模块提供的接口查询到加速资源
*/
ETDLL_API int32 et_add_cdn_peer_resource( u32 task_id, u32 file_index, char *peer_id, u8 *gcid, uint64 file_size, u8 peer_capability,  u32 host_ip, u16 tcp_port , u16 udp_port, u8 res_level, u8 res_from );

/*
	添加离线加速SERVER资源，可以通过下载文件的CID/GCID/FILE-SIZE等信息通过离线模块提供的接口查询到加速资源
*/
ETDLL_API int32 et_add_lixian_server_resource( u32 task_id, u32 file_index, char *url, u32 url_size, char* ref_url, u32 ref_url_size, char* cookie, u32 cookie_size,u32 resource_priority );

/*
	获取BT任务文件在服务器上的索引信息（文件特征信息）
	参数说明：
		task_id：[IN]任务ID
		file_index：[IN]文件在BT任务中的序号
		cid：[OUT]文件CID（20字节二进制流）
		gcid：[OUT]文件GCID（20字节二进制流）
		file_size：[OUT]文件大小
*/
ETDLL_API int32 et_get_bt_file_index_info(u32 task_id, u32 file_index, char* cid, char* gcid, uint64 *file_size);

//////////////////////////////////////////////////////////////

/* 设置一个可读写的路径，用于下载库存放临时数据*/
ETDLL_API int32 et_set_system_path(const char * system_path);

/*
	设置任务是否只从原始地址下载（适用P2SP任务）
	参数说明：
		task_id：任务ID
		origin_mode：TRUE(1)只从原始地址下载，FALSE(0)可以多资源下载
	注意：1.该接口要在et_start_task之后调用
		  2.若设置了多资源下载，则不可以再设置会只从原始地址下载
		  3.默认是只从原始地址下载，要多资源加速需要设置多资源下载
*/
ETDLL_API int32 et_set_origin_mode(u32 task_id, BOOL origin_mode);

/*
	是否是只从原始地址下载
*/
ETDLL_API int32 et_is_origin_mode(u32 task_id, BOOL* p_is_origin_mode);

/*
 获取从原始地址下载的数据流量
 参数说明：
	task_id：任务ID
	download_data_size：返回原始地址下载的流量
 */
ETDLL_API int32 et_get_origin_download_data(u32 task_id, uint64 *download_data_size);

/************************************************* 
  Function:    et_set_task_dispatch_mode   
  Description: //设置下载库任务调度模式, 尽量在任务没有启动时调用
  Input:       ET_TASK_DISPATCH_MODE mode 取值范围:  
                               ET_TASK_DISPATCH_MODE_DEFAULT:默认模式
                               ET_TASK_DISPATCH_MODE_LITTLE_FILE:  单资源单pipe调度模式
                               ET_TASK_DISPATCH_MODE_ORIGIN_MULTI_PIPE: 单资源多pipe调度模式
                  u64 filesize_to_little_file 文件大小，当下载的文件大小小于此大小时启用ET_TASK_DISPATCH_MODE_LITTLE_FILE模式,如果设置为0，则无视文件大小写直接启用
  Output:      无
  Return:      成功返回: SUCCESS

  History:     created: zhangxiaobing 2013-11-22
               modified:   
*************************************************/

typedef enum t_et_task_dispatch_mode
{
    ET_TASK_DISPATCH_MODE_DEFAULT = 0,                           //采用默认的方式进行下载调度
    ET_TASK_DISPATCH_MODE_LITTLE_FILE = 1,           //单资源单pipe调度模式
} ET_TASK_DISPATCH_MODE;

ETDLL_API int32 et_set_task_dispatch_mode(u32 task_id, ET_TASK_DISPATCH_MODE mode, uint64 filesize_to_little_file);

#ifdef __cplusplus
}
#endif
#endif
