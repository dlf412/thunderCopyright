#!/bin/sh

print_usage()
{
    cat << HELP
rollback.sh -- rollback the module specified to last version

Usage:
    ./rollback.sh <module_name> [install_dir]

    moduel_name     - name of the module, will be used as the directory name
    install_dir     - directory where the module is installed into, default to '/opt/media_wise'

Example:
    ./rollback.sh server /opt/media_wise

HELP
    exit 1
}

# file or dir exist error
# usage: exist_error [file_dir [err_msg]]
exist_error()
{
    file_dir="$1"
    err_msg="$2"
    [ -z "$file_dir" ] && exit 1
    echo "Rollback failed - file or directory '$file_dir' exist already"
    [ -n "$err_msg" ] && echo " * $err_msg"
    [ -z "$err_msg" ] && echo " * please remove it manually"
    exit 1
}

# file or dir not exist error
# usage: not_exist_error [file_dir [err_msg]]
not_exist_error()
{
    file_dir="$1"
    err_msg="$2"
    [ -z "$file_dir" ] && exit 1
    echo "Rollback failed - file or directory '$file_dir' not exist"
    [ -n "$err_msg" ] && echo " * $err_msg"
    [ -z "$err_msg" ] && echo " * make sure '$err_msg' exists before proceeding"
    exit 1
}

# echo and exec a shell command
# usage: echo_and_exec <command>
echo_and_exec()
{
    command="$1"
    [ -n "$command" ] && echo $command
    `$command`
}

# check argument list
[ $# -gt 2 ] && print_usage
[ -z "$1" ] && print_usage
[ "$1" = "-h" -o "$1" = "--help" ] && print_usage

project="mediawise"
module="$1"
install_dir="/opt/media_wise"
[ -n "$2" ] && install_dir="$2"

# validate dirs
[ -d "$install_dir" ] || not_exist_error "$install_dir"
tdir="$install_dir/$module"
[ -d "$tdir" ] || not_exist_error "$tdir" "$module not installed yet"
tdir="$install_dir/app/$module/current"
[ -d "$tdir" ] || not_exist_error "$tdir" "$module not installed yet"
tdir="$install_dir/app/$module/current/last_version"
[ -f "$tdir" ] || not_exist_error "$tdir" "no last version detected, can not rollback"

last_version=$(cat $install_dir/app/$module/current/last_version)
tdir="$install_dir/app/$module/${module}_v${last_version}"
[ -d "$tdir" ] || not_exist_error "$tdir" "last version $last_version lost"

# get current version
cur_version=$(echo $(basename $(readlink $install_dir/app/$module/current)) | awk -F_ '{print $NF}' | cut -b 2-)

# restore etc dir
tdir="$install_dir/app/$module/current/etc.bk"
[ -d "$tdir" ] && echo_and_exec "cp -r $tdir/* $install_dir/$module/etc"

# relink current
echo_and_exec "unlink $install_dir/app/$module/current"
echo_and_exec "ln -s ${module}_v${last_version} $install_dir/app/$module/current"

# remove privious current version
echo_and_exec "rm -rf $install_dir/app/$module/${module}_v${cur_version}"

exit 0
