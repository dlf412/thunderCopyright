#include "stdint.h"

#ifndef __VCRI_H__
#define __VCRI_H__

#ifdef __cplusplus
    extern "C" {
#endif

typedef enum {
    NO_PROXY,
    SYSTEM_PROXY,
    SOCKS_PROXY,
    HTTPS_PROXY,
    LAST_PROXY
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

typedef struct {
    const char* path;
    uint32_t result;
} vcri_result_t;

typedef void (*vcri_result_notify_t)(int32_t overview,
                                     const vcri_result_t* results,
                                     uint32_t result_count,
                                     const char* url,
                                     const char* file_private_id);

#define VCRI_EXPORT __declspec(dllexport)

VCRI_EXPORT int32_t vcri_init(vcri_proxy_type_t proxy_type,
                              const vcri_proxy_t* proxy);

VCRI_EXPORT int32_t vcri_set_api_key(const char* api_key);

VCRI_EXPORT int32_t vcri_set_program_info(const char* program_info);

VCRI_EXPORT int32_t vcri_set_client_id(const char* client_id);

VCRI_EXPORT int32_t vcri_identify(vcri_result_notify_t notify,
                                  const vcri_params_t* params);

VCRI_EXPORT int32_t vcri_cancel(const vcri_params_t* params);

VCRI_EXPORT int32_t vcri_progress(const vcri_params_t* params,
                                  uint8_t progress);

VCRI_EXPORT void vcri_fini();

#ifdef __cplusplus
}
#endif

#endif /* __VCRI_H__ */
