import sys
import click
import boto3
from tabulate import tabulate
import pandas as pd
from .ec2 import EC2
import boto3
import base64
from .configuration import config, profile

@click.group()
def main():
    pass

@click.command()
@click.option('--all', is_flag=True, help="list all instances")
def list(all):
    session = boto3.Session(profile_name="ebdev")
    client = session.client("ec2")

    if all is True:
        response = client.describe_instances()
    else:
        response = client.describe_instances(
            Filters = [
                {'Name': 'tag:origin', 'Values': ['rixtribute',]},
                {'Name': 'tag:origin-email', 'Values': [profile.email,]},
                {'Name': 'tag:origin-name', 'Values': [profile.name,]},
            ]
        )

    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    instances = []
    for reservation in response["Reservations"]:
        for instance in reservation["Instances"]:
            instances.append(EC2.parse_boto_obj(instance))

    print(tabulate(pd.DataFrame(instances), headers='keys', showindex=False))

@click.command()
def run():
    print("Run..")
    print(config.get_provider("aws"))

@click.command()
def start():
    instances = config.get_instances().copy()
    # Drop config from instanes
    [x.pop("config", None) for x in instances]

    print("Specified instances:")
    print(tabulate(pd.DataFrame(instances), headers='keys'))

    n = int(input("Choose instance to start: "))

    print(f"starting instance {n}...")
    instance_cfg = config.get_instance(instances[n]["name"])

    if instance_cfg['provider'] == "aws":
        if instance_cfg['config']["spot"] is True:
            EC2.create_spot_instance(instance_cfg, profile)



main.add_command(list)
main.add_command(run)
main.add_command(start)
