#ifndef SD_MEDIUM_DEFINE_H
#define SD_MEDIUM_DEFINE_H

#ifdef __cplusplus
extern "C" 
{
#endif

#ifdef _MEDIUM_DEFINE
/**** �ֻ�Ѹ�ס�iPad������AndoridѸ��  ******/
/****ֻ���幦����صĺ꣬����廷������Ŀ��صģ����ڱ���ʱָ��*****/

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
#define ENABLE_HSC  		/* ����ͨ�� */
#define UI_PAY_HSC  		/* ����ͨ���еĿ۷Ѳ����ɽ������ */
#define ENABLE_LIXIAN
#define ENABLE_LIXIAN_CACHE

#define EMBED_REPORT    
#define UPLOAD_ENABLE
// �����ϱ�ʹ��ѹ��
#define ENABLE_ZIP    
#define ENABLE_EMBED_REPORT_GZIP

#define ENABLE_VOD  
#define _VOD_NO_DISK

/**����ʱָ��**/
//#define ENABLE_CHECK_NETWORK     /* �Զ��������״̬�Ƿ�����,�������,����ͣ���е�pipe,����ϵͳѹ��,��ֹ���������� */
//#define LITTLE_FILE_TEST   
//#define ENABLE_HTTP_VOD   /* ����http�㲥������ */
//#define KANKAN_PROJ
//#define ENABLE_ASSISTANT
//#define DISABLE_TASK_STORE_FILE_BACKUP_TO_SDCARD		/*�������������¼�б���б���*/
//#define ENABLE_LX_XML_ZIP
//#define ENABLE_FLASH_PLAYER     /* http vod�㲥������֧��FLASH ���������� */
//#define ENABLE_REMOTE_CONTROL
//#define ENABLE_JSON
//#define ENABLE_XV_FILE_DEC   	/* http vod�㲥������֧��xv ��ʽ�ļ����ܹ���*/
//#define _LOGGER
/*******������*******/
//#define ENABLE_WALKBOX  

#endif //_MEDIUM_DEFINE
#ifdef __cplusplus
}
#endif
#endif
