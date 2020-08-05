import boto3
from .configuration import config, profile

def get_boto_session():
    aws_config = None
    aws_config = config.get_provider("aws")

    if aws_config["profile_name"] is not None:
        return boto3.Session(profile_name=aws_config['profile_name'])

    elif 'access_key' in aws_config and 'secret_key' in aws_config:
        if aws_config['access_key'] is None or aws_config['secret_key'] is None:
            raise Exception("both 'secret_key' and 'access_key' has to be set.")

        # Otherwise return the boto session
        return boto3.Session(aws_access_key_id=aws_config['access_key'],
                             aws_secret_access_key=aws_config['secret_key'])

    else:
        return boto3.Session()

def generate_tags(name :str):
    #TODO: Check if aws or Google
    return [{'Key': 'Name', 'Value': name},
            {'Key': 'origin', 'Value': 'rixtribute'},
            {'Key': 'origin-email', 'Value': profile.email},
            {'Key': 'origin-name', 'Value': profile.name}]

