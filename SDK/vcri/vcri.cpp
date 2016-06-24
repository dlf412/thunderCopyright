#include <map>
#include <string>
#include <vector>

#include <curl/curl.h>
#include <io.h>
#include <json/json.h>
#include <openssl/ssl.h>
#include <stdio.h>
#include <string.h>
#include <time.h>

#include "vcri.h"
#include "consts.h"
#include "digest.h"
#include "proxy.h"
#include "task.h"
#include "thread.h"
#include "utils.h"
#include "vcri_global.h"
#include "http_client.h"
#include "identify_task.h"

using namespace std;

// internal control
static cri_section s_lock;
static bool       s_inited = false;
string            g_program_info;
string            g_api_key;
string            g_client_id;

static tr1::shared_ptr<task_runner> s_task_runner;

// helper funcs
static bool is_inited();
static int32_t check_proxy_params(vcri_proxy_type_t proxy_type,
                                  const vcri_proxy_t* proxy);
static void check_params(const vcri_params_t* params);
static int32_t get_conn_server_index(uint32_t& index, const proxy_t& proxy);
static void set_proxy(vcri_proxy_type_t proxy_type, const vcri_proxy_t* proxy);

// implement

#define VCRI_TRY_BEGIN              \
    try {

// not show error when cannot connect our server for customer,
// retry backend thread
#define VCRI_TRY_END                        \
    } catch (vcri_error_code error_code) {  \
        if (error_code == NETWORK_ERROR)    \
             return VCRI_OK;                \
        else                                \
            return error_code;              \
    } catch (const std::bad_alloc &) {      \
        return OUT_OF_MEMORY;               \
    } catch (...) {                         \
        return UNKNOWN_ERROR;               \
    }

int32_t vcri_init(vcri_proxy_type_t proxy_type, const vcri_proxy_t* proxy) {
VCRI_TRY_BEGIN
    if (s_inited) {
        g_log.error_log("vcri plugin already initialized");
        return ALREADY_INITED;
    }

    int32_t ret = check_proxy_params(proxy_type, proxy);
    if (ret != VCRI_OK) {
        g_log.error_log("bad proxy");
        return ret;
    }

    if (proxy_type == SYSTEM_PROXY) {

        ret = get_system_proxy(g_cur_server_index, g_proxy_config);
        if (ret != VCRI_OK)
            return ret;

        g_sys_proxy = true;
    } else if (proxy_type == SOCKS_PROXY || proxy_type == HTTPS_PROXY) {
        set_proxy(proxy_type, proxy);

        ret = get_conn_server_index(g_cur_server_index, g_proxy_config);
        if(ret != VCRI_OK)
            return ret;

    } else { // no-proxy
        g_proxy_config.proxy_type = NO_PROXY;

        proxy_t proxy;
        proxy.proxy_type = NO_PROXY;
        ret = get_conn_server_index(g_cur_server_index, proxy);
        if(ret != VCRI_OK)
            return ret;
    }

    s_task_runner.reset(new task_runner);

    g_log.info_log("vcri plugin init success");
    s_inited = true;
    return VCRI_OK;
VCRI_TRY_END
}

int32_t vcri_set_config(const char *val, string &config) {
    try {
        vcri_lock lk(s_lock);
        if(!s_inited) {
            g_log.error_log("vcri plugin not initialized");
            return NOT_INITED;
        } else if(!val || !*val) {
            g_log.error_log("empty value for config param");
            return BAD_ARGUMENTS;
        }
        config = val;
        g_log.info_log("field properly set: %s", val);
        return VCRI_OK;
    } catch(...) {
        g_log.error_log("something unexpectedly bad happened");
        return UNKNOWN_ERROR;
    }
}

int32_t vcri_set_api_key(const char* api_key) {
    return vcri_set_config(api_key, g_api_key);
}

int32_t vcri_set_program_info(const char* program_info) {
    return vcri_set_config(program_info, g_program_info);
}

int32_t vcri_set_client_id(const char* client_id) {
    return vcri_set_config(client_id, g_client_id);
}

int32_t vcri_identify(vcri_result_notify_t notify,
                      const vcri_params_t* params) {
VCRI_TRY_BEGIN
    int32_t res_code = VCRI_OK;
    if (!is_inited()) {
        g_log.error_log("vcri plugin not initialized");
        return NOT_INITED;
    }

    if (NULL == notify) {
        g_log.error_log("notify is null");
        return BAD_ARGUMENTS;
    }
    check_params(params);

    task_ptr task(new Task(notify, params));
    if (s_task_runner->push(task) == false) {
        g_log.error_log("push task failure");
        return UNKNOWN_ERROR;
    }
    return VCRI_OK;
VCRI_TRY_END
}

int32_t vcri_cancel(const vcri_params_t* params) {
VCRI_TRY_BEGIN
    if (!is_inited()) {
        g_log.error_log("vcri plugin not initialized");
        return NOT_INITED;
    }
    check_params(params);
    task_ptr task(new Task(0, params));
    return s_task_runner->del(*params) ? VCRI_OK : TASK_NOT_FOUND;
VCRI_TRY_END
}

int32_t vcri_progress(const vcri_params_t* params, uint8_t progress) {
VCRI_TRY_BEGIN
    if (!is_inited()) {
        g_log.error_log("vcri plugin not initialized");
        return NOT_INITED;
    }
    check_params(params);
    if(progress > 100) {
        g_log.error_log("bad progress %d", (int) progress);
        return BAD_ARGUMENTS;
    }
    task_ptr task(new Task(0, params));
    return s_task_runner->set_task_progress(task, progress);
VCRI_TRY_END
}

uint32_t vcri_fini_impl () {
VCRI_TRY_BEGIN
    vcri_lock lk(s_lock);
    if(!s_inited)
        return VCRI_OK;
    g_log.write_to_file();
    s_task_runner.reset ();

    g_api_key = "";
    g_client_id = "";
    g_program_info = "";
    s_inited = false;
    g_log.info_log("vcri plugin finish");
    return VCRI_OK;
VCRI_TRY_END
}

void vcri_fini () {
    (void) vcri_fini_impl();
}

// helper funcs
static int32_t check_proxy_params (vcri_proxy_type_t proxy_type,
                                   const vcri_proxy_t* proxy) {
    if(proxy_type < NO_PROXY || proxy_type >= LAST_PROXY)
        return BAD_ARGUMENTS;
    if(proxy_type == NO_PROXY || proxy_type == SYSTEM_PROXY)
        return VCRI_OK;
    if(!proxy)
        return BAD_ARGUMENTS;
    if(!proxy->host || proxy->host[0] == '\0' || proxy->port == 0)
        return BAD_ARGUMENTS;
    return VCRI_OK;
}

static bool is_inited() {
    return (s_inited && g_program_info != ""
        && g_api_key != "" && g_client_id != "");
}

static void check_params(const vcri_params_t* params) {
    if (NULL == params) {
        g_log.error_log("params is null");
        throw BAD_ARGUMENTS;
    }
    if (params->struct_version != VCRI_VERSION
        || params->struct_size < sizeof(vcri_params_t)) {
        g_log.error_log("struct size or version is wrong");
        throw BAD_ARGUMENTS;
    }
    if (NULL == params->url || params->url[0] == '\0') {
        g_log.error_log("url is null or empty");
        throw BAD_ARGUMENTS;
    }

    bool is_seed_file = is_file_url(params->url);
    if(!is_seed_file) {
        if (NULL == params->file_name || params->file_name[0] == '\0'
                || params->file_size == 0) {
            g_log.error_log("file name or file_size is wrong, url %s",
                            params->url);
            throw BAD_ARGUMENTS;
        }
    }
}

static int32_t get_conn_server_index(uint32_t& server_index,
                                     const proxy_t& proxy) {
    int ret = VCRI_OK;
    http_client client(proxy);
    int i = 0;
    for (; i < SERVER_LEN; ++i) {
        try {
            string url = "https://" + server_list[i] + "/identified";
            request_t pro;
            vector<char> body;
            vector<char> head;

            client.do_get(url, pro, head, body, TIME_OUT);  
            server_index = i;
            break;
        } catch (...) {
            
        } 
    }

    return (i < SERVER_LEN ? VCRI_OK : NETWORK_ERROR);
}

static void set_proxy(vcri_proxy_type_t proxy_type,
                      const vcri_proxy_t* proxy) {
    g_proxy_config.proxy_type = proxy_type;

    g_proxy_config.proxy_url = (string)proxy->host + ":" + int2str(proxy->port);

    if(proxy->username && proxy->password 
        && proxy->username[0] != '\0' && proxy->password[0] != '\0'){
        g_proxy_config.proxy_userpwd = (string)proxy->username
        + ":" + proxy->password;
    }
}
