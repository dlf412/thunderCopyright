#include <string>
#include <set>
#include <vector>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "log.h"
#include "consts.h"
#include "utils.h"
#include "thread.h"

using namespace std;

extern log_level_t g_log_level;

vcri_log::vcri_log (const log_level_t &level): level_ (level) {
    char temp_path[MAX_PATH];
    if(GetTempPath(MAX_PATH, temp_path) == 0)
        throw SYSTEM_ERROR;

    string log_dir = (string)temp_path + "\\vcri";
    if(!file_exist(log_dir)) {
        if(!CreateDirectory(log_dir.c_str(), NULL)) {
            throw FILESYS_ERROR;
        }
    }
    this->path_ = log_dir;

    char* buf = (char*)malloc(LOG_BUF_SIZE +1);
    if(!buf)
        throw OUT_OF_MEMORY;

    memset(buf, '\0', LOG_BUF_SIZE + 1);
    this->buf_ = buf;

    reload_level();
}

vcri_log::~vcri_log () {
    if (this->buf_) {
        write_to_file();
        free(this->buf_);
    }
}

void vcri_log::impl_log (unsigned int level, const char *fmt, va_list al) {
    try {
        if(level > level_)
            return;

        vcri_lock lock(lock_);
        string level_info;
        switch(level) {
            case VCRI_LOG_ERROR:
                level_info = "ERROR";
                break;
            case VCRI_LOG_DEBUG:
                level_info = "DEBUG";
                break;
            case VCRI_LOG_INFO:
                level_info = "INFO";
                break;
        }

        time_t ts = time(NULL);
        if (ts == (time_t)-1)
            return;

        tm* local_time = gmtime(&ts);
        char msg[BUF_PER_LOG] = {0};
        strftime(msg + strlen(msg), BUF_PER_LOG - strlen(msg),
            "%Y-%m-%d_%H:%M:%S", local_time);
        _snprintf(msg + strlen(msg), BUF_PER_LOG - strlen(msg), 
            "#%s:", level_info.c_str());
        vsnprintf(msg + strlen(msg), BUF_PER_LOG - strlen(msg), fmt, al);
        _snprintf(msg + strlen(msg), BUF_PER_LOG - strlen(msg), "\n");

        size_t log_len = strlen(msg);
        size_t used_buf_len = strlen(this->buf_);

        if(used_buf_len + log_len > LOG_BUF_SIZE) {
            write_to_file();

            memset(this->buf_, '\0', LOG_BUF_SIZE + 1);
            strncpy(this->buf_, msg, log_len);
        }else{
            strncpy(this->buf_ + used_buf_len, msg, log_len);
        }
    } catch(...) {
        // not affect main function when log failed
    }
}


void vcri_log::write_to_file() {

    //get local time
    time_t now = time(NULL);
    if(now == (time_t)-1)
        return;

    tm* local_time = gmtime(&now);
    char log_name[20];
    strftime(log_name, sizeof(log_name), "vcri.%Y%m%d.log", local_time);

    //write
    string log_path = this->path_ + "\\" + log_name;
    FILE* fp = fopen(log_path.c_str(), "a");
    if(!fp)
        return;
    tr1::shared_ptr<FILE> log_closer(fp, fclose);
    fwrite(this->buf_, sizeof(char), strlen(this->buf_), fp);

    delete_outdated_log();
}



void vcri_log::delete_outdated_log() {
    set<string> set_filename;
    get_dir_files(this->path_, (string)"vcri.*.log", set_filename);

    time_t now = time(NULL);
    if(now == (time_t)-1)
        return;
    //ignore those logs still during LOG_LIFE_TIME 
    for(int i = 0; i < LOG_LIFE_TIME; ++i) {
        time_t pre_ts = now - i*SECONDS_PER_DAY;
        tm* pre_time = gmtime(&pre_ts);
        char tmp_name[20];
        strftime(tmp_name, sizeof(tmp_name), "vcri.%Y%m%d.log", pre_time);
        set_filename.erase(tmp_name);
    }

    //delete outdated log file
    for(set<string>::iterator it = set_filename.begin(); 
        it != set_filename.end(); it++) {
            string log_path = this->path_ + "\\" + *it;
            if(!DeleteFile(log_path.c_str())) {
                continue;
            }
    }
}

void vcri_log::log (unsigned int level, const char *fmt, ...) {
    va_list al;
    va_start (al, fmt);
    impl_log (level, fmt, al);
    va_end (al);
}

void vcri_log::error_log (const char *fmt, ...) {
    va_list al;
    va_start (al, fmt);
    impl_log (VCRI_LOG_ERROR, fmt, al);
    va_end (al);
}

void vcri_log::info_log (const char *fmt, ...) {
    va_list al;
    va_start (al, fmt);
    impl_log (VCRI_LOG_INFO, fmt, al);
    va_end (al);
}

void vcri_log::debug_log (const char *fmt, ...) {
    va_list al;
    va_start (al, fmt);
    impl_log (VCRI_LOG_DEBUG, fmt, al);
    va_end (al);
}

void vcri_log::reload_level() {
    const char *env = getenv (VCRI_LOG);
    unsigned int log_level;
    if (!env || !*env)
        return;
    log_level = atoi (env);
    if (!log_level)
        return;
    if (log_level == 70)
        level_ = VCRI_LOG_DEBUG;
    else if (log_level == 60)
        level_ = VCRI_LOG_INFO;
    else if (log_level == 50)
        level_ = VCRI_LOG_ERROR;
}

