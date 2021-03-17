from rixtribute.helper import get_boto_session, generate_tags
from rixtribute.configuration import config
from rixtribute import aws_helper
from typing import List, Optional
from botocore import errorfactory
import base64

class ECRRepo(object):
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

        # boto_instance_dict
        # {'repositoryArn': 'arn:aws:ecr:eu-west-1:293331033030:repository/aws-cdk/assets',
        #  'registryId': '293331033030',
        #  'repositoryName': 'aws-cdk/assets',
        #  'repositoryUri': '293331033030.dkr.ecr.eu-west-1.amazonaws.com/aws-cdk/assets',
        #  'createdAt': datetime.datetime(2020, 5, 26, 7, 45, 23, tzinfo=tzlocal()),
        #  'imageTagMutability': 'MUTABLE',
        #  'imageScanningConfiguration': {'scanOnPush': True}}

        self.registry_id :str = boto_instance_dict.get("registryId", '')
        self.repository_arn :str = boto_instance_dict.get("repositoryArn", '')
        self.repository_name :str = boto_instance_dict.get("repositoryName", '')
        self.repository_uri :str = boto_instance_dict.get("repositoryUri", '')
        self.image_tag_mutability :str = boto_instance_dict.get("imageTagMutability", '')
        self.tags = self.get_tags()

    def get_tags(self):

        client = ECR._get_ecr_boto_client()
        response = client.list_tags_for_resource(resourceArn=self.repository_arn)

        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

        tags = {x['Key']:x['Value'] for x in response['tags']}
        return tags

    def get_printable_dict(self):
        keys = [
                "repository_name",
                "registry_id",
                "repository_arn",
                "repository_name",
        ]
        return {k: getattr(self, k) for k in keys if k in keys}

    def delete(self):
        ECR.delete_repository(self.repository_name, self.registry_id, force=True)

    def __repr__(self):
        return self.repository_name



class ECR(object):

    def __init__(self):
        """ STATIC class used as API """
        pass

    @classmethod
    def _get_session(cls, region_name :str=None):
        session = get_boto_session(region_name=region_name)
        return session

    @classmethod
    def _get_ecr_boto_client(cls, region_name :str=None):
        session = cls._get_session(region_name=region_name)
        client = session.client("ecr")
        return client

    @classmethod
    def get_repository(cls, repository_name :str=None, region_name :str=None) -> Optional[ECRRepo]:
        """List repositories"""
        ecr = cls._get_ecr_boto_client(region_name=region_name)
        response = ecr.describe_repositories(repositoryNames=[repository_name])

        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

        for repo in response["repositories"]:
            return ECRRepo(repo)
        return None

    @classmethod
    def list_repositories(cls, filter_project_name :str=None, region_name :str=None):
        """List repositories"""
        ecr = cls._get_ecr_boto_client(region_name=region_name)
        response = ecr.describe_repositories()


        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

        repositories = []
        for repo in response["repositories"]:
            tmp_repo = ECRRepo(repo)
            tmp_repo_project_tag = tmp_repo.tags.get("project", "")
            if filter_project_name is not None:
                if tmp_repo_project_tag == filter_project_name:
                    repositories.append(ECRRepo(repo))
            else:
                repositories.append(ECRRepo(repo))

        return repositories

    @classmethod
    def get_or_create_repository(cls, name :str) -> Optional[ECRRepo]:
        try:
            repo = cls.get_repository(name)
        except:
            repo = ECR.create_repository(name)

        return repo

    @classmethod
    def create_repository(cls, name :str, region_name :str=None):
        """Create a ECR repository"""
        client = cls._get_ecr_boto_client(region_name=region_name)
        response = client.create_repository(
            repositoryName=name,
            tags=generate_tags(name)
        )

        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
        return ECRRepo(response['repository'])

    @classmethod
    def delete_repository(cls, name :str, registry_id :str, force :bool=False, region_name :str=None):
        """Create a ECR repository"""
        client = cls._get_ecr_boto_client(region_name=region_name)
        response = client.delete_repository(
            registryId=registry_id,
            repositoryName=name,
            force=force
        )

        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    @classmethod
    def get_auth_token(cls, region_name :str=None) -> dict:
        """ get auth_config for logging into docker
        Args:
            None
        Returns:
            dict : {'username': username,
                    'password': password,
                    'registry': registry}
                    docker_client.login(**get_auth_token())
        Raises:
            None
        """
        client = cls._get_ecr_boto_client(region_name=region_name)
        response = client.get_authorization_token()

        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

        registry = response['authorizationData'][0]['proxyEndpoint']
        auth_token = response['authorizationData'][0]['authorizationToken']
        auth_token = base64.b64decode(auth_token).decode()

        username, password = auth_token.split(':')

        return {'username': username,
                'password': password,
                'registry': registry}
