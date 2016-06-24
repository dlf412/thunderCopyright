#ifndef __VCRI_GLOBAL_H__
#define __VCRI_GLOBAL_H__

#include "vcri.h"
#include "consts.h"
#include "stdint.h"
#include "log.h"
#include <string>

typedef struct {
    vcri_proxy_type_t proxy_type;
    std::string proxy_url;
    std::string proxy_userpwd;
} proxy_t;

extern bool g_sys_proxy;
extern proxy_t g_proxy_config;

extern uint32_t g_cur_server_index;
extern uint32_t g_cur_server_error;

extern log_level_t g_log_level;

extern vcri_log g_log;

extern std::string g_program_info;
extern std::string g_api_key;
extern std::string g_client_id;

#endif // #ifndef __VCRI_GLOBAL_H__
