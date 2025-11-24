import os
import time
import json
import requests
import yaml
from datetime import datetime

WORKSPACE = os.environ.get('WORKSPACE', '/workspace')
MANAGER_URL = os.environ.get('MANAGER_URL', 'http://manager:8080')
MANAGER_API_TOKEN = os.environ.get('MANAGER_API_TOKEN')
CHECKS_FILE = os.environ.get('CHECKS_FILE', '/monitoring/checks.yaml')
STATE_FILE = os.path.join(WORKSPACE, 'monitoring_state.json')

HEADERS = {}
if MANAGER_API_TOKEN:
    HEADERS['Authorization'] = f"Bearer {MANAGER_API_TOKEN}"

print('Monitoring agent starting, workspace=', WORKSPACE, 'manager=', MANAGER_URL, 'checks=', CHECKS_FILE)

# load checks
def load_checks():
    if not os.path.exists(CHECKS_FILE):
        return []
    try:
        with open(CHECKS_FILE) as f:
            return yaml.safe_load(f) or []
    except Exception as e:
        print('Failed to load checks', e)
        return []

# load state
def load_state():
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {}

def save_state(state):
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f)
    except Exception as e:
        print('Failed to save state', e)


def create_followup(check, reason):
    # create a task to request investigation/fix
    payload = {
        'title': f"Monitoring alert: {check.get('name')}",
        'spec': {
            'description': f"Monitoring detected a failure for check {check.get('name')}: {reason}",
            'owner': 'coding-agent',
            'kind': 'coding',
            'priority': 'high',
            'related_check': check.get('name')
        }
    }
    try:
        r = requests.post(f"{MANAGER_URL}/api/tasks", json=payload, headers=HEADERS, timeout=5)
        if r.status_code in (200,201):
            print('Created follow-up task for', check.get('name'))
        else:
            print('Failed to create follow-up task, status', r.status_code, r.text)
    except Exception as e:
        print('Error creating follow-up task', e)


while True:
    checks = load_checks()
    state = load_state()
    for check in checks:
        name = check.get('name')
        kind = check.get('type', 'http')
        interval = check.get('interval', 30)
        threshold = check.get('threshold', 2)
        last = state.get(name, {})
        # perform check
        ok = False
        info = None
        if kind == 'http':
            url = check.get('url')
            expected = check.get('status', 200)
            try:
                r = requests.get(url, timeout=5)
                if r.status_code == expected:
                    ok = True
                else:
                    info = f'status={r.status_code}'
            except Exception as e:
                info = str(e)
        else:
            info = f'unknown check type: {kind}'
        if ok:
            # reset failure count
            if name in state:
                state.pop(name, None)
            print(f'Check OK: {name}')
        else:
            # increment failure counter
            cnt = last.get('failures', 0) + 1
            state[name] = {'failures': cnt, 'last_failure': datetime.utcnow().isoformat() + 'Z'}
            print(f'Check FAILED: {name} (count={cnt}) info={info}')
            if cnt >= threshold:
                # create follow-up task and reset counter
                create_followup(check, info)
                state.pop(name, None)
        save_state(state)
        # sleep between checks if specified (non-blocking behavior is simple serial loop)
        time.sleep(1)
    # main loop pause
    time.sleep(5)
