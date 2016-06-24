#include <io.h>
#include <openssl/evp.h>
#include <openssl/bio.h>
#include <openssl/buffer.h>
#include <openssl/sha.h>
#include <string.h>
#include <windows.h>

#include "consts.h"
#include "utils.h"

#include <sstream>
#include <string>

using namespace std;

static int multibyte_to_widechar(const std::string& str_src,
                                 std::wstring& wstr_dst,
                                 unsigned int code_page);

static int widechar_to_multibyte(const std::wstring& wstr_src,
                                 std::string& str_dst,
                                 unsigned int code_page);
static int get_codec_error();

int format_time(time_t ts, string& str) {
    char date[100];
    tm* local_time = gmtime(&ts);
    strftime(date, sizeof(date), "%a, %d %b %Y %H:%M:%S %Z", local_time);
    return encode_utf8((string)date, str);
}

string int2str(unsigned long long num) {
    ostringstream str;
    str << num;
    return str.str();
}

int get_file_size(const string& file_path, int64_t& len) {
    len = 0;
    FILE* fp = fopen(file_path.c_str(), "rb");
    if (fp == NULL)
        return FILESYS_ERROR;
    tr1::shared_ptr<FILE> file(fp, fclose);
    if(_fseeki64(fp, 0, SEEK_END))
        return FILESYS_ERROR;
    len = _ftelli64(fp);
    if(len == (size_t) -1)
        return FILESYS_ERROR;
    return 0;
}

int read_file_content(const string& file_path, unsigned char* dst,
                      int64_t& len) {
    FILE* fp = fopen(file_path.c_str(), "rb");
    if (fp == NULL)
        return FILESYS_ERROR;
    tr1::shared_ptr<FILE> file(fp, fclose);

    size_t total_read = 0;
    while(total_read < len) {
        size_t read = fread(dst + total_read, sizeof(unsigned char),
                            (size_t)len - total_read, fp);
        if (read == 0)
            return FILESYS_ERROR;
        total_read += read;
    }
    return 0;
}


void base64_encode(const char* input, int length, string& dst, 
                     bool with_new_line) {
    BIO * bmem = NULL;
    BIO * b64 = NULL;
    BUF_MEM * bptr = NULL;

    b64 = BIO_new(BIO_f_base64());
    if (NULL == b64)
        throw OUT_OF_MEMORY;
    tr1::shared_ptr<BIO> b64_ptr(b64, BIO_free);

    if(!with_new_line)
        BIO_set_flags(b64, BIO_FLAGS_BASE64_NO_NL);

    bmem = BIO_new(BIO_s_mem());
    if(NULL == bmem)
        throw OUT_OF_MEMORY;
    tr1::shared_ptr<BIO> bmem_ptr(bmem, BIO_free_all);

    b64 = BIO_push(b64, bmem);
    if (NULL == b64)
        throw OUT_OF_MEMORY;;

    int len = BIO_write(b64, input, length);
    if (len == 0)
        throw OUT_OF_MEMORY;

    BIO_flush(b64);
    BIO_get_mem_ptr(b64, &bptr);
    if (NULL == bptr || 0 == bptr->length)
        throw OUT_OF_MEMORY;

    char * buf = (char *)malloc(bptr->length + 1);
    if (NULL == buf)
        throw OUT_OF_MEMORY;
    tr1::shared_ptr<char> buf_ptr(buf, free);

    memcpy(buf, bptr->data, bptr->length);
    buf[bptr->length] = '\0';
    dst = buf;
}

void base64_decode(const string &srt_input, string& dst, 
                   bool with_new_line) {
    BIO * b64 = NULL;
    BIO * bmem = NULL;
    const char *input = srt_input.c_str();

    b64 = BIO_new(BIO_f_base64());
    if (NULL == b64)
        throw OUT_OF_MEMORY;
    tr1::shared_ptr<BIO> b64_ptr(b64, BIO_free);

    if(!with_new_line)
        BIO_set_flags(b64, BIO_FLAGS_BASE64_NO_NL);

    int length = strlen(input);
    bmem = BIO_new_mem_buf((void*)input, length);
    if (NULL == bmem) 
        throw OUT_OF_MEMORY;
    tr1::shared_ptr<BIO> bmem_ptr(bmem, BIO_free_all);

    b64 = BIO_push(b64, bmem);
    if (NULL == b64) 
        throw OUT_OF_MEMORY;

    char * buffer = (char *)malloc(length + 1);
    if (NULL ==buffer) 
        throw OUT_OF_MEMORY;
    tr1::shared_ptr<char> buf_ptr(buffer, free);

    memset(buffer, 0, length + 1);
    int len = BIO_read(b64, buffer, length);
    if (len == 0) 
        throw OUT_OF_MEMORY;
    buffer[len] = '\0';
    dst = buffer;
}

string hex_escape(unsigned int len, const unsigned char *s) {
    string res(len*2+1, '\0');
    for (uint32_t i = 0; i < len; ++i)
        sprintf(&res[i*2], "%02x", s[i]);
    res.resize(len*2);

    return res;
}

string digest_sha1(const char* src) {
    unsigned char buf[20];
    SHA1((const unsigned char*)src, strlen(src), &buf[0]);
    return hex_escape(20, buf);
}

int encode_native(const std::string& src,std::string& dst) {
    int ret = 0;
    wstring wstr;
    ret = multibyte_to_widechar(src, wstr, CP_UTF8);
    if (ret != 0)
        return ret;

    ret = widechar_to_multibyte(wstr ,dst, CP_ACP);
    return ret;
}

int encode_utf8(const std::string& src,std::string& dst) {
    int ret = 0;
    wstring wstr;
    ret = multibyte_to_widechar(src, wstr, CP_ACP);
    if (ret != 0)
        return ret;

    ret = widechar_to_multibyte(wstr, dst, CP_UTF8);
    return ret;
}

int multibyte_to_widechar(const std::string& str_src, std::wstring& wstr_dst,
                          unsigned int code_page) {
    size_t w_len = 0;
    w_len = MultiByteToWideChar(code_page, MB_ERR_INVALID_CHARS,
        (LPCTSTR)str_src.c_str(), -1, NULL,0);
    if (w_len == 0)
        return get_codec_error();

    WCHAR * wch =(WCHAR*) malloc(sizeof(WCHAR)*w_len);
    if (NULL == wch)
        return OUT_OF_MEMORY;

    tr1::shared_ptr<WCHAR> wch_ptr(wch, free);
    memset(wch, 0, sizeof(WCHAR)*w_len);
    w_len = MultiByteToWideChar(code_page, MB_ERR_INVALID_CHARS,
        (LPCTSTR)str_src.c_str(), -1, wch, w_len);
    if (w_len == 0) 
        return get_codec_error();

    wstr_dst = wch;

    return 0;
}

int widechar_to_multibyte(const std::wstring& wstr_src, std::string& str_dst,
                          unsigned int code_page) {
    size_t c_len = 0;
    c_len = WideCharToMultiByte(code_page, 0, wstr_src.c_str(), -1,
        NULL, 0, NULL, NULL);
    if (c_len == 0)
        return get_codec_error();

    char *ch = (char*)malloc(c_len);
    if (NULL == ch)
        return OUT_OF_MEMORY;

    tr1::shared_ptr<char> ch_ptr(ch, free);
    memset(ch, 0, c_len);
    c_len = WideCharToMultiByte (code_page, 0, wstr_src.c_str(), -1,
        ch, c_len, NULL,NULL);
    if (c_len == 0) 
        return get_codec_error();

    str_dst = ch;
    return 0;
}

int get_codec_error() {
    int error_code = GetLastError();
    if (error_code == ERROR_NO_UNICODE_TRANSLATION)
        return BAD_ARGUMENTS;
    else
        return SYSTEM_ERROR;
}

int string_to_wchar(const string& str, wstring& str_dst) {
    int ret = 0;
    ret = multibyte_to_widechar(str, str_dst, CP_UTF8);
    return ret;
}

int wchar_to_string(const wstring& wstr, string& str_dst) {
    int ret = 0;
    ret = widechar_to_multibyte(wstr, str_dst, CP_UTF8);
    return ret;
}

bool file_exist(const string& path) {
    return (access(path.c_str(), 0) == 0);
}

void get_dir_files(const string& dir, const string& filter,
                   set<string>& set_name) {
    WIN32_FIND_DATA find_data;
    string find = dir + "\\" + filter;

    HANDLE find_handle = FindFirstFile(find.c_str(), &find_data);
    if(INVALID_HANDLE_VALUE == find_handle)
        throw SYSTEM_ERROR;

    tr1::shared_ptr<void> find_release(find_handle, FindClose);
    while(TRUE) {
        if(!(find_data.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY)) {
            set_name.insert((string)find_data.cFileName);
        }

        if(!FindNextFile(find_handle, &find_data))
            break;
    }
}

void cpy_str(const char ** dst, const char* src) {
    if(src == NULL) {
        *dst = NULL;
        return;
    }

    *dst = strdup(src);
    if(*dst == NULL)
        throw OUT_OF_MEMORY;
}