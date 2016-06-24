#!/bin/bash

set -e
if [ $# -lt 1 ] ; then
    echo "$0 pkgname"
    exit 1
fi
source $(cd "$(dirname "$0")";pwd)/PROG_VERSION.def
pkg_root=$1
version="$APP_VERSION"
pkg_name="$pkg_root.tar.gz"
prog_pkg=$pkg_root/vddb_async
tool_pkg=$pkg_root/tool
bin_dir=$prog_pkg/bin
conf_dir=$prog_pkg/etc
lib_dir=$prog_pkg/lib

if [ -d $pkg_root ] ; then
  echo -n "$pkg_root exists, override? [Y/n]"
  read flag
  if [ "$flag" == "n" ] ; then
    echo "abort"
    exit 1
  else
    rm -rf $pkg_root
  fi
fi


echo
echo "Phase 1. Update Verison"
echo ------------------------------------------------------------
bash build/update_version.sh

echo "Phase 2. Creating directory hierarchy"
echo ------------------------------------------------------------

mkdir $pkg_root $prog_pkg  $bin_dir $conf_dir $lib_dir
mkdir -p $prog_pkg/var/{log,lib,cache,run}

cp PROG_VERSION.def $pkg_root
echo "Packing TaskManager Module"
install src/task_manager/*.py $lib_dir
install src/task_manager/task/*.py $lib_dir
mv $lib_dir/task_manager.py $bin_dir
mv $lib_dir/celeryconfig.py $conf_dir
install src/task_adapter/*.py $lib_dir
install src/task_pusher/*.py $lib_dir
mv $lib_dir/task_adapter.py $bin_dir
mv $lib_dir/task_pusher.py $bin_dir
install tools/{dna_slice,dna_status,swift} $bin_dir

echo "Packing WebInterface Module"
cp src/web_interface/*.py $lib_dir
mv $lib_dir/web_intf.py $bin_dir

echo "Packing configuration files"
cp src/config/vddb_async.conf $conf_dir
cp src/config/logging.conf $conf_dir
cp src/config/supervisord.conf $conf_dir
cp src/config/gunicorn_config.py $conf_dir
cp src/config/web_config.json $conf_dir

install src/server $bin_dir
# cp -Lr bin/* $bin_dir

echo "Packing deps"
cp lib/python-dbtxn/db_txn.py $lib_dir
cp lib/*.py $lib_dir

mkdir $pkg_root/auto_deploy
cp auto_deploy_tool/{*.sh,*.py} $pkg_root/auto_deploy
cp build/{crontab_add.sh,check_custom.sh} $pkg_root/auto_deploy
cp build/{dependence.deb,dependence.lib,add_svd_crontab.sh} $pkg_root/auto_deploy
install build/{Install.sh,Upgrade.sh,Rollback.sh} $pkg_root
echo "CURRENT_VERSION = ${version}" > "${conf_dir}/version"

echo
echo "Phase 5. Making package tarball"
echo ------------------------------------------------------------
tar czvf $pkg_name $pkg_root
