#!/bin/bash
res_dir=$1
if [ -d $res_dir/pictureDirectory ]; then
    num=`ls $res_dir/pictureDirectory/ | wc -l`
    if [ $num -gt 0 ] ; then
        (cp `ls $res_dir/pictureDirectory/* | head -n 1` "$res_dir/image.jpeg" & convert -delay 30 "$res_dir/pictureDirectory/*.jpeg" -loop 0 "$res_dir/animation.gif" &)
    fi
fi
