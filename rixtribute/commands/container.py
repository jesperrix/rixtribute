import sys
import click
import pandas as pd
from tabulate import tabulate
from rixtribute import container_utils
from typing import Optional, List
from rixtribute.helper import filter_list_of_dicts

# import rixtribute.container
from rixtribute.configuration import config, profile
# from rixtribute.ec2 import EC2, EC2Instance
from rixtribute.ecr import ECR


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
def list(ctx):
    cfg_containers = config.get_containers()
    containers = filter_list_of_dicts(cfg_containers, ["name", "file"])

    print("Containers from configuration file:")
    print(tabulate(pd.DataFrame(containers), headers='keys'))


@container.command(help="Build docker container")
# @click.argument('name', required=False)
@click.pass_context
def build(ctx):
    """ Build container """
    cfg_containers = config.get_containers()
    containers = filter_list_of_dicts(cfg_containers, ["name", "file"])

    print("Containers from configuration file:")
    print(tabulate(pd.DataFrame(containers), headers='keys'))
    n = int(click.prompt("Choose container to build"))

    container_cfg = cfg_containers[n]

    container_utils.docker_build_from_cfg(container_cfg)


@container.command(help="push docker container")
# @click.argument('name', required=False)
@click.pass_context
def push(ctx):
    cfg_containers = config.get_containers()
    containers = filter_list_of_dicts(cfg_containers, ["name", "tag"])
    container_tags = [x["tag"] for x in containers]

    # Select image to push
    print("Image from configuration file:")
    print(tabulate(pd.DataFrame(containers), headers='keys'))
    n = int(click.prompt("Choose container to push"))

    push_tag = [x["tag"] for x in containers][n] + ":latest"

    images = container_utils.docker_images()

    image_is_built = False
    # __import__('pdb').set_trace()
    for image in images:
        for tag in image.tags:
            if push_tag == tag:
                image_is_built = True

    if image_is_built == False:
        print("Selected image is not build yet, call the build command")

    # __import__('pdb').set_trace()
    # # TODO push should be in commands.ecr

    __import__('pdb').set_trace()
    auth_config = ECR.get_auth_token()
    container_utils.docker_login(auth_config)

    # n = int(click.prompt("Choose container to build"))
    # repos = ECR.list_repositories(filter_project_name=config.project_name)

    # cfg_containers = config.get_containers()
    # containers = filter_list_of_dicts(cfg_containers, ["name", "file"])


    # docker_client = docker.from_env()
    # docker_client.login(**auth_config)

# TODO Push containers

    # print(tabulate(pd.DataFrame([repo.get_printable_dict() for repo in repos]), headers='keys'))

