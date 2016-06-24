#!/bin/sh

print_usage()
{
    cat << HELP
install.sh -- install the module into the system

Usage:
    ./install.sh <module_name> <module_version> [install_dir]

    moduel_name     - name of the module, will be used as the directory name
    moduel_version  - version of the module
    install_dir     - directory to install the module into, default to '/opt/media_wise'

Example:
    ./install.sh server 2.9.1 /opt/media_wise

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
    echo "Install failed - file or directory '$file_dir' exist already"
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
    echo "Install failed - file or directory '$file_dir' not exist"
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
    if [ -d "$install_dir/$module" ] ; then
        exit 0
    else
        exit 1
    fi
}

# check argument list
[ $# -gt 3 ] && print_usage
[ -z "$1" ] && print_usage
[ "$1" = "-h" -o "$1" = "--help" ] && print_usage

project="VddbAsync"
module="$1"
version="$2";
install_dir="/opt/media_wise"
[ -n "$3" ] && install_dir="$3"

full_name="${module}_v${version}"

# validate dirs
[ -d "./vddb_async/etc" ] || not_exist_error "./etc"
[ -d "$install_dir" ] || not_exist_error "$install_dir"
tdir="$install_dir/$module"
[ -e "$tdir" ] && exist_error "$tdir"
tdir="$install_dir/app/$module/current"
[ -e "$tdir" ] && exist_error "$tdir"
tdir="$install_dir/app/$module/$full_name"
[ -e "$tdir" ] && exist_error "$tdir"

# install the module
fake_install_dir=`mktemp -d`
trap exit_clean EXIT

# copy module files and configuration files to fake_install_dir
tdir="$fake_install_dir/app/$module/$full_name"
echo_and_exec "mkdir -p $tdir"
echo_and_exec "cp -r ./vddb_async/bin ./vddb_async/etc ./vddb_async/lib ./vddb_async/var $tdir"
#echo_and_exec "cp -r ./tool $tdir/bin"
#for var in `ls`; do
#    if [ $var != "auto_deploy" -a $var != "Install.sh" -a $var != "Upgrade.sh" -a $var != "Rollback.sh" ]; then
#        echo_and_exec "cp -R $var $tdir"
#    fi
#done

echo_and_exec "mkdir $fake_install_dir/$module"
tdir="$fake_install_dir/app/$module/$full_name/etc"
[ -d "$tdir" ] && echo_and_exec "cp -r $tdir $fake_install_dir/$module/etc"
tdir="$fake_install_dir/app/$module/$full_name/var"
[ -d "$tdir" ] && echo_and_exec "cp -r $tdir $fake_install_dir/$module/var"

# construct directory structure
echo_and_exec "ln -s $full_name $fake_install_dir/app/$module/current"
tdir="$fake_install_dir/app/$module/current/bin"
[ -d "$tdir" ] && echo_and_exec "ln -s ../app/$module/current/bin $fake_install_dir/$module/bin"
tdir="$fake_install_dir/app/$module/current/lib"
[ -d "$tdir" ] && echo_and_exec "ln -s ../app/$module/current/lib $fake_install_dir/$module/lib"

# copy file to the install_dir
tdir="$install_dir/app/$module"
[ -d "$tdir" ] || echo_and_exec "mkdir -p $tdir"
echo_and_exec "mv $fake_install_dir/app/$module/$full_name $install_dir/app/$module"
echo_and_exec "mv $fake_install_dir/app/$module/current $install_dir/app/$module"
echo_and_exec "mv $fake_install_dir/$module $install_dir"

trap EXIT

exit 0
