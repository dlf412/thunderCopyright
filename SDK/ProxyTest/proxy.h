
#ifndef _VCRI_PROXY_H_
#define _VCRI_PROXY_H_
#include <string>
#include "stdint.h"

int string_to_wchar(std::wstring& wchar_res, const std::string& str);
int wchar_to_string(const wchar_t *pwstr, std::string& res_str);
int get_host_and_port(const std::string& proxy_server, std::string& proxy_host, uint32_t& proxy_port);
int get_proxy_addr(const std::string& proxy_addr_info, const std::string& protocol_type, std::string& proxy_server);
int get_proxy_config(const std::string& req_url,std::string& proxy_info);

#endif