import os
import time
import json
import requests
import yaml

WORKSPACE = os.environ.get('WORKSPACE', '/workspace')
MANAGER_URL = os.environ.get('MANAGER_URL', 'http://manager:8080')
MANAGER_API_TOKEN = os.environ.get('MANAGER_API_TOKEN')
TASKS_DIR = os.path.join(WORKSPACE, 'tasks')

os.makedirs(TASKS_DIR, exist_ok=True)

HEADERS = {}
if MANAGER_API_TOKEN:
    HEADERS['Authorization'] = f"Bearer {MANAGER_API_TOKEN}"

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
            requests.post(f"{MANAGER_URL}/api/tasks/{name}/status", json={'status': 'in_progress'}, headers=HEADERS)
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
            # After scaffolding, attempt GitHub PR flow if configured
            try:
                github_repo = os.environ.get('GITHUB_REPO')  # expected form: owner/repo
                github_token = os.environ.get('GITHUB_TOKEN')
                github_user = os.environ.get('GITHUB_USER', 'devsys-bot')
                github_email = os.environ.get('GITHUB_EMAIL', 'devsys-bot@example.com')
                dry_run = os.environ.get('GITHUB_DRY_RUN', '').lower() == 'true'
                if github_repo and github_token:
                    branch = f"task/{name}"
                    src_repo = src_dir
                    # Initialize git repo and commit
                    import subprocess
                    try:
                        subprocess.check_call(['git', 'init'], cwd=src_repo)
                        subprocess.check_call(['git', 'config', 'user.name', github_user], cwd=src_repo)
                        subprocess.check_call(['git', 'config', 'user.email', github_email], cwd=src_repo)
                        subprocess.check_call(['git', 'add', '.'], cwd=src_repo)
                        subprocess.check_call(['git', 'commit', '-m', f"Scaffold for task {name}"], cwd=src_repo)
                        # add remote using token in URL
                        owner_repo = github_repo.strip()
                        remote_url = f"https://{github_token}:x-oauth-basic@github.com/{owner_repo}.git"
                        subprocess.check_call(['git', 'remote', 'add', 'origin', remote_url], cwd=src_repo)
                        # create and push branch
                        subprocess.check_call(['git', 'checkout', '-b', branch], cwd=src_repo)
                        if not dry_run:
                            subprocess.check_call(['git', 'push', '--set-upstream', 'origin', branch], cwd=src_repo)
                        else:
                            print('GITHUB_DRY_RUN enabled; skipping push')
                    except Exception as e:
                        print('GitHub PR flow failed at git ops', e)
                        raise

                    # Create or update PR via GitHub API
                    try:
                        if not dry_run:
                            headers = {'Authorization': f'token {github_token}', 'Accept': 'application/vnd.github.v3+json'}
                            api_url = f'https://api.github.com/repos/{owner_repo}/pulls'
                            pr_payload = {'title': f'Task {name}: {title}', 'head': branch, 'base': 'main', 'body': f'Automated PR for task {name} (scaffold).'}
                            r = requests.post(api_url, json=pr_payload, headers=headers, timeout=10)
                            if r.status_code in (200, 201):
                                pr = r.json()
                                pr_url = pr.get('html_url')
                                print('Created PR:', pr_url)
                            elif r.status_code == 422:
                                # PR may already exist; attempt to find existing PR and update
                                search_url = f'https://api.github.com/search/issues?q=repo:{owner_repo}+head:{branch}+type:pr'
                                sr = requests.get(search_url, headers=headers, timeout=10)
                                if sr.status_code == 200:
                                    items = sr.json().get('items', [])
                                    if items:
                                        pr_url = items[0].get('html_url')
                                        print('Existing PR found:', pr_url)
                                    else:
                                        print('PR creation failed', r.status_code, r.text)
                                else:
                                    print('PR search failed', sr.status_code, sr.text)
                            else:
                                print('PR creation failed', r.status_code, r.text)
                        else:
                            print('GITHUB_DRY_RUN enabled; skipping PR creation')
                    except Exception as e:
                        print('GitHub PR flow failed at API step', e)
            except Exception:
                # don't block task completion on PR failures
                pass

            # mark completed
            requests.post(f"{MANAGER_URL}/api/tasks/{name}/status", json={'status': 'completed'}, headers=HEADERS)
            print('Completed task', name)
    except Exception as e:
        print('Worker error', e)
    time.sleep(5)
