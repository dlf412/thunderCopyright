#! /bin/bash

print_usage()
{
    echo "Usage: $0 queue message_threshold"
}

safe()
{
    #TODO: safe handler
    echo "under thres, safe.."
}

alarm()
{
    #TODO:alarm handler
    echo "how to alarm..."
}

if [ $# -lt 2 ]; then
    print_usage
    exit 0
fi

queue=$1
thres=$2

s=$(sudo rabbitmqctl list_queues |grep -w $queue)

if [ -n "$s" ]
then
    num=$(echo $s |grep -Eo '[0-9]+')
    echo $num
    if [ $num -lt $thres ]
    then
        safe
    else
        alarm
    fi
fi
