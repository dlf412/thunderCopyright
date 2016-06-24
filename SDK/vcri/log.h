#ifndef __LOG_H__
#define __LOG_H__

#include <stdarg.h>
#include <stdio.h>
#include <string>

#include "thread.h"

typedef enum {
    VCRI_LOG_NONE,
    VCRI_LOG_ERROR,
    VCRI_LOG_INFO,
    VCRI_LOG_DEBUG
} log_level_t;

class vcri_log {
public:
    vcri_log (const log_level_t &level);
    ~vcri_log ();
    void log (unsigned int level, const char *fmt, ...);
    void error_log (const char *fmt, ...);
    void info_log (const char *fmt, ...); 
    void debug_log (const char *fmt, ...);
    void write_to_file();
private:
    void impl_log (unsigned int level, const char *fmt, va_list al);
   
    void delete_outdated_log();
    void reload_level();
private:
    char* buf_;
    cri_section lock_;
    unsigned int level_;
    std::string path_;
};

#endif // #ifndef __LOG_H__


