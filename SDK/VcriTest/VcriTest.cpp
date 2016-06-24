#include <stdlib.h>
#include <crtdbg.h>

#include <iostream>
#include <vcri.h>
#include <utils.cpp>
#include <string>
#include <string.h>
#include <Windows.h>

using namespace std;


#define new  new(_CLIENT_BLOCK, __FILE__, __LINE__)
#define malloc  malloc(_CLIENT_BLOCK, __FILE__, __LINE__)
#define realloc  realloc(_CLIENT_BLOCK, __FILE__, __LINE__)

void vcri_callback(int32_t overview, const vcri_result_t* results, 
                   uint32_t result_count, const char* url, 
                   const char* file_private_id);
int main(int argc, const char* argv[])
{

    vcri_params_t params;

    const char* user_agent = "thunder_client_v7.1.25";
    const char* client_id = "this-is-test-client-id";
    const char* api_key = "this-is-TMP-apikey";

    int code;
    vcri_proxy_t proxy = {0};
    proxy.host = "192.168.3.42";
    proxy.port = 808;
    proxy.username = "voile";
    proxy.password = "123";

    code = vcri_init(NO_PROXY, &proxy);
    if (code != 0)
    {
        cout<<"init error"<<code;
        return -1;
    }

    code = vcri_set_api_key(api_key);
    if (code != 0)
    {
        cout<<"set api key error"<<code;
        return -1;
    }

    code = vcri_set_client_id(client_id);
    if (code != 0)
    {
        cout<<"set client id error"<<code;
        return -1;
    }

    code = vcri_set_program_info(user_agent);
    if (code != 0)
    {
        cout<<"set program info error"<<code;
        return -1;
    }

    string file_name = "01ample.mp4";
    params.file_name = file_name.c_str();

    string url;
    //encode_utf8(string("thunder://QUFmdHA6Ly82OjZAZnRwLjY2eXMub3JnOjQ1MTgvob7RuMDXz8LU2Hd3dy5keTEzMS5jb22hv7Hk0M698LjVMUJE1tDTosur19YxMDI0uN/H5S5ybXZiWlo="),url);
    encode_utf8(string("file://C:\\Users\\研发01\\Desktop\\mentage.torrent"), url)
    params.url = url.c_str();

    params.file_private_id = "";
    params.file_size = 65324;
    params.mime_type = "变形金刚";
    string referer = "http://host:port/sample.html";
    encode_utf8(string("http://host:port/sample金刚.html"), referer);

    string tmp;
    code = encode_native(referer, tmp);
    params.referer = referer.c_str();

    string pid;
    //encode_utf8(string("this-is-bad&乱码&digest=错误"), pid);
    params.file_private_id = "this-is-bad-pid";
    //params.file_private_id = pid.c_str();

    params.struct_version = 1;
    params.struct_size = sizeof(params);

    Sleep(10000);

    code = vcri_identify(vcri_callback, &params);
    cout<<"vcri_identidy return:" << code<<endl; 

    //Sleep(40000);

    code = vcri_progress(&params, 67);
    cout<<"vcri_progress ret:" << code<<endl;

    //Sleep(3000);

    code = vcri_cancel(&params);
    cout<<"vcri_cancel ret:" << code<<endl;

    vcri_fini();

    cout<<"exit vcri"<<endl;

    _CrtDumpMemoryLeaks();
    system("pause");
    return 0;
}

void vcri_callback(int32_t overview, const vcri_result_t* results, 
                   uint32_t result_count, const char* url, 
                   const char* file_private_id){
    //string tmp_url = encode_native(string(url));

    cout << "url:" << url << " overview:" << overview << " ,result_count:" << result_count << endl;

    if (results != NULL && result_count > 0){
        cout << "results:" <<endl;
        for (int i = 0; i < result_count; ++i){
                cout<< "result:" << results[i].result << " ,path: " << results[i].path <<endl;
        }
    }
}
