import os
import copy
import yaml
from typing import List, Optional
import sys
from enum import Enum
import re

class ProviderType(Enum):
    AWS = 'aws'
    GCP = 'gcp'
    # AZURE = 'azure'

def str_presenter(dumper, data):
    if len(data.splitlines()) > 1:  # check for multiline string
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)
yaml.add_representer(str, str_presenter)

def _write_yaml(file_path :str, data :dict):
    f = open(file_path, 'w')
    yaml.dump(data, f)
    f.close()



class ProfileParser():

    def __init__(self):
        self._dir_absolute = None
        self._file_path_absolute = None
        try:
            self._raw_profile = self.find_and_parse_profile()
        except Exception as e:
            answer = str(input("No rxtb-profile.yaml found, create one (y/n)")).lower().strip()
            if answer == 'y':
                self.create_profile_yaml()
            else:
                sys.exit(1)

    def create_profile_yaml(self):
        name = str(input(f"{'Enter name':12s}: ")).lower().strip()
        email = str(input(f"{'Enter email':12s}: ")).lower().strip()

        global_conf_dir = os.path.expanduser("~")
        conf_file_loc = os.path.join(global_conf_dir, "rxtb-profile.yaml")

        _write_yaml(conf_file_loc, {"name": name, "email": email})
        # f = open(conf_file_loc, 'w')
        # yaml.dump({"name": name, "email": email}, f)
        # f.close()

        print(f"successfully created: {conf_file_loc}")
        return True

    @property
    def file_path(self):
        return self._file_path_absolute

    @property
    def name(self):
        try:
            return self._raw_profile["name"]
        except Exception as e:
            raise e

    @property
    def email(self):
        try:
            return self._raw_profile["email"]
        except Exception as e:
            raise e

    def find_and_parse_profile(self):
        config = None
        locations = []
        for loc in os.curdir, os.path.expanduser("~"), os.environ.get("RIXTRIBUTE_PROFILE", None):
            if loc is None: continue
            locations.append(loc)
            try:
                profile_path = os.path.join(loc, "rxtb-profile.yaml")
                with open(profile_path, 'rb') as f:
                    self._dir_absolute = os.path.dirname(os.path.abspath(profile_path))
                    self._file_path_absolute = os.path.abspath(profile_path)
                    return yaml.load(f, Loader=yaml.FullLoader)
            except IOError:
                pass

        raise Exception(f"No rxtb-profile.yaml found in: {locations}")


class ConfigParser(object):

    def __init__(self):
        self._dir_absolute :Optional[str] = None
        self._config_file_path_absolute :Optional[str] = None
        self._keys_file_path_absolute :Optional[str] = None
        self._ssh_key_filename = "rxtb-keys.yaml"

        # find config .rxtb-config.yaml
        self._raw_config = self._find_and_parse_config()
        # parse keys .rxtb-keys.yaml
        self._raw_keys = self._parse_keys()

        self._provider = self._parse_provider()
        self._containers = self._parse_containers()
        self._instances = self._parse_instances()
        self._commands = self._parse_commands()

        # TODO parse project

    @property
    def project_name(self):
        return self.get_project()['name']

    @property
    def file_path(self):
        return self._config_file_path_absolute

    @property
    def project_root(self):
        return self._dir_absolute

    def verify_config(self):
        self.get_instances()

    def _find_and_parse_config(self):
        locations = []
        for loc in os.curdir, os.path.expanduser("~"), os.environ.get("RIXTRIBUTE_CONF", None):
            if loc is None: continue
            locations.append(loc)
            try:
                config_path = os.path.join(loc, "rxtb-config.yaml")
                with open(config_path, 'rb') as f:
                    self._dir_absolute = os.path.dirname(os.path.abspath(config_path))
                    self._file_path_absolute = os.path.abspath(config_path)
                    return yaml.load(f, Loader=yaml.FullLoader)
            except IOError:
                pass

        raise Exception(f"No rxtb-config.yaml found in: {locations}")

    # ssh key
    def _parse_keys(self):
        if self._dir_absolute != None:
            keys_path = os.path.join(self._dir_absolute, self._ssh_key_filename)
            self._keys_file_path_absolute = keys_path
            if os.path.isfile(keys_path):
                with open(keys_path, 'rb') as f:
                    return yaml.load(f, Loader=yaml.FullLoader)

        return dict()


    def add_ssh_key(self, key_name :str, private_key :str):
        raw_cp = copy.deepcopy(self._raw_keys)

        # raw_cp["
        provider_name = self._provider["name"]
        if provider_name not in raw_cp: raw_cp[provider_name] = {}
        raw_cp[provider_name]["ssh-key"] = {"key_name": key_name,
                                            "private_key": private_key}
        if self._keys_file_path_absolute:
            _write_yaml(self._keys_file_path_absolute, raw_cp)

    def get_ssh_key(self) -> Optional[dict]:
        provider_name = self._provider["name"]
        if provider_name in self._raw_keys and "ssh-key" in self._raw_keys[provider_name]:
            return copy.deepcopy(self._raw_keys[provider_name]["ssh-key"])
        return None


    # Provider section

    def _parse_provider(self) -> dict:
        if 'provider' not in self._raw_config:
            raise Exception("No provider section in rxtb-config.yaml")

        raw_providers = copy.deepcopy(self._raw_config['provider'])

        if len(raw_providers.keys()) > 1:
            raise Exception("Multiple providers specified in the provider section in rxtb-config.yaml")

        for k, v in raw_providers.items():
            return {"name": k, "config": v}


    def get_provider(self):
        return copy.deepcopy(self._provider)

    # Project section

    def get_project_sync(self):
        if 'project' not in self._raw_config:
            raise Exception("No project section in rxtb-config.yaml")

    def get_project(self):
        if 'project' not in self._raw_config:
            raise Exception("No project section in rxtb-config.yaml")
        return copy.deepcopy(self._raw_config['project'])

    # container section

    def _parse_containers(self) -> List[dict]:
        if 'container' not in self._raw_config:
            raise Exception("No container section in rxtb-config.yaml")

        raw_containers = copy.deepcopy(self._raw_config['container'])

        containers = []
        for raw_container in raw_containers:
            tmp_container = dict()

            ## instance meta data
            if "name" not in raw_container:
                raise Exception("missing name in container section in rxtb-config.yaml")
            if "file" not in raw_container:
                raise Exception("missing file in instance section in rxtb-config.yaml")

            tmp_container['name'] = raw_container['name']
            tmp_container['tag'] = f"{self.project_name}/{raw_container['name']}"
            tmp_container["file"] = os.path.join(self._dir_absolute, raw_container["file"])
            tmp_container["ports"] = []

            path = os.path.join(self._dir_absolute, raw_container.get("path", ""))
            if not os.path.isdir(path):
                raise Exception("invalid container build path: {path} in {tmp_container['name']} in rxtb-config.yaml")
            tmp_container["path"] = path

            ports = raw_container.get("ports", None)
            if ports:
                for port_spec in ports:
                    names = ["containerPort", "hostPort"]
                    for k in names:
                        if k not in port_spec:
                            raise Exception("Needs {' and '.join(names)} in ports section for \"{raw_container['name']}\"")

                        port = port_spec[k]
                        if type(port) != int:
                            raise Exception((
                                f"Wrong type in container ports {type(port)} for \"{raw_container['name']}\", "
                                f"expected {int}")
                            )

                    tmp_container["ports"].append(port_spec)

            if os.path.isfile(tmp_container["file"]) == False:
                raise Exception((
                    f"dockerfile \"{raw_container['file']}\" does not exist for container "
                    f"\"{tmp_container['name']} in rxtb-config.yaml")
                )

            containers.append(tmp_container)

        return containers

    def get_containers(self):
        return copy.deepcopy(self._containers)

    def get_container(self, container_name :str):
        for container in self._containers:
            if container['name'] == container_name:
                return copy.deepcopy(container)

        raise Exception(f"No container called '{container_name}', add to the container section")

    # instance section

    def _parse_instances(self) -> List[dict]:
        if 'instance' not in self._raw_config:
            raise Exception("No instance section in rxtb-config.yaml")

        raw_instances = copy.deepcopy(self._raw_config["instance"])
        instances = []

        for raw_instance in raw_instances:
            tmp_instance = dict()
            ## instance meta data
            if "name" not in raw_instance:
                raise Exception("missing name in instance section in rxtb-config.yaml")
            if "provider" not in raw_instance:
                raise Exception("missing provider in instance section in rxtb-config.yaml")
            if "config" not in raw_instance:
                raise Exception("missing config in instance section in rxtb-config.yaml")

            tmp_instance["name"] = raw_instance["name"]
            tmp_instance["provider"] = raw_instance["provider"]

            if "container" in raw_instance:
                try:
                    self.get_container(raw_instance["container"])
                except:
                    raise Exception((
                        f"container \"{raw_instance['container']}\" for instance "
                        f"\"{raw_instance['name']}\" is not defined in container the section")
                    )
                tmp_instance["container"] = raw_instance["container"]


            ## Parse instance config

            config_attrs = {
                "region": {"required": True, "type": str},
                "type": {"required": True, "type": str},
                "ami": {"required": True, "type": str},
                "keyname": {"required": False, "type": str}, # Plan on deprecating
                "volumes": {"required": False, "type": list},
                "ports": {"required": False, "type": list},
                "spot": {"required": False, "type": bool}
            }
            ## Loop over available config attributes and check if required is set.
            for attr, val in config_attrs.items():
                if attr not in raw_instance["config"] and val["required"] == True:
                    raise Exception(f"missing required field {attr} in {raw_instance['name']} config section")

            # Parse each config attribute, raise error if unknown attr occurs
            tmp_config = {}
            for k, v in raw_instance["config"].items():
                if k not in config_attrs.keys():
                    raise Exception(f"Unsupported config field \"{k}\" in \"{raw_instance['name']}\" config")
                expected_type = config_attrs[k]["type"]
                if type(v) != expected_type:
                    raise Exception((
                        f"Wrong type in config field \"{k}\" in \"{raw_instance['name']}\" "
                        "config, expected {expected_type}")
                    )

                # parse volumes
                if k == "volumes":
                    tmp_config["volumes"] = []
                    for volume in v:
                        if "devname" not in volume.keys():
                            raise Exception(f"missing devname in volumes section for \"{raw_instance['name']}\"")
                        if "size" not in volume.keys():
                            raise Exception(f"missing size in volumes section for \"{raw_instance['name']}\"")

                        if type(volume["devname"]) != str:
                            raise Exception((
                                f"Wrong type for devname in volumes section for \"{raw_instance['name']}\", "
                                f"expected {str}")
                            )
                        if type(volume["size"]) != int:
                            raise Exception((
                                f"Wrong type for size in volumes section for \"{raw_instance['name']}\", "
                                f"expected {int}")
                            )

                        tmp_config["volumes"].append(volume)
                    continue

                # parse ports
                if k == "ports":
                    tmp_config["ports"] = []
                    port_regex = re.compile('(:?tcp|udp|icmp):\d+')
                    for port_str in v:
                        if port_regex.match(port_str) == None:
                            raise Exception((
                                f"Wrong port format \"{port_str}\"in ports section for \"{raw_instance['name']}\", "
                                f"expected: {port_regex.pattern}")
                            )
                        protocol, port = "tcp:21".split(":")
                        tmp_config["ports"].append({"port": int(port), "protocol": protocol})
                    continue

                tmp_config[k] = v

            # Add 22 as default port
            if "ports" not in tmp_config:
                tmp_config["ports"] = [{"port": 22, "protocol": "tcp"}]
            if "spot" not in tmp_config:
                tmp_config["spot"] = False
            if "volumes" not in tmp_config:
                tmp_config['volumes'] = [{'devname': '/dev/xvda', 'size': 50},]

            tmp_instance["config"] = tmp_config
            instances.append(tmp_instance)

        return instances


    def get_instances(self):
        return copy.deepcopy(self._instances)

    def get_instance(self, instance_name :str):
        for instance in self._instances:
            if instance["name"] == instance_name:
                return copy.deepcopy(instance)

        raise Exception(f"No instance called '{instance_name}', add to the instance section")

    # command section

    def _parse_commands(self) -> dict:
        if 'commands' not in self._raw_config:
            return {}
            # raise Exception("No provider section in rxtb-config.yaml")

        raw_commands = copy.deepcopy(self._raw_config['commands'])
        return raw_commands

    def get_commands(self):
        return list(copy.deepcopy(self._commands).keys())

    def get_command(self, name :str) -> Optional[str]:
        commands = copy.deepcopy(self._commands)
        try:
            return commands[name]
        except Exception as e:
            return None

try:
    config = ConfigParser()
    profile = ProfileParser()
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
