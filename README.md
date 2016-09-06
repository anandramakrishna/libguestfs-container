This is a Docker container that wraps libguestfs and exposes a simple REST API around it.  The function of the API is as follows:
* The REST API takes in parameters pointing to a VHD.  
* The REST API is listening on container port 8080.  
* It then automates the fetching and inspection of the VHD.  The assumption is that the URL is readable.
* It extracts a specific set of log files from the VHD, looking across all partitions.  
* Once it finds the log files, it exports the files out and then zips the files up.
* The contents of the zip file are then written out as the response.

To run the container do:
    $ docker run [-it] -p 8080:8080 azlinux/libguestfs:0.01

To send a request to the service do:
    $ curl "http://<Service URL and port>/<Azure storage acct name>/<Azure storage path>"

# libguestfs-container
The Docker container for libguestfs allows for interactive interaction with remote virtual machine disk images.  It is particularly useful for interacting with Microsoft Azure vhd images.  From inside the container do:

    $ ./run virt-rescue --ro -a "<vhd URI>"
    …
    ------------------------------------------------------------
    
    Welcome to virt-rescue, the libguestfs rescue shell.
    
    Note: The contents of / are the rescue appliance.
    You have to mount the guest's partitions under /sysroot
    before you can examine them.
    
    groups: cannot find name for group ID 0
    ><rescue> mount /dev/sda1 /sysroot
    ><rescue> chroot /sysroot
    ><rescue> ls
    bin   etc         initrd.img.old  lost+found  opt   run   sys  var
    ...

## 1. [Install Docker](https://docs.docker.com/installation/)##
## 2. Generate an Image URI ##

Generate a SAS key.  For example:

    $ AZURE_STORAGE_ACCOUNT=<storage_account_name> AZURE_STORAGE_ACCESS_KEY=<storage_key> azure storage blob sas create <container_name> <blob_name> r 2016-01-01
    info:    Executing command storage blob sas create
    Creating shared access signature for blob osdiskforconsul0-osdisk.vhd in container vhds
    data:    Shared Access Signature
    se=2016-01-01T00%3A00%3A00Z&sp=r&sv=2014-02-14&sr=b&sig=LOlrHXrQeaqlSEP51hRi7E5KDa9lnkqSvLTaZBmTkrQ%3D
    info:    storage blob sas create command OK

The "r" term means read-only, other access levels are allowed.  The final date is the expiration time of the SAS key.

Concatenate the resulting key to the blob URI.  The final result should look like:

**https://azurestoragename.blob.core.windows.net/vhds/osdiskforconsul0-osdisk.vhd?se=2016-01-01T00%3A00%3A00Z&sp=r&sv=2014-02-14&sr=b&sig=RaNdOmLeTtErSSEP51hRi7E5KDa9lnkqSvLTaZBmTkrQ%3D**

## 3. Browse the VHD ##

    $ docker run -it gabrielhartmann/libguestfs
    $ ./run virt-rescue --ro -a "<vhd URI>"
    ><rescue> mount /dev/sda1 /sysroot
    ><rescue> chroot /sysroot
  

This container includes [fixes](https://github.com/gabrielhartmann/libguestfs) for handling http and https URIs which contain query strings.  The current implementation of libguestfs has two defects around URI handling.

 1. https://bugzilla.redhat.com/show_bug.cgi?id=1092583
 2. https://bugzilla.redhat.com/show_bug.cgi

The [fixes made here](https://github.com/gabrielhartmann/libguestfs) are incompatible with protocols other than http and https.  Permanent, fully compatible fixes are pending.
