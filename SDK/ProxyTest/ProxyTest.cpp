#include <iostream>
#include <string>
#include <vcri.h>
#include <vector>
#include <proxy.cpp>
#include <utils.cpp>
#include <http_client.cpp>
#include <vcri_global.cpp>
#include <thread.cpp>
#include <log.cpp>
#include <consts.cpp>
using namespace std;

int main()
{
    uint32_t index = 0;
    proxy_t proxy;
    int ret = get_system_proxy(index, proxy);
        
    system("pause");

    return 0;
}