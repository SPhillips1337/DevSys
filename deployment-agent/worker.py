import os
import sys
import time
import json
import shutil
import requests
import yaml
from datetime import datetime

# allow importing utils from repository root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from utils import runner as runner_utils
except Exception:
    runner_utils = None

WORKSPACE = os.environ.get('WORKSPACE', '/workspace')
MANAGER_URL = os.environ.get('MANAGER_URL', 'http://manager:8080')
MANAGER_API_TOKEN = os.environ.get('MANAGER_API_TOKEN')
DEPLOY_DIR = os.path.join(WORKSPACE, 'deploy')
TASKS_DIR = os.path.join(WORKSPACE, 'tasks')

os.makedirs(DEPLOY_DIR, exist_ok=True)

HEADERS = {}
if MANAGER_API_TOKEN:
    HEADERS['Authorization'] = f"Bearer {MANAGER_API_TOKEN}"

print('Deployment agent started. Deploy dir:', DEPLOY_DIR)

def read_meta(task_dir):
    meta_file = os.path.join(task_dir, 'meta.json')
    if not os.path.exists(meta_file):
        return None
    with open(meta_file) as f:
        return json.load(f)


def write_deploy_record(task_dir, record):
    records_file = os.path.join(task_dir, 'deploy_records.json')
    records = []
    if os.path.exists(records_file):
        try:
            with open(records_file) as f:
                records = json.load(f)
        except Exception:
            records = []
    records.append(record)
    with open(records_file, 'w') as f:
        json.dump(records, f)


def create_followup_task(task_id, reason):
    # Create a follow-up task asking for a fix
    payload = {
        'title': f'Fix deployment: {task_id}',
        'spec': {
            'title': f'Fix deployment for {task_id}',
            'description': reason,
            'owner': 'coding-agent',
            'kind': 'coding',
            'priority': 'high'
        }
    }
        try:
                requests.post(f"{MANAGER_URL}/api/tasks", json=payload, timeout=5, headers=HEADERS)
            except Exception as e:
                print('Failed to create follow-up task', e)



def check_acceptance(task_dir, spec):
    # Look for acceptance criteria with a URL and expected response code
    acceptance = spec.get('acceptance') or []
    for a in acceptance:
        if isinstance(a, dict) and 'url' in a:
            url = a.get('url')
            expected = a.get('should_respond', 200)
            try:
                r = requests.get(url, timeout=5)
                if r.status_code == expected:
                    return True, {'url': url, 'status_code': r.status_code}
                else:
                    return False, {'url': url, 'status_code': r.status_code}
            except Exception as e:
                return False, {'url': url, 'error': str(e)}
    # No URL-based acceptance criteria: consider verified
    return True, {'info': 'no_url_checks'}

while True:
    try:
        for name in os.listdir(TASKS_DIR):
            task_dir = os.path.join(TASKS_DIR, name)
            if not os.path.isdir(task_dir):
                continue
            meta = read_meta(task_dir)
            if not meta:
                continue
            status = meta.get('status')
            # Consider tasks that are completed or explicitly ready for deploy
            if status not in ('completed', 'ready_for_deploy'):
                continue
            # Check task spec for deploy flag
            spec_path = os.path.join(task_dir, 'spec.yaml')
            deploy_flag = False
            spec = {}
            if os.path.exists(spec_path):
                try:
                    with open(spec_path) as f:
                        spec = yaml.safe_load(f) or {}
                        deploy_flag = bool(spec.get('deploy', False))
                except Exception as e:
                    print('Failed to read spec for', name, e)
                    deploy_flag = False
            if not deploy_flag:
                # Skip tasks that are not marked for deployment
                continue
            src_dir = os.path.join(task_dir, 'src')
            if not os.path.exists(src_dir):
                continue
            # Prepare per-task deploy directories
            task_deploy_dir = os.path.join(DEPLOY_DIR, name)
            os.makedirs(task_deploy_dir, exist_ok=True)
            revisions_dir = os.path.join(task_deploy_dir, 'revisions')
            os.makedirs(revisions_dir, exist_ok=True)
            current_dir = os.path.join(task_deploy_dir, 'current_tmp')
            if os.path.exists(current_dir):
                shutil.rmtree(current_dir)
            shutil.copytree(src_dir, current_dir)
            final_dir = os.path.join(task_deploy_dir, 'current')
            # Archive old current
            if os.path.exists(final_dir):
                ts = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
                archived = os.path.join(revisions_dir, ts)
                shutil.move(final_dir, archived)
            # Atomically move new current into place
            os.rename(current_dir, final_dir)
            # Decide runner and optionally copy deployed files to a remote host or local www (fallback served dir)
            runner = 'local'
            if runner_utils:
                try:
                    runner = runner_utils.select_runner('deploy')
                except Exception:
                    runner = 'local'

            remote_deploy_path = None
            if runner == 'remote-ssh':
                host = os.environ.get('EXTERNAL_DEPLOY_HOST') or os.environ.get('REMOTE_TEST_HOST')
                user = os.environ.get('EXTERNAL_DEPLOY_USER') or os.environ.get('REMOTE_TEST_USER')
                port = os.environ.get('EXTERNAL_DEPLOY_SSH_PORT') or os.environ.get('REMOTE_TEST_SSH_PORT')
                key = os.environ.get('EXTERNAL_DEPLOY_SSH_KEY') or os.environ.get('REMOTE_TEST_SSH_KEY')
                remote_base = os.environ.get('EXTERNAL_DEPLOY_REMOTE_PATH', '/tmp/devsys/deploy')
                remote_path = f"{remote_base}/{name}"
                try:
                    if not host or not user:
                        raise RuntimeError('remote deploy host/user not configured')
                    ok = False
                    known_hosts = os.environ.get('EXTERNAL_DEPLOY_KNOWN_HOSTS')
                    if runner_utils:
                        ok = runner_utils.remote_copy(final_dir, remote_path, host, user, port=port, key_path=key, known_hosts=known_hosts)
                    if ok:
                        remote_deploy_path = f"{user}@{host}:{remote_path}"
                        print('Deployed task', name, 'to remote', remote_deploy_path)
                        # Optionally run docker compose on remote host if requested
                        run_compose = os.environ.get('EXTERNAL_DEPLOY_RUN_COMPOSE', '').lower() == 'true'
                        if run_compose:
                            try:
                                compose_cmd = f"docker compose up -d --build"
                                ret, out = runner_utils.remote_run(compose_cmd, host, user, port=port, key_path=key, known_hosts=known_hosts, cwd=remote_path, timeout=600)
                                print('Remote compose result:', ret)
                                remote_compose_result = {'rc': ret, 'output': out}
                            except Exception as e:
                                print('Remote compose failed', e)
                                remote_compose_result = {'error': str(e)}
                        else:
                            remote_compose_result = None
                    else:
                        print('Remote copy failed, falling back to local www copy')
                        runner = 'local'
                except Exception as e:
                    print('Remote deploy error', e)
                    runner = 'local'

            if runner != 'remote-ssh':
                try:
                    www_root = os.path.join(WORKSPACE, 'www')
                    if os.path.exists(www_root):
                        # clear www root
                        for entry in os.listdir(www_root):
                            full = os.path.join(www_root, entry)
                            if os.path.isdir(full):
                                shutil.rmtree(full)
                            else:
                                os.remove(full)
                    else:
                        os.makedirs(www_root, exist_ok=True)
                    # copy files
                    for item in os.listdir(final_dir):
                        s = os.path.join(final_dir, item)
                        d = os.path.join(www_root, item)
                        if os.path.isdir(s):
                            shutil.copytree(s, d)
                        else:
                            shutil.copy2(s, d)
                except Exception as e:
                    print('Failed to copy to www root', e)

            # Record deployment
            record = {
                'task': name,
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'path': remote_deploy_path if remote_deploy_path else final_dir
            }
            # attach remote compose result if present
            try:
                if 'remote_compose_result' in locals() and remote_compose_result is not None:
                    record['remote_compose'] = remote_compose_result
            except Exception:
                pass
            write_deploy_record(task_dir, record)
            # Update task status to deployed
                try:
                    requests.post(f"{MANAGER_URL}/api/tasks/{name}/status", json={'status': 'deployed'}, timeout=5, headers=HEADERS)
                except Exception as e:
                    print('Failed to update manager status', e)

            print('Deployed task', name, 'to', final_dir)
            # Perform acceptance check
            ok, info = check_acceptance(task_dir, spec)
            record['acceptance'] = info
            record['verified'] = ok
            write_deploy_record(task_dir, record)
            if ok:
                try:
                    requests.post(f"{MANAGER_URL}/api/tasks/{name}/status", json={'status': 'verified'}, timeout=5, headers=HEADERS)
                except Exception as e:
                    print('Failed to update manager status to verified', e)
            else:
                try:
                    requests.post(f"{MANAGER_URL}/api/tasks/{name}/status", json={'status': 'failed'}, timeout=5, headers=HEADERS)
                except Exception as e:
                    print('Failed to update manager status to failed', e)
                # Create follow-up task to fix deployment
                create_followup_task(name, f"Acceptance checks failed: {info}")

    except Exception as e:
        print('Deployment worker error', e)
    time.sleep(5)
