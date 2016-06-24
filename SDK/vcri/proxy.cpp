#include <string>
#include <vector>

#include "consts.h"
#include "utils.h"
#include "http_client.h"

#include <Windows.h>
#include <Winhttp.h>

using namespace std;

typedef vector<proxy_t> vec_proxy_t;

static void free_proxy_ops(WINHTTP_PROXY_INFO &auto_proxy_info,
                           WINHTTP_CURRENT_USER_IE_PROXY_CONFIG &ie_proxy_config);
static int read_sys_proxy(const string& server, string& proxy_info);
static int parse_sys_proxy(const string& server, string& proxy_info, 
                           proxy_t& proxy);
static int add_proxy(const string& proxy_addr, vec_proxy_t& vec_proxy);
static int verify_proxy(const string& url, const proxy_t& proxy);

int get_system_proxy(uint32_t& server_index, proxy_t& proxy) {
     int ret = VCRI_OK;
     int i = 0;

     for (; i < SERVER_LEN; ++i) {
         string proxy_info;
         ret = read_sys_proxy(server_list[i], proxy_info);
         if (ret != VCRI_OK)
             return PROXY_NOT_SUPPORTED ;

         ret = parse_sys_proxy(server_list[i], proxy_info, proxy);
         if (ret == VCRI_OK) {
             server_index = i;
             break;
         }
     }

     return (i < SERVER_LEN ? VCRI_OK : PROXY_NOT_SUPPORTED);
}

void free_proxy_ops(WINHTTP_PROXY_INFO &auto_proxy_info,
                  WINHTTP_CURRENT_USER_IE_PROXY_CONFIG &ie_proxy_config) {
    if(auto_proxy_info.lpszProxy != NULL)
        GlobalFree(auto_proxy_info.lpszProxy);

    if(auto_proxy_info.lpszProxyBypass !=NULL )
        GlobalFree(auto_proxy_info.lpszProxyBypass);

    if(ie_proxy_config.lpszAutoConfigUrl != NULL)
        GlobalFree(ie_proxy_config.lpszAutoConfigUrl);

    if(ie_proxy_config.lpszProxy != NULL)
        GlobalFree(ie_proxy_config.lpszProxy);

    if(ie_proxy_config.lpszProxyBypass != NULL)
        GlobalFree(ie_proxy_config.lpszProxyBypass);
}

int read_sys_proxy(const string& server, string& proxy_info) {
    int res_code = 0;
    BOOL b_auto_config = false;

    WINHTTP_PROXY_INFO auto_proxy_info = {0};
    WINHTTP_AUTOPROXY_OPTIONS auto_proxy_options = {0};
    WINHTTP_CURRENT_USER_IE_PROXY_CONFIG ie_proxy_config = {0};

    if(WinHttpGetIEProxyConfigForCurrentUser(&ie_proxy_config)) {
        if (ie_proxy_config.fAutoDetect) b_auto_config = true;
        if(ie_proxy_config.lpszAutoConfigUrl != NULL) {
            b_auto_config = true;
            auto_proxy_options.lpszAutoConfigUrl 
                = ie_proxy_config.lpszAutoConfigUrl;
        }
    }
    else
        b_auto_config = true;

    if (!b_auto_config) {
        if (NULL == ie_proxy_config.lpszProxy) {
            free_proxy_ops(auto_proxy_info,ie_proxy_config);
            return -1;
        }
        res_code = wchar_to_string(ie_proxy_config.lpszProxy, proxy_info);
        if (res_code != 0) {
            free_proxy_ops(auto_proxy_info,ie_proxy_config);
            return -1;
        }

    }
    else{
        if (auto_proxy_options.lpszAutoConfigUrl != NULL )
            auto_proxy_options.dwFlags = WINHTTP_AUTOPROXY_CONFIG_URL;
        else{
            auto_proxy_options.dwFlags = WINHTTP_AUTOPROXY_AUTO_DETECT;
            auto_proxy_options.dwAutoDetectFlags = 
                WINHTTP_AUTO_DETECT_TYPE_DHCP | WINHTTP_AUTO_DETECT_TYPE_DNS_A;
        }

        auto_proxy_options.fAutoLogonIfChallenged = TRUE;

        wstring url_wstr;
        res_code = string_to_wchar(server, url_wstr);
        if (res_code != 0) {
            free_proxy_ops(auto_proxy_info,ie_proxy_config);
            return -1;
        }

        HINTERNET session = ::WinHttpOpen(0,WINHTTP_ACCESS_TYPE_DEFAULT_PROXY,
            WINHTTP_NO_PROXY_NAME,WINHTTP_NO_PROXY_BYPASS,WINHTTP_FLAG_ASYNC);
        if(NULL == session) { 
            free_proxy_ops(auto_proxy_info,ie_proxy_config);
            return -1;
        }

        // here we reset b_auto_config in case an auto-proxy isn't actually
        // configured for this url
        BOOL b_ret = WinHttpGetProxyForUrl(session, url_wstr.c_str(), 
            &auto_proxy_options, &auto_proxy_info);
        WinHttpCloseHandle(session);

        if (!b_ret) {
            if (NULL == ie_proxy_config.lpszProxy) {
                free_proxy_ops(auto_proxy_info,ie_proxy_config);
                return -1;
            }
            res_code = wchar_to_string(ie_proxy_config.lpszProxy, proxy_info);
            if (res_code != 0) {
                free_proxy_ops(auto_proxy_info,ie_proxy_config);
                return -1;
            }
        }
        else{
            if (NULL == auto_proxy_info.lpszProxy) {
                free_proxy_ops(auto_proxy_info,ie_proxy_config);
                return -1;
            }

            res_code = wchar_to_string(auto_proxy_info.lpszProxy, proxy_info);
            if (res_code != 0) {
                free_proxy_ops(auto_proxy_info,ie_proxy_config);
                return -1;
            }
        }

    }

    free_proxy_ops(auto_proxy_info,ie_proxy_config);
    return 0;
}

int parse_sys_proxy(const string& server, string& proxy_info,proxy_t& proxy) {

    vec_proxy_t vec_proxy;

    // add a last semicolon, so once we run out of semicolons, we're done
    proxy_info += ";";
    size_t segstart = 0;
    while(true) {
        size_t semicolon = proxy_info.find(';', segstart);
        if(semicolon == segstart) {
            segstart = semicolon + 1;
            continue;
        }
        if(semicolon == string::npos)
            break;
        add_proxy(proxy_info.substr(segstart, semicolon - segstart), vec_proxy);
        segstart = semicolon + 1;
    }

    //no available https/socks proxy, even if network is ok without proxy
    if(vec_proxy.empty()) {
        return PROXY_NOT_SUPPORTED;
    }

    string url;
    int ret = -1;
    url = "https://" + server + "/identified";
    for(size_t i = 0; i < vec_proxy.size(); i++) {
        proxy = vec_proxy[i];
        ret = verify_proxy(url, proxy);
        if(ret == VCRI_OK) {
            break;
        }
    }

    return ret;
}

int add_proxy(const string& proxy_info, vec_proxy_t& vec_proxy) {
    proxy_t proxy;

    size_t equal = proxy_info.find('=');
    if(equal == string::npos) {
        proxy.proxy_url = proxy_info;
        proxy.proxy_type = HTTPS_PROXY;
        vec_proxy.push_back(proxy);
        proxy.proxy_type = SOCKS_PROXY;
        vec_proxy.push_back(proxy);
    } else {
        string type_str = proxy_info.substr(0, equal);
        if(type_str == "https")
            proxy.proxy_type = HTTPS_PROXY;
        else if (type_str == "socks")
            proxy.proxy_type = SOCKS_PROXY;
        else
            return PROXY_NOT_SUPPORTED;

        proxy.proxy_url = proxy_info.substr(equal + 1);
        if(proxy.proxy_url.empty())
            return PROXY_NOT_SUPPORTED;
        vec_proxy.push_back(proxy);
    }

    return VCRI_OK;
}

int verify_proxy(const string& url, const proxy_t& proxy) {
    int ret = VCRI_OK;
    try{
        http_client client(proxy);
        request_t request;
        vector<char> body;
        vector<char> head;
        client.do_get(url, request, head, body, TIME_OUT);
    }
    catch (vcri_error_code) {
        ret = PROXY_NOT_SUPPORTED;
    }

    return ret;
}
