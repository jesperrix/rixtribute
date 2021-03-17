import sys
import os
import click
from rixtribute.ec2 import EC2
import pandas as pd
from tabulate import tabulate
# import glob

# from rixtribute import container_utils
from rixtribute.configuration import config, profile

@click.group(short_help="run commands", invoke_without_command=True)
@click.pass_context
def run(ctx):
    group_commands = run.list_commands(ctx)

    if ctx.invoked_subcommand is None:
        # No command supplied
        # Inform user on the available commands when running the app

        click.echo("Specify one of the commands below:")
        click.echo("----------------------------------")
        print(*group_commands, sep='\n')
    pass

@run.command(short_help="List commands")
@click.pass_context
def list_commands(ctx):
    """ List instances """
    commands = config.get_commands()
    print("Available commands: ")
    for command in commands:
        print(f"  {command}")


@run.command(short_help="Run a command")
@click.argument("command-name", type=str)
@click.pass_context
def cmd(ctx, command_name):
    """ List instances """
    command = config.get_command(command_name)
    if command == None:
        print(f"No command named: {command_name} - use run: rxtb run list-commands")
        sys.exit(3)

    ec2_instances = EC2.list_instances(profile, all)
    print(tabulate(pd.DataFrame([instance.get_printable_dict() for instance in ec2_instances]), headers='keys'))
    n = int(click.prompt("Choose instance to ssh into"))

    ec2_instances[n].docker_run(command)

