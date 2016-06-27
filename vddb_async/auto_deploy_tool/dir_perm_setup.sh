#!/bin/bash
set -e

print_usage()
{
    echo "Usage: $0 -d INST_DIR [-u MW_USER]"
}


trap_exit()
{
    echo " * Failed"
}

if [ $# -lt 1 ]; then
    print_usage
    exit 0
fi

# parse opts
set -- `getopt "d:u:" "$@"`
while [ $# -gt 0 ]; do
    case "$1" in
        -d) INST_DIR=$(cd $2; pwd); shift;;
        -u) MW_USER=$2; shift;;
        --) shift; break;;
        -*) print_usage; exit;;
         *) break;;
    esac
    shift
done

[ -z $INST_DIR ] && echo "please specify the install dir" && print_usage && exit 1
[ -z $MW_USER ] && MW_USER="media_wise" && echo "[Note] default MW_USER media_wise is used"
[ $MW_USER != "media_wise" -a $MW_USER != "mysystem" ] && echo "[Err] MW_USER must be media_wise or mysystem" && exit 1

DEST_DIR="$INST_DIR/server"

[ ! -d "$DEST_DIR/var/cache" -o ! -d "$DEST_DIR/var/log" -o ! -d "$DEST_DIR/var/tmp" -o ! -f "$DEST_DIR/bin/server" ] && echo "[Err] server module not installed properly" && exit 1

# root privileges required
[ `id -u` -ne 0 ] && echo "are you root?" && exit 1

trap trap_exit EXIT

# change directory permissions
if [ -z "`grep "$MW_USER" /etc/passwd | cut -d":" -f1`" ]; then
    useradd -m -s /bin/bash -U $MW_USER
    echo " * new user $MW_USER created, please specify its password"
    passwd $MW_USER
fi
if [ -z "`grep "$MW_USER" /etc/group | cut -d":" -f1`" ]; then
    groupadd $MW_USER
    gpasswd -a $MW_USER $MW_USER
    echo " * new group $MW_USER added"
fi
if [ -z "`grep ^$MW_USER /etc/sudoers`" ]; then
    echo " * add sudo privilege to $MW_USER"
    sed -i "/^root.*/a $MW_USER ALL=(ALL) ALL" /etc/sudoers
fi

APA_GRP=`grep APACHE_RUN_GROUP /etc/apache2/envvars | cut -d "=" -f2`
if [ -z "$APA_GRP" ]; then
    APA_GRP=`grep Group /etc/apache2/apache2.conf | cut -d " " -f 2`
fi
if ! groups $MW_USER | grep $APA_GRP >/dev/null 2>&1; then
    echo " * add $MW_USER to apache2 start user group"
    gpasswd -a $MW_USER $APA_GRP
fi

chown $MW_USER:$MW_USER -R $DEST_DIR
chgrp $APA_GRP $DEST_DIR/var/log $DEST_DIR/var/tmp $DEST_DIR/var/cache
chmod g+w $DEST_DIR/var/log $DEST_DIR/var/tmp $DEST_DIR/var/cache
chmod +t $DEST_DIR/var/tmp

sed -i "s/\(^MW_USER=\).*/\1\"$MW_USER\"/" $DEST_DIR/bin/server

trap EXIT
echo " * Success"
