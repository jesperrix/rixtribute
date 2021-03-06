import datetime
import tempfile
import copy
import boto3
import botocore
from rixtribute.helper import get_boto_session, generate_tags, get_external_ip, get_uuid_part_str
from rixtribute import aws_helper
import base64
import os
from typing import List, Optional, Tuple
from rixtribute import ssh
from rixtribute.configuration import config
from rixtribute.ecr import ECR
# from rixtribute.ssh import (
    # ssh as _ssh,
    # scp as _scp,
    # ssh_command as _ssh,
import json
from enum import Enum

# For typing and auto-completion
try:
    if TYPE_CHECKING is not None:
        from .configuration import ProfileParser
except NameError as e:
    pass

class IpProtocol(Enum):
    TCP = 'tcp'
    UDP = 'udp'
    ICMP = 'icmp'

class EC2Instance(object):
    def __init__(self, boto_instance_dict :dict):
        self.instance_name = ''
        try:
            for tag in boto_instance_dict["Tags"]:
                key = tag["Key"]
                value = tag["Value"]
                if key == 'Name':
                    self.instance_name = value
        except KeyError as e:
            pass


        self.instance_id :str = boto_instance_dict.get("InstanceId", '')
        self.image_id :str = boto_instance_dict.get("ImageId", '')
        self.instance_type :str = boto_instance_dict.get("InstanceType", '')
        self.status :str = boto_instance_dict.get("State", {}).get("Name", '')
        self.ssh_port :int = 22

        self.workdir = "/workdir"

        self.uptime = datetime.datetime.utcnow()-boto_instance_dict["LaunchTime"].replace(tzinfo=None)
        if self.status != "running": self.uptime = ''

        self.spot_request_id :str = boto_instance_dict.get("SpotInstanceRequestId", '')
        # Spot or not
        self.instance_lifecycle :str = boto_instance_dict.get("InstanceLifecycle", '')
        self.public_dns :str =  boto_instance_dict.get("PublicDnsName", '')

    def get_printable_dict(self):
        keys = [
                "instance_name",
                "instance_id",
                "status",
                "uptime",
                "instance_lifecycle",
                "instance_type",
                "public_dns"
        ]
        return {k: getattr(self, k) for k in keys if k in keys}

    def cancel_spot_request(self):
        EC2.cancel_spot_instance_request(self.spot_request_id)

    def stop(self):
        session = get_boto_session()
        client = session.client("ec2")

        print(f"Stopping name/id: {self.instance_name}/{self.instance_id}")

        # Handle spot requests seperately
        if self.spot_request_id:
            print(f"this is a spot instance, cancelling spot request: {self.spot_request_id}")
            self.cancel_spot_request()

        res = client.stop_instances(
            InstanceIds=[self.instance_id]
        )

        if res and res["ResponseMetadata"]["HTTPStatusCode"] != 200:
            raise Exception(f"Error when trying to stop {self.instance_id}")

        print("Wait for instance to stop..")

        waiter = client.get_waiter('instance_stopped')
        waiter.wait(
            InstanceIds=instance_ids,
            WaiterConfig={
                'Delay': 5,
                'MaxAttempts': 100}
        )

    def terminate(self):
        session = get_boto_session()
        client = session.client("ec2")

        print(f"Terminating name/id: {self.instance_name}/{self.instance_id}")

        if self.spot_request_id:
            print(f"this is a spot instance, cancelling spot request: {self.spot_request_id}")
            self.cancel_spot_request()

        res = client.terminate_instances(
            InstanceIds=[self.instance_id]
        )

        if res and res["ResponseMetadata"]["HTTPStatusCode"] != 200:
            raise Exception(f"Error when trying to terminate {self.instance_id}")

        print("Wait for instance to terminate..")
        waiter = client.get_waiter('instance_terminated')
        waiter.wait(
            InstanceIds=[self.instance_id],
            WaiterConfig={
                'Delay': 5,
                'MaxAttempts': 100}
        )

    def get_username(self):
        user = EC2.determine_ec2_user_from_image_id(self.image_id)
        return user

    def ssh(self):
        # key = None
        # key = "/home/jri/.ssh/jesper_ssh.pem"
        key = config.get_ssh_key()["private_key"]
        user = self.get_username()
        ssh.ssh(host=self.public_dns, user=user, port=self.ssh_port, key_str=key)

    def docker_run(self, cmd :str=None):
        key = config.get_ssh_key()["private_key"]
        user = self.get_username()
        docker_gpu = '$(nvidia-smi --list-gpus > /dev/null && echo "--gpus=all")'
        if cmd != None:
            f = tempfile.NamedTemporaryFile(suffix='_temp', prefix='rxtb_', delete=True)
            f.write(f"#!/bin/sh\n".encode("utf8"))
            f.write(cmd.encode("utf8"))
            f.flush()
            cmd_file_abs_path = f.name
            cmd_file_name = os.path.basename(cmd_file_abs_path)

            # SCP the command file
            self.copy_files_to_tmp([cmd_file_abs_path])

            cmd_str = (
                f'docker run --rm -v /tmp/{cmd_file_name}:/cmd.sh --entrypoint="" {docker_gpu} $DOCKER_IMAGE bash '
                f"/cmd.sh"
            )
        else:
            cmd_str = "docker run --rm "+docker_gpu+" $DOCKER_IMAGE"

        # cmd = "docker run --gpus=all $DOCKER_IMAGE"
        ssh.ssh_command_tmux(host=self.public_dns, command=cmd_str, user=user, port=self.ssh_port, key_str=key)

    def copy_files_to_tmp(self, files :List[str], recursive :bool=False):
        key = config.get_ssh_key()["private_key"]
        user = self.get_username()
        dest = f"{user}@{self.public_dns}:/tmp/"

        success = ssh.scp(source=files,
                          dest=dest,
                          recursive=recursive,
                          port=self.ssh_port,
                          key_str=key)
        return success

    def copy_files_to_workdir(self, files :List[str], recursive :bool=False):
        key = config.get_ssh_key()["private_key"]
        user = self.get_username()
        dest = f"{user}@{self.public_dns}:{self.workdir}"

        success = ssh.scp(source=files,
                          dest=dest,
                          recursive=recursive,
                          port=self.ssh_port,
                          key_str=key)
        return success

    def copy_files_from_workdir(self, source :List[str], recursive :bool, dest :str='.'):
        """ Copy files from the instance workdir """
        key = config.get_ssh_key()["private_key"]
        key = None
        user = self.get_username()
        source_prefix = f"{user}@{self.public_dns}:"

        for i, path in enumerate(source):
            source[i] = source_prefix + os.path.join(self.workdir, path)

        success = ssh.scp(source=source,
                          dest=dest,
                          recursive=recursive,
                          port=self.ssh_port,
                          key_str=key)
        return success


    def list_files(self):
        user = self.get_username()
        host = self.public_dns
        key = None
        ssh.ssh_command(host=host,
                        user=user,
                        command=f"ls -1a {self.workdir}/",
                        port=self.ssh_port,
                        key=key,
                        print_output=True)




class EC2(object):

    def __init__(self, boto_object):
        """ STATIC class used as API """
        pass

    @staticmethod
    def encode_userdata(data :str):
        return base64.b64encode(data.encode('utf-8')).decode('utf-8')

    @staticmethod
    def determine_ec2_user_from_image_id(image_id :str):
        session = get_boto_session()
        client = session.client("ec2")

        res = client.describe_images(
            Filters = [
                {'Name': 'image-id', 'Values': [image_id,]},
            ])

        if res and res["ResponseMetadata"]["HTTPStatusCode"] != 200:
            raise Exception(f"Error in ami lookup '{image_id}")

        image_name = res['Images'][0]['Name']

        #see https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/connection-prereqs.html
        #####################################
        # Distro       # username
        #####################################
        # Amazon Linux # ec2-user
        # Debian       # admin
        # Fedora       # ec2-user or fedora
        # RHEL         # ec2-user or root
        # SUSE         # ec2-user or root
        # Ubuntu       # ubuntu
        # CentOS       # centos
        #####################################
        if 'amazon linux' in image_name.lower() or 'amzn2-ami' in image_name.lower():
            return "ec2-user"
        if 'centos' in image_name.lower():
            return "centos"
        elif 'debian' in image_name.lower():
            return "admin"
        elif 'fedora' in image_name.lower():
            return "fedora"
        elif 'rhel' in image_name.lower() or 'red hat' in image_name.lower():
            return "ec2-user"
        elif 'suse' in image_name.lower():
            return "ec2-user"
        elif 'ubuntu' in image_name.lower():
            return "ubuntu"
        else:
            raise Exception(f"Unknown ami, {image_id}")

    @classmethod
    def _get_session(cls, region_name :str=None):
        session = get_boto_session(region_name=region_name)
        return session

    @classmethod
    def _get_ec2_boto_client(cls, region_name :str=None):
        session = cls._get_session(region_name=region_name)
        client = session.client("ec2")
        return client

    #########################
    #  BOTO3 API functions  #
    #########################

    @classmethod
    def list_instances(cls, profile, all=False) -> List[EC2Instance]:
        client = cls._get_ec2_boto_client()

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
                instances.append(EC2Instance(instance))

        return instances

    @classmethod
    def get_instance_from_dns_name(cls, dns_name :str) -> Optional[EC2Instance]:
        client = cls._get_ec2_boto_client()

        response = client.describe_instances(
            Filters = [
                {'Name': 'dns-name', 'Values': [dns_name]},
            ]
        )

        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

        instances = []
        for reservation in response["Reservations"]:
            for instance in reservation["Instances"]:
                instances.append(EC2Instance(instance))

        try:
            return instances[0]
        except IndexError as e:
            return None

        return instances[0]

    @classmethod
    def list_regions(cls) -> List[str]:
        ec2 = EC2._get_ec2_boto_client()
        response = ec2.describe_regions()

        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

        return [row['RegionName'] for row in response['Regions']]


    @classmethod
    def list_spot_prices(cls,
                         instance_types: List[str],
                         region_names :List[str],
                         start_dt :datetime.datetime=None,
                         end_dt :datetime.datetime=None,
                         range_dt :datetime.timedelta=None
                         ) -> List[dict]:
        """ Get spot pricing for instance_types in regions
        valid usage:
            start_dt
            start_dt and end_dt
            range_dt
            (No dt or range) latest 3 hours
        Args:
            None
            instance_types  list of instance type e.g. m5.xlarge
            region_names    list of regions
            start_dt        (optional) start datetime for spot pricing window
            end_dt          (optional) end datetime for spot pricing window
            range_dt        (optional) range timedelta from now for spot pricing window
        Returns:
            dict with pricing info
        """
        params :dict = {
            "InstanceTypes": instance_types,
            "ProductDescriptions": ['Linux/UNIX'],
        }

        if range_dt is not None:
            now = datetime.datetime.today()
            params["StartTime"] = now - range_dt
            params["EndTime"] = now
        elif start_dt is not None or end_dt is not None:
            if start_dt is not None: params["StartTime"] = start_dt
            if end_dt is not None: params["EndTime"] = end_dt
        else:
            # 3 hours window
            params["StartTime"] = datetime.datetime.today() - datetime.timedelta(hours=3)

        # if VERBOSE:
            # print(params)

        prices_l :List[dict] = list()
        for region_name in region_names:
            ec2 = cls._get_ec2_boto_client(region_name=region_name)

            response = ec2.describe_spot_price_history(**params)

            assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

            for item in response['SpotPriceHistory']:
                prices_l.append({
                    "zone":  item['AvailabilityZone'],
                    "price": float(item['SpotPrice']),
                    "instance-type": item['InstanceType'],
                })

        return prices_l

    @classmethod
    def list_prices(cls, instance_types :List[str], region_names :List[str]) -> List[dict]:
        """Return list of prices for instance_type
        Args:
            instance_types  : types of ec2 instances e.g. ['p3.8xlarge']
            region_names    : list of region codes e.g ['us-east-1', 'eu-west-1']
        Returns:
            list of dicts:
                [{'region_name': 'eu-west-1',
                  'instance_type': 'p3.8xlarge',
                  'price': 13.22},]
        """
        # pricing = cls._get_session(region_name="us-east-1").client("pricing")
        pricing = EC2._get_session(region_name="us-east-1").client("pricing")

        region_names = [aws_helper.region_name_to_region_code(x) for x in region_names]

        # region = aws_helper.region_code_to_region_name(region_name)
        # region1 = aws_helper.region_code_to_region_name("eu-west-2")
        # locations
        # locations = pricing.get_attribute_values(ServiceCode="AmazonEC2",AttributeName="location")
        # locations["AttributeValues"]
        prices_l :list = []

        for instance_type in instance_types:
            response = pricing.get_products(
                ServiceCode='AmazonEC2',
                Filters=[
                    {'Type': 'TERM_MATCH', 'Field': 'operatingSystem', 'Value': 'Linux'},
                    # {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': region},
                    {'Type': 'TERM_MATCH', 'Field': 'capacitystatus', 'Value': 'UnusedCapacityReservation'},
                    {'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': instance_type},
                    {'Type': 'TERM_MATCH', 'Field': 'tenancy', 'Value': 'Shared'},
                    {'Type': 'TERM_MATCH', 'Field': 'preInstalledSw', 'Value': 'NA'}
                ],
            )

            assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

            # Run through price list and return filter locations
            for price_elm in response['PriceList']:
                elm = json.loads(price_elm)
                location = elm['product']['attributes']['location']
                instance_type = elm['product']['attributes']['instanceType']
                if location in region_names:
                    on_demand = json.loads(price_elm)['terms']['OnDemand']

                    # Example of price element:
                    # {'F78KERDK968ABWNU.JRTCKXETXF': {
                        # 'priceDimensions': {
                            # 'F78KERDK968ABWNU.JRTCKXETXF.6YS6EN2CT7': {
                                # 'unit': 'Hrs',
                                # 'endRange': 'Inf',
                                # 'description': '$13.22 per Unused Reservation Linux p3.8xlarge Instance Hour',
                                # 'appliesTo': [],
                                # 'rateCode': 'F78KERDK968ABWNU.JRTCKXETXF.6YS6EN2CT7',
                                # 'beginRange': '0',
                                # 'pricePerUnit': {'USD': '13.2200000000'}
                            # }
                        # },
                        # 'sku': 'F78KERDK968ABWNU',
                        # 'effectiveDate': '2020-10-01T00:00:00Z',
                        # 'offerTermCode': 'JRTCKXETXF',
                        # 'termAttributes': {}
                    # }}

                    # NOTE: hack to get into pricePerUnit since keys are obscure
                    key1 = list(on_demand.keys())[0]
                    key2 = list(on_demand[key1]['priceDimensions'].keys())[0]
                    price = on_demand[key1]['priceDimensions'][key2]['pricePerUnit']['USD']

                    prices_l.append({"region-name": aws_helper.region_code_to_region_name(location),
                                   "instance-type": instance_type,
                                   "price": float(price)})

        return prices_l

    # @staticmethod
    # def lookup_ami(image_id :str):
        # session = get_boto_session()
        # client = session.client("ec2")
        # res = client.describe_images(
            # Filters = [
                # {'Name': 'image-id', 'Values': ['ami-0d30ddc9d3cc48bac',]},
            # ])

        # client.describe_images(
            # Filters = [
                # {'Name': 'image-id', 'Values': ['ami-036f665a5b53a18ce',]},
            # ])

    @staticmethod
    def create_spot_instance(instance_cfg :dict):
        session = get_boto_session()
        client = session.client("ec2")

        cfg = instance_cfg["config"]
        region_name = aws_helper.strip_to_region(cfg['region'])
        instance_username = EC2.determine_ec2_user_from_image_id(cfg["ami"])

        # TODO: if no key then create a key and use it

        # TODO start and test env variables
        aws_access_key = session.get_credentials().access_key
        aws_secret_key = session.get_credentials().secret_key
        aws_default_region = session.region_name

        user_data = (
            f"#!/usr/bin/env bash\n"
            f'su - {instance_username} <<AAA\n'
            f'echo "export TERM=xterm-256color" >> ~/.bashrc\n'
            f'echo "source /home/{instance_username}/.profile" >> ~/.bashrc\n'
            f'echo "export AWS_ACCESS_KEY_ID={aws_access_key}" >> ~/.profile\n'
            f'echo "export AWS_SECRET_ACCESS_KEY={aws_secret_key}" >> ~/.profile\n'
            f'echo "export AWS_DEFAULT_REGION={aws_default_region}" >> ~/.profile\n'
            f'echo "set-option -g allow-rename off" > ~/.tmux.conf\n'
            f'mkdir ~/workdir\n'
            f'AAA\n'
            f'source /home/{instance_username}/.profile\n'
            f'ln -s /home/{instance_username}/workdir /workdir\n'
        )

        # IF container then add it to userdata
        container_name = instance_cfg.get('container', None)
        if container_name:
            container_cfg = config.get_container(container_name)
            repo = ECR.get_repository(container_cfg['tag'], region_name=region_name)
            if repo is not None:
                user_data += (
                    f'su - {instance_username} <<AAA\n'
                    f'echo "DOCKER_IMAGE=\"{repo.repository_uri}:latest\"" >> ~/.profile\n'
                    f'$(aws ecr get-login --no-include-email --region {region_name})\n'
                    f'docker pull {repo.repository_uri}:latest\n'
                    f'source /home/{instance_username}/.profile\n'
                    f'AAA\n'
                )

        encoded_user_data = EC2.encode_userdata(user_data)
        security_group_id = EC2.get_or_create_security_group(instance_cfg["name"])
        EC2.update_ingress_rules(security_group_id, cfg["ports"])
        ssh_key_name = EC2.get_valid_key_pair_name()


        name = instance_cfg["name"] + "-" + get_uuid_part_str()
        response = client.request_spot_instances(
            InstanceCount=1,
            LaunchSpecification={
                'ImageId': cfg['ami'],
                'InstanceType': cfg['type'],
                'KeyName': ssh_key_name,
                'Placement': {
                    'AvailabilityZone': cfg['region'],
                },
                # 'Monitoring': {
                    # 'Enabled': True,
                # },
                'SecurityGroupIds': [
                    security_group_id,
                ],
                'BlockDeviceMappings': [
                    {'DeviceName': x['devname'],
                     'Ebs': {
                        'DeleteOnTermination': True,
                        'VolumeSize': x['size']
                      }
                    } for x in cfg['volumes']
                ],
                'UserData': encoded_user_data,
            },
            TagSpecifications=[
                {'ResourceType': 'spot-instances-request',
                 'Tags': generate_tags(name),
                },
            ],
            Type='persistent',
            InstanceInterruptionBehavior='stop',
        )
        request_id = response['SpotInstanceRequests'][0]['SpotInstanceRequestId']

        print("Wait for request to be fulfilled...")
        waiter = client.get_waiter('spot_instance_request_fulfilled')
        waiter.wait(
            SpotInstanceRequestIds=[request_id,],
            WaiterConfig={
                'Delay': 5,
                'MaxAttempts': 100,
            }
        )

        response = client.describe_spot_instance_requests(SpotInstanceRequestIds=[request_id,])
        instance_id = response['SpotInstanceRequests'][0]['InstanceId']

        response = client.create_tags(
            Resources=[instance_id,],
            Tags=generate_tags(name),
        )

        if response and response["ResponseMetadata"]["HTTPStatusCode"] != 200:
            raise Exception(f"Error when adding tags to instance_id: {instance_id}")

        print("Wait for instance to start..")
        waiter = client.get_waiter('instance_status_ok')
        waiter.wait(
            InstanceIds=[instance_id,],
            WaiterConfig={
                'Delay': 5,
                'MaxAttempts': 100}
        )

    @staticmethod
    def cancel_spot_instance_request(spot_request_id: str):
        session = get_boto_session()
        client = session.client("ec2")

        response = client.cancel_spot_instance_requests(
            SpotInstanceRequestIds=[spot_request_id]
        )

        if response and response["ResponseMetadata"]["HTTPStatusCode"] != 200:
            raise Exception(f"Error when trying to stop {spot_request_id}")

        print("Wait for spot request(s) to cancel..")
        waiter = client.get_waiter('spot_instance_request_fulfilled')
        waiter.wait(
            SpotInstanceRequestIds=[spot_request_id,],
            WaiterConfig={
                'Delay': 5,
                'MaxAttempts': 100,
            }
        )

    @staticmethod
    def create_security_group(instance_name :str) -> str:
        session = get_boto_session()
        client = session.client("ec2")

        # NOTE groupNames are prefixed with: "rxtb-"
        response = client.create_security_group(
            Description="Created from rxtb",
            GroupName=f"rxtb-{instance_name}",
            TagSpecifications=[
                {'ResourceType': 'security-group',
                 'Tags': generate_tags(instance_name),
                },
            ],
        )

        if response and response["ResponseMetadata"]["HTTPStatusCode"] != 200:
            raise Exception(f"Error when trying to create a security_group")

        group_id = response["GroupId"]
        return group_id

    @staticmethod
    def get_or_create_security_group(instance_name :str) -> str:
        session = get_boto_session()
        client = session.client("ec2")

        # NOTE groupNames are prefixed with: "rxtb-"
        response = client.describe_security_groups(
            Filters=[
                {
                    'Name': 'group-name',
                    'Values': [
                        f"rxtb-{instance_name}",
                    ]
                },
            ]
        )

        if response and response["ResponseMetadata"]["HTTPStatusCode"] != 200:
            raise Exception(f"Error when trying to create a security_group")

        if len(response["SecurityGroups"]) <= 0:
            print("Creating sg")
            group_id = EC2.create_security_group(instance_name)
        else:
            group_id = response["SecurityGroups"][0]["GroupId"]

        return group_id

    @staticmethod
    def update_ingress_rules(security_group_id :str, ports :List[dict]):
        """Update ingress rules
        Args:
            security_group_id : security group id
            ports             : list of ports in format: {"port": 22, "protocol": "tcp"}
        Returns:
            None
        """
        session = get_boto_session()
        security_group = session.resource("ec2").SecurityGroup(security_group_id)

        ports = copy.deepcopy(ports)

        public_ip_range = get_external_ip() + "/32"

        ip_permissions = security_group.ip_permissions

        for port in ports:
            match = False

            for rule in ip_permissions:
                for ip_range in rule["IpRanges"]:
                    if ip_range["CidrIp"] == public_ip_range:
                        ip_match = True

                if port["port"] == rule["FromPort"] and rule["IpProtocol"] == port["protocol"]:
                    match = True
                else:
                    match = False


            if match == False:
                print(f"adding ingress rule to security_group, port={port['port']}, protocol={port['protocol']}")
                security_group.authorize_ingress(
                    CidrIp=public_ip_range,
                    ToPort=port["port"],
                    FromPort=port["port"],
                    IpProtocol=port["protocol"],
                )

    @staticmethod
    def create_key_pair() -> Tuple[str, str]:
        """Create an SSH key-pair
        Args:
            None
        Returns:
            (key name, fingerprint)
        """
        session = get_boto_session()
        client = session.client("ec2")

        project_name = config.project_name

        response = client.create_key_pair(
            KeyName=f"rxtb-{get_uuid_part_str()}",
            TagSpecifications=[
                {'ResourceType': 'key-pair',
                 'Tags': generate_tags(project_name),
                },
            ],
        )

        if response and response["ResponseMetadata"]["HTTPStatusCode"] != 200:
            raise Exception(f"Error when trying to create a security_group")

        return (response["KeyName"], response["KeyMaterial"])

    @staticmethod
    def verify_key_pair_name(key_name :str) -> bool:
        session = get_boto_session()
        client = session.client("ec2")

        try:
            response = client.describe_key_pairs(
                KeyNames=[key_name],
            )
            if response and response["ResponseMetadata"]["HTTPStatusCode"] != 200:
                raise Exception(f"Error when trying to describe_key_pairs")
        except botocore.exceptions.ClientError as e:
            return False
        return True

    @staticmethod
    def get_valid_key_pair_name() -> str:
        # load existing key if any
        ssh_key_name = config.get_ssh_key().get("key_name", None)
        if ssh_key_name == None or EC2.verify_key_pair_name(ssh_key_name) == False:
            key_name, private_key = EC2.create_key_pair()
            config.add_ssh_key(key_name, private_key)
            ssh_key_name = key_name

        return ssh_key_name



"""
ssh ec2-user@ec2-18-203-155-39.eu-west-1.compute.amazonaws.com
BOTO OBJECT EXAMPLE
{'Groups': [],
 'Instances': [{'AmiLaunchIndex': 0,
   'ImageId': 'ami-003a0987ccad642ec',
   'InstanceId': 'i-092ecefa5e0781cfd',
   'InstanceType': 't2.micro',
   'KeyName': 'steffen-ssh-key',
   'LaunchTime': datetime.datetime(2019, 9, 5, 6, 25, 2, tzinfo=tzutc()),
   'Monitoring': {'State': 'disabled'},
   'Placement': {'AvailabilityZone': 'eu-west-1c',
    'GroupName': '',
    'Tenancy': 'default'},
   'PrivateDnsName': 'ip-172-31-5-209.eu-west-1.compute.internal',
   'PrivateIpAddress': '172.31.5.209',
   'ProductCodes': [],
   'PublicDnsName': '',
   'State': {'Code': 80, 'Name': 'stopped'},
   'StateTransitionReason': 'User initiated (2019-09-05 06:53:58 GMT)',
   'SubnetId': 'subnet-9b6255fe',
   'VpcId': 'vpc-c6c486a3',
   'Architecture': 'x86_64',
   'BlockDeviceMappings': [{'DeviceName': '/dev/sda1',
     'Ebs': {'AttachTime': datetime.datetime(2019, 9, 5, 6, 25, 3, tzinfo=tzutc()),
      'DeleteOnTermination': True,
      'Status': 'attached',
      'VolumeId': 'vol-0331b158407c04ebb'}}],
   'ClientToken': '',
   'EbsOptimized': False,
   'EnaSupport': True,
   'Hypervisor': 'xen',
   'NetworkInterfaces': [{'Attachment': {'AttachTime': datetime.datetime(2019, 9, 5, 6, 25, 2, tzinfo=tzutc()),
      'AttachmentId': 'eni-attach-0d55e48d960945264',
      'DeleteOnTermination': True,
      'DeviceIndex': 0,
      'Status': 'attached'},
     'Description': '',
     'Groups': [{'GroupName': 'launch-wizard-7',
       'GroupId': 'sg-09e76ae1c227db804'}],
     'Ipv6Addresses': [],
     'MacAddress': '02:36:28:a3:8f:30',
     'NetworkInterfaceId': 'eni-0a6a4fb64050fc8a4',
     'OwnerId': '293331033030',
     'PrivateDnsName': 'ip-172-31-5-209.eu-west-1.compute.internal',
     'PrivateIpAddress': '172.31.5.209',
     'PrivateIpAddresses': [{'Primary': True,
       'PrivateDnsName': 'ip-172-31-5-209.eu-west-1.compute.internal',
       'PrivateIpAddress': '172.31.5.209'}],
     'SourceDestCheck': True,
     'Status': 'in-use',
     'SubnetId': 'subnet-9b6255fe',
     'VpcId': 'vpc-c6c486a3',
     'InterfaceType': 'interface'}],
   'RootDeviceName': '/dev/sda1',
   'RootDeviceType': 'ebs',
   'SecurityGroups': [{'GroupName': 'launch-wizard-7',
     'GroupId': 'sg-09e76ae1c227db804'}],
   'SourceDestCheck': True,
   'StateReason': {'Code': 'Client.UserInitiatedShutdown',
    'Message': 'Client.UserInitiatedShutdown: User initiated shutdown'},
   'Tags': [{'Key': 'Name', 'Value': 'steffen-rstudio-test'}],
   'VirtualizationType': 'hvm',
   'CpuOptions': {'CoreCount': 1, 'ThreadsPerCore': 1},
   'CapacityReservationSpecification': {'CapacityReservationPreference': 'open'},
   'HibernationOptions': {'Configured': False},
   'MetadataOptions': {'State': 'applied',
    'HttpTokens': 'optional',
    'HttpPutResponseHopLimit': 1,
    'HttpEndpoint': 'enabled'}}],
 'OwnerId': '293331033030',
 'ReservationId': 'r-0dd4d193f8704f1f8'}
"""

# To test
    #rxtb start
