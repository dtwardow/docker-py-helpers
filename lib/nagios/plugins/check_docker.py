#!/usr/bin/env python

import argparse
import logging
import string

import extdocker
import nagiosplugin

__author__ = "Dennis Twardowsky"
__copyright__ = "Copyright 2016, Dennis Twardowsky"
__credits__ = ["Dennis Twardowsky"]
__license__ = "GPL"
__version__ = "1.0.0"
__maintainer__ = "Dennis Twardowsky"
__email__ = "twardowsky@gmail.com"
__status__ = "Production"


# Configure Logging
logging.basicConfig(format='%(asctime)-15s %(module)-15s %(levelname)-8s %(message)s')
l = logging.getLogger('nagiosplugin')

c = extdocker.ExtDocker()


def calc_cpu_usage(container_stats):
    """
    Calculate CPU usage based on output of docker.stats()
    :param container_stats: dict() as returned by docker.stats()
    :return: Overall CPU usage percentage [float]
    """
    all_cpu_usage = 0.0

    cpu_usage = float(container_stats["cpu_stats"]["cpu_usage"]["total_usage"])
    precpu_usage = float(container_stats["precpu_stats"]["cpu_usage"]["total_usage"])
    sys_usage = float(container_stats["cpu_stats"]["system_cpu_usage"])
    presys_usage = float(container_stats["precpu_stats"]["system_cpu_usage"])
    num_cpus = float(len(container_stats["cpu_stats"]["cpu_usage"]["percpu_usage"]))

    cpu_delta = cpu_usage - precpu_usage
    sys_delta = sys_usage - presys_usage

    if cpu_delta > 0 and sys_delta > 0:
        all_cpu_usage = (cpu_delta / sys_delta) * num_cpus * 100.0

    return all_cpu_usage


def calc_mem_usage(container_stats):
    """
    Calculate Memory usage based on output of docker.stats()
    :param container_stats: dict() as returned by docker.stats()
    :return: Memory usage percentage of the given container [float]
    """
    return float(float(container_stats["memory_stats"]["max_usage"]) / float(container_stats["memory_stats"]["limit"]))


def split_multiline_string(value):
    """
    Split Multiline strings in a two-dimensional list
    :param value: Input String
    :return: Two-dimensional list of strings (lines[words[...]])
    """
    ret = []

    if isinstance(value, str):
        ret += [string.split(line) for line in value.splitlines()]

    return ret


def call_supervisor(container_id):
    ret = None

    context = c.exec_create(container_id,
                            "supervisorctl status",
                            stdout=True,
                            stderr=False,
                            stdin=False,
                            tty=False,
                            user='root')

    if context:
        ret = c.exec_start(context,
                           detach=False,
                           tty=False,
                           stream=False,
                           socket=False)

    return ret


# ----------------------------------------------------------------------------------------------------------------------


class ServiceStateContext(nagiosplugin.Context):
    """
    Evaluate service (contianer) states
    This Context evaluates the container's Status-string and returns service state flag
    """
    state = None

    def evaluate(self, metric, resource):
        value = metric.valueunit
        if value == "running":
            self.state = nagiosplugin.Ok
        elif value == "paused":
            self.state = nagiosplugin.Warn
        elif value == "exited":
            self.state = nagiosplugin.Critical
        elif value == "dead":
            self.state = nagiosplugin.Critical
        else:
            self.state = nagiosplugin.Critical

        l.info("'" + metric.name + "' in state '" + value + "' with result '" + self.state.__str__() + "'")
        return nagiosplugin.Result(self.state, metric=metric)

    def performance(self, metric, resource):
        return metric.name + "=" + metric.valueunit


class ServiceNumContext(nagiosplugin.Context):
    """
    Evaluate Number of running Services
    This context just compares the number of services with the given commandline parameter
    """
    state = None

    def __init__(self, name, numservices):
        super(ServiceNumContext, self).__init__(name, fmt_metric=None, result_cls=nagiosplugin.Result)
        self.num_services_expected = numservices

    def evaluate(self, metric, resource):
        if int(metric.valueunit) == int(self.num_services_expected):
            self.state = nagiosplugin.Ok
        else:
            self.state = nagiosplugin.Warn

        l.info(metric.name + " / " + metric.__str__() + " of " + self.num_services_expected.__str__() + " services")
        return nagiosplugin.Result(self.state, metric=metric)

    def describe(self, metric):
        return metric.valueunit.__str__() + ";" + self.num_services_expected.__str__()

    def performance(self, metric, resource):
        return metric.name + ".numservices=" + metric.__str__() + ";" + self.num_services_expected.__str__()


class SupervisorStatusContext(nagiosplugin.Context):
    """
    Evaluate output of SupervisorD's command 'supervisorctl'
    It extracts the first two columns of the given command output
    """
    def __init__(self, name):
        super(SupervisorStatusContext, self).__init__(name, fmt_metric=None, result_cls=nagiosplugin.Result)

    @staticmethod
    def eval_state(current_state, new_state):
        if (current_state == nagiosplugin.Ok and
            (new_state == nagiosplugin.Warn or new_state == nagiosplugin.Critical)) \
                or (current_state == nagiosplugin.Warn and new_state == nagiosplugin.Critical):
            return new_state
        else:
            return current_state

    def evaluate(self, metric, resource):
        state = nagiosplugin.Ok
        values = split_multiline_string(metric.valueunit)

        for item in values:
            if item[1] == "STOPPED":
                state = self.eval_state(state, nagiosplugin.Warn)
            elif item[1] == "STARTING":
                state = self.eval_state(state, nagiosplugin.Ok)
            elif item[1] == "RUNNING":
                state = self.eval_state(state, nagiosplugin.Ok)
            elif item[1] == "BACKOFF":
                state = self.eval_state(state, nagiosplugin.Critical)
            elif item[1] == "STOPPING":
                state = self.eval_state(state, nagiosplugin.Ok)
            elif item[1] == "EXITED":
                state = self.eval_state(state, nagiosplugin.Warn)
            elif item[1] == "FATAL":
                state = self.eval_state(state, nagiosplugin.Critical)
            elif item[1] == "UNKNOWN":
                state = self.eval_state(state, nagiosplugin.Critical)
            else:
                state = self.eval_state(state, nagiosplugin.Critical)

            l.info(metric.name + '.' + item[0].__str__() + " in state '" +
                   item[1].__str__() + "' with result '" + state.__str__() + "'")

        return nagiosplugin.Result(state, metric=metric)

    def describe(self, metric):
        ret = str()
        values = split_multiline_string(metric.valueunit)

        for item in values:
            if ret.__len__() > 0:
                ret += ";"
            ret += item[0] + ":" + item[1]

        return ret

    def performance(self, metric, resource):
        ret = metric.name + "="
        values = split_multiline_string(metric.valueunit)

        first = True
        for item in values:
            if not first:
                ret += ";"
            else:
                first = False

            ret += item[0] + ":" + item[1]

        return ret


# ----------------------------------------------------------------------------------------------------------------------


class DockerProjectSummary(nagiosplugin.Summary):
    """
    Format the Nagiosplugin's Summary String
    """
    def empty(self):
        return ""

    def problem(self, results):
        text = ""
        for item in results.most_significant:
            text += item.context.name + "=" + item.__str__() + " "
        return text.strip()


class DockerProject(nagiosplugin.Resource):
    """
    The Worker
    Collect data of all available container's (services) attached to a 'docker-compose'-project
    """
    def __init__(self, project, service=None, numservices=0, servicesupervisor=str()):
        assert isinstance(servicesupervisor, str)
        assert isinstance(numservices, int)

        self.project = project
        self.service = service
        self.numservices = numservices
        self.servicesupervisor = servicesupervisor

    def analyse_container(self):
        retlist = []
        l_list = c.containers(all=True, filters={
            "label":
                [
                    "com.docker.compose.project=" + self.project if self.project else "com.docker.compose.project",
                    "com.docker.compose.service=" + self.service if self.service else "com.docker.compose.service"
                ]
        })

        for item in l_list:
            l.debug(item)

            d_stats = c.stats(container=item, stream=False, decode=True)
            d_info = c.inspect_container(container=item)

            container_id = item["Id"]
            service_name = item["Labels"]["com.docker.compose.service"]
            service_state = d_info["State"]["Status"]
            cpu_usage = calc_cpu_usage(d_stats)
            mem_usage = calc_mem_usage(d_stats)
            supervisor_ret = call_supervisor(container_id) \
                if service_state == "running" and self.servicesupervisor.split(',').__contains__(service_name) else None

            l.info(container_id + " / " + service_name + " / " + str(cpu_usage) + " / " + str(
                mem_usage) + " / " + service_state)

            retlist.append({
                'container_id': container_id,
                'name': service_name,
                'cpu_usage': cpu_usage,
                'mem_usage': mem_usage,
                'status': service_state,
                'supervisor_state': supervisor_ret
            })

        return retlist

    def probe(self):
        service_list = self.analyse_container()

        for item in service_list:
            if isinstance(item["supervisor_state"], str):
                yield nagiosplugin.Metric(item["name"] + '.procs', item["supervisor_state"], context='procs')
            yield nagiosplugin.Metric(item["name"] + '.cpu_usage', round(item["cpu_usage"], 2), min=0.0, context='cpu')
            yield nagiosplugin.Metric(item["name"] + '.mem_usage', round(item["mem_usage"], 2), min=0.0, context='mem')
            yield nagiosplugin.Metric(item["name"] + '.state', item["status"], context='state')

        if self.numservices > 0:
            # Ignore number of services if required value is 0
            yield nagiosplugin.Metric(self.project, len(service_list), context='numservices')


def main():
    global args

    argp = argparse.ArgumentParser(description=__doc__)
    argp.add_argument('-p', '--project', help="Project Name [string]")
    argp.add_argument('-s', '--service', help="Service Name [string]")
    argp.add_argument('-S', '--servicesupervisor', default=str(), help="Service Name [string]")
    argp.add_argument('-n', '--numservices', default=0, help="Number of Services assumed")
    argp.add_argument('-m', '--memwarning', default=60.0, help="Memory Warning Threshold")
    argp.add_argument('-M', '--memcritical', default=80.0, help="Memory Critical Threshold")
    argp.add_argument('-c', '--cpuwarning', default=80.0, help="CPU Warning Threshold")
    argp.add_argument('-C', '--cpucritical', default=100.0, help="CPU Critical Threshold")
    argp.add_argument('-t', '--timeout', default=0, help="Timeout for Check [s]")
    argp.add_argument('-V', '--verbose', action='count', default=0, help="Output Verbosity (use up to 3 times)")
    argp.add_argument('-v', '--version', action="version", version="%(prog)s " + __version__)
    args = argp.parse_args()

    # Start Nagiosplugin-Check
    check = nagiosplugin.Check(
        DockerProject(args.project, args.service, args.numservices, args.servicesupervisor),
        nagiosplugin.ScalarContext('cpu', args.cpuwarning, args.cpucritical, fmt_metric='\'{name}\'={value}% CPU'),
        nagiosplugin.ScalarContext('mem', args.memwarning, args.memcritical, fmt_metric='\'{name}\'={value}% MEM'),
        ServiceNumContext('numservices', args.numservices),
        ServiceStateContext('state', fmt_metric='\'{name}\'={value}'),
        SupervisorStatusContext('procs'),
        DockerProjectSummary()
    )
    check.main(verbose=args.verbose, timeout=args.timeout)


if __name__ == "__main__":
    main()
