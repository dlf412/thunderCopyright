#ifndef SD_MEDIUM_DEFINE_H
#define SD_MEDIUM_DEFINE_H

#ifdef __cplusplus
extern "C" 
{
#endif

#ifdef _MEDIUM_DEFINE
/**** 手机迅雷、iPad看看、Andorid迅雷  ******/
/****只定义功能相关的宏，与具体环境或项目相关的，请在编译时指定*****/

#define ENABLE_CFG_FILE
#define ENABLE_COOKIES
#define _CONNECT_DETAIL

#define _USE_GLOBAL_MEM_POOL  
#define _USE_OS_MEM_ONLY 
#define _EXTENT_MEM_FROM_OS  
#define _MEMPOOL_10M

#define _WRITE_BUFFER_MERGE

#define _DK_QUERY  
#define ENABLE_BT  
#define ENABLE_BT_PROTOCOL

#define ENABLE_CDN
#define ENABLE_MEMBER
#define ENABLE_HSC  		/* 高速通道 */
#define UI_PAY_HSC  		/* 高速通道中的扣费部分由界面完成 */
#define ENABLE_LIXIAN
#define ENABLE_LIXIAN_CACHE

#define EMBED_REPORT    
#define UPLOAD_ENABLE
// 定义上报使用压缩
#define ENABLE_ZIP    
#define ENABLE_EMBED_REPORT_GZIP

#define ENABLE_VOD  
#define _VOD_NO_DISK

/**编译时指定**/
//#define ENABLE_CHECK_NETWORK     /* 自动检测网络状态是否良好,如果不好,则暂停所有的pipe,减轻系统压力,防止网卡出问题 */
//#define LITTLE_FILE_TEST   
//#define ENABLE_HTTP_VOD   /* 本地http点播服务器 */
//#define KANKAN_PROJ
//#define ENABLE_ASSISTANT
//#define DISABLE_TASK_STORE_FILE_BACKUP_TO_SDCARD		/*不对下载任务记录列表进行备份*/
//#define ENABLE_LX_XML_ZIP
//#define ENABLE_FLASH_PLAYER     /* http vod点播服务器支持FLASH 播放器功能 */
//#define ENABLE_REMOTE_CONTROL
//#define ENABLE_JSON
//#define ENABLE_XV_FILE_DEC   	/* http vod点播服务器支持xv 格式文件解密功能*/
//#define _LOGGER
/*******随身盘*******/
//#define ENABLE_WALKBOX  

#endif //_MEDIUM_DEFINE
#ifdef __cplusplus
}
#endif
#endif
