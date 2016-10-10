#!/bin/bash -x

SERVICENAME="InspectAzureDiskSvc_US"
LOG_FILE="/var/log/azureDiskInspectorSvc.log"

echo "Connecting to log..."
docker exec -it $SERVICENAME tail -f $LOG_FILE 
