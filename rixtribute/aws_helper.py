import sys

region_name_to_code_dict = {'us-east-2': 'US East (Ohio)',
                       'us-east-1': 'US East (N. Virginia)',
                       'us-west-1': 'US West (N. California)',
                       'us-west-2': 'US West (Oregon)',
                       'ap-south-1': 'Asia Pacific (Mumbai)',
                       'ap-northeast-2': 'Asia Pacific (Seoul)',
                       'ap-southeast-1': 'Asia Pacific (Singapore)',
                       'ap-southeast-2': 'Asia Pacific (Sydney)',
                       'ap-northeast-1': 'Asia Pacific (Tokyo)',
                       'ca-central-1': 'Canada (Central)',
                       'cn-north-1': 'China (Beijing)',
                       'cn-northwest-1': 'China (Ningxia)',
                       'eu-central-1': 'EU (Frankfurt)',
                       'eu-west-1': 'EU (Ireland)',
                       'eu-west-2': 'EU (London)',
                       'eu-west-3': 'EU (Paris)',
                       'eu-north-1': 'EU (Stockholm)',
                       'sa-east-1': 'South America (Sao Paulo)'}


def region_name_to_region_code(region_name :str) -> str:
    """ Region Name to Region Code e.g. eu-west-1 -> EU (Ireland)"""
    try:
        return region_name_to_code_dict[region_name]
    except KeyError as e:
        print("Error: No such region {region_name}")
        sys.exit(1)


def region_code_to_region_name(region_code :str) -> str:
    """ Region Code to Region Name e.g. EU (Ireland) -> eu-west-1"""
    reverse_region_mapping_dict = {v:k for k,v in region_name_to_code_dict.items()}
    try:
        return reverse_region_mapping_dict[region_code]
    except KeyError as e:
        print("Error: No such region {region_code}")
        sys.exit(1)
