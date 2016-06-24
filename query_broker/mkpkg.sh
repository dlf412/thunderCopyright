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
mkdir -p $pkgname/etc
mkdir -p $pkgname/bin
mkdir -p $pkgname/auto_deploy


cp -r src/qb_priority/*py $pkgname/bin
cp -r src/qb_pull/*py $pkgname/bin
cp -r src/qb_push/*py $pkgname/bin
cp -r src/qb_resultpush/*py $pkgname/bin
cp -r src/qb_rating/*py $pkgname/bin
cp -r ../common/dbpc.py $pkgname/bin
cp -r ../common/mylogger.py $pkgname/bin
cp -r ../common/hot_url_queue.py $pkgname/bin
cp -r ../common/redis_oper.py $pkgname/bin
cp -r ../common/utils.py $pkgname/bin
cp -r ../common/swift $pkgname/bin

chmod +x $pkgname/bin/task_priority_escalator.py
chmod +x $pkgname/bin/process_task.py
chmod +x $pkgname/bin/exceptionhandle_query.py
chmod +x $pkgname/bin/push_result.py
chmod +x $pkgname/bin/task_rating_escalator.py

cp -r etc/* $pkgname/etc

cp -r build/Install.sh $pkgname
cp -r build/Upgrade.sh $pkgname
cp -r build/Rollback.sh $pkgname

cp PROG_VERSION.def $pkgname
cp build/dependence.pym $pkgname
cp build/dependence.deb $pkgname
cp build/auto_deploy_tool/{*.sh,*.py} $pkgname/auto_deploy
cp build/server $pkgname/bin
cp build/*.sh $pkgname/auto_deploy

find $pkgname -name "*svn*" | xargs rm -rf

tar czvf $pkgname.tar.gz $pkgname

rm -rf $pkgname
exit $?
