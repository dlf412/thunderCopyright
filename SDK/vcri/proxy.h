#ifndef _VCRI_PROXY_H_
#define _VCRI_PROXY_H_

#include <string>
#include "vcri.h"
#include "vcri_global.h"

// if success, return 0  and record useful server and proxy
// else, return error code
int get_system_proxy(uint32_t& server_index, proxy_t& proxy);

#endif