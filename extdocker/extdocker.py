import docker
from docker import errors
import yaml

class DockerContainerException(docker.errors.APIError):
    def __init__(self, expr, msg):
        self.expression = expr
        self.message    = msg

    def error(self, message, errorcode):
        print("ERROR: " + message + "[" + errorcode + "]")
        return errorcode

    def warning(self, message):
        print("WARNING: " + message)
        return 0

    def info(self, message):
        print("INFO: " + message)
        return 0


class DockerContainer(dict):
    NAME = 'Names'
    IMAGE = 'Image'
    PORTS = 'Ports'
    VOLUMES = 'Volumes'
    LINK = 'Links'
    PRIV = 'Privileged'
    STATUS = 'Status'
    ID = 'Id'
    COMMAND = 'Command'

    def __init__(self, container):
        self.c = ExtDocker()
        self.i = container

    def _convertName(self, value):
        return value.strip('/')

    def name(self):
        return self.data(self.NAME) if self.i else None

    def data(self, datatype):
        if (datatype == self.NAME):
            return self.i['Name'].strip('/')
        elif (datatype == self.VOLUMES):
            return self.i['HostConfig']['Binds']
        elif (datatype == self.PORTS):
            values = self.i['HostConfig']['PortBindings']
            if values:
                retval = dict()
                for src, dst in values.iteritems():
                    for dstItem in dst:
                        if (dstItem['HostIp']):
                            retval[src] = list( [ dstItem['HostIp'], int(dstItem['HostPort']) ] )
                        else:
                            retval[src] = int(dstItem['HostPort'])
                return retval
            else:
                return None
        elif (datatype == self.PRIV):
            return self.i['HostConfig']['Privileged']
        elif (datatype == self.LINK):
            values = self.i['HostConfig']['Links']
            if values:
                retval = list()
                for item in values:
                    name = self._convertName(item.split(':')[0])
                    alias = self._convertName(item.split(':')[1]).split('/')[1]
                    retval.append(name + ":" + alias)
                return retval
            else:
                return None
        else:
            return self.i[datatype]

    def ipAddress(self):
        containerInspect = self.c.inspect_container(container=self.data(self.ID))
        if (containerInspect != None):
            return containerInspect['NetworkSettings']['IPAddress']
        else:
            return None

    def export(self, filename):
        export = {
            self.NAME: self.data(self.NAME),
            self.IMAGE: self.c.image(id=self.data(self.IMAGE)).name(),
            self.PORTS: self.data(self.PORTS),
            self.VOLUMES: self.data(self.VOLUMES),
            self.LINK: self.data(self.LINK) if self.data(self.LINK) else None,
            self.PRIV: self.data(self.PRIV)
        }
        with open(filename + ".dockercont", 'w') as file:
            file.write(yaml.dump(export))

    def readFromFile(self, filename):
        with open(filename + ".dockercont", 'r') as file:
            i = file.read()
        return self


class DockerImage:
    def __init__(self, image):
        self.c = ExtDocker()
        self.i = image

    def name(self):
        return self.i['RepoTags'][0] if self.i else None


class ExtDocker(docker.Client):
    def container(self, name, isRunning=False):
        for item in self.containers(all=not(isRunning)):
            if ((item['Id'] == name) or ('/'+name in item['Names'])):
                return DockerContainer(self.inspect_container(item['Id']))
        return None

    def image(self, name=None, id=None):
        for item in self.images(name=name, all=False):
            if (id):
                if (id == item['Id']):
                    return DockerImage(item)
            elif (name):
                if (name == item['RepoTags'][0].split(':')[0]):
                    return DockerImage(item)
        else:
            return None

    def untaggedImages(self):
        return self.images(quiet=True, filters={"dangling": True})

    def containersOfImagetype(self, image_name, all=True):
        return list( ( DockerContainer(self.inspect_container(item)) for item in self.containers(all=all) if item['Image'].split(':')[0] == image_name) )

    def run(self, image, name, volumes=None, ports=None, privileged=False, link=None):
        new_container = self.create_container(image=image,
                                              name=name,
                                              host_config=self.create_host_config(binds=volumes,
                                                                                  port_bindings=ports,
                                                                                  privileged=privileged,
                                                                                  links=link)
                                              )

        if (new_container):
            self.start(new_container)
            return self.container(new_container['Id'])
        else:
            return None
