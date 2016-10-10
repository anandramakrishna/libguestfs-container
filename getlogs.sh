#!/bin/bash -x

SERVICENAME="InspectAzureDiskSvc_US"
LOG_FILE="/var/log/azureDiskInspectorSvc.log"

echo "Connecting to log..."
if [ ! -d "logs" ]; then
  mkdir logs
fi
docker cp $SERVICENAME:$LOG_FILE ./logs
