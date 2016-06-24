#include "stdint.h"

#ifndef __VCRI_H__
#define __VCRI_H__

#ifdef __cplusplus
   extern "C" {
#endif

#define VCRI_EXPORT __declspec(dllexport)

typedef enum 
{
  INFRINGING = 0,
  NON_INFRINGING = 1,
  CANNOT_IDENTIFY = 2,
  PROCESSING = 3
} vcri_query_code;

typedef enum
{
  BAD_ARGUMENTS = -0x40000,
  ACCESS_DENIED = -0x40003,
  PROXY_NOT_SUPPORTED = -0x40007,
  ALREADY_INITED = -0x40009,
  NOT_INITED = -0x40012,
  UNKHOWN_ERROR = -0x50000,
  SERVER_BUSY = -0x50003,
  NETWORK_ERROR = -0x50004,
  OUT_OF_MEMORY = -0x50005
} vcri_error_code;

typedef enum {
  NO_PROXY,
  SYSTEM_PROXY,
  SOCKS_PROXY,
  HTTPS_PROXY
} vcri_proxy_type_t;

typedef struct {
  uint32_t port;
  const char* host;
  const char* username;
  const char* password;
} vcri_proxy_t;

typedef struct {
  uint32_t struct_size; 
  uint32_t struct_version;
  const char* url; 
  const char* referer;        
  const char* file_private_id; 
  const char* mime_type; 
  const char* file_name;  
  uint64_t file_size; 
} vcri_params_t;


typedef void (*vcri_result_notify_t)(int32_t result, const char* url, const char* file_private_id);

VCRI_EXPORT int32_t vcri_init(vcri_proxy_type_t proxy_type, const vcri_proxy_t* proxy);

VCRI_EXPORT int32_t vcri_set_api_key(const char* api_key);

VCRI_EXPORT int32_t vcri_set_program_info(const char* program_info);

VCRI_EXPORT int32_t vcri_set_client_id(const char* client_id);

VCRI_EXPORT int32_t vcri_identify(vcri_result_notify_t notify, const vcri_params_t* params);

VCRI_EXPORT int32_t vcri_progress(const vcri_params_t* params, uint8_t progress);

VCRI_EXPORT void vcri_fini();

#ifdef __cplusplus
}
#endif

#endif /* __VCRI_H__ */
