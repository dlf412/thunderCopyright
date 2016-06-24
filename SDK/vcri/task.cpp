#include <string>
#include <cassert>

#include "vcri_global.h"
#include "task.h"
#include "consts.h"
#include "digest.h"
#include "utils.h"
#include "log.h"
#include "identify_task.h"

using namespace std;

DWORD WINAPI run_tasks(LPVOID param);

response_t::response_t() : status_code(200), retry_after(0), code(0), data(0),
             overview(PROCESSING), results(0), result_count(0){
}

response_t::~response_t() {
    if(results) {
        for (uint32_t i=0; i< result_count; ++i) {
            if(results[i].path != NULL)
                free((char*)results[i].path);
        }

        free(results);
    }
}

Task::Task(vcri_result_notify_t notify, const vcri_params_t* params)
    : execute_at((unsigned int)time(0)), backoff(BACKOFF_STEP) ,seed_sent_ (false),
     progress(0),proxy_retries(0), status(TASK_WAITING) {

    this->notify = notify;

    cpy_str(&this->params.file_name, params->file_name);
    cpy_str(&this->params.file_private_id, params->file_private_id);
    cpy_str(&this->params.mime_type, params->mime_type);
    cpy_str(&this->params.referer, params->referer);
    cpy_str(&this->params.url, params->url);

    this->params.file_size = params->file_size;
    this->params.struct_size = params->struct_size;
    this->params.struct_version = params->struct_version;

    if(execute_at == (time_t)-1)
        // we cannot get current time, so we assume it's 0
        // the task will execute before everything else
        execute_at = 0;

    this->is_seed_file = is_file_url(params->url);
    if(this->is_seed_file) {
        string url;
        int32_t ret = encode_native (params->url, url);
        if(ret != VCRI_OK) {
            g_log.error_log("decode url failed, url %s", params->url);
            throw BAD_ARGUMENTS;
        }
        this->seed_file = url.substr(7);
        if (!file_exist(this->seed_file)) {
            g_log.error_log("seed file not exist, url %s", params->url);
            throw BAD_ARGUMENTS;
        }
        digest_seed(this->seed_file, this->digest, this->digest_algorithm);
    } else 
        digest_from_url(this->params.url, this->digest,
                        this->digest_algorithm);

    g_log.info_log("Task create, digest %s, url: %s",
                   this->digest.c_str(), this->params.url);
}

void Task::fill_request(request_t &request) {
    int ret = 0;
    header_t header;
    query_param_t query_param;
    opt_t opt;

    opt.opt = CURLOPT_USERAGENT;
    opt.value = g_program_info;
    request.opts.push_back(opt);

    if (this->params.referer
        &&this->params.referer[0] != '\0') {
        opt.opt = CURLOPT_REFERER;
        opt.value = this->params.referer;
        request.opts.push_back(opt);
    }

    header.key = "X-Client-ID";
    header.value = g_client_id;
    request.headers.push_back(header);

    header.key = "If-Modified-Since";
    ret = format_time(this->execute_at, header.value);
    if(ret != VCRI_OK)
        throw ret;
    request.headers.push_back(header);

    header.key = "Date";
    time_t now = time(NULL);
    if(now == (time_t)(-1))
        throw SYSTEM_ERROR;
    ret = format_time(now, header.value);
    if(ret != VCRI_OK)
        throw ret;
    request.headers.push_back(header);

    header.key = "X-Progress";
    header.value = "0";
    request.headers.push_back(header);

    header.key = "X-Client-Address";
    header.value = "0.0.0.0:0";
    request.headers.push_back(header);

    if(!is_seed_file) {
        if(this->params.file_name
            && this->params.file_name[0] != '\0') {
                header.key = "X-File-Name";
                header.value = this->params.file_name;
                request.headers.push_back(header);
        }

        header.key = "X-File-Size";
        header.value = int2str(this->params.file_size);
        request.headers.push_back(header);

        if(this->params.url 
            && this->params.url[0] != '\0') {
                header.key = "X-URL";
                header.value = this->params.url;
                request.headers.push_back(header);
        }
    }

    if(this->params.mime_type && this->params.mime_type[0] != '\0') {
        header.key = "X-Mime-Type";
        header.value = this->params.mime_type;
        request.headers.push_back(header);
    }

    query_param.key = "key";
    query_param.value = g_api_key;
    request.query_params.push_back(query_param);

    query_param.key = "digest";
    query_param.value = this->digest;
    request.query_params.push_back(query_param);

    query_param.key = "digest-algorithm";
    query_param.value = this->digest_algorithm;
    request.query_params.push_back(query_param);

    if(this->params.file_private_id && this->params.file_private_id[0] != '\0') {
        query_param.key = "hash";
        query_param.value = this->params.file_private_id;
        request.query_params.push_back(query_param);
    }
}

unsigned int Task::approximately_now() const {
    time_t now = time(0);
    if(now == (time_t)-1)
        // we cannot backoff from current ts, we can only backoff from last
        // attempt
        now = execute_at;
    return (unsigned int)now;
}

void Task::retry() {
    execute_at = approximately_now() + backoff;
    backoff *= 2;
    if(backoff > BACKOFF_LIMIT)
        backoff = BACKOFF_LIMIT;
}

void Task::reschedule(unsigned retry_after) {
    if(retry_after < MIN_POLL_INTERVAL || retry_after > MAX_POLL_INTERVAL)
        retry_after = BASE_POLL_INTERVAL;
    execute_at = approximately_now() + retry_after;
}

Task::~Task() {
    if(this->params.file_name)
        free((void*)this->params.file_name);
    if(this->params.file_private_id)
        free((void*)this->params.file_private_id);
    if(this->params.mime_type)
        free((void*)this->params.mime_type);
    if(this->params.referer)
        free((void*)this->params.referer);
    if(this->params.url)
        free((void*)this->params.url);
}

task_runner::task_runner() : stop_(false) {
    vrci_thread_cond_init(&cond, NULL);

    thread_ = CreateThread(NULL, 0, run_tasks, (void *) this, 0, NULL);
    if (thread_ == NULL)
        throw SYSTEM_ERROR;
}

task_runner::~task_runner() {
    // notify the bg thread that we're to stop
    stop_ = true;
    vrci_thread_cond_signal(&cond);

    // join the thread
    WaitForSingleObject(thread_, INFINITE);
    CloseHandle(thread_);

    // destroy the cond
    vrci_thread_cond_destroy(&cond);
}

void task_runner::insert(const task_ptr& task) {
    // our timer queue is not a multimap, so ts as the key cannot collide
    // with earlier tasks. however, since we execute 1 task at a time, and
    // 1s is not that long a time, we can offset the ts by 1s if there is a
    // collision

    for(timer_queue::iterator it = timed_queue.find(task->execute_at);
        it != timed_queue.end() && it->first == task->execute_at; ++it)
        ++task->execute_at;
    timed_queue[task->execute_at] = task;
}

bool task_runner::push(const task_ptr &task) {
    try {
        vcri_lock lock(mutex);
        if (tasks.find(task->params.url) != tasks.end ())
            return true;
        tasks[task->params.url] = task;
        insert(task);
        vrci_thread_cond_signal(&cond);
        return true;
    } catch (const std::bad_alloc &) {
        g_log.error_log("Task create, out of memory. url %s",
                        task->params.url);
        return false;
    } catch (...) {
        g_log.error_log("Task create, unknown error. url %s",
                        task->params.url);
        return false;
    }
}

bool task_runner::del(const vcri_params_t& params) {
    vcri_lock lock(mutex);
    map<string, task_ptr>::iterator it = tasks.find(params.url);
    if (it == tasks.end () || !is_same_task(params, it->second))
        return false;

    timed_queue.erase(it->second->execute_at);
    tasks.erase(params.url);
    return true;
}

task_ptr task_runner::pop_front() {
    tr1::shared_ptr<Task> task = timed_queue.begin()->second;
    timed_queue.erase(timed_queue.begin());
    return task;
}

bool task_runner::pop(task_ptr &task) {
    vcri_lock lock(mutex);
    unsigned last_time = 0;
    while(!stop_) {
        if(timed_queue.empty()) {
            block();
            continue;
        }

        unsigned int now = (unsigned int)time(0);
        unsigned int execute_at = timed_queue.begin()->first;
        if(now == (unsigned)(time_t)-1
           // we cannot tell what time it is now, so we execute the first task
           // immediately
           || now < last_time
           // clock goes backwards, someone's trying to trick us, so we execute
           // a task to not be easily fooled
           || now >= execute_at) {
            task = pop_front();
            last_time = max(now, last_time);
            return true;
        }

        block(execute_at - now);
    }
    return false;
}

void task_runner::block(unsigned s) {
    if(!s)
        vrci_thread_cond_wait(&cond, &mutex.m_critclSection);
    else {
        vrci_thread_cond_timedwait(&cond, &mutex.m_critclSection,
                                   (int)s * MS_PER_SECOND);
    }
}

void task_runner::requeue(const task_ptr &task) {
    vcri_lock lock(mutex);
    if (tasks.find(task->params.url) == tasks.end ()) // task deleted
        return;
    else
        insert(task);
}

void task_runner::finish(const task_ptr &task) {
    vcri_lock lock(mutex);
    tasks.erase(task->params.url);
}

bool task_runner::is_stop()
{
    vcri_lock lock(mutex);
    return stop_;

}

void task_runner::run() {

    while (!is_stop()) {
        try {
            task_ptr task;
            if (pop(task)) {
                if(identify_task(task))
                    finish(task);
                else
                    requeue(task);
            }
        } catch(...) {
            g_log.error_log("something unexpectedly bad happened");
        }

    }

}

int32_t task_runner::set_task_progress(task_ptr &task,
                                      uint8_t progress) {
    vcri_lock lock(mutex);
    if (tasks.find(task->params.url) == tasks.end ())
        return TASK_NOT_FOUND;
    if((tasks[task->params.url]->progress == 0 && progress != 0)
       || (tasks[task->params.url]->progress != 100 && progress == 100))
           g_log.info_log("Task progress, url: %s, progress: %u",
                          task->params.url, (unsigned) progress);
    tasks[task->params.url]->progress = progress;
    return VCRI_OK;
}

bool task_runner::is_same_task(const vcri_params_t &params,
                               const task_ptr &task) const {
    if(!params.url || strcmp(params.url, task->params.url) != 0)
        return false;
    return true;
}

DWORD WINAPI run_tasks(LPVOID param) {
    assert(param);

    task_runner *runner = (task_runner *) param;
    runner->run();

    return 0;
}
