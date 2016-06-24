#include "digest.h"
#include "vcri_global.h"
#include "consts.h"
#include "utils.h"

#include <openssl/sha.h>

#include <vector>

using namespace std;

static void digest_url(const string &url, string &digest, string &digest_alg);

static void digest_thunder(const string& url, string& digest, string& algo);
static void digest_ed2k(const string &url, string& digest, string& algo);
static void digest_magnet(const string &url, string& digest, string& algo);
static void remove_AAZZ(string &url);


bool is_file_url(const char *url) {
    return (strncmp(url, "file://", 7) == 0);
}
void digest_from_url(const string &url, string &digest, string &algo) {
    try {
        const char* buf_url = url.c_str();
        if (strncmp(buf_url, "magnet:?", 8) == 0) {
            digest_magnet(url, digest, algo);
        } else if (strncmp(buf_url, "ed2k://", 7) == 0) {
            digest_ed2k(url, digest, algo);
        } else if (strncmp(buf_url, "thunder://", 10) == 0) {
            digest_thunder(url, digest, algo);
        } else {
            digest_url(url, digest, algo);
        }
    } catch (vcri_error_code error_code) {
        throw error_code;
    } catch (...) {
        throw UNKNOWN_ERROR;
    }
}

static void digest_url(const string &url, string &digest, string &algo) {
    digest = digest_sha1(url.c_str());
    algo = "sha1";
}

static void digest_magnet(const string &url, string& digest, string& algo) {
    //magnet:?xt=urn:btih:54DC8FB49410D897544ACFF13C73F47B6154165C&dn=Need.for.Speed.2014.BluRay.720p.DTS.x264-CHD
    static const char *magnet_head = "magnet:?xt=urn:btih:";
    static int btih_hash_len = 40;
    int len = strlen(magnet_head);
    if (url.compare(0, len, magnet_head) == 0
        && (int)url.length() >= len + btih_hash_len) {
        digest = url.substr(len, btih_hash_len);
        algo = "magnet";
    } else {
        digest_url(url, digest, algo);
    }
}

static bool get_ed2k_hash(const string &url, string &hash) {
    size_t file_pos = url.find('|');
    if (file_pos == std::string::npos)
        return false;
    size_t filename_pos = url.find('|', file_pos + 1);
    if (filename_pos == std::string::npos)
        return false;
    size_t filesize_pos = url.find('|', filename_pos + 1);
    if (filesize_pos == std::string::npos)
        return false;
    size_t hash_pos = url.find('|', filesize_pos + 1);
    if (hash_pos == std::string::npos)
        return false;
    size_t hashend_pos = url.find('|', hash_pos + 1);
    if (hashend_pos == std::string::npos)
        return false;
    if (hashend_pos - hash_pos != 33)
        return false;
    hash = url.substr(hash_pos + 1, 32);
    return true;
}

static void digest_ed2k(const string &url, string& digest, string& algo) {
    // ed2k://|file|filename|file_size|dc6454510f631eacb1f13594252ab857|other....|/
    if(get_ed2k_hash(url, digest))
        algo = "ed2k";
    else
        digest_url(url, digest, algo);
}

static void digest_thunder(const string& url, string& digest, string& algo) {
    //thunder://QUFodHRwOi8vczIubXA0LmRhdGEuYTY3LmNvbS9tcDQvMjAxMy8wNy8xMC90YWlqaXhpYTAxLm1wNFpa/

    static const char *thunder_head = "thunder://";
    static const int len = strlen(thunder_head);
    string encoded_url = url[url.length()] == '/'
        ? url.substr(len, url.length() - len - 1)
        : url.substr(len, url.length() - len);
    if (encoded_url.empty ()) {
        digest_url(url, digest, algo);
        return;
    }

    string decoded_url;
    base64_decode(encoded_url, decoded_url);
    remove_AAZZ(decoded_url);
    if (decoded_url.compare(0, 7, "ed2k://") == 0) {
        digest_ed2k(decoded_url, digest, algo);
        algo = string("thunder-") + algo;
    } else {
        digest_url(decoded_url, digest, algo);
        algo = string("thunder-") + algo;
    }
}

static void remove_AAZZ(string &url) {
    size_t len = url.length();
    if (len >=4 && url[0]=='A' && url[1] =='A' 
        && url[len -2]=='Z' && url[len-1]=='Z')
        url = url.substr(2, len - 4);
    else if (len >= 2 && (url[0] =='A' && url[1] =='A'))
        url = url.substr(2, len - 2);
}

void digest_seed(const string &seed, string &digest, string &algo) {
    static const int64_t MAX_SEED_SIZE = 1024*1024;
    static const int64_t MIN_SEED_SIZE = 0; // NOTE I donot know
    static const int64_t MAX_READ = MAX_SEED_SIZE;

    FILE *seed_fp = fopen(seed.c_str(), "rb");
    if(!seed_fp) {
        g_log.error_log("cannot open file: %s, error: %s", seed.c_str(),
                        strerror(errno));
        throw FILESYS_ERROR;
    }
    tr1::shared_ptr<FILE> file(seed_fp, fclose);
    // NOTE: seek and then tell only works on seekable device!
    //       per http://msdn.microsoft.com/en-us/library/0ys3hc0b.aspx
    //       and http://msdn.microsoft.com/en-us/library/75yw9bf3.aspx
    //       if device is unseekable, return value is undefined!!!
    if(_fseeki64(seed_fp, 0, SEEK_END)) {
        g_log.error_log("failed to seek in seed file: %s, error: %s",
                        seed.c_str(), strerror(errno));
        throw FILESYS_ERROR;
    }
    int64_t size = _ftelli64(seed_fp);
    if(size == (int64_t) -1) {
        g_log.error_log("failed to tell file size: %s, error: %s", seed.c_str(),
                        strerror(errno));
        throw FILESYS_ERROR;
    }
    // NOTE: sizeof(MAX_SEED_SIZE) should not be greater than sizeof(size_t)
    if(size > MAX_SEED_SIZE || size < MIN_SEED_SIZE) {
        g_log.error_log("bad seed file: %s, size: %llu", seed.c_str(),
                        (unsigned long long)size);
        throw BAD_SEED;
    }

    vector<unsigned char> seed_buffer;
    seed_buffer.resize((unsigned int)min(size,MAX_READ));
    if(_fseeki64(seed_fp, 0, SEEK_SET)) {
        g_log.error_log("failed to seek in seed file: %s, error: %s",
                        seed.c_str(), strerror(errno));
        throw FILESYS_ERROR;
    }

    SHA_CTX sha_ctx;
    if (SHA1_Init(&sha_ctx) != 1)
        throw SYSTEM_ERROR;
    int64_t rest = size;
    while (rest > 0) {
        int64_t to_read = min(rest, MAX_READ);
        if(fread(&seed_buffer[0], 1, (size_t)to_read, seed_fp) != to_read) {
            //g_log.log(VCRI_LOG_ERROR, "failed to read from file: %s", path);
            throw FILESYS_ERROR;
        }
        if(SHA1_Update(&sha_ctx, &seed_buffer[0], (size_t)to_read) != 1)
            throw SYSTEM_ERROR;
        rest -= to_read;
    }
    unsigned char sha1_buf[20];
    SHA1_Final(&sha1_buf[0], &sha_ctx);

    digest = hex_escape(20, sha1_buf);
    algo = "sha1";
}
