#!/bin/bash

function PrintHelp()
{ 
	cat <<- ENDIT

	Usage:
	     ./download_url.sh url path [postdata] [httphead] [cookie_method] [cookie_file] [log_file]

	  url 
	     the url which will be downloaded.

	  path 
	     the path of the file in which the content being downloaded will be saved.

	  postdata 
	     use POST as the method for all HTTP requests and send "postdata" in the request body.

	  httphead 
	     send "httphead" along with the rest of the headers in each HTTP request.

	  cookie_method and cookie_file
	     if cookie_method is "save", "cookie_file" will be saved cookies before exiting
	     if cookie_method is "load", "cookie_file" will be load before the first HTTP retrieval

	ENDIT
}

list_all_pid()
{
    [ "$#" -eq 0 ] && return
    local pid=
    for pid in "$@" ; do
        echo "$pid"
        list_all_pid $(ps -o pid --no-headers --ppid "$pid")
    done
}

kill_process()
{
    kill -9 $(list_all_pid "$@")
} 2>/dev/null

function GetConfigDir()
{
	if [ -n "$CRAWLER_HOME" ] ; then
		config_dir="$CRAWLER_HOME/etc"
	else
		config_dir="$(dirname "$(readlink -f "$0")")"
	fi
}

function SetFileSizeLimit()
{
	[[ "$url" == *.56.com/* ]] && maxsize=10485760		# 10M

	shopt -s nocasematch
	[[ "$path" == */resource/media/*/tudou/* ]] && maxsize=13619200		# 13M
	[[ "$path" == */resource/media/*/pomoho/* ]] && maxsize=21888000		# 21M
	[[ "$path" == */resource/media/*/pandora/* ]] && maxsize=32588800	# 32M
	[[ "$path" == */resource/media/*/youtube/* ]] && maxsize=13619200		# 13M

	[[ "$url" == *megavideo.*.mp4 || "$url" == *megavideo.*.avi || \
		"$url" == *megavideo.*.mov || "$url" == *megavideo.*.mkv ]] && maxsize=107374182400		# 100GB (no limit)
	shopt -u nocasematch
	echo "Max download filesize: $maxsize bytes."
}

function GenerateCurlCommand()
{
	command="curl --limit-rate 5m --retry 25 --retry-delay 20 "

    if [[ $url =~ "https://" ]] ; then
        command="$command --insecure "
    fi

    command="$command -o \"$path\" "

	command="$command -A \"$user_agent\" "

	if [ -n "$httphead" ] ; then
		command="$command --header \"$httphead\" "
	fi

	if [ -n "$cookie_file" ] ; then
		if [ "$cookie_method" = "save" ] ;then
			command="$command --cookie-jar \"$cookie_file\" "
		elif [ "$cookie_method" = "load" ] ; then
			command="$command --cookie \"$cookie_file\" "
		fi
	fi

	if [ -n "$debug" ] ; then
		command="$command -v "
	fi

	if [ -n "$continue_download" ] ; then
		command="$command -C - "
	fi

	command="$command \"$url\" "

}

# generate command function
function GenerateCommand() 
{
	command="wget -a \"$log_name\" \
	--limit-rate=5m --tries=25 --waitretry=20 "

    if [[ $url =~ "https://" ]] ; then
        command="$command --no-check-certificate "
    fi

    command="$command -O \"$path\" "

	command="$command -U \"$user_agent\" "

	if [ -n "$continue_download" ] ; then
		command="$command -c "
	fi

	command="$command \"$url\" "
}

# downlaod according to the url
function download()
{
	local real_command="$*"
    echo "$real_command" | tee -a $log_name
    bash $BIN_DIR/sub_command.sh "${path}.ret_code" "$real_command" &
	pid=$!

	sec_elapsed=0
	cur_size=0
	last_size=0
	fsize=0
	sleep 3
	while [ -d /proc/$pid ] ; do
		sec_elapsed=$(( sec_elapsed + 1 ))
		fsize=`stat -c '%s' $path`
		cur_size=$fsize
		if [ $last_size -lt $cur_size ] ; then
			sec_elapsed=0
			last_size=$cur_size
		fi
		if [ $sec_elapsed -gt $timeout_secs ] ; then
			echo "">>$log_name
            kill_process $pid && echo "[$(date)][$0] $tool_type process killed since filesize unchanged for more than $timeout_secs seconds." >>$log_name
            rm -f "${path}.ret_code"
			return 1
		fi
		if [ $fsize -gt $maxsize ] ; then
			echo "">>$log_name
			kill_process $pid && echo "[$(date)][$0] $tool_type process killed since filesize larger than $maxsize bytes." >>$log_name
            rm -f "${path}.ret_code"
			return 0
		fi
		sleep 1
	done
    
    ret=0
    ret_code=`cat ${path}.ret_code 2>/dev/null`
    if [ -z "$ret_code" ] || [ "$ret_code" != "0" ]; then
        ret=1
    else
        ret=0
	fi

    rm -f "${path}.ret_code"
    return $ret
}

# choise one of local ip which is record in "downloader.conf" randomly to download.
function IPBanlanceDownlaod()
{
	local base_command="$*"
	download $base_command
	ret=$?
	return $ret
}

function ProxyDownload()
{
	for (( i = 0; i < 1; i++ )) ; do
		IPBanlanceDownlaod $command
		ret=$?
		[ $ret -eq 0 ] && [ -s "$path" ] && return 0
	done
	return $ret
}

# append download log to assigned log file
function AppendLog()
{
	local ret=$1
	if [ "$ret" -eq 0 ] && [ -s "$path" ] ; then
		return 0
	fi
	if [ -z "$log_file"	] ; then
		grep -v '\.\.\.\.\.\.\.\.[[:space:]]\{1,4\}[[:digit:]]\{1,4\}%' "$log_name" 1>&2
	else
		log_file+=$(date +%Y%m%d)
		mkdir -p "$(dirname "$log_file")"
		grep -v '\.\.\.\.\.\.\.\.[[:space:]]\{1,4\}[[:digit:]]\{1,4\}%' "$log_name" >> "$log_file"
	fi
}

################### main  ######################
continue_download=""
maxsize=52428800 # max filesize 50MB;
user_agent="Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.2 ) Firefox/2.0.0.12"
tool_type="wget"
last_proxy=""

while getopts "p:C:m:U:cT:a:" option ; do
	case $option in
		c ) continue_download=1 ;;
		m )
		[ -n "$OPTARG" ] && maxsize="$OPTARG"
		;;
		U )
		[ -n "$OPTARG" ] && user_agent="$OPTARG"
		;;
		* )
		PrintHelp
		exit 1
		;;
	esac
done

[ "$maxsize" -eq 0 ] && maxsize=20374182400  # 20GB (no limit)
shift $((OPTIND-1))

# init parameters
SELF=$0
BIN_DIR=$(dirname $(readlink -f $SELF))

url=$1
path=$2
log_file=$3
log_name=$3

PATH=/bin:/usr/bin:$PATH
LC_ALL=en_US
LANG=en_US

is_resource_file=0		# 0 --> false, 1 --> true
config_dir=""
command=""

timeout_secs=60  # filesize unchanged timeout;
ret=1

if [ $# -lt 2 ];then
	PrintHelp
	exit 1
fi

GenerateCommand
ProxyDownload

ret=$?
if [ $ret -eq 0 ] ; then
	echo "download ok!"
else
	echo "download fail!"
fi

AppendLog "$ret"

exit $ret

### end
