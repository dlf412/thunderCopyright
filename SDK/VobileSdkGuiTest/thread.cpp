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
#include "stdafx.h"
#include "thread.h"



void sp_sleep(size_t dwMilliseconds)
{
#if !defined(_WIN32)

	// 20040729 在linux\unix下usleep的最大值为1秒，>=1秒时，改用sleep()单位为秒;

	if (dwMilliseconds>=1000)

		sleep(dwMilliseconds/1000);

	else

		usleep( dwMilliseconds * 1000);

#else

	Sleep(dwMilliseconds);

#endif

}

//初始化临界资源对象   
CriSection::CriSection()  
{  
	sp_thread_mutex_init(&m_critclSection,NULL);
}  

//释放临界资源对象   
CriSection::~CriSection()  
{  
	sp_thread_mutex_destroy(&m_critclSection);
}  

//进入临界区，加锁   
void CriSection::Lock() const  
{  
	sp_thread_mutex_lock((sp_thread_mutex_t*)&m_critclSection);
}     

//离开临界区，解锁   
void CriSection::Unlock() const  
{  
	sp_thread_mutex_unlock((sp_thread_mutex_t*)&m_critclSection);
}  



//利用C++特性，进行自动加锁   
ThreadLock::ThreadLock(const ILock& m) : m_lock(m)  
{ 
	m_lock.Lock();  
	m_block=true;
}  

//利用C++特性，进行自动解锁   
ThreadLock::~ThreadLock()  
{  
	if (m_block)
	{
		m_lock.Unlock();
		m_block=false;
	}

}  


void ThreadLock::Unlock()
{
	if (m_block)
	{
		m_lock.Unlock(); 
		m_block=false;
	}
}

/*------------------------------线程池-------------------------------------*/
#ifdef WIN32
int sp_thread_mutex_init( sp_thread_mutex_t * mutex, void * attr )
{
	InitializeCriticalSection(mutex);
	//*mutex = CreateMutex( NULL, FALSE, NULL );
	//return NULL == * mutex ? GetLastError() : 0;
	return 0;
}

int sp_thread_mutex_destroy( sp_thread_mutex_t * mutex )
{
	DeleteCriticalSection(mutex);
	//int ret = CloseHandle( *mutex );
	//return 0 == ret ? GetLastError() : 0;
	return 0;
}

int sp_thread_mutex_lock( sp_thread_mutex_t * mutex )
{
	EnterCriticalSection((LPCRITICAL_SECTION)mutex);
	//int ret = WaitForSingleObject( *mutex, INFINITE );
	//return WAIT_OBJECT_0 == ret ? 0 : GetLastError();
	return 0;
}

int sp_thread_mutex_unlock( sp_thread_mutex_t * mutex )
{
	LeaveCriticalSection((LPCRITICAL_SECTION)mutex);
	//int ret = ReleaseMutex( *mutex );
	//return 0 != ret ? 0 : GetLastError();
	return 0;
}

int sp_thread_cond_init( sp_thread_cond_t * cond, void * attr )
{
	*cond = CreateEvent( NULL, FALSE, FALSE, NULL );
	return NULL == *cond ? GetLastError() : 0;
}

int sp_thread_cond_destroy( sp_thread_cond_t * cond )
{
	int ret = CloseHandle( *cond );
	return 0 == ret ? GetLastError() : 0;
}

/*
Caller MUST be holding the mutex lock; the
lock is released and the caller is blocked waiting
on 'cond'. When 'cond' is signaled, the mutex
is re-acquired before returning to the caller.
*/
int sp_thread_cond_wait( sp_thread_cond_t * cond, sp_thread_mutex_t * mutex )
{
	int ret = 0;

	sp_thread_mutex_unlock( mutex );

	ret = WaitForSingleObject( *cond, INFINITE );

	sp_thread_mutex_lock( mutex );

	return WAIT_OBJECT_0 == ret ? 0 : GetLastError();
}

int sp_thread_cond_signal( sp_thread_cond_t * cond )
{
	int ret =SetEvent( *cond );
	return 0 == ret ? GetLastError() : 0;
}

sp_thread_t sp_thread_self()
{
	return GetCurrentThreadId();
}

int sp_thread_attr_init(sp_thread_attr_t * attr )
{
	*attr = 0;
	return 0;
}

int sp_thread_attr_setdetachstate( sp_thread_attr_t * attr, int detachstate )
{
	*attr |= detachstate;
	return 0;
}

int sp_thread_create( sp_thread_t * thread, sp_thread_attr_t * attr,
	sp_thread_func_t myfunc, void * args )
{
	// _beginthreadex returns 0 on an error
	HANDLE h = (HANDLE)_beginthreadex( NULL, 0, myfunc, args, 0, thread );
	if ( h >0)
	{
		CloseHandle(h);
		return 0;
	}
	else
		return GetLastError();
	
}


#endif


/*-------------------------------线程操作-------------------------------------*/

thHandle ThreadCreate(pThread_fn pfn,void *arg,bool bClose, size_t dwStackSize )
{

#ifdef WIN32
	HANDLE pHandle =::CreateThread(NULL,dwStackSize,(LPTHREAD_START_ROUTINE)pfn,arg,NULL,0);
	if (pHandle && bClose)
	{
		::CloseHandle(pHandle);
		pHandle=NULL;
	}
	return pHandle;
	
#else
	if (bClose)
	{
		pthread_attr_t tattr;
		pthread_attr_init (&tattr);
		pthread_attr_setdetachstate (&tattr,PTHREAD_CREATE_DETACHED);
		if (dwStackSize >0)
			 pthread_attr_setstacksize(&tattr, dwStackSize);
		
		pthread_t Handle;
		pthread_create(&Handle, &tattr, (sp_thread_func_t)pfn, arg);
		pthread_attr_destroy(&tattr);
		return NULL;
	}
	else
	{
		pthread_t *pHandle=(pthread_t*)malloc(sizeof(pthread_t));
		pthread_create(pHandle, NULL, (sp_thread_func_t)pfn, arg);
		return pHandle;
	}
#endif
	return NULL;
}

void CloseThHandle(thHandle pHandle)
{
	if (NULL!=pHandle)
	{
#ifdef WIN32
		::CloseHandle(pHandle);
#else
		free(pHandle);
#endif
		pHandle=NULL;
	}
}