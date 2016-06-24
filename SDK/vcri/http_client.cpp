#include <memory>
#include <string>
#include <vector>
#include <curl/curl.h>

#include "vcri_global.h"
#include "http_client.h"
#include "vcri.h"
#include "consts.h"
#include "task.h"

using namespace std;

extern CURLcode sslctx_function(CURL * curl, void * sslctx, void * param);

static size_t curl_callback(char *ptr, size_t size, size_t nmemb,
                            void *userdata) {
    vector<char> *vec_buf = static_cast<vector<char>*>(userdata);
    vec_buf->insert(vec_buf->end(), ptr, ptr + size * nmemb);

    return size * nmemb;
}

http_client::http_client() {
    init();
}

http_client::http_client(const proxy_t& proxy) {
    init();
    set_proxy(proxy);
}

http_client::~http_client() {
    if (curl_handle_)
        curl_easy_cleanup(curl_handle_);
}

void http_client::init() {
    curl_handle_ = curl_easy_init();
    if(!curl_handle_)
        throw OUT_OF_MEMORY;

#ifdef VCRI_DEBUG
    int ret = curl_easy_setopt(curl_handle_, CURLOPT_VERBOSE, 1L);
    throw_on_error(ret);
#endif // VCRI_DEBUG

    set_ssl();
    set_timeout(TIME_OUT);
}

void http_client::set_proxy(const proxy_t& proxy) {
    int ret = 0;
    if (proxy.proxy_type == SOCKS_PROXY || proxy.proxy_type == HTTPS_PROXY) {
        if (proxy.proxy_type == HTTPS_PROXY) {
            ret = curl_easy_setopt(curl_handle_,
                CURLOPT_PROXYTYPE, CURLPROXY_HTTP);
            throw_on_error(ret);
            
        }

        if (proxy.proxy_type == SOCKS_PROXY) {
            ret = curl_easy_setopt(curl_handle_, 
                CURLOPT_PROXYTYPE, CURLPROXY_SOCKS5);
            throw_on_error(ret);
        }

        ret = curl_easy_setopt(curl_handle_, CURLOPT_PROXY, proxy.proxy_url.c_str());
        throw_on_error(ret);

        if (!proxy.proxy_userpwd.empty()) {
            ret = curl_easy_setopt(curl_handle_, CURLOPT_PROXYUSERPWD,
                proxy.proxy_userpwd.c_str());
            throw_on_error(ret);
        }
    }
}

void http_client::set_ssl() {
    int ret = 0;
   
    ret = curl_easy_setopt(curl_handle_, CURLOPT_SSL_VERIFYPEER, 1L);
    throw_on_error(ret);

    ret = curl_easy_setopt(curl_handle_, CURLOPT_SSL_VERIFYHOST, 2L);
    throw_on_error(ret);

    ret = curl_easy_setopt(curl_handle_, CURLOPT_SSLCERTTYPE, "PEM");
    throw_on_error(ret);

    ret = curl_easy_setopt(curl_handle_, 
         CURLOPT_SSL_CTX_FUNCTION, *sslctx_function);
    throw_on_error(ret);
    
}

void http_client::set_request(const string& url, const request_t& request,
                              curl_slist **headers) {
    if(url == "")
        throw BAD_ARGUMENTS;

    int ret = 0;
    if(!request.headers.empty()) {
        for(vector<header_t>::const_iterator it = request.headers.begin();
            it != request.headers.end(); ++it) {
            string tmp = it->key + ": " + it->value;
            *headers = curl_slist_append(*headers, tmp.c_str());
        }

        ret = curl_easy_setopt(curl_handle_, CURLOPT_HTTPHEADER, *headers);
        throw_on_error(ret);
    }

    if(!request.opts.empty()) {
        for(vector<opt_t>::const_iterator it = request.opts.begin(); 
            it != request.opts.end(); ++it) {
            ret = curl_easy_setopt(curl_handle_, it->opt, it->value.c_str());
            throw_on_error(ret);
        }
    }

    string query_string;
    for(vector<query_param_t>::const_iterator it = request.query_params.begin();
        it != request.query_params.end(); ++it) {
        string key = curl_escape(it->key);
        string value = curl_escape(it->value);
        query_string += key + "=" + value + "&";
    }
    string full_url = url + "?" + query_string;
    ret = curl_easy_setopt(curl_handle_, CURLOPT_URL, full_url.c_str());
    throw_on_error(ret);

}

void http_client::set_callback(vector<char> &resp_head,
                              vector<char> &resp_body) {
    int ret = 0;

    ret = curl_easy_setopt(curl_handle_, CURLOPT_HEADERDATA, 
        static_cast<void*>(&resp_head));
    throw_on_error(ret);

    ret = curl_easy_setopt(curl_handle_, CURLOPT_HEADERFUNCTION, curl_callback);
    throw_on_error(ret);

    ret = curl_easy_setopt(curl_handle_, CURLOPT_WRITEDATA, 
        static_cast<void*>(&resp_body));
    throw_on_error(ret);

    ret = curl_easy_setopt(curl_handle_, CURLOPT_WRITEFUNCTION, curl_callback);
    throw_on_error(ret);
}

void http_client::set_timeout(time_t timeout) {
    int ret = curl_easy_setopt(curl_handle_, CURLOPT_TIMEOUT, timeout);
    throw_on_error(ret);
}

void http_client::set_post_data(const string& post_data) {
    int ret = 0;
    ret = curl_easy_setopt(curl_handle_, CURLOPT_POST, 1L);
    throw_on_error(ret);

    ret = curl_easy_setopt(curl_handle_, CURLOPT_POSTFIELDSIZE,
        post_data.size());
    throw_on_error(ret);

    ret = curl_easy_setopt(curl_handle_, CURLOPT_POSTFIELDS, 
        post_data.c_str());
    throw_on_error(ret);
}

void http_client::do_get(const string& url, const request_t& request,
                     vector<char>& resp_head, vector<char>& resp_body,
                     time_t timeout) {
    set_timeout(timeout);
    set_callback(resp_head, resp_body);

    curl_slist* headers = NULL;
    set_request(url, request, &headers);
    int ret = curl_easy_perform(curl_handle_);
    curl_slist_free_all(headers);
    throw_on_error(ret);
}

void http_client::do_post(const string& url, const request_t& request,
                 const string& post_data, vector<char>& resp_head,
                 vector<char>& resp_body, time_t timeout) {
    set_timeout(timeout);
    set_callback(resp_head, resp_body);
    set_post_data(post_data);

    curl_slist* headers = NULL;
    set_request(url, request, &headers);
    int ret = curl_easy_perform(curl_handle_);
    curl_slist_free_all(headers);
    throw_on_error(ret);
}

void http_client::throw_on_error(int& code) {
    if(code == CURLE_OK)
        return;

    switch(code) {
        case CURLE_COULDNT_RESOLVE_PROXY:
            throw PROXY_NOT_SUPPORTED;
            break;
        case CURLE_OUT_OF_MEMORY:
            throw OUT_OF_MEMORY;
            break;
        default:
            throw NETWORK_ERROR;
            break;
    }
}

string http_client::curl_escape(const string &input) {
    //if the length argument is set to 0 (zero), 
    //curl_easy_escape uses strlen() on the input url to find out the size.
    char *tmp = tmp = curl_easy_escape (curl_handle_, input.c_str(), 0);
    if(!tmp)
        throw OUT_OF_MEMORY;

    tr1::shared_ptr<char> release(tmp, curl_free);
    string output(tmp);
    return output;
}
