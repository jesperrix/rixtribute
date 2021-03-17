import sys
import click
from rixtribute.commands.ec2 import ec2 as ec2_commands
from rixtribute.commands.ecr import ecr as ecr_commands
from rixtribute.commands.container import container as container_commands
from rixtribute.commands.init import init as init_commands
from rixtribute.commands.run import run as run_commands

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])

@click.group(invoke_without_command=True, context_settings=CONTEXT_SETTINGS)
@click.pass_context
@click.option('--verbose', '-v', is_flag=True, help="Increase output verbosity")
def main(ctx, verbose):
    group_commands = main.list_commands(ctx)

    if ctx.invoked_subcommand is None:
        # No command supplied
        # Inform user on the available commands when running the app

        click.echo("Specify one of the commands below:")
        click.echo("----------------------------------")
        print(*group_commands, sep='\n')

    ctx.obj = {
        'VERBOSE': verbose
    }



## Add command groups
main.add_command(ec2_commands)
main.add_command(ecr_commands)
main.add_command(container_commands)
main.add_command(init_commands)
main.add_command(run_commands)
