#include <string>
#include <string.h>
#include <Windows.h>
#include <Winhttp.h>
#include "stdint.h"
using namespace std;

int string_to_wchar(wstring& w_str, const string& str)
{
    size_t need_size = MultiByteToWideChar(CP_UTF8,NULL,str.c_str(),-1,NULL,0);
    if (need_size == 0)
    {
        return -1;
    }

    wchar_t* buf = (wchar_t*)malloc(sizeof(wchar_t) * need_size);
    if (NULL == buf)
    {
        return -1;
    }

    memset(buf,0,sizeof(wchar_t) *need_size);
    MultiByteToWideChar(CP_UTF8,NULL,str.c_str(),-1,buf,sizeof(wchar_t) *need_size);

    w_str = buf;
    free(buf);

    return 0;
}

int wchar_to_string(string& res_str, const wchar_t *pwstr)
{
    size_t need_size = WideCharToMultiByte(CP_UTF8,NULL,pwstr,-1,NULL,0,NULL,NULL);
    if (need_size == 0)
    {
        return -1;
    }

    char *buf = (char*)malloc(need_size);
    if (buf == NULL)
    {
        return -1;
    }

    memset(buf,0,need_size);
    WideCharToMultiByte(CP_UTF8,NULL,pwstr,-1,buf,need_size,NULL,NULL);

    res_str = buf;
    free(buf);

    return 0;
}

int get_proxy_addr(const string& proxy_info, const string& protocol_type, string& proxy_server)
{
    //https=127.0.0.1:8888;ftp=127.0.0.1:9098
    size_t type_pos = proxy_info.find(protocol_type);

    if(type_pos != string::npos)
    {
        //check "=" 
        type_pos += protocol_type.size() + 1;

        size_t semi_pos = proxy_info.find_first_of(';', type_pos);
        if (semi_pos != string::npos)
            //"https=127.0.0.1:8888;ftp=127.0.0.1:9098" find https type server==>127.0.0.1:8888
            proxy_server = proxy_info.substr(type_pos, semi_pos - type_pos);
        else
            //"https=127.0.0.1:8888" find https type proxy server==>127.0.0.1:8888
            proxy_server = proxy_info.substr(type_pos);

        //like:127.0.0.1:8888
        return 0;
    }

    return -1;
}

int get_host_and_port(const string& proxy_server, string& proxy_host, uint32_t& proxy_port)
{
    // 127.0.0.1:8888
    size_t pos = proxy_server.find(":");
    if (pos == string::npos)
    {
        return -1;
    }

    proxy_host = proxy_server.substr(0, pos);

    // ":"
    pos += 1;

    if (pos >= proxy_server.length())
    {
        return -1;
    }
    
    proxy_port = atoi(proxy_server.substr(pos).c_str());

    return 0;
}

int get_proxy_config(const string& req_url, string& proxy_info)
{
    int res_code = 0;
    BOOL b_auto_proxy = false;

    WINHTTP_PROXY_INFO auto_proxy_info = {0};
    WINHTTP_AUTOPROXY_OPTIONS auto_proxy_options = {0};
    WINHTTP_CURRENT_USER_IE_PROXY_CONFIG ie_proxy_config = {0};

    if(WinHttpGetIEProxyConfigForCurrentUser( &ie_proxy_config))
    {
        if(ie_proxy_config.fAutoDetect)
        {
            b_auto_proxy = true;
        }

        if(ie_proxy_config.lpszAutoConfigUrl != NULL)
        {
            b_auto_proxy = true;
            auto_proxy_options.lpszAutoConfigUrl = ie_proxy_config.lpszAutoConfigUrl;
        }
    }
    else
    {
        // use autoproxy
        b_auto_proxy = true;
    }

    if(b_auto_proxy)
    {
        if (auto_proxy_options.lpszAutoConfigUrl != NULL )
        {
            auto_proxy_options.dwFlags = WINHTTP_AUTOPROXY_CONFIG_URL;
        }
        else
        {
            auto_proxy_options.dwFlags = WINHTTP_AUTOPROXY_AUTO_DETECT;
            auto_proxy_options.dwAutoDetectFlags = WINHTTP_AUTO_DETECT_TYPE_DHCP | WINHTTP_AUTO_DETECT_TYPE_DNS_A;
        }

        // basic flags you almost always want
        auto_proxy_options.fAutoLogonIfChallenged = TRUE;

        // no agent string
        HINTERNET session = ::WinHttpOpen(0,
            WINHTTP_ACCESS_TYPE_DEFAULT_PROXY,
            WINHTTP_NO_PROXY_NAME,
            WINHTTP_NO_PROXY_BYPASS,
            WINHTTP_FLAG_ASYNC);

        wstring url_wstr;
        string_to_wchar(url_wstr, req_url);

        // here we reset b_auto_proxy in case an auto-proxy isn't actually
        // configured for this url
        
        b_auto_proxy = WinHttpGetProxyForUrl(session, url_wstr.c_str(), &auto_proxy_options, &auto_proxy_info );
        if(session)
        {
            WinHttpCloseHandle(session);
        }
    }

    if (b_auto_proxy)
    {
        // set proxy options for libcurl based on auto_proxy_info

        // auto_proxy_info.lpszProxy
        if(auto_proxy_info.lpszProxy)
        {
            wchar_to_string(proxy_info, auto_proxy_info.lpszProxy);
        }
        else
        {
            res_code = -1;
            goto PROXY_END;
        }
    }
    else
    {
        if( ie_proxy_config.lpszProxy != NULL )
        {
            // IE has an explicit proxy. set proxy options for libcurl here
            // based on ie_proxy_config
            //
            // note that sometimes IE gives just a single or double colon
            // for proxy or bypass list, which means "no proxy"
            wchar_to_string(proxy_info, ie_proxy_config.lpszProxy);
        }
        else
        {
            // there is no auto proxy and no manually
            res_code = -1;
            goto PROXY_END;
        }
    }

PROXY_END:
    if(auto_proxy_info.lpszProxy != NULL)
    {
        GlobalFree(auto_proxy_info.lpszProxy);
    }

    if(auto_proxy_info.lpszProxyBypass !=NULL )
    {
        GlobalFree(auto_proxy_info.lpszProxyBypass);
    }

    if(ie_proxy_config.lpszAutoConfigUrl != NULL)
    {
        GlobalFree(ie_proxy_config.lpszAutoConfigUrl);
    }

    if(ie_proxy_config.lpszProxy != NULL)
    {
        GlobalFree(ie_proxy_config.lpszProxy);
    }

    if(ie_proxy_config.lpszProxyBypass != NULL)
    {
        GlobalFree(ie_proxy_config.lpszProxyBypass);
    }

    return res_code;
}
