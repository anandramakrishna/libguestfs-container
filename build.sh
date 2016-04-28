#!/bin/bash -x

CONTAINERREPO="azlinux/libguestfs"
CONTAINERTAG="0.01"
CONTAINERNAME="$CONTAINERREPO:$CONTAINERTAG"

CONTAINERID=$(docker build -t "$CONTAINERNAME" . | grep "Successfully built" | awk '{print $3}')

# if the export directory option is set, then export this built container to the directory
if [ "$EXPORTDIR" ];then
    docker save $CONTAINERID > $EXPORTDIR/$CONTAINERNAME.tar
fi


