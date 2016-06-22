#!/libguestfs/fish/guestfish -f


echo 'Launching guestfish...'
launch
echo 'Mounting sda1'
mount /dev/sda1 /
echo 'Var log output dir set to ' $VARLOGDIR
echo 'Copying waagent logs'
glob copy-out /var/log/waagent* $VARLOGDIR
echo 'Copying syslog'
glob copy-out /var/log/syslog* $VARLOGDIR
echo 'Copying rsyslog'
glob copy-out /var/log/rsyslog* $VARLOGDIR
echo 'Copying kern logs'
glob copy-out /var/log/kern* $VARLOGDIR
echo 'Copying dmesg logs'
glob copy-out /var/log/dmesg* $VARLOGDIR
echo 'Copying dpkg logs'
glob copy-out /var/log/dpkg* $VARLOGDIR
echo 'Copying cloud-init logs'
glob copy-out /var/log/cloud-init* $VARLOGDIR
echo 'Copying boot logs'
glob copy-out /var/log/boot* $VARLOGDIR
echo 'Copying auth logs'
glob copy-out /var/log/auth* $VARLOGDIR
echo 'All copying done!'

