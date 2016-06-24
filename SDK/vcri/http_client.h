#ifndef __HTTP_CLIENT_H__
#define __HTTP_CLIENT_H__

#include <time.h>
#include <curl/curl.h>
#include <string>
#include <vector>

#include "task.h"
#include "vcri.h"
#include "vcri_global.h"

class http_client {
public:
    http_client();

    http_client(const proxy_t& proxy);

    ~http_client();

    void do_get(const std::string& url, const request_t& request, 
                std::vector<char>& resp_head, std::vector<char>& resp_body,
                time_t timeout);

    void do_post(const std::string& url, const request_t& request,
                 const std::string& post_data, std::vector<char>& resp_head,
                 std::vector<char>& resp_body, time_t timeout);

private:
    void init();

    void set_proxy(const proxy_t& proxy);
    void set_ssl();
    void set_timeout(time_t timeout);
    void set_callback(std::vector<char> &resp_head,
                      std::vector<char> &resp_body);
    void set_request(const std::string& url, const request_t& request,
                     curl_slist **headers);
    void set_post_data(const std::string& post_data);
private:
    void throw_on_error(int& code);
    std::string curl_escape(const std::string &input);
private:
    CURL* curl_handle_;
};

#endif // #ifndef __HTTP_CLIENT_H__

