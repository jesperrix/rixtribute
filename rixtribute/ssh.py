import os
import subprocess
from typing import List, Optional

def generate_scp_command(source_files :List[str],
                         destination :str,
                         recursive :bool=False,
                         port :int=22,
                         key_path :str=None,
                         skip_host_check :bool=False,
                         no_verbose :bool=True):

    # TODO support for more custom args

    # If key is specified
    if key_path:
        cmd = ['scp', '-i', key_path]
    else:
        cmd = ['scp']

    if port != 22:
        cmd = cmd + ['-p', str(port)]

    if recursive is True:
        cmd = cmd + ['-r']

    if skip_host_check is True:
        cmd = cmd + ['-o', 'StrictHostKeyChecking=no']

    if no_verbose is True:
        cmd = cmd + ['-q']

    # Add source
    cmd = cmd + source_files
    # add dest
    cmd = cmd + [destination]

    return cmd

def generate_ssh_command(host :str,
                         user :str,
                         port :int=22,
                         key_path :str=None,
                         command :str=None,
                         skip_host_check :bool=False,
                         no_verbose :bool=True):
    # If key is specified
    if key_path:
        cmd = ['ssh', '-ti', key_path]
    else:
        cmd = ['ssh', '-t']

    if skip_host_check is True:
        cmd = cmd + ['-o', 'StrictHostKeyChecking=no']

    if port != 22:
        cmd = cmd + ['-p', str(port)]

    if no_verbose is True:
        cmd = cmd + ['-q']

    # TODO support for more custom args
    cmd = cmd + [f'{user}@{host}']

    if command:
        cmd.append(command)

    return cmd


def attach_tmux_session_and_run_command(session_name :str, command :str):
    # -s = session name, -n = window name
    tmux_init_cmd = f'tmux new-session -d -s {session_name} -n main'
    # tmux select-window -t "$SESSION":model \;
    # tmux attach-session -t "$SESSION" \;

    tmux_create_cmd = (
        f'if ! tmux has-session -t {session_name} > /dev/null 2>&1; then '
        f'{tmux_init_cmd}; '
        f'fi'
    )

    tmux_run_command = (
        f'tmux send-keys -t "{session_name}":main "{command}" Enter \; '
    )

    tmux_attach_cmd = f"tmux attach-session -t {session_name}"

    tmux_command = f"{tmux_create_cmd} && {tmux_run_command}"

    return tmux_command

def ssh_command_tmux(host :str,
                     user :str,
                     command :str,
                     port :int=22,
                     key :str=None):
    # tmux_attach_cmd = attach_tmux_session("automated-session")
    # remote_cmd = f'{tmux_attach_cmd} && {command}'

    remote_cmd = attach_tmux_session_and_run_command("automated-session", command)
    cmd = generate_ssh_command(host=host,
                               user=user,
                               port=port,
                               key_path=key,
                               skip_host_check=True,
                               command=command)
    subprocess.call(cmd)


def ssh_command(host :str,
                user :str,
                command :Optional[str],
                port :int=22,
                key :str=None,
                print_output :bool=False):
    # cmd = ssh_command(host, user, port, key, command)
    # subprocess.call(cmd)
    cmd = generate_ssh_command(host=host,
                               user=user,
                               port=port,
                               key_path=key,
                               skip_host_check=True,
                               command=command)

    # output = subprocess.check_output(cmd)
    # print(output)

    cmd_str = ' '.join(cmd)

    rc, output = subprocess.getstatusoutput(cmd_str)
    if rc != 0:
        print(output)
        return False

    if print_output:
        print(f"\n{output}")
    # subprocess.check_output(cmd)

def scp(source :List[str],
        dest :str,
        recursive :bool,
        port :int=22,
        key :str=None) -> bool:
    # Generate scp command
    cmd = generate_scp_command(source_files=source,
                      destination=dest,
                      recursive=recursive,
                      port=port,
                      key_path=key,
                      skip_host_check=True)

    cmd_str = ' '.join(cmd)

    rc, output = subprocess.getstatusoutput(cmd_str)
    if rc != 0:
        print(output)
        return False

    return True


    # subprocess.call(cmd)

def ssh(host :str, user :str, port :int=22, key :str=None):
    command = generate_ssh_command(host=host, user=user, command=None, port=port, key_path=key)
    print(f"SSHing into: {host}")
    # WORKING FOR INITIAL CONNECT
    ssh = subprocess.Popen(' '.join(command), shell=True, env=os.environ)
    ssh.wait()


if __name__ == "__main__":

    host = "ec2-52-214-34-243.eu-west-1.compute.amazonaws.com"
    # cmd = ssh_command(host, 22, 'ec2-user', '/home/jri/.ssh/jesper_ssh.pem', 'ls -la')
    # subprocess.check_output(cmd)
    ssh(host, 'ec2-user', 22, '/home/jri/.ssh/jesper_ssh.pem')

    # import datetime
    # cmd = f'sleep 2; echo "{str(datetime.datetime.now())}" >> /tmp/testing/hello.txt'
    # run_remote_command(host, 22, 'ec2-user', key='/home/jri/.ssh/jesper_ssh.pem', command=cmd)

