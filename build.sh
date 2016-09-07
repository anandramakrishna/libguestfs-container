#!/bin/bash -x

exec 5>&1
CONTAINERREPO="azlinux/libguestfs"
CONTAINERTAG="0.01"
CONTAINERNAME="$CONTAINERREPO:$CONTAINERTAG"

CONTAINERID=$((docker build -t "$CONTAINERNAME" .|tee /dev/fd/5) | grep "Successfully built" | awk '{print $1}')

# if the export directory option is set, then export this built container to the directory
if [ "$EXPORTDIR" ];then
    docker save $CONTAINERID > $EXPORTDIR/$CONTAINERNAME.tar
fi


