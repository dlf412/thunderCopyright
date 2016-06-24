#ifndef _VCRI_CONSTS_H__
#define _VCRI_CONSTS_H__

#include "stdint.h"

#include <string>

typedef enum {
    INFRINGING      = 0,
    NON_INFRINGING  = 1,
    CANNOT_IDENTIFY = 2,
    PROCESSING      = 3
} vcri_result;

typedef enum {
    VCRI_OK             = 0,
    BAD_ARGUMENTS       = -0x40000,
    ACCESS_DENIED       = -0x40003,
    TASK_NOT_FOUND      = -0x40004,
    PROXY_NOT_SUPPORTED = -0x40007,
    ALREADY_INITED      = -0x40009,
    NOT_INITED          = -0x40012,
    BAD_SEED            = -0x40013,
    UNKNOWN_ERROR       = -0x50000,
    SERVER_BUSY         = -0x50003,
    NETWORK_ERROR       = -0x50004,
    OUT_OF_MEMORY       = -0x50005,
    FILESYS_ERROR       = -0x50006,
    SYSTEM_ERROR        = -0x50007
} vcri_error_code;

typedef enum {
    SERVER_BAD_ARGUMENTS  = 0x40000,
    SERVER_HASH_NOT_HIT   = 0x40004,
    SERVER_ACCESS_DENIED  = 0x40003,
    SERVER_SEED_TOO_LARGE = 0x40013
} vcri_server_code;

const uint32_t VCRI_VERSION = 0x00000001;
const uint32_t TIME_OUT = 4;

const uint32_t LOG_BUF_SIZE = 100*1024;//100k
const uint32_t BUF_PER_LOG = 8*1024;//8k
const uint32_t LOG_LIFE_TIME = 7;//7 day

const uint32_t BACKOFF_LIMIT = 640;
const uint32_t BACKOFF_STEP = 10;

const uint32_t PROXY_RETRY_LIMIT = 5;

const uint32_t MIN_POLL_INTERVAL = 10;
const uint32_t MAX_POLL_INTERVAL = 1800;
const uint32_t BASE_POLL_INTERVAL = 600;

#define SERVER_LEN 4 
extern const std::string server_list[SERVER_LEN];
const uint32_t MAX_MASTER_ERROR_ATTEMPT = 2;
const uint32_t MAX_SLAVE_ERROR_ATTEMPT = 1;

const uint32_t SECONDS_PER_DAY = 86400;
const uint32_t MS_PER_SECOND = 1000;

#endif

