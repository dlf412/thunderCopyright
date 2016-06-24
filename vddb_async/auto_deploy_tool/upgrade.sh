#!/bin/sh

print_usage()
{
    cat << HELP
upgrade.sh -- upgrade the module into the system

Usage:
    ./upgrade.sh <module_name> <module_version> [install_dir]

    moduel_name     - name of the module, will be used as the directory name
    moduel_version  - version of the module
    install_dir     - directory where the module is installed in, default to '/opt/media_wise'

Example:
    ./upgrade.sh server 2.9.1 /opt/media_wise

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
    echo "Upgrade failed - file or directory '$file_dir' exist already"
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
    echo "Upgrade failed - file or directory '$file_dir' not exist"
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

exit_clean()
{
    [ -n "$fake_install_dir" ] && echo_and_exec "rm -rf $fake_install_dir"
    if [ -d "$install_dir/app/$module/$full_name" ] ; then
        exit 0
    else
        exit 1
    fi
}

# check argument list
[ $# -gt 3 ] && print_usage
[ -z "$1" ] && print_usage
[ "$1" = "-h" -o "$1" = "--help" ] && print_usage

module="$1"
version="$2";
install_dir="/opt/media_wise"
[ -n "$3" ] && install_dir="$3"

full_name="${module}_v${version}"

# validate dirs
[ -d "$install_dir" ] || not_exist_error "$install_dir"
tdir="$install_dir/app/$module"
[ -d "$tdir" ] || not_exist_error "$tdir"
tdir="$install_dir/app/$full_name"
[ -e "$tdir" ] && exist_error "$tdir"

# install the module
fake_install_dir=`mktemp -d`
trap exit_clean EXIT

# copy module files and configuration files to fake_install_dir
tdir="$fake_install_dir/app/$module/$full_name"
echo_and_exec "mkdir -p $tdir"
echo_and_exec "cp -r ./vddb_async/bin ./vddb_async/etc ./vddb_async/lib ./vddb_async/var $tdir"
#echo_and_exec "cp -r ./tool $tdir/bin"

# move file to the install_dir
echo_and_exec "mv $fake_install_dir/app/$module/$full_name $install_dir/app/$module"

trap EXIT
exit 0
