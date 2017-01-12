#!/usr/bin/env python
import getopt
import signal
import sys
import os
import extdocker
import subprocess

running = True
headfoot_identifier = "DOCKER CONTAINERS"
header_identifier = "# === " + headfoot_identifier + " START ==="
footer_identifier = "# === " + headfoot_identifier + " END ==="

# Default: Hosts-file path
_HOSTS_FILE_ = "/etc/hosts"
# Default: Domain Suffix
_HOST_DOMAIN_ = "docker"
# Default: Don't send SIGHUP to process
_SIGHUPPROC_ = ""

c = extdocker.ExtDocker()


def on_init():
    """
    Initialize HOSTS-file with a header
    :return: Nothing
    """

    listfile = open(_HOSTS_FILE_, "r")
    lines = listfile.readlines()
    listfile.close()

    found = False

    with open(_HOSTS_FILE_, "a") as output:
        for line in lines:
            if line.lstrip().startswith(header_identifier):
                # print ("Hosts File already initialized!")
                found = True
                break
        if not found:
            output.write("\n" + header_identifier + "\n")


def on_terminate(signum, frame):
    """
    Signal handler which is executed on script termination
    :param signum: Caught signal number
    :param frame: Frame
    :return:
    """

    print("Daemon stopped [by signal " + signum.__str__() + "], clean-up hosts file ...")
    # Stop event loop on next event
    global running
    running = False
    # Clean-up hosts file
    remove_host()

    exit(0)


def on_daemonize():
    """
    Event Loop to dynamically add / remove Docker-containers from HOSTS-file
    :return: Nothing
    """

    # Register signal handler for clean-up before termination
    signal.signal(signal.SIGINT, on_terminate)
    signal.alarm(0)

    while running:
        event = c.events(decode=True)

        for i in event:
            # EventLoop Exit Handler
            if not running:
                break

            if not 'status' in i:
                continue

            event_type = i['status']
            event_object = i['id']

            event_container = c.container(event_object)

            if not isinstance(event_container, extdocker.DockerContainer):
                continue

            container_name = event_container.name()
            container_ip = event_container.ipAddress()

                # Handle event based on container status
            if event_type == 'start':
                if container_name.strip() and container_ip.strip():
                    print ("START <" + container_name + "> with IP <" + container_ip + ">")
                    add_host(container_name, container_ip)
                    send_signal(_SIGHUPPROC_, signal.SIGHUP)
            if event_type == 'stop':
                print ("STOP  <" + container_name + ">")
                remove_host(container_name)
                send_signal(_SIGHUPPROC_, signal.SIGHUP)


def on_prepare():
    """
    Add all currently running Docker-containers
    :return: Nothing
    """

    containers = c.containers(all=False)

    for item in containers:
        container = c.container(item['Id'])
        ip_addr = container.ipAddress()
        name = container.name()
        if ip_addr and name:
            print ("Add container <" + name + "> with IP " + ip_addr)
            add_host(name, ip_addr)


def remove_host(hostname=None):
    """
    Remove one / all host(s) from HOSTS-file, based on fixed domain-suffix
    :param hostname: Hostname to remove (if empty, all hosts are removed)
    :return: Nothing
    """

    listfile = open(_HOSTS_FILE_, "r")
    lines = listfile.readlines()
    listfile.close()

    domainname = '.' + _HOST_DOMAIN_

    with open(_HOSTS_FILE_, "w") as output:
        for line in lines:
            if line.lstrip().startswith('#') or not line.strip():
                output.write(line)
            else:
                parts = line.split()
                size = parts.__len__()
                found = False

                for i in range(1, size):
                    if not hostname:
                        if parts[i].endswith(domainname):
                            found = True
                            break
                    elif hostname + domainname in parts[i]:
                        found = True
                        break

                if not found:
                    output.write(line)


def add_host(hostname, ip):
    """
    Append a host to the HOSTS-file with a fixed domain-suffix
    :param hostname: Hostname (domain-suffix added automatically)
    :param ip: IP address assigned to the given hostname
    :return: True on success, False when parameters missing
    """

    if not hostname.strip() or not ip.strip():
        print ("ERROR: addHost: Hostname and IP must not be empty!")
        return False

    complete_name = hostname + '.' + _HOST_DOMAIN_
    hosts_line = ip.ljust(15) + " " + complete_name + "\n"

    with open(_HOSTS_FILE_, "a") as output:
        output.write(hosts_line)

    return True


def send_signal(name, sig):
    if name != "":
        pid_to_kill = get_pid(name)
        if pid_to_kill > 0:
            print ("SIGHUP > " + name + ":" + str(pid_to_kill))
            os.kill(pid_to_kill, sig)
        else:
            print ("WARNING: PID of process <" + name + "> not found!")


def get_pid(name):
    return int(subprocess.check_output(["pidof","-s",name]))

def usage():
    print('dockerdns.py [-hdc] [-s <domain-suffix>] [-f <alt-hosts-file>]')
    print('Options:')
    print('    -h             Print help message (and exit)')
    print('    -d             Start Docker event-lister')
    print('    -c             Clean hosts-file and exit (not compatible with -d)')
    print('    -u string      Send signal SIGHUP to given process')
    print('    -d string      Domain-Suffix to in hosts-file (default: ' + _HOST_DOMAIN_ + ')')
    print('    -f filename    Alternate path of the hosts file (default: ' + _HOSTS_FILE_ + ')')


def main(argc, argv):
    # Default: do NOT daemonize!
    _LISTENER_ = False
    # Default: update hosts file
    _UPDATE_ = True

    global _HOST_DOMAIN_
    global _HOSTS_FILE_
    global _SIGHUPPROC_

    try:
        opts, args = getopt.getopt(argv, 'ds:f:cu:h')
    except getopt.GetoptError:
        usage()
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-d':
            _LISTENER_ = True
        elif opt == '-s':
            _HOST_DOMAIN_ = arg
        elif opt == '-f':
            _HOSTS_FILE_ = arg
        elif opt == '-c':
            _UPDATE_ = False
        elif opt == '-u':
            _SIGHUPPROC_ = arg
        elif opt == '-h':
            usage()
            sys.exit(0)

    # Init hosts-file first
    remove_host()
    on_init()

    if _UPDATE_:
        on_prepare()
        if _LISTENER_:
            on_daemonize()


if __name__ == "__main__":
    main(len(sys.argv), sys.argv[1:])
