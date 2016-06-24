#! /bin/bash

function dtor ()
{
    rm -f $crontab_file;
}

function main ()
{
    [ $# -ne 2 ] && echo "Usage $0 install_dir module" && exit 1;
    install_dir=$1;
    module=$2;
    script="$install_dir/${module}/bin/server"
    [ ! -e $script ] && echo "$script is not exist" && exit 1;
    crontab_file=`mktemp`;
    trap dtor EXIT;
    > $crontab_file;
    crontab -l > $crontab_file 2>/dev/null;
    grep -q "^[^#]*$script" $crontab_file
    [ $? -eq 0 ] && echo "$module in crontab already!" && exit 0;
    echo "@reboot $script restart" >> $crontab_file;
    crontab $crontab_file;
}

main $@
