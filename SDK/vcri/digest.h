#ifndef _VCRI_DIGEST_H__
#define _VCRI_DIGEST_H__

#include "stdint.h"

#include <string>

bool is_file_url(const char *url);
void digest_seed(const std::string &seed, std::string &digest,
                 std::string &algo);
void digest_from_url(const std::string &url, std::string &digest,
                     std::string &digest_alg);

#endif // #ifndef _VCRI_DIGEST_H__
