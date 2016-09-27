#!/usr/bin/env python

import extdocker

c = extdocker.ExtDocker()

for image in c.untaggedImages():
    print("[IMAGE] " + image)

    containers_of_image     = c.containersOfImagetype(image_name=image, all=True)
    num_containers_of_image = containers_of_image.__len__()

    for container in containers_of_image:
        container_digest = container.data('Id')
        print("  [CONTAINER] " + container_digest)
        if c.container(name=container_digest, isRunning=False):
            c.remove_container(container=container_digest, force=True)

    c.remove_image(image=image, force=False)
