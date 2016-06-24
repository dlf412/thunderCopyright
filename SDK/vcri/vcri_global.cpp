#include "vcri_global.h"
#include "log.h"

bool g_sys_proxy = false;
proxy_t g_proxy_config;

uint32_t g_cur_server_index = 0;
uint32_t g_cur_server_error = 0;

log_level_t g_log_level = VCRI_LOG_ERROR;

vcri_log g_log(g_log_level);
