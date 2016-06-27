#!/bin/bash
# Written by Junwei Sun< sun_junwei@mysite.cn>
# 2008-11
#
set -x
if [ $# -lt 1 ] ; then
	echo "$0 pkgname"
	exit 1
fi

pkgname=$1
mkdir $pkgname
mkdir -p $pkgname/bin
mkdir -p $pkgname/var
if [ $? -ne 0 ] ; then
	exit 1
fi

echo "Compiling..."
if [ $? -ne 0 ] ; then
	exit 1
fi

echo "Packaging..."

cp -Lr ./gateway-server/src/common ./gateway-server/src/scripts ./gateway-server/src/tools $pkgname/bin
cp -Lr ./gateway-server/bin/* ./gateway-server/src/*.py $pkgname/bin
cp -r ./gateway-server/tests $pkgname/bin

cp -r ./gateway-server/etc $pkgname/

cp ./PROG_VERSION.def $pkgname
cp ./gateway-server/Install.sh  $pkgname
cp ./gateway-server/Upgrade.sh  $pkgname
cp ./gateway-server/Rollback.sh $pkgname

cd $pkgname
find . -name ".svn" -exec rm -rf {} \;
cd -

tar czvf $pkgname.tar.gz $pkgname
exit $?
