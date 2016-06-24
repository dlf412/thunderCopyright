#ifndef _VCRI_UTILS_H_
#define _VCRI_UTILS_H_
#include <string>
#include <set>
#include <vector>
#include <time.h>
#include "stdint.h"

int format_time(time_t ts, std::string& str);
std::string int2str(unsigned long long num);

int get_file_size(const std::string& file_path, int64_t& len);

int read_file_content(const std::string& file_path, 
                      unsigned char* dst, int64_t& len);

void base64_encode(const char* input, int length, std::string& dst, 
                          bool with_new_line = false);
void base64_decode(const std::string&  input, std::string& dst,
                          bool with_new_line = false);

std::string hex_escape(unsigned int len, const unsigned char *s);
std::string digest_sha1(const char* src);

int encode_utf8(const std::string& src,std::string& dst);
int encode_native(const std::string& src,std::string& dst);

int wchar_to_string(const std::wstring& wstr, std::string& str_dst);
int string_to_wchar(const std::string& str, std::wstring& str_dst);

bool file_exist(const std::string& path);
void get_dir_files(const std::string& dir, const std::string& filter, 
                   std::set<std::string>& set_name);

void cpy_str(const char** dst, const char* src);
#endif