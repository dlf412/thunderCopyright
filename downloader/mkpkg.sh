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
mkdir -p $pkgname/tools
mkdir -p $pkgname/etc
mkdir -p $pkgname/bin
mkdir -p $pkgname/bin/common
mkdir -p $pkgname/auto_deploy


cp -r src/*.py $pkgname/bin
cp -r src/server $pkgname/bin
cp -rl src/common/*.py $pkgname/bin/common

chmod +x $pkgname/bin/*

cp -r etc/* $pkgname/etc
cp -r tools/thunder_sdk/build/demo/bin/Downloader $pkgname/tools
cp -r tools/*.so* $pkgname/tools
cp -r tools/*.sh $pkgname/tools
cp -r tools/7z $pkgname/tools
cp -r tools/far_split $pkgname/tools
cp -r tools/dna_status $pkgname/tools
cp -rl src/common/swift $pkgname/tools
chmod +x $pkgname/tools/*

cp -r build/Install.sh $pkgname
cp -r build/Upgrade.sh $pkgname
cp -r build/Rollback.sh $pkgname

cp PROG_VERSION.def $pkgname
cp build/dependence.pym $pkgname
cp build/dependence.deb $pkgname
cp build/auto_deploy_tool/{*.sh,*.py} $pkgname/auto_deploy
chmod +x $pkgname/auto_deploy/*

find $pkgname -name "*svn*" | xargs rm -rf

tar czvf $pkgname.tar.gz $pkgname

rm -rf $pkgname
exit $?
