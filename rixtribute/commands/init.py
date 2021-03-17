import sys
import click
import pandas as pd
from tabulate import tabulate
import docker

from rixtribute.configuration import config, profile
from rixtribute.configuration import ProviderType
# from rixtribute.ec2 import EC2, EC2Instance
from rixtribute.ecr import ECR

@click.command(short_help="initialize project")
@click.pass_context
def init(ctx):
    """Initialize project and setup prerequisite infrastructure """

    print("Initializing project")
    print(f"config file: {config.file_path}")
    print(f"profile file: {profile.file_path}")

    cfg_instances = config.get_instances()
    cfg_containers = config.get_containers()
    cfg_project = config.get_project()

    project_name = cfg_project["name"]

    ##################################
    #  Setup container repositories  #
    ##################################

    ecr_repos = ECR.list_repositories()
    ecr_repo_names = [repo.repository_name for repo in ecr_repos]

    for instance in cfg_instances:
        container_name = instance.get("container", None)
        if container_name is not None:
            container_cfg = config.get_container(container_name)

            repo_name = f"{project_name}/{container_name}"

            if instance["provider"] == ProviderType.AWS.value:
                print(f"Creating ECR repo for container [{container_name}]")
                if repo_name not in ecr_repo_names:
                    ECR.create_repository(repo_name)
