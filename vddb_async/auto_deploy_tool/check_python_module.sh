#!/bin/bash
# by Honghui Ding <ding_honghui@vobile.cn>
# Wed, 01 Aug 2012 11:32:41 +0000
#
# Usage: ./check_python_module.sh dependence_file
#
# dependence file example:
# ================================
# #package        module
# python-webpy    web
# python-zmq      zmq
# python-protobuf google.protobuf
# ================================
#
# Note:
# Empty line or line with # as the first character will skipped
#

function system_exit ()
{
    [ -e $test_file ] && rm $test_file;
}

PROG_NAME=$0
trap system_exit EXIT

test_file="/tmp/test.py"

function filter()
{
    pkg=$1
    module=$2

    # 1. need skip, return 0
    # 2. need process, return 1, default
    # 3. invalid line, exit with error

    # the line is a comment, skip it
    if test "x${pkg:0:1}" == "x#"; then
        return 0
    fi
    # the line is empty, skip it
    if test "x$pkg" == "x"; then
        return 0
    fi
    # the field is not 2
    line=($(echo $*))
    if test ${#line[*]} -ne 2; then
        echo invalid line, less than 2 field: ${line[*]}
        exit 1
    fi
    return 1
}

function check_file()
{
    if test $# -ne 1; then
        echo Usage: $PROG_NAME dependence_file
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

    while read pkg module
    do
        filter $pkg $module && continue

        echo checking $pkg $module

        test_file="/tmp/test.py"
        echo "import $module" > $test_file
        python $test_file 2>/dev/null;

        if test $? -ne 0 ; then
            echo $pkg not installed
            exit 1
        fi
    done < $1

    # if all the check passed, exit with 0

    exit 0
}

main $@

