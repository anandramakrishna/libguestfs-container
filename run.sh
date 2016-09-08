#!/bin/bash -x

CONTAINERREPO="azlinux/libguestfs"
CONTAINERTAG="0.01"
CONTAINERNAME="$CONTAINERREPO:$CONTAINERTAG"
SERVICENAME="InspectAzureDiskSvc"
SERVICEVOLUMENAME="InspectAzureDiskSvcSSLVolume"
SSL_PATH="$HOME/logext_ssl"
SSL_PRIVATE_KEY="$SSL_PATH/logext_private.rsa"
SSL_PUBLIC_KEY="$SSL_PATH/logext_public.crt"

echo "Cleaning up previous instances..."
docker stop $SERVICENAME
docker rm -f $SERVICENAME
docker rm -f $SERVICEVOLUMENAME

if [ ! -f $SSL_PRIVATE_KEY ]
then
  echo "File $SSL_PRIVATE_KEY is missing."
  exit 1
fi
if [ ! -f $SSL_PUBLIC_KEY ]
then
  echo "File $SSL_PUBLIC_KEY is missing."
  exit 1
fi

echo "Starting service..."
docker create -v /etc/nginx/ssl --name $SERVICEVOLUMENAME ubuntu
docker cp ~/logext_ssl/. $SERVICEVOLUMENAME:/etc/nginx/ssl/.
docker run -it -p 8080:8080 --name $SERVICENAME --volumes-from $SERVICEVOLUMENAME $CONTAINERNAME
echo "Done."
