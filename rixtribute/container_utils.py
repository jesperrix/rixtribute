import json
from rixtribute.configuration import config
import docker
from typing import Optional

docker_client = docker.client.from_env()

def docker_build_from_cfg(container_cfg):
    """Build docker image from container config
    Args:
        container_cfg : dict with container cfg
    Returns:
        None
    """
    build_params :dict = {}

    if 'file' in container_cfg:
        build_params["dockerfile"] = container_cfg['file']

    build_params["path"] = container_cfg['path']
    build_params['tag'] = container_cfg['tag']
    build_params['squash'] = True
    build_params['gzip'] = True

    print("\nBuilding docker container:\n")
    docker_client = docker.client.from_env()
    # image = docker_client.images.build(**build_params)
    # f = BytesIO(dockerfile.encode('utf-8'))
    # docker_cli = docker.APIClient(base_url='unix://var/run/docker.sock')
    # for line in docker_cli.build(**build_params):
    docker_cli = docker_client.api
    for line in docker_cli.build(**build_params):
        line = json.loads(line)
        try:
            print(f"  {line['stream']}", end='')
        except:
            try:
                print(f"  {line['error']}", end='')
            except:
                pass

def docker_run_cmd(container_cfg):
    """Run command for docker container cfg
    Args:
        container_cfg : dict with container cfg
    Returns:
        None
    """

def docker_push(repository :str, tag :str, auth_config :dict) -> bool:
    """Push docker image to repository
    Args:
        repository      : e.g. 293331033030.dkr.ecr.eu-west-1.amazonaws.com/test/img
        tag             : e.g. latest
        auth_config     : dict {"username": "adsf", "password": "xxx"}
    Returns:
        bool True on success
    Raises:
        docker.errors.APIError
    """

    try:
        repo_w_tag = f"{repository}:{tag}"
        docker_cli = docker.APIClient(base_url='unix://var/run/docker.sock')

        # Description of character up when creating interactive cli lines
        # https://stackoverflow.com/questions/11474391/is-there-go-up-line-character-opposite-of-n/11474509#11474509
        lines_map :dict = {}
        for line in docker_cli.push(repo_w_tag,
                                    stream=True,
                                    decode=True,
                                    auth_config=auth_config):
            try:
                if 'status' in line and 'id' in line:
                    n_lines = len(lines_map.keys())
                    lines_map[line['id']] = line['status']
                    print("\033[F"*n_lines)
                    print_lines = [f'  {id}: {msg}' for id, msg in lines_map.items()]
                    print(*print_lines, sep='\n', end='')
                elif 'status' in line:
                    print(f'\n  {line["status"]}')
                else:
                    print(f"  {line['error']}")
                    return False
            except:
                # print(f"  \n{line}")
                pass

        return True
    except docker.errors.APIError as e:
        print(e.explanation)
        raise e

def docker_images() -> list:
    return docker_client.images.list()

def docker_login(auth_token :dict):
    docker_cli = docker.APIClient(base_url='unix://var/run/docker.sock')
    docker_cli.login(**auth_token)
    # docker_client.login(**auth_token)

def docker_image_get(name :str) -> Optional[docker.models.images.Image]:
    try:
        return docker_client.images.get(name)
    except docker.errors.ImageNotFound:
        return None
