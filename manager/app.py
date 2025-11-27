import os
import json
import uuid
from flask import Flask, request, jsonify
from datetime import datetime
import yaml
import jsonschema
import shutil

app = Flask(__name__)
WORKSPACE = os.environ.get('WORKSPACE', '/workspace')
TASKS_DIR = os.path.join(WORKSPACE, 'tasks')
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), 'task_schema.json')
PROJECT_SCHEMA_PATH = os.path.join(os.path.dirname(__file__), '..', 'specs', 'project.schema.json')
# Manager API token for simple auth (optional). If set, requests must provide this token.
MANAGER_API_TOKEN = os.environ.get('MANAGER_API_TOKEN')
from functools import wraps

def auth_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not MANAGER_API_TOKEN:
            return func(*args, **kwargs)
        # Accept Authorization: Bearer <token> or X-Api-Token header
        auth = request.headers.get('Authorization', '')
        token = None
        if auth.startswith('Bearer '):
            token = auth.split(' ', 1)[1].strip()
        if not token:
            token = request.headers.get('X-Api-Token')
        if token != MANAGER_API_TOKEN:
            return jsonify({'error': 'unauthorized'}), 401
        return func(*args, **kwargs)
    return wrapper

# Load schemas
def _load_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None

TASK_SCHEMA = _load_json(SCHEMA_PATH)
PROJECT_SCHEMA = _load_json(PROJECT_SCHEMA_PATH)

os.makedirs(TASKS_DIR, exist_ok=True)

def task_path(task_id):
    return os.path.join(TASKS_DIR, task_id)

@app.route('/api/tasks', methods=['POST'])
@auth_required
def create_task():
    data = request.get_json() or {}
    task_id = data.get('id') or f"task-{uuid.uuid4().hex[:8]}"
    title = data.get('title', 'untitled')
    spec = data.get('spec') or data

    # If the spec looks like a full project manifest and a project schema exists, validate and convert it
    is_project_manifest = False
    if PROJECT_SCHEMA and any(k in spec for k in ('schemaVersion', 'name', 'slug')):
        try:
            jsonschema.validate(instance=spec, schema=PROJECT_SCHEMA)
            is_project_manifest = True
        except jsonschema.ValidationError as e:
            return jsonify({'error': 'project manifest validation failed', 'message': str(e)}), 400

    if is_project_manifest:
        proj = spec
        # Prefer slug from project manifest as task id if available
        if proj.get('slug'):
            task_id = proj.get('slug')
        # Convert project manifest to a task spec for deployment by default
        spec = {
            'id': task_id,
            'title': proj.get('name'),
            'description': proj.get('summary'),
            'owner': (proj.get('contact') or {}).get('maintainer', 'manager'),
            'kind': 'deployment',
            'deploy': True,
            'project': proj
        }
        # If project includes a deployment block, copy it up into the task spec for easier consumption
        if isinstance(proj, dict) and proj.get('deployment'):
            spec['deployment'] = proj.get('deployment')


    # Validate spec against the task schema if available
    if TASK_SCHEMA:
        try:
            jsonschema.validate(instance=spec, schema=TASK_SCHEMA)
        except jsonschema.ValidationError as e:
            return jsonify({'error': 'spec validation failed', 'message': str(e)}), 400

    task_dir = task_path(task_id)
    os.makedirs(task_dir, exist_ok=True)
    spec_path = os.path.join(task_dir, 'spec.yaml')
    meta = {
        'id': task_id,
        'title': title,
        'status': 'created',
        'created_at': datetime.utcnow().isoformat() + 'Z'
    }
    with open(spec_path, 'w') as f:
        yaml.safe_dump(spec, f)

    # If deployment env/secrets are present, persist them under workspace/tasks/<id>/secrets
    deployment = spec.get('deployment') if isinstance(spec, dict) else None
    if deployment:
        secrets_dir = os.path.join(task_dir, 'secrets')
        try:
            os.makedirs(secrets_dir, exist_ok=True)
            # Write env vars as .env file
            env = deployment.get('env') or {}
            if env:
                env_path = os.path.join(secrets_dir, '.env')
                with open(env_path, 'w') as ef:
                    for k, v in env.items():
                        ef.write(f"{k}={v}\n")
                try:
                    os.chmod(env_path, 0o600)
                except Exception:
                    pass
            # Create placeholder secret files for declared secrets (manager won't store secret values in manifest)
            declared = deployment.get('secrets') or []
            for name in declared:
                p = os.path.join(secrets_dir, name)
                if not os.path.exists(p):
                    open(p, 'w').close()
                    try:
                        os.chmod(p, 0o600)
                    except Exception:
                        pass
            # Update meta to indicate secrets present
            meta['secrets'] = True
        except Exception as e:
            print('Failed to write deployment secrets/env for task', task_id, e)

    with open(os.path.join(task_dir, 'meta.json'), 'w') as f:
        json.dump(meta, f)
    return jsonify(meta), 201

@app.route('/api/tasks', methods=['GET'])
def list_tasks():
    tasks = []
    for name in os.listdir(TASKS_DIR):
        d = task_path(name)
        meta_file = os.path.join(d, 'meta.json')
        if os.path.exists(meta_file):
            with open(meta_file) as f:
                tasks.append(json.load(f))
    return jsonify(tasks)

@app.route('/api/tasks/<task_id>', methods=['GET'])
def get_task(task_id):
    d = task_path(task_id)
    meta_file = os.path.join(d, 'meta.json')
    if not os.path.exists(meta_file):
        return jsonify({'error': 'not found'}), 404
    with open(meta_file) as f:
        return jsonify(json.load(f))

@app.route('/api/tasks/<task_id>/status', methods=['POST'])
@auth_required
def update_status(task_id):
    d = task_path(task_id)
    meta_file = os.path.join(d, 'meta.json')
    if not os.path.exists(meta_file):
        return jsonify({'error': 'not found'}), 404
    payload = request.get_json() or {}
    status = payload.get('status')
    if not status:
        return jsonify({'error': 'missing status'}), 400
    with open(meta_file) as f:
        meta = json.load(f)
    meta['status'] = status
    meta['updated_at'] = datetime.utcnow().isoformat() + 'Z'
    with open(meta_file, 'w') as f:
        json.dump(meta, f)
    return jsonify(meta)


@app.route('/api/tasks/<task_id>/deploy', methods=['POST'])
@auth_required
def trigger_deploy(task_id):
    # Mark a task as ready for deploy (deployment-agent will pick it up)
    d = task_path(task_id)
    meta_file = os.path.join(d, 'meta.json')
    if not os.path.exists(meta_file):
        return jsonify({'error': 'not found'}), 404
    with open(meta_file) as f:
        meta = json.load(f)
    meta['status'] = 'ready_for_deploy'
    meta['updated_at'] = datetime.utcnow().isoformat() + 'Z'
    with open(meta_file, 'w') as f:
        json.dump(meta, f)
    return jsonify(meta)


@app.route('/api/tasks/<task_id>/deploys', methods=['GET'])
def get_deploy_history(task_id):
    d = task_path(task_id)
    records_file = os.path.join(d, 'deploy_records.json')
    if not os.path.exists(records_file):
        return jsonify([])
    with open(records_file) as f:
        return jsonify(json.load(f))


@app.route('/api/tasks/<task_id>/tests/latest', methods=['GET'])
@auth_required
def get_latest_test_report(task_id):
    d = task_path(task_id)
    records_file = os.path.join(d, 'test_records.json')
    if not os.path.exists(records_file):
        return jsonify({'error': 'no test records'}), 404
    try:
        with open(records_file) as f:
            records = json.load(f)
    except Exception:
        return jsonify({'error': 'failed to read test records'}), 500
    if not records:
        return jsonify({'error': 'no test records'}), 404
    latest = records[-1]
    report_path = latest.get('report')
    if not report_path:
        return jsonify({'latest': latest})
    # report_path is relative to TASKS_DIR/<task_id>/
    full_report = os.path.join(d, os.path.relpath(report_path, start=task_id))
    if not os.path.exists(full_report):
        return jsonify({'latest': latest, 'warning': 'report file not found'}), 200
    try:
        with open(full_report) as rf:
            content = rf.read()
    except Exception:
        content = None
    return jsonify({'latest': latest, 'report_content': content})


@app.route('/api/tasks/<task_id>/rollback', methods=['POST'])
@auth_required
def rollback_deploy(task_id):
    # Roll back a deployment for a given task to a specified revision timestamp or last revision
    payload = request.get_json() or {}
    revision = payload.get('revision')
    deploy_root = os.path.join(WORKSPACE, 'deploy', task_id)
    if not os.path.exists(deploy_root):
        return jsonify({'error': 'no deploy history for task'}), 404
    revisions_dir = os.path.join(deploy_root, 'revisions')
    if not os.path.exists(revisions_dir):
        return jsonify({'error': 'no revisions available'}), 404
    # Determine target revision
    if revision:
        target = os.path.join(revisions_dir, revision)
        if not os.path.exists(target):
            return jsonify({'error': 'specified revision not found'}), 404
    else:
        # pick most recent revision
        revs = sorted(os.listdir(revisions_dir))
        if not revs:
            return jsonify({'error': 'no revisions available'}), 404
        target = os.path.join(revisions_dir, revs[-1])
    current_dir = os.path.join(deploy_root, 'current')
    if os.path.exists(current_dir):
        # archive current
        archived = os.path.join(revisions_dir, datetime.utcnow().strftime('%Y%m%dT%H%M%SZ') + '_rollback')
        shutil.move(current_dir, archived)
    # restore target
    restored = os.path.join(deploy_root, 'restored_tmp')
    if os.path.exists(restored):
        shutil.rmtree(restored)
    shutil.copytree(target, restored)
    if os.path.exists(current_dir):
        shutil.rmtree(current_dir)
    os.rename(restored, current_dir)
    # Update task meta
    d = task_path(task_id)
    meta_file = os.path.join(d, 'meta.json')
    if os.path.exists(meta_file):
        with open(meta_file) as f:
            meta = json.load(f)
        meta['status'] = 'rolled_back'
        meta['updated_at'] = datetime.utcnow().isoformat() + 'Z'
        with open(meta_file, 'w') as f:
            json.dump(meta, f)
    return jsonify({'result': 'rolled_back', 'restored_from': os.path.basename(target)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
