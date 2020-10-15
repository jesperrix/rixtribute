import sys
import click
import pandas as pd
from tabulate import tabulate
import docker
from typing import Optional

from rixtribute.configuration import config, profile
# from rixtribute.ec2 import EC2, EC2Instance
# from rixtribute.ecr import ECR

@click.group(short_help="container commands (docker)", invoke_without_command=True)
@click.pass_context
def container(ctx):
    group_commands = container.list_commands(ctx)

    if ctx.invoked_subcommand is None:
        # No command supplied
        # Inform user on the available commands when running the app

        click.echo("Specify one of the commands below:")
        click.echo("----------------------------------")
        print(*group_commands, sep='\n')
    pass


@container.command(help="List configured containers")
# @click.option('--all', '-a', is_flag=True, help="list all repositiories")
@click.pass_context
def list_containers(ctx):
    cfg_containers = config.get_containers()

    # Filter for view
    fields = ["name", "file"]
    containers = [{k:v for k,v in x.items() if k in fields} for x in cfg_containers]

    print("Containers from configuration file:")
    print(tabulate(pd.DataFrame(containers), headers='keys'))


@container.command(help="Build docker container")
@click.argument('name', required=False)
@click.pass_context
def build_container(ctx, name :Optional[str]):
    """ Build container """
    cfg_containers = config.get_containers()

    # Filter for view
    fields = ["name", "file"]
    containers = [{k:v for k,v in x.items() if k in fields} for x in cfg_containers]

    # Drop config from instanes
    # [x.pop("config", None) for x in cfg_instances]

    cfg_containers = config.get_containers()
    [x.pop("ports", None) for x in cfg_containers]
    # for container in cfg_containers:
        # print(container)

    #docker build -t <image-name>:latest -f file .
    # Support for build args?
    # support for custom args

    print("Containers from configuration file:")
    print(tabulate(pd.DataFrame(cfg_containers), headers='keys'))


# TODO Build container
# TODO Create repos
# TODO Push containers

    # repos = ECR.list_repositories(filter_project_name=project_name)
    # print(tabulate(pd.DataFrame([repo.get_printable_dict() for repo in repos]), headers='keys'))

