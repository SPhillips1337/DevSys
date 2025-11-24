import os
import time
import json
import yaml
import subprocess
import requests
from datetime import datetime

WORKSPACE = os.environ.get('WORKSPACE', '/workspace')
MANAGER_URL = os.environ.get('MANAGER_URL', 'http://manager:8080')
MANAGER_API_TOKEN = os.environ.get('MANAGER_API_TOKEN')
TASKS_DIR = os.path.join(WORKSPACE, 'tasks')

os.makedirs(TASKS_DIR, exist_ok=True)

HEADERS = {}
if MANAGER_API_TOKEN:
    HEADERS['Authorization'] = f"Bearer {MANAGER_API_TOKEN}"

print('Testing agent started, workspace:', WORKSPACE, 'manager:', MANAGER_URL)


def read_meta(task_dir):
    meta_file = os.path.join(task_dir, 'meta.json')
    if not os.path.exists(meta_file):
        return None
    with open(meta_file) as f:
        return json.load(f)


def run_tests(task_dir, spec, run_dir=None):
    # run_dir: directory where the tests should be executed (defaults to task_dir)
    reports_dir = os.path.join(task_dir, 'reports')
    os.makedirs(reports_dir, exist_ok=True)
    target_dir = run_dir or task_dir
    # Prefer an explicit run-tests.sh in the target dir
    test_script = os.path.join(target_dir, 'run-tests.sh')
    # Or tests defined in spec: tests -> run
    spec_tests = spec.get('tests') if spec else None
    if os.path.exists(test_script) and os.access(test_script, os.X_OK):
        cmd = [test_script]
    elif spec_tests and isinstance(spec_tests, list) and isinstance(spec_tests[0], dict) and 'run' in spec_tests[0]:
        cmd = ['/bin/sh', '-c', spec_tests[0]['run']]
    else:
        # No tests to run
        return True, 'no_tests'

    timestamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    report_file = os.path.join(reports_dir, f'test-report-{timestamp}.txt')
    try:
        proc = subprocess.run(cmd, cwd=target_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
        output = proc.stdout.decode('utf-8', errors='replace')
        with open(report_file, 'w') as f:
            f.write(output)
        success = proc.returncode == 0
        return success, report_file
    except subprocess.TimeoutExpired as e:
        with open(report_file, 'w') as f:
            f.write(f'Timeout: {e}\n')
        return False, report_file
    except Exception as e:
        with open(report_file, 'w') as f:
            f.write(f'Error running tests: {e}\n')
        return False, report_file


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
            # Look for completed tasks that haven't been tested yet
            if status not in ('completed', 'ready_for_test'):
                continue
            spec = {}
            spec_path = os.path.join(task_dir, 'spec.yaml')
            if os.path.exists(spec_path):
                try:
                    with open(spec_path) as f:
                        spec = yaml.safe_load(f) or {}
                except Exception:
                    spec = {}
            # Determine if tests should run in a related task dir
            related = spec.get('related_task') if spec else None
            run_dir = None
            if related:
                run_dir = os.path.join(TASKS_DIR, related)
            # Run tests if present
            ok, info = run_tests(task_dir, spec, run_dir=run_dir)
            if info and info != 'no_tests':
                report_rel = os.path.relpath(info, TASKS_DIR)
            else:
                report_rel = info
            if info == 'no_tests':
                # mark as tested but note no tests
                try:
                    requests.post(f"{MANAGER_URL}/api/tasks/{name}/status", json={'status': 'tested'}, headers=HEADERS, timeout=5)
                except Exception as e:
                    print('Failed to update manager status', e)
                continue
            # Update manager status and record report path in task dir
            try:
                new_status = 'tested' if ok else 'failed'
                requests.post(f"{MANAGER_URL}/api/tasks/{name}/status", json={'status': new_status}, headers=HEADERS, timeout=5)
            except Exception as e:
                print('Failed to update manager status', e)
            # write a small metadata entry
            records_file = os.path.join(task_dir, 'test_records.json')
            rec = {'timestamp': datetime.utcnow().isoformat() + 'Z', 'ok': ok, 'report': report_rel}
            records = []
            if os.path.exists(records_file):
                try:
                    with open(records_file) as f:
                        records = json.load(f)
                except Exception:
                    records = []
            records.append(rec)
            with open(records_file, 'w') as f:
                json.dump(records, f)
            print(f'Tested task {name}: ok={ok} report={report_rel}')
    except Exception as e:
        print('Testing worker error', e)
    time.sleep(5)
