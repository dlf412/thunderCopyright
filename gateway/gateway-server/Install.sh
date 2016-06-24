#!/usr/bin/env bash

set -e

################################################################################
# Read CLI args
################################################################################
print_usage()
{
    echo "Usage: $0 [-d INSTALL_DIR] [-f INSTALL_SETTINGS]";
}

if [ $# -lt 1 ]; then
    print_usage
    exit 0
fi

set -- `getopt "d: f:" "$@"`
while [ $# -gt 0 ]; do
    case "$1" in
        -d) install_dir=$2; shift;;
        -f) global_conf=$2; shift;;
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
module="gateway"
version=$(cat ${WORKDIR}/PROG_VERSION.def | cut -d '=' -f 2 | cut -d "\\" -f 1)


long_pkg_name=${proj}_${module}_v${version}
real_module_dir=${install_dir}/app/${module}
real_dir=${real_module_dir}/${long_pkg_name}
use_dir=${install_dir}/${module}

################################################################################
# Check files/directories
################################################################################
[ -z $install_dir ] && echo "Please specify the install dir" && print_usage && exit 1
[ -z $global_conf ] && echo "please specify the config file" && print_usage && exit 1
[ ! -e $global_conf ] && echo "${global_conf} not found" && exit 1

################################################################################
# Doing real jobs
################################################################################
echo "Real dir: ${real_dir}"

mkdir -p ${real_dir}
mkdir -p ${use_dir}/var

# Copy files
#-----------
echo " * Copying files..."
cp -r ${WORKDIR}/bin  ${real_dir}
cp -r ${WORKDIR}/etc  ${use_dir}

# Make linkings
#--------------
echo " * Making links..."
cd ${real_module_dir}
ln -s ${long_pkg_name} current

cd ${use_dir}
ln -s ../app/${module}/current/bin bin

# Merge config
#--------------
cd ${WORKDIR}
python ${use_dir}/bin/common/config_updater.py merge  ${use_dir}/etc/mapping.json  ${global_conf} > ${use_dir}/etc/gateway.conf

echo ">> Install successfully!"
