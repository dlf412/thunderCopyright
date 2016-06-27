#! /bin/bash
set -e

print_usage()
{
    echo "Usage: $0 [-d INSTALL_DIR] [-f INSTALL_SETTINGS]"
}

if [ $# -lt 1 ]; then
    print_usage
    exit 0
fi

set -- `getopt "d: f:" "$@"`
while [ $# -gt 0 ]; do
    case "$1" in
        -d) install_dir=$2; shift;;
        -f) global_conf=$2; shift;;
        --) shift; break;;
        -*) print_usage; exit;;
         *) break;;
    esac
    shift
done

[ -z $install_dir ] && echo "please specify the install dir" && print_usage && exit 1
[ -z $global_conf ] && echo "please specify the config file" && print_usage && exit 1
[ ! -e $global_conf ] && echo "$global_conf not found" && exit 1;

project="mysystem"
version="2.9.1";
module="[module_name]";
main_binfile="[module_main]";
server_script="$install_dir/$module/bin/[module_server]";
target_conf="$install_dir/$module/etc/[module_conf]";

WORKDIR=$(cd "$(dirname "$0")"; pwd)
TOOLDIR="$WORKDIR/auto_deploy"

DEPS_FILE="$TOOLDIR/dependence.deb";
LIBS_FILE="$TOOLDIR/dependence.lib";
PYMS_FILE="$TOOLDIR/dependence.pym";
CRON_TOOL="$TOOLDIR/crontab_add.sh";
DEPS_CHECK_TOOL="$TOOLDIR/check_deps.sh";
LIBS_CHECK_TOOL="$TOOLDIR/check_lib_deps.sh";
PYMS_CHECK_TOOL="$TOOLDIR/check_python_module.sh";
CSTS_CHECK_TOOL="$TOOLDIR/check_custom.sh";
FOLDER_CP_TOOL="$TOOLDIR/install.sh";
CONF_UPDATER_TOOL="$TOOLDIR/[module_config_updater]";
SERVICE_CHECK_TOOL="$TOOLDIR/service_checker.sh";

echo "[Note] Install start"

# dependence check
echo " * Checking dependencies..."
bash $DEPS_CHECK_TOOL $DEPS_FILE
bash $LIBS_CHECK_TOOL $LIBS_FILE
bash $PYMS_CHECK_TOOL $PYMS_FILE
bash $CSTS_CHECK_TOOL

# copy file
echo " * Copying files..."
bash $FOLDER_CP_TOOL $module $version $install_dir;

# update conf file
echo " * Updating config files..."
python $CONF_UPDATER_TOOL $global_conf $target_conf;
## make config update take effect (pyweb/webserver)
#cp $target_conf $install_dir/app/$module/current/etc

# function check
echo " * Checking functionalities..."
bash $SERVICE_CHECK_TOOL $module $main_binfile $install_dir

# start service
echo " * Restarting service..."
$server_script restart;

# add into crontab
echo " * Adding service to crontab..."
bash $CRON_TOOL $install_dir $module

echo "[Note] Install success"

# hint for apache configuation
#echo "[Note] you probably have to configure apache properly before starting this module"
#echo "[Note] please refer the install manual for detail"
