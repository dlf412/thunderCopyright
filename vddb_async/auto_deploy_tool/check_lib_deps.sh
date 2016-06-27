#!/bin/bash
# by Honghui Ding <ding_honghui@mysite.cn>
# Wed, 29 Aug 2012 02:35:35 +0000
#
# Usage: ./check_lib_deps.sh manifest
#
# input file example:
# ===============================
# bin/lsattr
# /opt/mysite/utils/bin/getmail
# ./lib/libm.so
#================================
#
# Note:
# Empty line or line with # as the first character will skipped
#

PROG_NAME=$0

function filter()
{
    pkg=$1

    # 1. need skip, return 0
    # 2. need process, return 1, default

    # the line is a comment, skip it
    if test "x${pkg:0:1}" == "x#"; then
        return 0
    fi
    # the line is empty, skip it
    if test "x$pkg" == "x"; then
        return 0
    fi
    return 1
}

function check_file()
{
    if test $# -ne 1; then
        echo Usage: $PROG_NAME manifest
        exit 1
    fi

    if ! test -f $1; then
        echo file $1 does not exist
        exit 1
    fi
}

function main()
{
    check_file $@

    while read binfile
    do
        filter "$binfile" && continue

        echo -n "checking $binfile "
    if test ! -f "$binfile"; then 
            echo "fail: target file not exist"
            exit 1
        fi

        if ldd "$binfile" | grep "not found" ; then
            exit 1
        fi
   	echo "pass"
    done < $1

    # if all the check passed, exit with 0

    exit 0
}

main $@



    exit 0
}

main $@

