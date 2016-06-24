#pragma warning(disable:4996)

#ifndef _VCRI_THREAD_H_
#define _VCRI_THREAD_H_
#include <stdio.h>
#include <stdlib.h>

#include <winsock2.h>
#include <Windows.h>
#include <process.h>

typedef CRITICAL_SECTION vrci_thread_mutex_t;
typedef HANDLE  vrci_thread_cond_t;


int vrci_thread_mutex_init( vrci_thread_mutex_t * mutex, void * attr );

int vrci_thread_mutex_destroy( vrci_thread_mutex_t * mutex );

int vrci_thread_mutex_lock( vrci_thread_mutex_t * mutex );

int vrci_thread_mutex_unlock( vrci_thread_mutex_t * mutex );

int vrci_thread_cond_init( vrci_thread_cond_t * cond, void * attr );

int vrci_thread_cond_destroy( vrci_thread_cond_t * cond );

int vrci_thread_cond_wait( vrci_thread_cond_t * cond, vrci_thread_mutex_t * mutex );

int vrci_thread_cond_timedwait( vrci_thread_cond_t * cond, vrci_thread_mutex_t * mutex, int timeout_ms );

int vrci_thread_cond_signal( vrci_thread_cond_t * cond );



void vrci_sleep(size_t dwMilliseconds);

 
class ILock  
{  
public:  
	virtual ~ILock() {}  

	virtual void Lock() const = 0;  
	virtual void Unlock() const = 0;  
};  
 
class cri_section : public ILock  
{  
public:  
	cri_section();  
	~cri_section();  

	virtual void Lock() const;  
	virtual void Unlock() const;  

    vrci_thread_mutex_t m_critclSection;
};  


class vcri_lock 
{  
public:  
	vcri_lock(const ILock&);  
	~vcri_lock();  
	void Unlock();
    void Lock();
private:  
	const ILock& m_lock;  
	bool  m_block;

};



#endif

