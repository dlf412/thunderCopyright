#!/usr/bin/env bash

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

set -- `getopt "d: f:" "$@"`
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
module="gateway"
version=$(cat ${WORKDIR}/PROG_VERSION.def | cut -d '=' -f 2 | cut -d "\\" -f 1)

long_pkg_name=${proj}_${module}_v${version}
real_module_dir=${install_dir}/app/${module}
real_dir=${real_module_dir}/${long_pkg_name}
use_dir=${install_dir}/${module}

last_real_dir=$(find ${real_module_dir} -type d -name "*_v*" | sort -r | sed -n 2p)
last_long_pkg_name=$(basename ${last_real_dir})
last_version=$(echo ${last_long_pkg_name} | cut -d '_' -f 3 | cut -d 'v' -f 2)


################################################################################
# Check files/directories
################################################################################
[ -z $install_dir ] && echo "Please specify the install dir" && print_usage && exit 1

################################################################################
# Doing real jobs
################################################################################

echo ">>> Rollback for: (${version}) -> (${last_version})"

echo " * Stop supervisor"
cd ${use_dir}
./bin/server shutdown || true
cd -

echo " * Restore <etc> directory"
rm -r ${use_dir}/etc
mv ${use_dir}/etc_${last_version} ${use_dir}/etc

echo " * Remove current package files"
rm -r ${real_dir}

echo " * Rebuild symbolic links: <app/current>"
cd ${real_module_dir}
rm current
ln -s ${last_long_pkg_name} current

echo " * Start supervisor"
sleep 2
cd ${use_dir}
./bin/server boot

echo ">>> Rollback successfully! : (${version}) -> (${last_version})"
