#!/bin/bash
# Written by Junwei Sun< sun_junwei@vobile.cn>
# 2009-02~2011-03
# Universal build script to build all modules in all directories.
#
# In each build directory, we must write the following files:
#	* mkpkg.sh					* Packaging script including source code compiling.
#	* PROG_VERSION.def			* Software version definition with format like: "APP_VERSION=1.2.3.4b1".
#	* changelog.txt				* change log of this build module.
#
# TODO: check out all directories to build only one module??!

if [ $# -lt 2 ] || [ "$1" = "-h" ] ; then
	echo "$0 type(ut/cc/er) directory"
	exit 0
fi
export LANGUAGE=en_US
export LANG=en_US.UTF-8
projName=`svn info| grep URL| sed "s/.*svn\///g" | sed "s/\/.*//g"`
subProjName=`svn info|grep URL|sed "s/URL: //g"|xargs dirname $l|sed "s/branches//g"|sed "s/tags//g"|xargs basename`
. build.conf
verDef="./PROG_VERSION.def"
who=`whoami`
pkgtype=$1
secret="itosDeib8"
if [ "$pkgtype" = "" ] ; then
	pkgtype="ut"
fi
rootDir=`pwd`
modDir=$2
if [ "$modDir" = "" ] ; then
	modDir="Crawler"
fi
component=`basename $modDir`
modName=`echo "$modDir"|sed "s/\.//g"|sed "s/\//_/g"|sed "s/_$//g"|sed "s/^_//g"|tr "[:upper:]" "[:lower:]"`
buildTag=""
tagSrc=`svn info|grep URL| sed 's/URL: //g'`
isTagBuild=`echo $tagSrc | grep "/tags/"`
svn up
revnum=`svn info | grep "Last Changed Rev"|  sed "s/Last Changed Rev: //g"`
tsupdateri="current_release.txt"

if [ "$isTagBuild" != "" ] && [ "$pkgtype" = "cc" ] ; then
	echo "Skip login-ing for cc build on tags."
else 
	echo -n "Trac username:"
	read trac_username;
	echo -n "Trac password:"
	read -s trac_password;

	if [ "$pkgtype" = "er" ] || [ "$pkgtype" = "ut" ] ; then
		echo "Skip login and checking tickets."
	else 
		# retrieve cookie
		trac_cookie=`wget -d http://seals.vobile.cn/trac/$projName/login -O /dev/null \
		--post-data="__FORM_TOKEN=627bff2ee8f6e0589a8a0392&referer=&user=${trac_username}&password=${trac_password}" \
		--header="Cookie: trac_form_token=627bff2ee8f6e0589a8a0392; trac_session=34f7c2c6e135a7bb8e1788c5" 2>&1 \
		| grep Set-Cookie | sed "s/.*: //g"| sed "s/; .*//"| awk '{printf("%s;",$1);}' \
		| sed "s/;$//g" | sed "s/^/Cookie: /"`
		if [ "$trac_cookie" = "" ] ; then
			echo 
			echo "Trac authentication failed, build aborted."
			exit 1
		fi
		if [ "$projName" = "taisan" ] ; then
			# 1. check if all fixed tickets included in changelog.
			echo
			ftQueryURL="http://seals.vobile.cn/trac/$projName/query?status=fixed&group=status&max=10&component=$component&order=changetime&col=id&col=summary&col=changetime&desc=1&resolution=fixed&update=Update";
			#echo "Query URL: $ftQueryURL"
			echo -n "Checking fixed tickets..."
			>not_included_tickets
			wget --header="$trac_cookie" "$ftQueryURL" -O - 2>/dev/null \
				| grep "/ticket/" | grep "View" | grep -v "<td"|sed "s/.*ticket\///g" \
				|sed "s/\".*//g" | while read l; do
				log=`grep "#$l" $modDir/changelog.txt`
				if [ "$log" = ""  ]; then
					if [ "$i" = "" ] ; then
						echo 
						i="1"
					fi
					echo "http://seals.vobile.cn/trac/$projName/ticket/$l" |tee -a not_included_tickets
				else 
					echo -n "."
				fi
			done
			if [ -s not_included_tickets ] ; then
				rm -f not_included_tickets
				echo 
				echo "Above tickets are not added in <$modDir/changelog.txt>, please check it. Build aborted..."
				if [ "$isTagBuild" = "" ] ; then
					exit 1
				fi
			fi
			echo "OK"
		fi
	fi
fi

# 2. check Linux version if it match with production one.
#osVer=`cat /etc/issue.net`
#osVerPro="Debian GNU/Linux 5.0"
#if [ "$osVer" != "$osVerPro" ] ; then
#	echo "Warning: OS version($osVer) mismatch with production one($osVerPro), press <enter> to continue."
#	read key
#fi

# 3. check if PROG_VERSION.def file exist in build directory.
if ! [ -f $modDir/$verDef ] ; then
	echo "File <$verDef> not exists in directory <$modDir>, build aborted"
	exit 1
fi

# 4. check if mkpkg.sh file exist in build directory.
if ! [ -f $modDir/mkpkg.sh ] ; then
	echo "File <mkpkg.sh> not exists in directory <$modDir>, build aborted"
	exit 1
fi

# 5. prepare PROG_VERSION file
source $modDir/$verDef
cd $modDir
if [ "$isTagBuild" != "" ] ; then
	cp $verDef $verDef.orig
fi
if [ "$pkgtype" = "ut" ] ; then # build ut
	mv $verDef $verDef.orig
	echo "APP_VERSION=${APP_VERSION}_${who}_test" >$verDef
	source $verDef
fi
if [ "$pkgtype" = "cc" ] ; then
	# 6. check if has local modification.
	svn diff
	if [ "`svn diff`" != "" ]; then
		echo 
		echo "Local modification not commited, build aborted."
		exit 1
	fi
	if [ "$isTagBuild" = "" ] ; then
		# 7. check if all tickets in changelog are fixed.
		cat changelog.txt | while read l ; do 
			ftag=`echo $l| sed "s/ .*//g"`; 
			if [ "$ftag" = "-" ] || [ "$ftag" = "=" ] ; then 
				break; 
			fi; 
			echo $l|sed "s/.*#//g"| sed "s/ .*//g";
		done | egrep "[[:digit:]]" | while read l ; do 
			tst=`wget --header="$trac_cookie" http://seals.vobile.cn/trac/$projName/ticket/$l -O - 2>/dev/null |\
			grep "fixed)</span>"`; 
			if [ "$tst" = "" ] ; then 
				echo "	* Ticket #$l not fixed" | tee ./ticket_status
			fi;
		done
		if [ -s ./ticket_status ] ; then
			echo "Before you build formal package(s), fix above ticket(s) please!"
			rm -f ./ticket_status
			exit 1;
		fi
		# 8. add a build tag in svn.
		svnroot=`svn info | grep "URL:"| sed "s/URL: //g" | sed "s/\/trunk.*//g" | sed "s/\/branches.*//g"`
		tagver=`echo $APP_VERSION | sed 's/\./_/g' | sed 's/-/_/g'`
		if [ "$modName" = "" ] ; then
			tagDst="$svnroot/tags/cc_${subProjName}_v${APP_VERSION}_r${revnum}"
		else
			tagDst="$svnroot/tags/cc_${subProjName}_${modName}_v${APP_VERSION}_r${revnum}"
		fi
		echo "add a svn tag with above command(y/n)?"
		key="y"
		#read key
		if [ "$key" = "y" ] ; then
			svn cp -r$revnum -m "$APP_VERSION CC-ed" $tagSrc $tagDst
			buildTag=$tagDst
		else
			echo "Build aborted."
			exit 1
		fi
	fi
fi

# 9. construct build package name.
if [ "$modName" = "" ] ; then
	pkgname=${subProjName}_v${APP_VERSION}
else
	pkgname=${subProjName}_${modName}_v${APP_VERSION}
fi

if [ "$pkgtype" == "ut" ] ; then
	pkgname=${pkgname}_b`date +%Y%m%d%H%M`
fi
pkgname=`echo $pkgname| tr "[:upper:]" "[:lower:]"`

# 10. ER step, upload packages and create ER tag.
if [ $pkgtype = "er" ] ; then
	if [ "$isTagBuild" = "" ] ; then
		echo "ER build only allowed on CC tags, build aborted."
		exit 1
	fi
	# 10.1 upload build package into ProjectRelease directory.
	cd $rootDir
	modDirDSL=`basename $modDir`
	if [ $modDirDSL = "." ] ; then
		modDirDSL=""
	fi
	dsl_username=`cat ~/.subversion/auth/svn.simple/8bb78d72e233cb01fa484f701d61f4dd |tail -n 2 |head -n 1`
	if [ $subProjName = $projName ] ; then
		subProjName=""
	else 
		echo "mkdir $subProjName"|sftp $dsl_username@seals.vobile.cn:projects/$projName/
	fi
	echo "mkdir ProjectRelease"|sftp $dsl_username@seals.vobile.cn:projects/$projName/$subProjName/
	echo "\
	mkdir ${APP_VERSION}
	mkdir ${APP_VERSION}/$modDirDSL
	mkdir ${APP_VERSION}/tsupdater_info
	put .release/$pkgname.tar.gz ${APP_VERSION}/$modDirDSL/$pkgname.tar.gz
	put .release/$pkgname.tar.gz.md5 ${APP_VERSION}/$modDirDSL/$pkgname.tar.gz.md5
	put .release/$pkgname.tar.gz.md5.md5 ${APP_VERSION}/$modDirDSL/$pkgname.tar.gz.md5.md5
	chmod 0444 ${APP_VERSION}/$modDirDSL/$pkgname.tar.gz
	chmod 0444 ${APP_VERSION}/$modDirDSL/$pkgname.tar.gz.md5
	chmod 0444 ${APP_VERSION}/$modDirDSL/$pkgname.tar.gz.md5.md5
	put $modDir/changelog.txt ${APP_VERSION}/$modDirDSL/changelog.txt
	put $modDir/$tsupdateri ${APP_VERSION}/tsupdater_info/$tsupdateri
	put $modDir/$tsupdateri.md5 ${APP_VERSION}/tsupdater_info/$tsupdateri.md5
	put $modDir/$tsupdateri.md5.md5 ${APP_VERSION}/tsupdater_info/$tsupdateri.md5.md5
	"|sftp $dsl_username@seals.vobile.cn:projects/$projName/$subProjName/ProjectRelease/
	echo "Package uploaded@ http://seals.vobile.cn/share/$projName/files/$subProjName/ProjectRelease/${APP_VERSION}/$modDirDSL/$pkgname.tar.gz" | \
		tee -a released_packages.txt
	# 10.2 create ER Tag.
	tagDst=`echo "$tagSrc"| sed "s/tags\/cc_/tags\/er_/g"`
	tagRev=`echo $tagSrc|sed "s/.*_r//g"`
	echo "svn cp -r$tagRev -m \"$APP_VERSION released!\" $tagSrc $tagDst"
	svn cp -r$tagRev -m "$APP_VERSION released!" $tagSrc $tagDst
	echo "ER Tag@ $tagDst"
	echo "Done."
	exit 0
fi

# 11. check out source code from related svn tag.
if [ "$buildTag" != "" ] ; then
	cd $rootDir
	buildDir="build_dir"
	rm -rf $buildDir
	svn co $buildTag $buildDir
	if [ $? -ne 0 ] ; then
		exit 1
	fi
	cd $buildDir/$modDir
	source $verDef
fi
# 12. add svn revision number into version file.
echo "APP_VERSION=$APP_VERSION\(Rev.$revnum\)" >$verDef

# 13. build package with script mkpkg.sh.
./mkpkg.sh $pkgname
if [ $? -ne 0 ] ; then
	exit 1
fi

# update pkgname with bits
if [ -f ${pkgname}_32bit.tar.gz ] ; then
    pkgname=${pkgname}_32bit
elif [ -f ${pkgname}_64bit.tar.gz ] ; then
    pkgname=${pkgname}_64bit
fi

# 14. clean build directory.
rm -rf $pkgname
if [ "$buildTag" != "" ] ; then
    mv $pkgname.tar.gz $rootDir
    cd $rootDir
	rm -rf $buildDir
else
	mv $verDef.orig $verDef
	mv $pkgname.tar.gz $rootDir
	cd $rootDir
fi

# 15. calculate build package md5sum.
chmod 0444 $pkgname.tar.gz



md5sum $pkgname.tar.gz >$pkgname.tar.gz.md5
cat $pkgname.tar.gz.md5| sed "s/ .*/ $secret/g" | md5sum >$pkgname.tar.gz.md5.md5

if [ "$pkgtype" = "cc" ] ; then
	# 16. construct tsupdater instruction.
	rm -f $modDir/${tsupdateri}*
	cd $modDir
	source tsupdater_instruction.conf
	echo "${projName}_${modName},$verfication_command,$APP_VERSION,$reboot_after_update" >$tsupdateri
	chmod 0444 $tsupdateri
	md5sum $tsupdateri >$tsupdateri.md5
	cat $tsupdateri.md5 | sed "s/ .*/ $secret/g" | md5sum >$tsupdateri.md5.md5
	cd -
	# 17. create new version number in Trac system.
	if [ "$isTagBuild" = "" ] ; then
		echo "Create new version in Trac system..."
		releaseTime=`date "+%D %T"`
		wget --header="$trac_cookie;trac_form_token=0999eae1e9c07432540dd6be;" \
			--post-data="__FORM_TOKEN=0999eae1e9c07432540dd6be&name=${APP_VERSION}&time=$releaseTime&add=Add" \
			http://seals.vobile.cn/trac/$projName/admin/ticket/versions -O /dev/null
	fi
	# 18. add svn tag into changelog.
	if [ "$buildTag" != "" ] ; then
		sed -i "1i = `date +%F` $buildTag =" $modDir/changelog.txt
		svn ci -m "change of $modName $APP_VERSION" $modDir/changelog.txt
	fi
	# 19. save one copy for package upload when ER:
	rm -rf .release
	mkdir .release
	cp $pkgname.tar.gz .release/
	cp $pkgname.tar.gz.md5 .release/
	cp $pkgname.tar.gz.md5.md5 .release/
fi

echo "Done"
exit 0

