#include <iostream>
#include <vcri.h>
#include <utils.cpp>
#include <string>
#include <string.h>
#include <Windows.h>
using namespace std;

void vcri_callback(int32_t overview, const vcri_result_t* results, 
                   uint32_t result_count, const char* url, 
                   const char* file_private_id);

int  testCmd(int argc, const char* argv[]);
void output_argv(int argc, const char* argv[]);
void free_params(vcri_params_t* params);

int main(int argc, const char* argv[]){
    testCmd(argc, argv);

    system("pause");
    return 0;
}

int testCmd(int argc, const char* argv[])
{
    if (argc < 2){
        cerr<<"no params"<<endl;
        system("pause");
        return -1;
    }

    output_argv(argc, argv);

    string api_key;
    string client_info;
    string client_id;
    int proxy_type = 0;

    vcri_proxy_t proxy;
    proxy.host = "";
    proxy.port = 0;
    proxy.username = "";
    proxy.password = "";

    vcri_params_t params;
    params.file_name = "";
    params.file_private_id = "";
    params.file_size = 0;
    params.mime_type = "";
    params.referer = "";
    params.struct_size = sizeof(vcri_params_t);
    params.struct_version = 1;
    params.url = "";
    params.struct_version = 1;
    params.struct_size = sizeof(params);

    int i = 1;
    while ( i < argc){
        string argc_name = argv[i++];

        if (argc_name == "-key")
        {
            api_key = argv[i++];
        }
        else if (argc_name == "-cinfo")
        {
            client_info = argv[i++];
        }
        else if (argc_name == "-cid")
        {
            client_id = argv[i++];
        }
        else if (argc_name == "-proxy")
        {
            proxy_type = atoi(argv[i++]);
        }
        else if (argc_name == "-host")
        {
            proxy.host = argv[i++];
        }
        else if (argc_name == "-port")
        {
            proxy.port = atoi(argv[i++]);
        }
        else if (argc_name == "-user")
        {
            proxy.username = argv[i++];
        }
        else if (argc_name == "-pwd")
        {
            proxy.password = argv[i++];
        }
        else if (argc_name == "-url")
        {
            params.url = argv[i++];
        }
        else if (argc_name == "-referer")
        {
            params.referer = argv[i++];
        }
        else if (argc_name == "-pid")
        {
            params.file_private_id = argv[i++];
        }
        else if (argc_name == "-mime")
        {
            params.mime_type = argv[i++];
        }
        else if (argc_name == "-name")
        {
            params.file_name = argv[i++];
        }
        else if (argc_name == "-size")
        {
            params.file_size = atoi(argv[i++]);
        }
        else
        {
            cerr<<"illegal param:"<< argv[i -1] <<endl;
            ++i;
        }
    }

#ifdef UTF8_ENCODE
    if(params.file_name){
        string encode_name;
        encode_utf8((string)params.file_name, encode_name);
        params.file_name = strdup(encode_name.c_str());
    }

    if(params.file_private_id){
        string encode_pid;
        encode_utf8((string)params.file_private_id,encode_pid);
        params.file_private_id = strdup(encode_pid.c_str());
    }

    if(params.referer){
        string encode_ref;
        encode_utf8((string)params.referer,encode_ref);
        params.referer = strdup(encode_ref.c_str());
    }

    if(params.url){
        string encode_url;
        encode_utf8((string)params.url,encode_url);
        params.url = strdup(encode_url.c_str());
    }

    if(params.mime_type){
        string encode_mime;
        encode_utf8((string)params.mime_type,encode_mime);
        params.mime_type = strdup(encode_mime.c_str());
    }
#endif // UTF8_ENCODE

    int32_t res;
    res = vcri_init((vcri_proxy_type_t)proxy_type, &proxy);
    if( res < 0){
        cerr<< "init error:" << res << endl;
        return res;
    }

    res = vcri_set_api_key(api_key.c_str());
    if( res < 0){
        cerr<< "set api key error:"<<res << endl;
        return res;
    }

    res = vcri_set_client_id(client_id.c_str());
    if( res < 0){
        cerr<< "set client id:" <<res << endl;
        return res;
    }

    res = vcri_set_program_info(client_info.c_str());
    if( res < 0){
        cerr<< "set program info error:" << res << endl;
        return res;
    }

    //multi thread
    res = vcri_identify(vcri_callback, &params);
    cout<< "\nvcri result: " << res <<endl;

#ifdef UTF8_ENCODE
    free_params(&params);
#endif // UTF8_ENCODE

    vcri_fini();
    return 0;
}

void output_argv(int argc, const char* argv[])
{
    int i = 1;
    while (i < argc){
        string argc_name = argv[i++];
        argc_name = argc_name.substr(1);
        cout<< argc_name << ":\"" <<argv[i++] << "\"" <<endl;
    }
}

void vcri_callback(int32_t overview, const vcri_result_t* results, 
                   uint32_t result_count, const char* url, 
                   const char* file_private_id){
    //string tmp_url = encode_native(string(url));

    cout << "overview:" << overview <<endl;
    cout << "result_count:" << result_count << endl;

    if (results != NULL && result_count > 0){
        cout << "results:" <<endl;
        for (int i = 0; i < result_count; ++i){
            cout<< "status:" << results[i].result << " ,path: " << results[i].path <<endl;
        }
    }
}


void free_params(vcri_params_t* params)
{
    if(params->file_name)
        free((void*)params->file_name);
    if(params->file_private_id)
        free((void*)params->file_private_id);
    if(params->url)
        free((void*)params->url);
    if(params->referer)
        free((void*)params->referer);
    if(params->mime_type)
        free((void*)params->mime_type);

}