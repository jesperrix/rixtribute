import sys
import click
import pandas as pd
from tabulate import tabulate
import docker

from rixtribute.configuration import config, profile
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

@ecr.command()
@click.pass_context
def push(ctx):
    """ Push image to ECR repository """
    client = ECR._get_ecr_boto_client()
    response = client.get_authorization_token()
    token = response['authorizationData'][0]['authorizationToken']
    import base64
    # __import__('pdb').set_trace()
    token = base64.b64decode(token).decode()
    username, password = token.split(':')
    auth_config = {'username': username, 'password': password}

    docker_client = docker.from_env()
    image = docker_client.images.get("example-gpu:latest")
    image.tag("293331033030.dkr.ecr.eu-west-1.amazonaws.com/test-iptc", "latest")

    # image = docker_client..get("example-gpu:latest")
    # image.
    print("Pushing...")
    for line in \
        docker_client.images.push("293331033030.dkr.ecr.eu-west-1.amazonaws.com/test-iptc:latest",
                                  stream=True,
                                  auth_config=auth_config):
            print(line)

    # repos = ECR.list_repositories()
    # print(tabulate(pd.DataFrame([repo.get_printable_dict() for repo in repos]), headers='keys'))
    # __import__('pdb').set_trace()
