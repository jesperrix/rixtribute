import sys
import os
import click
import pandas as pd
from tabulate import tabulate
import glob

from rixtribute import container_utils
from rixtribute.configuration import config, profile
from rixtribute.ec2 import EC2, EC2Instance
from rixtribute.ecr import ECR

@click.group(short_help="ec2 server commands", invoke_without_command=True)
@click.pass_context
def ec2(ctx):
    group_commands = ec2.list_commands(ctx)

    if ctx.invoked_subcommand is None:
        # No command supplied
        # Inform user on the available commands when running the app

        click.echo("Specify one of the commands below:")
        click.echo("----------------------------------")
        print(*group_commands, sep='\n')
    pass

@ec2.command(short_help="List instances")
@click.pass_context
@click.option('--all', '-a', is_flag=True, help="list all instances")
def list_instances(ctx, all):
    """ List instances """
    ec2_instances = EC2.list_instances(profile, all)

    print(tabulate(pd.DataFrame([instance.get_printable_dict() for instance in ec2_instances]), headers='keys'))

@ec2.command(short_help="Start an instance")
@click.pass_context
def start(ctx):
    """ Start an instance from rxtb-config.yaml instance section"""
    cfg_instances = config.get_instances().copy()
    # Drop config from instanes
    [x.pop("config", None) for x in cfg_instances]

    print("Instances from configuration file:")
    print(tabulate(pd.DataFrame(cfg_instances), headers='keys'))

    # n = int(input("Choose instance to start: "))
    n = int(click.prompt("Choose instance to start"))

    print(f"starting instance {n}...")
    instance_cfg = config.get_instance(cfg_instances[n]["name"])

    # Docker container
    docker_container_name = instance_cfg.get('container', None)
    if docker_container_name is not None:
        container_cfg = config.get_container(docker_container_name)
        print("Instance has a docker container")

        # BUILD docker image
        container_utils.docker_build_from_cfg(container_cfg)

        # Get or Create repo
        repo = ECR.get_repository(container_cfg['tag'])
        if repo is None:
            repo = ECR.create_repository(container_cfg['tag'])

        # Get docker image
        docker_image = container_utils.docker_image_get(f"{container_cfg['tag']}:latest")
        if docker_image is None:
            print("image not built, run: rxtb container build")
            sys.exit()

        # Login to docker
        auth_config = ECR.get_auth_token()

        # Tag image, then push it
        docker_image.tag(repo.repository_uri, 'latest')
        container_utils.docker_push(repo.repository_uri, 'latest', auth_config)

    if instance_cfg['provider'] == "aws":
        if instance_cfg['config']["spot"] is True:
            EC2.create_spot_instance(instance_cfg)
        else:
            # TODO START NON-SPOT INSTANCE
            pass

@ec2.command(short_help="Stop a running instance")
@click.pass_context
def stop(ctx):
    """Stop a running instance"""
    ec2_instances = EC2.list_instances(profile, all)

    if len(ec2_instances) <= 0:
        print("You have no instances running")
        sys.exit(0)

    print(tabulate(pd.DataFrame([instance.get_printable_dict() for instance in ec2_instances]), headers='keys'))

    n = int(click.prompt("Choose instance to stop"))

    print(f"stopping instance {n}...")
    ec2_instances[n].terminate()


@ec2.command(short_help="SSH into an instance")
@click.pass_context
def ssh(ctx):
    """SSH into an instance"""
    ec2_instances = EC2.list_instances(profile, all)

    print(tabulate(pd.DataFrame([instance.get_printable_dict() for instance in ec2_instances]), headers='keys'))

    n = int(click.prompt("Choose instance to ssh into"))

    ec2_instances[n].ssh()

    # host = ec2_instances[n].public_dns
    # port = 22
    # user = EC2.determine_ec2_user_from_image_id(ec2_instances[n].image_id)

    # # host = "ec2-52-214-34-243.eu-west-1.compute.amazonaws.com"
    # # connect(host, user, 22, '/home/jri/.ssh/jesper_ssh.pem')
    # # __import__('pdb').set_trace()
    # connect(host, user)
    # pass

@ec2.command(short_help="List available regions")
@click.pass_context
def list_regions(ctx):
    """ List available regions """
    regions = EC2.list_regions()
    print(tabulate(pd.DataFrame(regions, columns=["region"]), headers='keys'))

@ec2.command(short_help="List spot prices")
@click.option('--region', '-r', 'regions_', multiple=True, type=str)
@click.option('--instance-type', '-i', 'instance_types_', multiple=True, type=str)
@click.pass_context
def list_spot_pricing(ctx, regions_, instance_types_):
    """List pricing on spot instances

    Examples:

      rxtb ec2 list-spot-pricing --region eu-west-1 --instance-type m5.xlarge

      rxtb ec2 list-spot-pricing --region eu-west-1 --region eu-west-2 --instance-type m5.xlarge
    """
    # get all regions
    regions = regions_
    instance_types = instance_types_
    available_regions = EC2.list_regions()
    if regions:

        # Invalid region if not in regions
        for region in regions:
            if region not in available_regions:
                print(f"Error: region={region} is not a valid region, valid regions are: {regions}")
                sys.exit(2)
        regions = list(regions)
    else:
        regions = available_regions

    instance_types = list(instance_types)

    click.echo(f'Getting spot instance prices for: {instance_types}\n')

    spot_prices = EC2.list_spot_prices(instance_types, regions)
    ondemand_prices = EC2.list_prices(instance_types=instance_types, region_names=regions)
    # __import__('pdb').set_trace()

    ## Merge spot and ondemand prices for displaying

    df_spot_prices = pd.DataFrame(spot_prices)
    df_prices = pd.DataFrame(ondemand_prices)

    # zone to region
    import string
    df_spot_prices['region-name'] = df_spot_prices["zone"].apply(lambda x: x.rstrip(string.ascii_letters))
    df_spot_prices = df_spot_prices.merge(df_prices, on=["region-name","instance-type"], suffixes=('-spot', '-ondemand'))

    df_spot_prices["price-reduction"] = df_spot_prices["price-ondemand"] - df_spot_prices["price-spot"]
    df_spot_prices["price-reduction-percent"] = (1 - (df_spot_prices["price-spot"] / df_spot_prices["price-ondemand"])) *100
    df_spot_prices["price-reduction-percent"].apply(lambda x: f"{x:.2f}")
    df_spot_prices = df_spot_prices.drop(columns=["region-name"])
    df_spot_prices.columns = ["zone","price-spot","instance-type","price-ondemand","price-reduction","price-reduction-percent"]
    df_spot_prices = df_spot_prices[["zone","instance-type","price-spot","price-ondemand","price-reduction","price-reduction-percent"]]

    df_spot_prices = df_spot_prices.sort_values(["instance-type","price-spot"], ascending=True).reset_index(drop=True)
    group = df_spot_prices.groupby('instance-type')
    for x in group.groups:
        tmp_df = group.get_group(x).reset_index(drop=True)
        print(tabulate(tmp_df, headers='keys'))


@ec2.command(short_help="SCP files to/from instance")
@click.option('--recursive', '-r', is_flag=True)
@click.argument('source', nargs=1)
@click.argument('dest', nargs=1)
@click.pass_context
def scp(ctx, recursive, source, dest):
    """\b SCP files to/from instance

    use server:/file/path.txt to select instance from running instances

    In some terminals globs are expanded, therefore put them in "" like: ".dir/**/*.py"

    Examples:

      rxtb ec2 scp /path/to/source.txt server:/path/to/dest.txt

      rxtb ec2 scp server:/path/to/source.txt /path/to/dest.txt

      rxtb ec2 scp /path/to/dest.txt ec2-user@ec2-34-255-217-225.eu-west-1.compute.amazonaws.com:~/workdir/
    """

    if ':' not in source and ':' not in dest:
        print("No server in source or destination, either use 'server:' or 'user@dns:' to denote server.")
        sys.exit()

    paths = [source, dest]
    remote_path_index = 0
    # Convert local path to absolute path
    for i, path in enumerate(paths):
        if ':' not in path:
            paths[i] = os.path.abspath(path)
        else:
            remote_path_index = i

    ## select or find matching EC2 Instance

    if 'server:' in paths[remote_path_index]:
        ec2_instances = EC2.list_instances(profile, all)
        print(tabulate(pd.DataFrame([instance.get_printable_dict() for instance in ec2_instances]), headers='keys'))

        n = int(click.prompt("Choose server to cp to"))
        ec2_instance = ec2_instances[n]

        tmp_remote_path = paths[remote_path_index]
        new_remote = f"{ec2_instance.get_username()}@{ec2_instance.public_dns}"
        paths[remote_path_index] = f"{new_remote}:{tmp_remote_path.split(':')[-1]}"

        if ctx.obj["VERBOSE"]:
            print(f'substituting remote: "server:" -> "{new_remote}"')
    else:
        dns_name = paths[remote_path_index].split(':')[0].split('@')[-1]
        ec2_instance = EC2.get_instance_from_dns_name(dns_name)

        if ec2_instance is None:
            print("No instances with dns_name={dns_name}")
            sys.exit()

    source, dest = paths

    # Verbose
    if ctx.obj["VERBOSE"]:
        print("files:")
        print(f" {source}")

        print("destination:")
        print(f" {dest}")

    if not ec2_instance.scp(source=source, dest=dest, recursive=recursive):
        sys.exit(1)

@ec2.command(short_help="Copy files to instance")
@click.option('--recursive', '-r', is_flag=True)
@click.argument('files', nargs=-1, type=click.Path(exists=True))
@click.pass_context
def copy_to(ctx, recursive, files):
    """\b Copy files to instance workdir

    In some terminals globs are expanded, therefore put them in "" like: ".dir/**/*.py"

    Examples:

      rxtb ec2 copy-to file1 /path/to/file2\n

      rxtb ec2 copy-to -r path/to/dir
    """

    ec2_instances = EC2.list_instances(profile, all)
    print(tabulate(pd.DataFrame([instance.get_printable_dict() for instance in ec2_instances]), headers='keys'))

    n = int(click.prompt("Choose server to copy to"))
    ec2_instance = ec2_instances[n]

    files = list(files)

    if not ec2_instance.copy_files_to_workdir(files, recursive=recursive):
        sys.exit(1)

@ec2.command(short_help="Copy files from instance")
@click.option('--recursive', '-r', is_flag=True)
@click.option('--directory', '-d', help="output directory",
              default='.',
              type=click.Path(exists=True, dir_okay=True, file_okay=False))
@click.argument('files', nargs=-1, type=click.Path(exists=False))
@click.pass_context
def copy_from(ctx, recursive, directory, files):
    """\b Copy files from instance

    In some terminals globs are expanded, therefore put them in "" like: ".dir/**/*.py"

    Examples:

      rxtb ec2 copy-from file1 /path/to/file2

      rxtb ec2 copy-from -r path/to/dir

      rxtb ec2 copy-from -r -d /path/to/output_dir "*"

      rxtb ec2 copy-from -r -d output_dir path/to/output_dir
    """

    ec2_instances = EC2.list_instances(profile, all)
    print(tabulate(pd.DataFrame([instance.get_printable_dict() for instance in ec2_instances]), headers='keys'))

    n = int(click.prompt("Choose server to copy from"))
    ec2_instance = ec2_instances[n]

    files = list(files)

    if not ec2_instance.copy_files_from_workdir(files,
            recursive=recursive,
            dest=directory):
        sys.exit(1)


@ec2.command(help="List files in workdir")
@click.pass_context
def list_files(ctx):
    ec2_instances = EC2.list_instances(profile, all)
    print(tabulate(pd.DataFrame([instance.get_printable_dict() for instance in ec2_instances]), headers='keys'))

    n = int(click.prompt("Choose server to copy from"))
    ec2_instance = ec2_instances[n]
    ec2_instance.list_files()

    # TODO:
    # PULL docker image
    # docker pull aws_account_id.dkr.ecr.us-west-2.amazonaws.com/amazonlinux:latest

@ec2.command(help="Run command")
@click.pass_context
def cmd(ctx):
    ec2_instances = EC2.list_instances(profile, all)
    print(tabulate(pd.DataFrame([instance.get_printable_dict() for instance in ec2_instances]), headers='keys'))

    n = int(click.prompt("Choose server to copy from"))
    print(n)
    # ec2_instance = ec2_instances[n]
    # ec2_instance.list_files()
