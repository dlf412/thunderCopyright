/*
* Copyright (c) 2013, 恒生电子股份有限公司
* All rights reserved.
*
* 文件名称：socket.h
* 摘　　要：对线程操作的类，已经多线同步的锁，支持多平台
*
*
* 作	者　：徐龙重
* 创建日期：2013年03月01日
* 
*/
//////////////////////////////////////////////////////////////////////
#pragma warning(disable:4996)

#ifndef _THREAD_H_   
#define _THREAD_H_ 
#include <stdio.h>
#include <stdlib.h>

#ifdef WIN32 // win32 thread
#include <winsock2.h>
#include <Windows.h>
#include <process.h>

#define SP_THREAD_CALL __stdcall

typedef unsigned sp_thread_t;
typedef unsigned sp_thread_result_t;
typedef sp_thread_result_t ( __stdcall * sp_thread_func_t )( void * args);

//typedef HANDLE  sp_thread_mutex_t;
//临界区效率高
typedef CRITICAL_SECTION sp_thread_mutex_t;
typedef HANDLE  sp_thread_cond_t;
typedef DWORD   sp_thread_attr_t;

#define SP_THREAD_CREATE_DETACHED 1

int sp_thread_mutex_init( sp_thread_mutex_t * mutex, void * attr );

int sp_thread_mutex_destroy( sp_thread_mutex_t * mutex );

int sp_thread_mutex_lock( sp_thread_mutex_t * mutex );

int sp_thread_mutex_unlock( sp_thread_mutex_t * mutex );

int sp_thread_cond_init( sp_thread_cond_t * cond, void * attr );

int sp_thread_cond_destroy( sp_thread_cond_t * cond );

int sp_thread_cond_wait( sp_thread_cond_t * cond, sp_thread_mutex_t * mutex );

int sp_thread_cond_signal( sp_thread_cond_t * cond );

sp_thread_t sp_thread_self();

int sp_thread_attr_init( sp_thread_attr_t * attr );

int sp_thread_attr_setdetachstate( sp_thread_attr_t * attr, int detachstate );

int sp_thread_create( sp_thread_t * thread, sp_thread_attr_t * attr,sp_thread_func_t myfunc, void * args );

#else // pthread

#include <pthread.h>
#include <unistd.h>

#define SP_THREAD_CALL

typedef void * sp_thread_result_t;
typedef pthread_mutex_t sp_thread_mutex_t;
typedef pthread_cond_t  sp_thread_cond_t;
typedef pthread_t       sp_thread_t;
typedef pthread_attr_t  sp_thread_attr_t;

#define sp_thread_mutex_init(m,a)   pthread_mutex_init(m,a)
#define sp_thread_mutex_destroy(m)  pthread_mutex_destroy(m)
#define sp_thread_mutex_lock(m)     pthread_mutex_lock(m)
#define sp_thread_mutex_unlock(m)   pthread_mutex_unlock(m)

#define sp_thread_cond_init(c,a)    pthread_cond_init(c,a)
#define sp_thread_cond_destroy(c)   pthread_cond_destroy(c)
#define sp_thread_cond_wait(c,m)    pthread_cond_wait(c,m)
#define sp_thread_cond_signal(c)    pthread_cond_signal(c)

#define sp_thread_attr_init(a)        pthread_attr_init(a)
#define sp_thread_attr_setdetachstate pthread_attr_setdetachstate
#define SP_THREAD_CREATE_DETACHED     PTHREAD_CREATE_DETACHED

#define sp_thread_self    pthread_self
#define sp_thread_create  pthread_create

typedef sp_thread_result_t ( * sp_thread_func_t )( void * args );

#endif

void sp_sleep(size_t dwMilliseconds);
//#include <map>

//锁接口类   
class ILock  
{  
public:  
	virtual ~ILock() {}  

	virtual void Lock() const = 0;  
	virtual void Unlock() const = 0;  
};  

 

//临界区锁类   
class CriSection : public ILock  
{  
public:  
	CriSection();  
	~CriSection();  

	virtual void Lock() const;  
	virtual void Unlock() const;  

private:  
	 sp_thread_mutex_t m_critclSection;
};  

//锁   
class ThreadLock  
{  
public:  
	ThreadLock(const ILock&);  
	~ThreadLock();  
	void Unlock();

private:  
	const ILock& m_lock;  
	bool  m_block;

};  


#ifdef WIN32
	typedef HANDLE thHandle;
#else
	typedef pthread_t* thHandle;
#endif
typedef void  ( SP_THREAD_CALL *pThread_fn)(void*);

//dwStackSize 单位是字节
thHandle ThreadCreate(pThread_fn pfn,void *arg,bool bClose=true,size_t dwStackSize=0); 
void CloseThHandle(thHandle pHandle);


#endif

