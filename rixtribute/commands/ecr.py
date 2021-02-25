import sys
import click
import pandas as pd
from tabulate import tabulate
import docker
from typing import Optional

from rixtribute.configuration import config, profile
from rixtribute.helper import filter_list_of_dicts
from rixtribute import container_utils
# from rixtribute.ec2 import EC2, EC2Instance
from rixtribute.ecr import ECR

@click.group(short_help="ecr repository commands", invoke_without_command=True)
@click.pass_context
def ecr(ctx):
    group_commands = ecr.list_commands(ctx)

    if ctx.invoked_subcommand is None:
        # No command supplied
        # Inform user on the available commands when running the app

        click.echo("Specify one of the commands below:")
        click.echo("----------------------------------")
        print(*group_commands, sep='\n')
    pass

@ecr.command(help="List ECR repositiories")
@click.option('--all', '-a', is_flag=True, help="list all repositiories")
@click.pass_context
def list(ctx, all):

    if all is True:
        project_name = None
    else:
        project_name = config.get_project()["name"]

    repos = ECR.list_repositories(filter_project_name=project_name)
    print(tabulate(pd.DataFrame([repo.get_printable_dict() for repo in repos]), headers='keys'))

@ecr.command()
@click.argument('name', type=str)
@click.pass_context
def create(ctx, name):
    """ Create an ECR repository """
    ECR.create_repository(name)


@ecr.command(help="push docker container")
@click.pass_context
def push(ctx):
    cfg_containers = config.get_containers()
    cfg_containers = filter_list_of_dicts(cfg_containers, ['name', 'tag', 'file'])

    print("push image to ecr:")
    print(tabulate(pd.DataFrame(cfg_containers), headers='keys'))
    n = int(click.prompt("Choose image"))

    container_cfg = cfg_containers[n]

    # Get built images from docker
    images = container_utils.docker_images()

    docker_image = container_utils.docker_image_get(f"{container_cfg['tag']}:latest")

    if docker_image is None:
        print("image not built, run: rxtb container build")
        sys.exit()

    # n = int(click.prompt("Choose container to build"))
    repos = ECR.list_repositories(filter_project_name=config.project_name)

    auth_config = ECR.get_auth_token()
    container_utils.docker_login(auth_config)

    for repo in repos:
        if repo.repository_name == container_cfg['tag']:
            # image = docker_client.images.get("example-gpu:latest")
            print(f"Pushing image to {repo.repository_uri}")
            docker_image.tag(repo.repository_uri, 'latest')
            container_utils.docker_push(repo.repository_uri, 'latest', auth_config)
