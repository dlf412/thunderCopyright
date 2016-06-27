#!/bin/bash
# by Honghui Ding <ding_honghui@mysite.cn>
# Wed, 01 Aug 2012 11:32:41 +0000
#
# Usage: ./check_deps.sh dependence_file
#
# dependence file example:
# ===============================
# vim >= 7.2.445
# lftp >= 4.0
# apache2 >= 2.0
#================================
#
# Note:
# Empty line or line with # as the first character will skipped
#

PROG_NAME=$0

function filter()
{
    pkg=$1
    op=$2
    ve=$3

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
    # the field is not 3
    line=($(echo $*))
    if test ${#line[*]} -ne 3; then
        echo invalid line, less than 3 field: ${line[*]}
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

    while read pkg op ve
    do
        filter $pkg $op $ve && continue

        echo checking $pkg $op $ve

        # fetch the local installed version
        vc=$(dpkg-query -W -f='${Version}' $pkg 2> /dev/null)

        # if the version is empty, that means the pkg is not installed
        if test $? -ne 0 -o "x$vc" == "x"; then
            echo $pkg not installed
            exit 1
        else
            # check to see if the version relation matches
            if ! dpkg --compare-versions "$vc" "$op" "$ve"; then
                echo $pkg version not satisfied: require local version $vc $op $ve
                exit 1
            else
                echo $pkg pass version verify: local version $vc $op $ve
            fi
        fi
    done < $1

    # if all the check passed, exit with 0

    exit 0
}

main $@

