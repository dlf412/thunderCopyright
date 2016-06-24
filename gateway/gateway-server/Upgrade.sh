#!/usr/bin/env bash

set -e

################################################################################
# Read CLI args
################################################################################
print_usage()
{
    echo "Usage: $0 [-d INSTALL_DIR]"
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

last_real_dir=$(find ${real_module_dir} -type d -name "*_v*" | sort -r | sed -n 1p)
last_pkg_name=$(basename ${last_real_dir})
last_version=$(echo ${last_pkg_name} | cut -d '_' -f 3 | cut -d 'v' -f 2)


################################################################################
# Check files/directories
################################################################################
[ -z $install_dir ] && echo "Please specify the install dir" && print_usage && exit 1

################################################################################
# Doing real jobs
################################################################################

echo ">>> Upgrade for: (${last_version}) -> (${version})"

echo " * Stop supervisor"
cd ${use_dir}
./bin/server shutdown || true
cd -

echo " * Backup last version <etc> dir (by Copy)"
cp -r ${use_dir}/etc ${use_dir}/etc_${last_version}

echo " * Make dirs "
mkdir -p ${real_dir}

echo " * Copy files"
cp -r ${WORKDIR}/bin ${real_dir}

#echo " * Patch last version config files"
#python ${WORKDIR}/bin/tools/config_patch_${last_version}_${version}.py -c ${use_dir}/etc

echo " * Rebuild symbolic links: <app/current>"
cd ${real_module_dir}
rm current
ln -s ${long_pkg_name} current

echo " * Start supervisor"
sleep 2
cd ${use_dir}
./bin/server boot
cd -

echo ">>> Upgrade successfully!: (${last_version}) -> (${version})"
