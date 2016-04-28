#!/libguestfs/fish/guestfish -f

#mount the disk and then chroot into it
launch
mount /dev/sda1 /

#create a local directory to store output
!rm -rf output
!mkdir output

!mkdir output/var
copy-out /var/log output/var




