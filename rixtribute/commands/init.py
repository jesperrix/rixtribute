import sys
import click
import pandas as pd
from tabulate import tabulate
import docker

from rixtribute.configuration import config, profile
from rixtribute.configuration import ProviderType
# from rixtribute.ec2 import EC2, EC2Instance
# from rixtribute.ecr import ECR

@click.command(short_help="initialize project")
@click.pass_context
def init(ctx):
    """Initialize project and setup prerequisite infrastructure """

    cfg_instances = config.get_instances()
    cfg_containers = config.get_containers()
    cfg_project = config.get_project()

    project_name = cfg_project["name"]

    for container in cfg_containers:
        print(container)
        if ctx.obj["VERBOSE"]:
            print("Creating ECR repo")

    print(cfg_project)

    for instance in cfg_instances:
        container_name = instance.get("container", None)
        if container_name:
            container_cfg = config.get_container(container_name)

            if instance["provider"] == ProviderType.AWS:
                print("Creating ECR repo")
                print("{project_name}/{container_name}")



