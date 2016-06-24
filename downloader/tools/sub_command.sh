#!/bin/bash

RET_CODE_FILE=$1
shift

real_command="$*"
bash -c "$real_command" 
ret=$?
echo $ret > $RET_CODE_FILE
exit $ret

