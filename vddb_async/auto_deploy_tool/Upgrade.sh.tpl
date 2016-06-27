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

project="mysystem";
old_version="2.9.0";
new_version="2.9.1";
module="[module_name]";
main_binfile="[module_main]";
server_script="$install_dir/$module/bin/[module_server]"
target_conf="$install_dir/$module/etc/[module_config]"
full_name="${project}_${module}_v${new_version}"

WORKDIR=$(cd "$(dirname "$0")"; pwd)
TOOLDIR="$WORKDIR/auto_deploy"

DEPS_FILE="$TOOLDIR/dependence.deb"
LIBS_FILE="$TOOLDIR/dependence.lib"
PYMS_FILE="$TOOLDIR/dependence.pym"
CRON_TOOL="$TOOLDIR/crontab_add.sh"
DEPS_CHECK_TOOL="$TOOLDIR/check_deps.sh"
LIBS_CHECK_TOOL="$TOOLDIR/check_lib_deps.sh"
PYMS_CHECK_TOOL="$TOOLDIR/check_python_module.sh"
CSTS_CHECK_TOOL="$TOOLDIR/check_custom.sh"
VERS_CHECK_TOOL="$TOOLDIR/check_vers.sh";
FOLDER_CP_TOOL="$TOOLDIR/upgrade.sh";
CONF_UPGRADE_TOOL="$TOOLDIR/[module_config_upgrader]";
SERVICE_CHECK_TOOL="$TOOLDIR/service_checker.sh"

echo "[Note] Upgrade start"

# version check
echo " * Checking versions..."
bash $VERS_CHECK_TOOL $module $old_version $new_version $install_dir

# get current version
echo " * Getting current version..."
last_version=$(echo $(basename $(readlink $install_dir/app/$module/current)) | awk -F_ '{print $NF}' | cut -b 2- )

# dependence check
echo " * Checking dependencies..."
bash $DEPS_CHECK_TOOL $DEPS_FILE
bash $LIBS_CHECK_TOOL $LIBS_FILE
bash $PYMS_CHECK_TOOL $PYMS_FILE
bash $CSTS_CHECK_TOOL

# stop service
echo " * Stoping service..."
$server_script stop

# copy file
echo " * Copying files..."
bash $FOLDER_CP_TOOL $module $new_version $install_dir

# backup etc dir
echo " * Backing up config dir..."
cp -r $install_dir/$module/etc $install_dir/app/$module/$full_name/etc.bk

# relink current
echo " * Relinking current..."
unlink $install_dir/app/$module/current
ln -s $full_name $install_dir/app/$module/current

# create file `last_version'
echo " * Creating last_version..."
echo $last_version > $install_dir/app/$module/current/last_version

# upgrade config file
echo " * Upgrading config files..."
#cp -r $install_dir/$module/etc $install_dir/app/$module/$full_name
cp $target_conf "$target_conf.`date +%y-%m-%d`"
python $CONF_UPGRADE_TOOL $global_conf $target_conf
## make config upgrade take effect (pyweb/webserver)
#cp $target_conf $install_dir/app/$module/current/etc

# function check
echo " * Checking functionalities..."
bash $SERVICE_CHECK_TOOL $module $main_binfile $install_dir

# start service
echo " * Starting service..."
$server_script restart

# add to crontab
echo " * Adding service to crontab..."
bash $CRON_TOOL $install_dir $module

echo "[Note] Upgrade success"

# hint for apache configuation
#echo "[Note] please restart apache2 manually to make this upgrade take effect immediately"
