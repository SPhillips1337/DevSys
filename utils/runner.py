import os
import subprocess
import shutil

# Runner selection helper
def _env_bool(name):
    v = os.environ.get(name)
    if v is None:
        return None
    return v.strip()


def select_runner(role='deploy'):
    """Selects runner for given role: 'deploy' or 'test'.
    Returns one of: 'remote-ssh', 'host-docker', 'dind', 'local'
    """
    role = role.lower()
    if role == 'deploy':
        runner_env = os.environ.get('DEPLOY_RUNNER', 'auto')
        remote_host = os.environ.get('EXTERNAL_DEPLOY_HOST')
        remote_user = os.environ.get('EXTERNAL_DEPLOY_USER')
    else:
        runner_env = os.environ.get('TEST_RUNNER', 'auto')
        remote_host = os.environ.get('REMOTE_TEST_HOST')
        remote_user = os.environ.get('REMOTE_TEST_USER')

    docker_socket = os.environ.get('DOCKER_SOCKET_PATH', '/var/run/docker.sock')

    runner_env = (runner_env or 'auto').lower()
    if runner_env != 'auto':
        if runner_env == 'remote-ssh':
            if remote_host:
                return 'remote-ssh'
            else:
                # requested remote but no host configured; fall back
                pass
        return runner_env

    # auto selection
    if remote_host:
        return 'remote-ssh'
    if os.path.exists(docker_socket):
        return 'host-docker'
    # dind detection could be implemented by env var; for now, prefer local
    return 'local'


def _ssh_base_args(key_path=None, port=None, known_hosts=None):
    args = ['ssh']
    if key_path:
        args += ['-i', key_path]
    if port:
        args += ['-p', str(port)]
    # If known_hosts provided, enforce strict checking; otherwise require explicit opt-in via env
    allow_insecure = os.environ.get('REMOTE_ALLOW_INSECURE_SSH', '').lower() == 'true'
    if known_hosts:
        args += ['-o', f'UserKnownHostsFile={known_hosts}', '-o', 'StrictHostKeyChecking=yes']
    else:
        if not allow_insecure:
            raise RuntimeError('No known_hosts provided for remote SSH. Set REMOTE_*_KNOWN_HOSTS or set REMOTE_ALLOW_INSECURE_SSH=true to override (not recommended).')
        args += ['-o', 'StrictHostKeyChecking=no']
    args += ['-o', 'BatchMode=yes']
    return args


def remote_copy(src, dest_path, host, user, port=None, key_path=None, known_hosts=None):
    """Copy local src (file or directory) to remote host:path using rsync/scp.
    dest_path is remote absolute path. Returns True on success.
    Requires known_hosts or REMOTE_ALLOW_INSECURE_SSH=true.
    """
    # Verify known_hosts or allow insecure
    allow_insecure = os.environ.get('REMOTE_ALLOW_INSECURE_SSH', '').lower() == 'true'
    if not known_hosts and not allow_insecure:
        raise RuntimeError('remote_copy: known_hosts not provided. Set REMOTE_*_KNOWN_HOSTS or REMOTE_ALLOW_INSECURE_SSH=true')

    # Prefer rsync if available
    rsync = shutil.which('rsync')
    scp = shutil.which('scp')
    if rsync:
        ssh_opts = ''
        if key_path:
            ssh_opts = f"ssh -i {key_path} -p {port or 22}"
        else:
            ssh_opts = f"ssh -p {port or 22}"
        if known_hosts:
            ssh_opts += f" -o UserKnownHostsFile={known_hosts} -o StrictHostKeyChecking=yes"
        else:
            ssh_opts += " -o StrictHostKeyChecking=no"
        cmd = ['rsync', '-a', '--delete', '-e', ssh_opts, src.rstrip('/') + '/', f"{user}@{host}:{dest_path}"]
    elif scp:
        cmd = [scp, '-r']
        if key_path:
            cmd += ['-i', key_path]
        if port:
            cmd += ['-P', str(port)]
        if known_hosts:
            cmd += ['-o', f'UserKnownHostsFile={known_hosts}', '-o', 'StrictHostKeyChecking=yes']
        else:
            cmd += ['-o', 'StrictHostKeyChecking=no']
        cmd += [src, f"{user}@{host}:{dest_path}"]
    else:
        raise RuntimeError('No rsync or scp available in container')

    try:
        subprocess.check_call(cmd)
        return True
    except subprocess.CalledProcessError as e:
        print('remote_copy failed:', e)
        return False


def remote_run(cmd, host, user, port=None, key_path=None, known_hosts=None, cwd=None, timeout=300):
    """Execute a command string on remote host via ssh. Returns (returncode, stdout+stderr)
    Requires known_hosts or REMOTE_ALLOW_INSECURE_SSH=true.
    """
    # Validate known_hosts presence
    allow_insecure = os.environ.get('REMOTE_ALLOW_INSECURE_SSH', '').lower() == 'true'
    if not known_hosts and not allow_insecure:
        raise RuntimeError('remote_run: known_hosts not provided. Set REMOTE_*_KNOWN_HOSTS or REMOTE_ALLOW_INSECURE_SSH=true')

    ssh_args = _ssh_base_args(key_path=key_path, port=port, known_hosts=known_hosts)
    ssh_args += [f"{user}@{host}"]
    if cwd:
        remote_cmd = f"cd {cwd} && {cmd}"
    else:
        remote_cmd = cmd
    full = ssh_args + [remote_cmd]
    try:
        out = subprocess.check_output(full, stderr=subprocess.STDOUT, timeout=timeout)
        return 0, out.decode('utf-8', errors='replace')
    except subprocess.CalledProcessError as e:
        return e.returncode, (e.output.decode('utf-8', errors='replace') if e.output else str(e))
    except Exception as e:
        return -1, str(e)
