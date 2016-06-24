#!/bin/sh

help()
{
    cat << HELP
Usage: ./service_checker.sh module_name bin_file [install_dir]

    module_name  - name of the module to be checked
    bin_file     - main executable file of the module
    install_dir  - directory where the module was installed, default to '/opt/vdna_system'

Example:
    ./service_checker.sh qe qe_worker /opt/vdna_system/

HELP
    exit 0
}

[ $# -gt 3 -o $# -lt 2 ] && help

module=$1
bin_file=$2
install_dir="/opt/vdna_system"
[ -n "$3" ] && install_dir="$3"

mainprog="${install_dir}/${module}/bin/${bin_file}"
$mainprog -v >/dev/null 2>&1
[ "$?" = "0" ] && exit 0
exit 1
