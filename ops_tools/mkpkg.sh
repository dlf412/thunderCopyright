#!/bin/bash
# Written by Junwei Sun< sun_junwei@vobile.cn>
# 2008-11
#
# Qian LinFeng<qian_linfeng@vobile.cn>
# Init:   [2014-08-08 11:11]
# Update: [2014-08-27 16:07]

set -x
if [ $# -lt 1 ] ; then
	echo "$0 pkgname"
	exit 1
fi

pkgname=$1
pkg_bin=${pkgname}/bin
pkg_etc=${pkgname}/etc
mkdir -p ${pkg_bin}
mkdir -p ${pkg_etc}

echo "Packaging..."

# Copy bin & etc files
for submodule in $( ls submodules ); do
    sub_path=./submodules/${submodule}
    module_bin=${pkg_bin}/${submodule}
    module_etc=${pkg_etc}/${submodule}
    mkdir -p ${module_bin}
    mkdir -p ${module_etc}
    cp -Lr ${sub_path}/src/* ${module_bin}
    cp -Lr ${sub_path}/etc/* ${module_etc}
done

# Copy other files
cp -Lr ./bin/* ${pkg_bin}    # Control script
cp -r ./etc/* ${pkg_etc}     # Common config files. (like supervisord)
cp ./PROG_VERSION.def ${pkgname}
cp ./Install.sh ${pkgname}

# Remove svn stuff
cd ${pkgname}
find . -name ".svn" -exec rm -rf {} \;
cd -


tar czvf ${pkgname}.tar.gz ${pkgname}
exit $?
