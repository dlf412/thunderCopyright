#include <cassert>
#include <string>
#include <time.h>
#include <json/json.h>

#include "consts.h"
#include "utils.h"
#include "log.h"
#include "thread.h"
#include "vcri_global.h"
#include "identify_task.h"
#include "http_client.h"
#include "proxy.h"

using namespace std;

size_t curl_callback(char *ptr, size_t size, size_t nmemb, void* userdata);

static void parse_head_data(vector<char> &head, response_t &resp);

static void parse_body_data(vector<char> &body, response_t &resp);

static void make_post_data(const string &path, string& json_str);

static void maybe_switch_server();

static void log_proxy_info();

void identify_by_url(const string &url, request_t &request,
                     http_client &client, response_t &resp,
                     time_t timeout);

void identify_by_seed(const string &url, request_t &request,
                      string &seed_file, http_client &client,
                      response_t &resp, time_t timeout);

void parse_http_status(const string &head_str, response_t &resp) {
    // HTTP/1.1 code msg
    size_t start_pos = head_str.find("HTTP/");
    if (start_pos == string::npos)
        return;
    size_t end_pos = head_str.find("\n", start_pos);
    if (end_pos == string::npos)
        return;

    string status_line = head_str.substr(start_pos, end_pos - start_pos);
    size_t skip_protocol_version = status_line.find (" ");
    if (skip_protocol_version == string::npos)
        return;
    string status_code = status_line.substr(skip_protocol_version + 1);
    resp.status_code = strtol(status_code.c_str(), NULL, 10);
}

void parse_retry_after(const string &head_str, response_t &resp) {
    string field = "Retry-After: ";
    size_t start_pos = head_str.find(field);
    if (start_pos == string::npos) {
        resp.retry_after = BASE_POLL_INTERVAL;
        return;
    }

    size_t end_pos = head_str.find("\n", start_pos + field.length());
    if (end_pos == string::npos) {
        resp.retry_after = BASE_POLL_INTERVAL;
        return;
    }

    string delay = head_str.substr (start_pos + field.length(),
                                    end_pos - start_pos - field.length());
    resp.retry_after = strtol(delay.c_str(), NULL, 10);
}

void parse_head_data(const vector<char> &head, response_t &resp) {
    string head_str(head.begin(), head.end());
    g_log.debug_log("response head %s", head_str.c_str());
    parse_http_status(head_str, resp);
    parse_retry_after(head_str, resp);
}

bool parse_body_result(json_object* result, response_t &resp) {
    json_object* overview_obj = json_object_object_get(result, "overall");
    if(!overview_obj)
        return false;

    // get overview first, get infringer detail if overview is infringer,
    // detail may not exist when all urls/files is infringer.
    int overview = json_object_get_int(overview_obj);
    if(overview < INFRINGING || overview > PROCESSING)
        return false;
    resp.overview = overview;

    if(overview != INFRINGING)
        return true;

    resp.result_count = 0;
    json_object* list_obj = json_object_object_get(result, "listing");
    if (!list_obj)
        return true;

    array_list* list = json_object_get_array(list_obj);
    if (list == NULL)
        return true;

    // parse detail failed, wo cannot report emough info for caller
    resp.result_count = list->length;
    resp.results
        = (vcri_result_t*)malloc(sizeof(vcri_result_t)*resp.result_count);
    if (resp.results == NULL)
        throw OUT_OF_MEMORY;

    memset(resp.results, '\0', sizeof(vcri_result_t)*resp.result_count);

    // ignore the result with empty path
    uint32_t result_index = 0;
    for (uint32_t i = 0; i < resp.result_count; ++i) {
        json_object* detail = json_object_array_get_idx(list_obj, i);
        if (detail == NULL)
            return false;
        json_object* status_obj
            = json_object_object_get(detail, "status");
        if (status_obj == NULL)
            return false;

        uint32_t status = json_object_get_int(status_obj);
        if (status > CANNOT_IDENTIFY)
            return false;
        json_object* path_obj
            = json_object_object_get(detail, "path");
        const char* path = json_object_get_string(path_obj);
        if (path == NULL || path[0] == '\0')
            continue;

        resp.results[result_index].result = status;
        resp.results[result_index].path = strdup(path);
        ++ result_index;
    }
    if(result_index < resp.result_count) {
        resp.result_count = result_index;
        resp.results = (vcri_result_t*)realloc(
                resp.results, sizeof(vcri_result_t)*resp.result_count);
    }
    return true;
}

bool parse_body_error(json_object* error, response_t &resp) {
    json_object* err_code_obj = json_object_object_get(error, "code");
    if (NULL == err_code_obj)
        return false;

    int error_code = json_object_get_int(err_code_obj);
    if (error_code == SERVER_ACCESS_DENIED
        || error_code == SERVER_BAD_ARGUMENTS
        || error_code == SERVER_HASH_NOT_HIT)
        resp.code = error_code;
    else
        resp.code = NETWORK_ERROR;

    json_object* err_data_obj = json_object_object_get(error, "data");
    if (err_data_obj)
        resp.data = json_object_get_int(err_data_obj);
    return true;
}

bool parse_body_data(const vector<char> &body, response_t &resp) {
    string body_str(body.begin(), body.end());
    g_log.debug_log("response body %s", body_str.c_str());

    json_object* root = json_tokener_parse(body_str.c_str());
    if(is_error(root))
        return false;
    tr1::shared_ptr<json_object> json_root(root, json_object_put);

    json_object* result = json_object_object_get(root, "result");
    json_object* error = json_object_object_get(root, "error");
    if((!result && !error) || (result && error))
        return false;

    bool ret = true;
    if (result) {
        ret = parse_body_result(result, resp);
        if (ret)
            resp.code = 0;
    } else
        ret = parse_body_error(error, resp);
    return ret;
}

void parse_response(const vector<char> &head, const vector<char> &body,
                    response_t &resp) {
    // request may stop by webserver when seek file is too large, should check
    // status code
    parse_head_data(head, resp);
    if (parse_body_data(body, resp))
        return;
    const int Request_Entity_Too_Large = 413;
    if (resp.status_code == Request_Entity_Too_Large)
        resp.code = SERVER_SEED_TOO_LARGE;
    else
        throw NETWORK_ERROR;
}

void make_post_data(const string& path, string& json_str) {
    int64_t len = 0;
    if(get_file_size(path, len) != VCRI_OK) {
        g_log.error_log("get file size failed %s", path.c_str());
        throw FILESYS_ERROR;
    }

    vector<unsigned char> buf((size_t)len);
    if(read_file_content(path, &buf[0], len) != VCRI_OK) {
        g_log.error_log("read file failed %s", path.c_str());
        throw FILESYS_ERROR;
    }

    string encoded_str;
    base64_encode((const char*)&buf[0], (int)len, encoded_str);

    json_object* obj = json_object_new_object();
    json_object_object_add(obj, "jsonrpc",json_object_new_string("2.0"));
    json_object_object_add(obj, "id",json_object_new_int(1));
    json_object_object_add(obj, "method",json_object_new_string("query"));

    json_object* prams_obj = json_object_new_object();
    json_object_object_add(prams_obj, "seed_file",
        json_object_new_string(encoded_str.c_str()));

    json_object_object_add(obj, "params", prams_obj);

    json_str =(char*)json_object_get_string(obj);
    json_object_put(obj);
}

void identify_by_url(const string &url, request_t &request,
                     http_client &client, response_t &resp, time_t timeout) {
    vector<char> head, body;
    client.do_get(url, request, head, body, timeout);
    parse_response(head, body, resp);
}

void identify_by_seed(const string &url, request_t &request,
                      string &seed_file, http_client &client,
                      response_t &resp, time_t timeout) {
    string post_data;
    vector<char> head, body;
    make_post_data(seed_file, post_data);
    client.do_post(url, request, post_data, head, body, timeout);
    parse_response(head, body, resp);
}

void do_identify(task_ptr &task, const string &server, response_t &resp) {
    time_t timeout = TIME_OUT;
    http_client client(g_proxy_config);

    request_t request;
    task->fill_request(request);
    string url = "https://" + server + "/identified";

    g_log.debug_log("identify_by_url digest %s, url %s",
                    task->digest.c_str(), task->params.url);
    identify_by_url(url, request, client, resp, timeout);

    if(task->need_send_seed () && resp.code == SERVER_HASH_NOT_HIT) {
        g_log.debug_log("identify_by_seed digest %s, url %s",
                        task->digest.c_str(), task->params.url);
        identify_by_seed(url, request, task->seed_file, client, resp,
                         timeout);
    }
    if (resp.code == 0 && task->need_send_seed ())
        task->seed_sent();
}

void task_done_notify(task_ptr &task, response_t &resp) {
    task->notify(resp.overview, resp.results,
                 resp.result_count, task->params.url,
                 task->params.file_private_id);
    task->status = TASK_DONE;
    g_log.info_log("Task digest: %s, status done, url: %s",
                   task->digest.c_str(), task->params.url);
}

void task_final_error_notify(task_ptr &task, int err) {
    task->notify(err, 0, 0, task->params.url,
                 task->params.file_private_id);
    task->status = TASK_DONE;
    g_log.info_log("Task digest: %s, status final error, url: %s",
                   task->digest.c_str(), task->params.url);
}

void task_processing_notify(task_ptr &task, response_t &resp) {
    task_status_t status = TASK_PROCESSING;
    if(task->status < status) {
        task->notify(resp.overview, resp.results,
                     resp.result_count, task->params.url,
                     task->params.file_private_id);
        task->status = status;
        g_log.info_log("Task digest: %s, status processing, url: %s",
                        task->digest.c_str(), task->params.url);
    }
    task->reschedule((unsigned int)resp.retry_after);
}

void task_error_notify(task_ptr &task, int err) {
    task_status_t status = TASK_ERROR;
    if(task->status < status) {
        task->notify(err, 0, 0, task->params.url,
                     task->params.file_private_id);
        task->status = status;
        g_log.info_log("Task digest: %s, status error, url: %s",
                        task->digest.c_str(), task->params.url);
    }
    task->retry();
}


bool identify_task (task_ptr &task) {
    response_t resp;
    try {
        g_log.debug_log("begin identify_task digest %s, url %s",
                        task->digest.c_str(), task->params.url);
        do_identify(task, server_list[g_cur_server_index], resp);

        if (resp.code == 0) {
            if (resp.overview == INFRINGING || resp.overview == NON_INFRINGING
                || resp.overview == CANNOT_IDENTIFY) {
                g_log.info_log("Task notify, digest: %s, overview %u, url: %s",
                               task->digest.c_str(), (int) resp.overview,
                               task->params.url);
                task_done_notify(task, resp);
                return true;
            } else {
                task_processing_notify(task, resp);
                return false;
            }
        } else if (resp.code == SERVER_SEED_TOO_LARGE
                   || resp.code == SERVER_BAD_ARGUMENTS
                   || resp.code == SERVER_ACCESS_DENIED) {
            int32_t err = 0;
            switch(resp.code) {
            case SERVER_SEED_TOO_LARGE:
                err = BAD_SEED;
                break;
            case SERVER_BAD_ARGUMENTS:
                err = BAD_ARGUMENTS;
                break;
            case SERVER_ACCESS_DENIED:
                err = ACCESS_DENIED;
                break;
            default:
                assert(0);
                break;
            }
            task_final_error_notify(task, err);
            return true;
        } else {
            task_error_notify(task, NETWORK_ERROR);
            return false;
        }
    } catch(vcri_error_code err) {
        // curl error, we cannot get any response from server, so we're retrying
        // rather than polling. we use backoff config rather than polling
        // interval

        if(err == PROXY_NOT_SUPPORTED || err == NETWORK_ERROR) {
            if(task->proxy_retries >= PROXY_RETRY_LIMIT) {
                log_proxy_info();
                g_log.error_log("Task retry %u times, digest %s, url %s",
                                task->proxy_retries, task->digest.c_str(),
                                task->params.url);
                if(err == PROXY_NOT_SUPPORTED && g_sys_proxy) {

                    proxy_t proxy;
                    unsigned index;
                    int ret = get_system_proxy(index, proxy);
                    // NOTE: for no proxy case, server is not checked for
                    //       connectibility, so we check if we got no proxy
                    //       both times
                    if (ret == 0 && index >= 0 
                        && (proxy.proxy_type != NO_PROXY
                            || g_proxy_config.proxy_type != NO_PROXY)) {
                        // NOTE: what if the customer periodically change
                        //       system proxy config, all non-functional?a
                        g_proxy_config = proxy;
                        task->proxy_retries = 0;
                    }
                }
            } else {
                ++task->proxy_retries;
                if(err == NETWORK_ERROR)
                    maybe_switch_server();
            }
            task_error_notify(task, err);
            return false;
        } else if (err == FILESYS_ERROR) {
            g_log.error_log("Task digest %s, read seed failed, url %s",
                            task->digest.c_str(), task->params.url);
            task_final_error_notify(task, FILESYS_ERROR);
            return true;
        }
        task_error_notify(task, UNKNOWN_ERROR);
        return false;
    } catch (const std::bad_alloc &) {
        task_error_notify(task, OUT_OF_MEMORY);
        return false;
    } catch (...) {
        task_error_notify(task, UNKNOWN_ERROR);
        return false;
    }
}

static void maybe_switch_server() {
    if((g_cur_server_index == 0
        && g_cur_server_error == MAX_MASTER_ERROR_ATTEMPT)
       ||(g_cur_server_index > 0
          && g_cur_server_error == MAX_SLAVE_ERROR_ATTEMPT)) {
        g_cur_server_index = (g_cur_server_index + 1) % SERVER_LEN;
        g_cur_server_error = 0;
    } else {
        ++ g_cur_server_error;
    }
}

static void log_proxy_info() {
    if(g_proxy_config.proxy_type < NO_PROXY
       || g_proxy_config.proxy_type >= LAST_PROXY)
        return;
    if(g_proxy_config.proxy_type == NO_PROXY)
        g_log.error_log("not use proxy");
    else
        g_log.error_log(
                "use proxy.system proxy: %s.proxy url: %s, userpwd: %s",
                g_sys_proxy ? "yes" : "no", g_proxy_config.proxy_url.c_str(),
                g_proxy_config.proxy_userpwd.c_str());
}
