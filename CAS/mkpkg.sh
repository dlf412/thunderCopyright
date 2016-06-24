#!/bin/bash

if [ $# -lt 1 ] ; then
	echo "$0 pkgname"
	exit 1
fi

pkgname=$1
mkdir $pkgname
if [ $? -ne 0 ] ; then
	exit 1
fi

echo "Packaging..."
mkdir -p $pkgname/bin
mkdir -p $pkgname/etc
mkdir -p $pkgname/auto_deploy

mkdir -p $pkgname/var/{log,run}

cp -r src/*py $pkgname/bin
cp ../common/{statsd_operator.py,mylogger.py,utils.py,task_container.py,hot_url_queue.py} $pkgname/bin
chmod +x $pkgname/bin/start_watch.py
chmod +x $pkgname/bin/start_dispatch.py
cp -r etc/* $pkgname/etc
cp build/cas.watchdog $pkgname/bin
cp build/server $pkgname/bin
cp -r build/{Install.sh,Upgrade.sh,Rollback.sh} $pkgname
cp PROG_VERSION.def $pkgname
cp build/dependence.pym $pkgname
cp build/auto_deploy_tool/{*.sh,*.py} $pkgname/auto_deploy

find $pkgname -name "*svn*" | xargs rm -rf

tar czvf $pkgname.tar.gz $pkgname

rm -rf $pkgname
exit $?
