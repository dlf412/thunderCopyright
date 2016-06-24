#! /bin/bash
set -e

print_usage()
{
    echo "Usage: $0 [-d INSTALL_DIR]"
}

if [ $# -lt 1 ]; then
    print_usage
    exit 0
fi

set -- `getopt "d:" "$@"`
while [ $# -gt 0 ]; do
    case "$1" in
        -d) install_dir=$2; shift;;
        --) shift; break;;
        -*) print_usage; exit;;
         *) break;;
    esac
    shift
done

[ -z $install_dir ] && echo "please specify the install dir" && print_usage && exit 1

module="[module_name]";
server_script="$install_dir/$module/bin/[module_server]";

WORKDIR=$(cd "$(dirname "$0")"; pwd);
TOOLDIR="$WORKDIR/auto_deploy";

if ! [ -x "$server_script" ] ; then
    echo "module $module not installed, quit rollback"
    exit 1
fi

echo "[Note] Rollback start"

# stop service
echo " * Stoping service..."
$server_script stop

# rollback
echo " * Rolling back..."
bash $TOOLDIR/rollback.sh $module $install_dir

# make config take effect (pyweb/webserver/index/imageindex)
#cp -r $install_dir/$module/etc $install_dir/app/$module/current

# restart service
echo " * Restarting service..."
$server_script restart

echo "[Note] Rollback success"

# hint for apache configuation
#echo "[Note] please restart apache2 manually to make this rollback take effect immediately"
