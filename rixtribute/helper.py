import boto3
import urllib.request
from .configuration import config, profile
from typing import List
import uuid

def get_boto_session(region_name :str=None):
    provider = config.get_provider()
    aws_config = provider["config"]

    if aws_config["profile_name"] is not None:
        return boto3.Session(profile_name=aws_config['profile_name'], region_name=region_name)

    elif 'access_key' in aws_config and 'secret_key' in aws_config:
        if aws_config['access_key'] is None or aws_config['secret_key'] is None:
            raise Exception("both 'secret_key' and 'access_key' has to be set.")

        # Otherwise return the boto session
        return boto3.Session(aws_access_key_id=aws_config['access_key'],
                             aws_secret_access_key=aws_config['secret_key'],
                             region_name=region_name)

    else:
        return boto3.Session(region_name=region_name)

def generate_tags(name :str):
    #TODO: Check if aws or Google
    project_name = config.get_project()["name"]
    return [{'Key': 'Name', 'Value': name},
            {'Key': 'project', 'Value': project_name},
            {'Key': 'origin', 'Value': 'rixtribute'},
            {'Key': 'origin-email', 'Value': profile.email},
            {'Key': 'origin-name', 'Value': profile.name}]

def get_uuid_part_str() -> str:
    return str(uuid.uuid1()).split("-")[0]

def filter_list_of_dicts(l : List[dict], keys :list) -> List[dict]:
    """Filter dict keys in list of dictionaries.
    Args:
        l       : list of dicts
        filter  : name of keys to retain
    Returns:
        list : with filtered dicts
    """
    return [{k:v for k,v in x.items() if k in keys} for x in l]


def print_process():
    """ WIP: print interactively on the same line(s) """
    import time
    for i in range(20):
        time.sleep(.2)
        sys.stdout.write(f"{i:02}\r")
        sys.stdout.flush()

def get_external_ip() -> str:
    resp = urllib.request.urlopen('http://checkip.amazonaws.com/')
    if resp.status != 200:
        return ''
    return resp.read().decode("utf8").strip()
