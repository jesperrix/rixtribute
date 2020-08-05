import os
import copy
import yaml
import sys

class ProfileParser():

    def __init__(self):
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

        f = open(conf_file_loc, 'w')
        yaml.dump({"name": name, "email": email}, f)
        f.close()

        print(f"successfully created: {conf_file_loc}")
        return True


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
        for loc in os.curdir, os.path.expanduser("~"), os.environ.get("RIXTRIBUTE_CONF", None):
            if loc is None: continue
            locations.append(loc)
            try:
                with open(os.path.join(loc, "rxtb-profile.yaml"), 'rb') as f:
                    return yaml.load(f, Loader=yaml.FullLoader)
            except IOError:
                pass

        raise Exception(f"No rxtb-profile.yaml found in: {locations}")


class ConfigParser(object):

    def __init__(self):
        # find config .rxtb-config.yaml
        self._raw_config = self.find_and_parse_config()

        # parse provider(s)
        # parse project
        # parse instance

    def get_project_sync(self):
        if 'project' not in self._raw_config:
            raise Exception("No project section in rxtb-config.yaml")


    def get_provider(self, provider :str):
        if 'provider' not in self._raw_config:
            raise Exception("No provider section in rxtb-config.yaml")
        try:
            return copy.deepcopy(self._raw_config['provider'][provider])
        except KeyError as e:
            raise Exception("No provider called '{provider}', add to the provider section.")

    def get_instances(self):
        return copy.deepcopy(self._raw_config["instance"])

    def get_instance(self, instance_name :str):
        if 'instance' not in self._raw_config:
            raise Exception("No instance section in rxtb-config.yaml")

        for instance in self._raw_config["instance"]:
            if instance["name"] == instance_name:
                return copy.deepcopy(instance)

        raise Exception(f"No instance called '{instance_name}', add to the instance section")

    def find_and_parse_config(self):
        config = None
        locations = []
        for loc in os.curdir, os.path.expanduser("~"), os.environ.get("RIXTRIBUTE_CONF", None):
            if loc is None: continue
            locations.append(loc)
            try:
                with open(os.path.join(loc, "rxtb-config.yaml"), 'rb') as f:
                    return yaml.load(f, Loader=yaml.FullLoader)
            except IOError:
                pass

        raise Exception(f"No rxtb-config.yaml found in: {locations}")

config = ConfigParser()
profile = ProfileParser()
