#include "thread.h"

#include "consts.h"

void vrci_sleep(size_t dwMilliseconds){
#if !defined(_WIN32)
    if (dwMilliseconds>=MS_PER_SECOND)
        sleep(dwMilliseconds/MS_PER_SECOND);
    else
        usleep( dwMilliseconds * MS_PER_SECOND);
#else
    Sleep(dwMilliseconds);
#endif

}

cri_section::cri_section(){
    vrci_thread_mutex_init(&m_critclSection,NULL);
}

cri_section::~cri_section(){
    vrci_thread_mutex_destroy(&m_critclSection);
}

void cri_section::Lock() const{
    vrci_thread_mutex_lock((vrci_thread_mutex_t*)&m_critclSection);
}

void cri_section::Unlock() const{
    vrci_thread_mutex_unlock((vrci_thread_mutex_t*)&m_critclSection);
}

vcri_lock::vcri_lock(const ILock& m) : m_lock(m) {
    m_lock.Lock();
    locked_ = 1;
}

vcri_lock::~vcri_lock(){
    if (locked_)
        m_lock.Unlock();
}


void vcri_lock::Unlock(){
    if(locked_ == 1)
        m_lock.Unlock();
    if(locked_)
        --locked_;
}

void vcri_lock::Lock(){
    if (!locked_)
        m_lock.Lock();
    ++locked_;
}

int vrci_thread_mutex_init( vrci_thread_mutex_t * mutex, void * attr){
    InitializeCriticalSection(mutex);
    return 0;
}

int vrci_thread_mutex_destroy( vrci_thread_mutex_t * mutex ){
    DeleteCriticalSection(mutex);
    return 0;
}

int vrci_thread_mutex_lock( vrci_thread_mutex_t * mutex ){
    EnterCriticalSection((LPCRITICAL_SECTION)mutex);
    return 0;
}

int vrci_thread_mutex_unlock( vrci_thread_mutex_t * mutex ){ 
    LeaveCriticalSection((LPCRITICAL_SECTION)mutex);
    return 0;
}

int vrci_thread_cond_init( vrci_thread_cond_t * cond, void * attr ){
    *cond = CreateEvent( NULL, FALSE, FALSE, NULL );
    return NULL == *cond ? GetLastError() : 0;
}

int vrci_thread_cond_destroy( vrci_thread_cond_t * cond ){
    int ret = CloseHandle( *cond );
    return 0 == ret ? GetLastError() : 0;
}

/*
Caller MUST be holding the mutex lock; the
lock is released and the caller is blocked waiting
on 'cond'. When 'cond' is signaled, the mutex
is re-acquired before returning to the caller.
*/
int vrci_thread_cond_wait( vrci_thread_cond_t * cond, vrci_thread_mutex_t * mutex ){
    int ret = 0;
    vrci_thread_mutex_unlock( mutex );
    ret = WaitForSingleObject( *cond, INFINITE );
    vrci_thread_mutex_lock( mutex );
    return WAIT_OBJECT_0 == ret ? 0 : GetLastError();
}

int vrci_thread_cond_timedwait( vrci_thread_cond_t * cond,
                             vrci_thread_mutex_t * mutex, int timeout_ms ){
    int ret = 0;

    vrci_thread_mutex_unlock( mutex );

    ret = WaitForSingleObject( *cond, timeout_ms );

    vrci_thread_mutex_lock( mutex );
    if (ret == WAIT_OBJECT_0) return 0;
    else if (ret == WAIT_TIMEOUT) return -1;
    else return GetLastError();
}

int vrci_thread_cond_signal( vrci_thread_cond_t * cond ){
    int ret =SetEvent( *cond );
    return 0 == ret ? GetLastError() : 0;
}

