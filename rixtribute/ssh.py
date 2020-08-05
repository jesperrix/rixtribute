import subprocess

def ssh_command(host :str,
                port :int,
                user :str,
                command :str,
                key_path :str,
                host_check :bool=False,
                no_verbose :bool=True):
    cmd = ['ssh', '-ti', key_path]

    if host_check is False:
        cmd = cmd + ['-o', 'StrictHostKeyChecking no']

    if port != 22:
        cmd = cmd + ['-p', str(port)]

    if no_verbose is True:
        cmd = cmd + ['-q']

    cmd = cmd + [f'{user}@{host}', command]
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

def run_remote_command(host :str, port :int, user :str, key :str, command :str):
    # tmux_attach_cmd = attach_tmux_session("automated-session")
    # remote_cmd = f'{tmux_attach_cmd} && {command}'

    remote_cmd = attach_tmux_session_and_run_command("automated-session", command)

    cmd = ssh_command(host, port, user, remote_cmd, key)
    subprocess.call(cmd)



host = "ec2-34-254-176-161.eu-west-1.compute.amazonaws.com"
# cmd = ssh_command(host, 22, 'ec2-user', 'sleep 2; ls -la', '/home/jri/.ssh/jesper_ssh.pem')
# subprocess.check_output(cmd)

import datetime
cmd = f'sleep 2; echo "{str(datetime.datetime.now())}" >> /tmp/testing/hello.txt'
run_remote_command(host, 22, 'ec2-user', key='/home/jri/.ssh/jesper_ssh.pem', command=cmd)

