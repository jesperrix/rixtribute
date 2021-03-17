import os
import shlex
import subprocess
from typing import List, Optional
import tempfile

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
        cmd.append(f"'{command}'")

    return cmd


def attach_tmux_session_and_run_command(session_name :str, command :str) -> str:
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
        f'tmux send-keys -t "{session_name}":main \"{command}\" Enter \; '
    )

    tmux_attach_cmd = f"tmux attach-session -t {session_name}"

    tmux_command = f"{tmux_create_cmd} && {tmux_run_command}"

    return tmux_command

def ssh_command_tmux(host :str,
                     user :str,
                     command :str,
                     port :int=22,
                     key_path :str=None,
                     key_str :str=None):

    remote_cmd = attach_tmux_session_and_run_command("automated-session", command)

    if key_str != None:
        f = tempfile.NamedTemporaryFile(suffix='_temp', prefix='rxtb_', delete=True)
        f.write(key_str.encode("utf8"))
        f.flush()
        key_path = f.name

    cmd = generate_ssh_command(host=host,
                               user=user,
                               port=port,
                               key_path=key_path,
                               skip_host_check=True,
                               command=remote_cmd)
    subprocess.call(" ".join(cmd), shell=True)


def ssh_command(host :str,
                user :str,
                command :Optional[str],
                port :int=22,
                key :str=None,
                print_output :bool=False):
    cmd = generate_ssh_command(host=host,
                               user=user,
                               port=port,
                               key_path=key,
                               skip_host_check=True,
                               command=command)

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
        recursive :bool=False,
        port :int=22,
        key_path :str=None,
        key_str :str=None) -> bool:

    if key_str != None:
        f = tempfile.NamedTemporaryFile(suffix='_temp', prefix='rxtb_', delete=True)
        f.write(key_str.encode("utf8"))
        f.flush()
        key_path = f.name

    # Generate scp command
    cmd = generate_scp_command(source_files=source,
                      destination=dest,
                      recursive=recursive,
                      port=port,
                      key_path=key_path,
                      skip_host_check=True)

    cmd_str = ' '.join(cmd)

    rc, output = subprocess.getstatusoutput(cmd_str)
    if rc != 0:
        print(output)
        return False

    return True


def ssh(host :str, user :str, port :int=22, key_path :str=None, key_str :str=None):
    print(f"SSHing into: {host}")
    if key_str != None:
        f = tempfile.NamedTemporaryFile(suffix='_temp', prefix='rxtb_', delete=True)
        f.write(key_str.encode("utf8"))
        f.flush()
        key_path = f.name

    command = generate_ssh_command(host=host, user=user, command=None, port=port, key_path=key_path)
    ssh = subprocess.Popen(' '.join(command), shell=True, env=os.environ)
    # WORKING FOR INITIAL CONNECT
    ssh.wait()


if __name__ == "__main__":

    host = "ec2-52-214-34-243.eu-west-1.compute.amazonaws.com"
    # cmd = ssh_command(host, 22, 'ec2-user', '/home/jri/.ssh/jesper_ssh.pem', 'ls -la')
    # subprocess.check_output(cmd)
    ssh(host, 'ec2-user', 22, '/home/jri/.ssh/jesper_ssh.pem')

    # import datetime
    # cmd = f'sleep 2; echo "{str(datetime.datetime.now())}" >> /tmp/testing/hello.txt'
    # run_remote_command(host, 22, 'ec2-user', key='/home/jri/.ssh/jesper_ssh.pem', command=cmd)

