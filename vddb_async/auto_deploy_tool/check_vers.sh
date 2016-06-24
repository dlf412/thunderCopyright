#!/bin/sh

print_usage()
{
    cat << HELP
check_vers.sh -- check the version of certain module

Usage:
    ./check_vers.sh <module_name> <begin_version> <end_version> [install_dir]

    moduel_name     - name of the module, will be used as the directory name
    begin_version   - start version of the check domain (inclusive)
    end_version     - end version of the check domain (exclusive)
    install_dir     - directory where the module is installed, default to '/opt/media_wise'

Note:
    1. end_version must not be less than begin_version
    2. check would succeed if module version is in the range [begin_version, end_version)
    3. if end_version equals begin_version, then perform equal check, check would succeed if module version equals begin_version
    4. note that instead of equal, version like 5.2.3 is less than 5.2.3.0


Example:
    ./check_vers.sh server 2.9.0 2.9.1 /opt/media_wise

HELP
    exit 1
}

# file or dir not exist error
# usage: not_exist_error [file_dir [err_msg]]
not_exist_error()
{
    file_dir="$1"
    err_msg="$2"
    [ -z $file_dir ] && exit 1
    echo "Check failed - file or directory '$file_dir' not exist"
    [ -n $err_msg ] && echo " * $err_msg"
    [ -z $err_msg ] && echo " * make sure module $module with version $version installed before upgrading"
    exit 1
}

# check argument list
[ $# -gt 4 ] && print_usage
[ -z "$1" ] && print_usage
[ "$1" = "-h" -o "$1" = "--help" ] && print_usage

project="mediawise"
module="$1"
begin_version="$2"
end_version="$3"
install_dir="/opt/media_wise"
[ -n "$4" ] && install_dir="$4"

# validate version arguments
if dpkg --compare-versions $end_version lt $begin_version ; then
    echo "[Err] end_version($end_version) must not less than begin_version($begin_version)" && exit 1
fi

# validate dirs
[ -d "$install_dir" ] || not_exist_error "$install_dir"
tdir="$install_dir/$module"
[ -d "$tdir" ] || not_exist_error "$tdir"
tdir="$install_dir/app/$module/current"
[ -d "$tdir" ] || not_exist_error "$tdir"

# get current version
cur_version=$(echo $(basename $(readlink $install_dir/app/$module/current)) | awk -F_ '{print $NF}' | cut -b 2- )

# check version
# if begin_version eq end_version, then perform equal check
if dpkg --compare-versions $begin_version eq $end_version ; then
    if ! dpkg --compare-versions $cur_version eq $begin_version ; then
        echo "[Err] versions does not match - current: $cur_version, required: $begin_version" && exit 1
    fi
# cur_version must be in the range [begin_version, end_version)
elif dpkg --compare-versions $cur_version lt $begin_version || dpkg --compare-versions $cur_version ge $end_version ; then
    echo "[Err] versions does not match - current: $cur_version, required: [$begin_version, $end_version)" && exit 1
fi

exit 0
