
#include "../json_c/json/json.h"
#include "../vcri/vcri.h"
#include "thread.h"
#include <stdlib.h>
#include <stdio.h>
#include <Windows.h>
#include <string>
#include <iostream>
#include <tchar.h>

using namespace std;

struct thread_arg
{
  int loop;
  int loop_config;
  vcri_params_t *params;
};

 cri_section g_cri_section;
 int g_loop_config;
 int g_thread_exit;

int multibyte_to_widechar(const std::string& str_src, std::wstring& wstr_dst,
  unsigned int code_page){
      size_t w_len = 0;
      w_len = MultiByteToWideChar(code_page, MB_ERR_INVALID_CHARS,
          (LPCTSTR)str_src.c_str(), -1, NULL,0);
      if (w_len == 0)
          return -1;

      WCHAR * wch =(WCHAR*) malloc(sizeof(WCHAR)*w_len);
      if (NULL == wch)
          return -1;

      memset(wch, 0, sizeof(WCHAR)*w_len);

      w_len = MultiByteToWideChar(code_page, MB_ERR_INVALID_CHARS,
          (LPCTSTR)str_src.c_str(), -1, wch, w_len);
      if (w_len == 0){
          free(wch);
          return -1;
      }

      wstr_dst = wch;
      free(wch);

      return 0;
}

int widechar_to_multibyte(const std::wstring& wstr_src, std::string& str_dst,
  unsigned int code_page){
      size_t c_len = 0;
      c_len = WideCharToMultiByte(code_page, 0, wstr_src.c_str(), -1,
          NULL, 0, NULL, NULL);
      if (c_len == 0)
          return -1;

      char *ch = (char*)malloc(c_len);
      if (NULL == ch)
          return -1;

      memset(ch, 0, c_len);

      c_len = WideCharToMultiByte (code_page, 0, wstr_src.c_str(), -1,
          ch, c_len, NULL,NULL);
      if (c_len == 0){
          free(ch);
          return -1;
      }

      str_dst = ch;

      free(ch);
      return 0;
}

int encode_utf8(const std::string& src,std::string& dst){
    int ret = 0;
    wstring wstr;
    ret = multibyte_to_widechar(src, wstr, CP_ACP);
    if (ret != 0)
        return ret;

    ret = widechar_to_multibyte(wstr, dst, CP_UTF8);
    return ret;
}

const char* get_json_valuse(json_object* obj,char *key)
{
    if (NULL==obj){
        return NULL;
    }
    json_object* res_obj = json_object_object_get(obj, key);
    if (NULL ==res_obj ){
        return NULL;
    }
    char *json_value =(char*)json_object_get_string(res_obj);
    if (NULL==json_value){
        return NULL;
    }
    return json_value;
}

void result_callback(int32_t overview,
                     const vcri_result_t* results,
                     uint32_t result_count,
                     const char* url,
                     const char* file_private_id) {
    cout << "[resuts] url:" << url << " ,overview:" << overview 
        << " ,result_count:" << result_count << endl;

    if (results != NULL && result_count > 0){
        cout << "results:" <<endl;
        for (int i = 0; i < result_count; ++i){
            cout<< "result:" << results[i].result << " ,path: " 
                << results[i].path <<endl;
        }
    }
}

void free_params(vcri_params_t *params){
    if (params){
        if (params->file_name){
            free((void*)params->file_name);
            params->file_name =NULL;
        }

        if (params->file_private_id){
            free((void*)params->file_private_id);
            params->file_private_id =NULL;
        }

        if (params->mime_type){
            free((void*)params->mime_type);
            params->mime_type =NULL;
        }

        if (params->referer){
            free((void*)params->referer);
            params->referer =NULL;
        }

        if (params->url){
            free((void*)params->url);
            params->url =NULL;
        }

        free(params);
    }
}

void print_param(const vcri_params_t* params){
    if(params){
        cout<< "========================================="<<endl;
        if(params->url)
            cout<<"url:"<<params->url<<endl;
        if(params->file_name)
            cout<<"file_name:"<<params->file_name<<endl;
        if(params->file_private_id)
            cout<<"file_private_id:"<<params->file_private_id<<endl;
        if(params->mime_type)
            cout<<"mime_type:"<<params->mime_type<<endl;
        if(params->referer)
            cout<<"referer:"<<params->referer<<endl;
        cout<<"file_size:"<<params->file_size<<endl;
    }
}

void submit_task(void *arg){
    int nLoop = 0;
    int ret =0;

    vcri_params_t *param =NULL;
    if (NULL != arg)
      param =(vcri_params_t *)arg;

    while(1){
        if(NULL != param){
             nLoop++;
             if(nLoop > g_loop_config)
                 break;
             ret = vcri_identify(result_callback, param);
             print_param(param);
             cout << "ret:" << ret << endl;
             cout<< "========================================="<<endl;
        }
        Sleep(1000);
    }

    if(NULL != param){
        free_params(param);
        param = NULL;
    }

    vcri_lock lock(g_cri_section);
    g_thread_exit++;
}

int init(json_object *json_parse,vcri_proxy_t &proxy){
    const char* json_value = get_json_valuse(json_parse,"proxy_type");
    vcri_proxy_type_t proxy_type = (vcri_proxy_type_t)atoi(json_value);

    json_value =get_json_valuse(json_parse,"host");
    if (json_value&& strlen(json_value) >0)
        proxy.host=json_value;

    json_value =get_json_valuse(json_parse,"port");
    if (json_value&& strlen(json_value) >0)
        proxy.port = atoi(json_value);

    json_value =get_json_valuse(json_parse,"username");
    if (json_value&& strlen(json_value) >0)
        proxy.username =json_value;

    json_value =get_json_valuse(json_parse,"password");
    if (json_value&& strlen(json_value) >0)
        proxy.username =json_value;
   
    int ret =vcri_init(proxy_type,&proxy);
    if(ret != 0) 
        return ret;

    json_value = get_json_valuse(json_parse,"api_key");
    ret = vcri_set_api_key(json_value);
    if(ret != 0) 
        return ret;

    json_value = get_json_valuse(json_parse,"client");
    ret = vcri_set_client_id(json_value);
    if(ret != 0) 
        return ret;

    json_value = get_json_valuse(json_parse,"program_info");
    ret = vcri_set_program_info(json_value);
    if(ret != 0) 
        return ret;

    return 0;
}

int main(){
    //get json object from .json file
    vcri_proxy_t proxy ={0};
    
    int ret=0;
    char* json_value = NULL;
    int loop_count = 1000;
    
    int end_loop_finish = 0;

    json_object  *json_parse = json_object_from_file("config.json");
    if (is_error(json_parse)){
        printf("json error\n");
        system("pause");

        return 0;
    }

    json_value =(char*) get_json_valuse(json_parse,"loop_count");
    if(json_value) {
        loop_count =atoi(json_value);
        if (loop_count <=0)  loop_count =1000;
    }
    g_loop_config = loop_count;

    json_value =(char*)get_json_valuse(json_parse,"end_loop_finish");
    if (json_value)
        end_loop_finish =atoi(json_value);
    
    ret = init(json_parse,proxy);
    if (ret != 0 ){
        printf("init error\n");
        system("pause");

        return 0;
    }
    
    json_object  *json_params = json_object_object_get(json_parse,"params");
    int array_num = json_object_array_length(json_params);

    string str_temp;
    for(int i = 0; i < array_num; i++){ 
        vcri_params_t *params =(vcri_params_t*)malloc(sizeof(vcri_params_t));
        memset(params,0,sizeof(vcri_params_t));

        json_object* json_index = json_object_array_get_idx(json_params, i);
        json_value = (char*)get_json_valuse(json_index,"url");
        if (json_value){
            encode_utf8(json_value,str_temp);
            params->url = strdup(str_temp.c_str());
        }

        json_value =(char*)get_json_valuse(json_index,"referer");
        if (json_value){
            encode_utf8(json_value,str_temp);
            params->referer = strdup(str_temp.c_str());
        }

        json_value = (char*)get_json_valuse(json_index,"file_name");
        if (json_value){
            encode_utf8(json_value,str_temp);
            params->file_name = strdup(str_temp.c_str());
        }

        json_value = (char*)get_json_valuse(json_index,"private_id");
        if (json_value){
            encode_utf8(json_value,str_temp);
            params->file_private_id = strdup(str_temp.c_str());
        }

        json_value = (char*)get_json_valuse(json_index,"mime_type");
        if (json_value) {
            encode_utf8(json_value,str_temp);
            params->mime_type = strdup(str_temp.c_str());
        }
      
        json_value =(char*)get_json_valuse(json_index,"file_size");
        if (NULL != json_value) {
            params->file_size = atoi(json_value);
        }

        params->struct_size = sizeof(vcri_params_t);
        params->struct_version = 1;
        
        HANDLE pHandle =::CreateThread(NULL,0,(LPTHREAD_START_ROUTINE)submit_task,params,NULL,0);
        CloseHandle(pHandle);
    }

    while(1){
        vcri_lock lock(g_cri_section);
        if(g_thread_exit >= array_num && end_loop_finish >0)
            break;
        lock.Unlock();

        Sleep(10000);
    }

    vcri_fini();
    json_object_put(json_parse);

    printf("test is finished thread_num=%d,\n",array_num);

    system("pause");
}