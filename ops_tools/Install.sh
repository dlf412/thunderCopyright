#!/usr/bin/env bash

########################################################################
##  Author: Qian Linfeng<qian_linfeng@mysite.cn> @[2014-08-08 11:12]  ##
########################################################################


set -e

################################################################################
# Read CLI args
################################################################################
print_usage()
{
    echo "Usage: $0 [-d INSTALL_DIR]";
}

if [ $# -lt 1 ]; then
    print_usage
    exit 0
fi

set -- `getopt "d:" "$@"`
while [ $# -gt 0 ]; do
    case "$1" in
        -d) install_dir=$2; shift;;
        --) shift; break;;
        -*) print_usage; exit;;
         *) break;;
    esac
shift
done

################################################################################
# Prepare variables
################################################################################
WORKDIR=$(cd "$(dirname "$0")"; pwd)
install_dir="$(cd "$install_dir"; pwd)"
proj='thunder'
module="ops_tools"
version=$(cat ${WORKDIR}/PROG_VERSION.def | cut -d '=' -f 2 | cut -d "\\" -f 1)


long_pkg_name=${proj}_${module}_v${version}
real_module_dir=${install_dir}/app/${module}
real_dir=${real_module_dir}/${long_pkg_name}
use_dir=${install_dir}/${module}

################################################################################
# Check files/directories
################################################################################
[ -z $install_dir ] && echo "Please specify the install dir" && print_usage && exit 1

################################################################################
# Doing real jobs
################################################################################
echo "Real dir:"
echo ${real_dir}

mkdir -p ${real_dir}
mkdir -p ${use_dir}/var

# Copy files
#-----------
cp -r ${WORKDIR}/bin  ${real_dir}
cp -r ${WORKDIR}/etc  ${use_dir}

# Make linkings
#--------------
cd ${real_module_dir}
ln -s ${long_pkg_name} current

cd ${use_dir}
ln -s ../app/${module}/current/bin bin

echo ">> Install successfully!"
