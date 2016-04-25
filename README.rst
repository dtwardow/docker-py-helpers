# Support Scripts for Docker

The tools provided by this package are delivered as is. 
It consist of the following tools:

    * **dockerdns**
        * A "DNS" daemon to update the '/etc/hosts' file under Linux.
        * It adds currently running and later started Docker(r) containers to the hosts file with the extension '.docker'.

    * **dockerRmUnknown**
        * Remove nameless (unused) images and their corresponding containers.

To use them the dependent package 'docker-py' and 'pyyaml' is required.

