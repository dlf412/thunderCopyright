#ifndef _SD_ANDROID_UTILITY_H
#define _SD_ANDROID_UTILITY_H

#if defined(_ANDROID_LINUX)

#ifdef __cplusplus
extern "C" {
#endif

// ------------------------------------

#include "utility/define.h"
#include <jni.h>

typedef struct tag_JavaParm
{
	JavaVM *_vm;
	jobject _thiz;
	jobject _downloadengine;
} JavaParm;

_int32 sd_android_utility_init(JavaVM * vm, jobject thiz,jobject  de);

_int32 sd_android_utility_uninit();

BOOL sd_android_utility_is_init();

JavaParm *sd_android_utility_get_java();

// ------------------------------------

#ifdef __cplusplus
}
#endif

#endif
#endif

