#ifndef _VCRI_TASK_H__
#define _VCRI_TASK_H__

#include <memory>
#include <deque>
#include <string>
#include <map>
#include <vector>

#include <curl/curl.h>
#include <time.h>

#include "stdint.h"
#include "thread.h"

#include "vcri.h"

typedef struct {
    std::string key;
    std::string value;
} header_t, query_param_t;

typedef struct {
    CURLoption opt;
    std::string value;
} opt_t;

typedef struct {
    std::vector<opt_t> opts;
    std::vector<header_t> headers;
    std::vector<query_param_t> query_params;
} request_t;

typedef struct response_t{
    int status_code;
    time_t retry_after;

    int32_t code;
    time_t data;
    int32_t overview;
    vcri_result_t* results;
    uint32_t result_count;

    response_t();
    ~response_t();
} response_t;

typedef enum {
    TASK_WAITING,
    TASK_ERROR,
    TASK_PROCESSING,
    TASK_DONE
} task_status_t;

class Task : public std::tr1::enable_shared_from_this<Task> {
public:
    vcri_result_notify_t notify;
    vcri_params_t params;
    uint8_t progress;

public:
    bool is_seed_file;
    std::string seed_file;
    std::string digest;
    std::string digest_algorithm;

public:
    unsigned execute_at;
    unsigned backoff;
    unsigned proxy_retries;
    task_status_t status;

public:
    Task(vcri_result_notify_t notify, const vcri_params_t* params);
    ~Task();
    void fill_request(request_t &request);
    void retry();
    void reschedule(unsigned retry_after);

private:
    unsigned int approximately_now() const;

public:
    bool need_send_seed() const { return (is_seed_file == true && seed_sent_ == false); }
    void seed_sent () { seed_sent_ = true; }
private:
    bool seed_sent_;
};

typedef std::tr1::shared_ptr<Task> task_ptr;

class task_runner {
public:
    task_runner();
    ~task_runner();

public:
    void run();
    bool push(const task_ptr &task);
    bool del(const vcri_params_t& params);
    bool pop(task_ptr &task);
    int32_t set_task_progress(task_ptr &task, uint8_t progress);

private:
    void finish(const task_ptr &task);
    void requeue(const task_ptr &task);
    void block(unsigned s = 0);
    void insert(const task_ptr &task);
    task_ptr pop_front();
    bool is_same_task(const vcri_params_t &params, const task_ptr &task) const;
    void del_task_from_queue(const task_ptr &task);
    bool is_stop();

private:
    mutable cri_section mutex;
    mutable vrci_thread_cond_t cond;
    HANDLE thread_;
    mutable bool stop_;
    std::map<std::string, task_ptr> tasks;
    typedef std::map<unsigned, task_ptr> timer_queue;
    timer_queue timed_queue;
};

#endif


