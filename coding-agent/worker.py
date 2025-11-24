import os
import time
import json
import requests
import yaml

WORKSPACE = os.environ.get('WORKSPACE', '/workspace')
MANAGER_URL = os.environ.get('MANAGER_URL', 'http://manager:8080')
TASKS_DIR = os.path.join(WORKSPACE, 'tasks')

os.makedirs(TASKS_DIR, exist_ok=True)

print('Coding agent started, workspace:', WORKSPACE, 'manager:', MANAGER_URL)

def read_meta(task_dir):
    meta_file = os.path.join(task_dir, 'meta.json')
    if not os.path.exists(meta_file):
        return None
    with open(meta_file) as f:
        return json.load(f)

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
            if status != 'created':
                continue
            print('Found new task', name)
            # mark in_progress
            requests.post(f"{MANAGER_URL}/api/tasks/{name}/status", json={'status': 'in_progress'})
            # read spec
            spec_path = os.path.join(task_dir, 'spec.yaml')
            spec = {}
            if os.path.exists(spec_path):
                with open(spec_path) as f:
                    try:
                        spec = yaml.safe_load(f)
                    except Exception:
                        spec = {}
            # Simulate opencode work: scaffold a simple static site
            src_dir = os.path.join(task_dir, 'src')
            os.makedirs(src_dir, exist_ok=True)
            index_path = os.path.join(src_dir, 'index.html')
            title = spec.get('title', 'Generated Site')
            html = f"<html><head><title>{title}</title></head><body><h1>{title}</h1><p>Scaffolded by coding-agent.</p></body></html>"
            with open(index_path, 'w') as f:
                f.write(html)
            # mark completed
            requests.post(f"{MANAGER_URL}/api/tasks/{name}/status", json={'status': 'completed'})
            print('Completed task', name)
    except Exception as e:
        print('Worker error', e)
    time.sleep(5)
