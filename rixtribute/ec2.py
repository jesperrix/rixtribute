import datetime
from .helper import get_boto_session, generate_tags
import base64

# For typing and auto-completion
try:
    if TYPE_CHECKING is not None:
        from .configuration import ProfileParser
except NameError as e:
    pass

class EC2(object):

    def __init__(self, boto_object):
        self.instance_id = boto_object["Instances"]["InstanceId"]
        self.instance_type = boto_object["Instances"]["InstanceType"]
        self.public_dns = boto_object["Instances"]["PublicDnsName"]

        for tag in boto_object["Tags"]:
            key = tag["Key"]
            value = tag["Value"]
            if key == 'Name':
                self.instance_name = value

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
        print(image_name)

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
        if 'amazon linux' in image_name.lower():
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


    @staticmethod
    def lookup_ami(image_id :str):
        session = get_boto_session()
        client = session.client("ec2")
        res = client.describe_images(
            Filters = [
                {'Name': 'image-id', 'Values': ['ami-0d30ddc9d3cc48bac',]},
            ])

        client.describe_images(
            Filters = [
                {'Name': 'image-id', 'Values': ['ami-036f665a5b53a18ce',]},
            ])


    @staticmethod
    def parse_boto_obj(boto_object):
        d = dict()

        try:
            for tag in boto_object["Tags"]:
                key = tag["Key"]
                value = tag["Value"]
                if key == 'Name':
                    d["instance_name"] = value
        except KeyError as e:
            d["instance_name"] = ''


        d["instance_id"] = boto_object["InstanceId"]
        d["status"] = boto_object["State"]["Name"]
        d["uptime"] = datetime.datetime.utcnow()-boto_object["LaunchTime"].replace(tzinfo=None)
        if d["status"] != "running":
            d["uptime"] = ''

        if "InstanceLifecycle" in boto_object and boto_object["InstanceLifecycle"]:
            d["spot"] = 'spot'
        else:
            d["spot"] = ''
        d["instance_type"] = boto_object["InstanceType"]
        d["public_dns"] =  boto_object["PublicDnsName"]

        return d

    @staticmethod
    def create_spot_instance(instance_cfg :dict, profile :"configuration.ProfileParser"):
        session = get_boto_session()
        client = session.client("ec2")

        cfg = instance_cfg["config"]

        instance_username = EC2.determine_ec2_user_from_image_id(cfg["ami"])

        # TODO: if no key then create a key and use it

        encoded = EC2.encode_userdata(f"""#!/usr/bin/env bash
        cat << EOF | su {instance_username}
        echo "export TERM=xterm-256color" >> ~/.bashrc
mkdir ~/workdir
echo "test" > ~/hello.txt
EOF""")

        if not 'volumes' in cfg or len(cfg['volumes']) == 0:
            cfg['volumes'] = [{'devname': '/dev/xvda', 'size': 50},]


        response = client.request_spot_instances(
            InstanceCount=1,
            LaunchSpecification={
                'ImageId': cfg['ami'],
                'InstanceType': cfg['type'],
                'KeyName': cfg['keyname'],
                'Placement': {
                    'AvailabilityZone': cfg['region'],
                },
                # 'Monitoring': {
                    # 'Enabled': True,
                # },
                'SecurityGroupIds': [
                    'sg-090c41c001c202249',
                ],
                'BlockDeviceMappings': [
                    {'DeviceName': x['devname'],
                     'Ebs': {
                        'DeleteOnTermination': True,
                        'VolumeSize': x['size']
                      }
                    } for x in cfg['volumes']
                ],
                'UserData': encoded,
            },
            TagSpecifications=[
                {'ResourceType': 'spot-instances-request',
                 'Tags': generate_tags(instance_cfg['name']),
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
            Tags=generate_tags(instance_cfg['name']),
        )

        print("Wait for instance to start..")
        waiter = client.get_waiter('instance_status_ok')
        waiter.wait(
            InstanceIds=[instance_id,],
            WaiterConfig={
                'Delay': 5,
                'MaxAttempts': 100}
        )


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
