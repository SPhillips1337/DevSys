import os
import json
import uuid
import sys
from flask import Flask, request, jsonify
from datetime import datetime
import yaml
import jsonschema
import shutil
from functools import wraps
from werkzeug.utils import secure_filename

# Add utils to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.logging_config import setup_logging, get_logger, log_operation
from utils.config import get_config, ConfigurationError
from utils.exceptions import (
    DevSysError, ValidationError, FilesystemError, 
    AuthenticationError, handle_errors
)

# Initialize logging and configuration
logger = setup_logging('manager')
config = None
try:
    config = get_config('manager')
    logger.info("Manager service starting", extra={'config': config.to_dict()})
except ConfigurationError as e:
    logger.error(f"Configuration error: {e}")
    # Use fallback configuration for testing
    from utils.config import DevSysConfig
    config = DevSysConfig(service_name='manager')

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = config.manager.max_request_size

WORKSPACE = config.agent.workspace
TASKS_DIR = os.path.join(WORKSPACE, 'tasks')
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), 'task_schema.json')
PROJECT_SCHEMA_PATH = os.path.join(os.path.dirname(__file__), '..', 'specs', 'project.schema.json')
MANAGER_API_TOKEN = config.manager.api_token

def auth_required(func):
    """Decorator to require API token authentication."""
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
            logger.warning("Unauthorized API access attempt", extra={
                'endpoint': request.endpoint,
                'remote_addr': request.remote_addr,
                'user_agent': request.headers.get('User-Agent')
            })
            raise AuthenticationError("Invalid or missing API token")
        
        return func(*args, **kwargs)
    return wrapper


@app.errorhandler(DevSysError)
def handle_devsys_error(error):
    """Handle DevSys custom exceptions."""
    logger.error(f"DevSys error: {error.message}", extra=error.to_dict())
    return jsonify(error.to_dict()), 400


@app.errorhandler(Exception)
def handle_generic_error(error):
    """Handle unexpected exceptions."""
    logger.error(f"Unexpected error: {str(error)}", exc_info=True)
    return jsonify({
        'error': 'Internal server error',
        'message': 'An unexpected error occurred'
    }), 500

# Load schemas
@log_operation("load_json_schema")
def _load_json(path):
    """Load JSON schema with error handling."""
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"Schema file not found: {path}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in schema file {path}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error loading schema {path}: {e}")
        return None

TASK_SCHEMA = _load_json(SCHEMA_PATH)
PROJECT_SCHEMA = _load_json(PROJECT_SCHEMA_PATH)

# Lazy initialization flag
_workspace_initialized = False

def ensure_workspace():
    """Ensure workspace directories exist (lazy initialization)."""
    global _workspace_initialized
    if _workspace_initialized:
        return
    
    try:
        os.makedirs(TASKS_DIR, exist_ok=True)
        logger.info(f"Workspace initialized at {WORKSPACE}")
        _workspace_initialized = True
    except OSError as e:
        logger.error(f"Failed to create workspace directory: {e}")
        raise FilesystemError(f"Cannot create workspace directory: {WORKSPACE}", path=WORKSPACE, cause=e)


def task_path(task_id: str) -> str:
    """Get the filesystem path for a task."""
    if not task_id or '..' in task_id or '/' in task_id:
        raise ValidationError("Invalid task ID", field="task_id", value=task_id)
    return os.path.join(TASKS_DIR, task_id)

def _handle_deployment_secrets(task_dir: str, deployment: dict, meta: dict) -> None:
    """Handle deployment secrets and environment variables."""
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
            except OSError:
                logger.warning(f"Could not set permissions on {env_path}")
        
        # Create placeholder secret files for declared secrets
        declared = deployment.get('secrets') or []
        for name in declared:
            if not name or '..' in name or '/' in name:
                logger.warning(f"Skipping invalid secret name: {name}")
                continue
            p = os.path.join(secrets_dir, name)
            if not os.path.exists(p):
                with open(p, 'w') as f:
                    f.write('')  # Create empty placeholder
                try:
                    os.chmod(p, 0o600)
                except OSError:
                    logger.warning(f"Could not set permissions on {p}")
        
        # Update meta to indicate secrets present
        meta['secrets'] = True
        logger.debug(f"Created secrets directory with {len(env)} env vars and {len(declared)} secret files")
        
    except OSError as e:
        logger.error(f"Failed to create deployment secrets: {e}")
        raise FilesystemError("Failed to create secrets directory", path=secrets_dir, cause=e)

@app.route('/api/tasks', methods=['POST'])
@auth_required
@handle_errors("create_task")
def create_task():
    """Create a new task from user input or project manifest."""
    ensure_workspace()  # Lazy initialization
    
    data = request.get_json() or {}
    task_id = data.get('id') or f"task-{uuid.uuid4().hex[:8]}"
    title = data.get('title', 'untitled')
    spec = data.get('spec') or data

    logger.info(f"Creating task {task_id}", extra={
        'task_id': task_id,
        'title': title,
        'has_spec': bool(spec)
    })

    # Validate task ID
    if not task_id.replace('-', '').replace('_', '').isalnum():
        raise ValidationError("Task ID must be alphanumeric with hyphens/underscores only", 
                            field="id", value=task_id)

    # Check if task already exists
    task_dir = task_path(task_id)
    if os.path.exists(task_dir):
        raise ValidationError(f"Task {task_id} already exists", field="id", value=task_id)

    # If the spec looks like a full project manifest and a project schema exists, validate and convert it
    is_project_manifest = False
    if PROJECT_SCHEMA and any(k in spec for k in ('schemaVersion', 'name', 'slug')):
        try:
            jsonschema.validate(instance=spec, schema=PROJECT_SCHEMA)
            is_project_manifest = True
            logger.info(f"Validated project manifest for task {task_id}")
        except jsonschema.ValidationError as e:
            logger.error(f"Project manifest validation failed for task {task_id}: {e}")
            raise ValidationError(f"Project manifest validation failed: {str(e)}")

    if is_project_manifest:
        proj = spec
        # Prefer slug from project manifest as task id if available
        if proj.get('slug'):
            task_id = proj.get('slug')
            task_dir = task_path(task_id)  # Update task_dir with new ID
        
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
            logger.debug(f"Task spec validated for {task_id}")
        except jsonschema.ValidationError as e:
            logger.error(f"Task spec validation failed for {task_id}: {e}")
            raise ValidationError(f"Task spec validation failed: {str(e)}")

    # Create task directory and files
    try:
        os.makedirs(task_dir, exist_ok=True)
        
        spec_path = os.path.join(task_dir, 'spec.yaml')
        with open(spec_path, 'w') as f:
            yaml.safe_dump(spec, f)
        
        meta = {
            'id': task_id,
            'title': title,
            'status': 'created',
            'created_at': datetime.utcnow().isoformat() + 'Z'
        }
        
        # Handle deployment secrets if present
        deployment = spec.get('deployment') if isinstance(spec, dict) else None
        if deployment:
            _handle_deployment_secrets(task_dir, deployment, meta)
        
        meta_path = os.path.join(task_dir, 'meta.json')
        with open(meta_path, 'w') as f:
            json.dump(meta, f, indent=2)
        
        logger.info(f"Task {task_id} created successfully", extra={
            'task_id': task_id,
            'has_secrets': meta.get('secrets', False)
        })
        
        return jsonify(meta), 201
        
    except OSError as e:
        logger.error(f"Failed to create task files for {task_id}: {e}")
        raise FilesystemError(f"Failed to create task directory", path=task_dir, cause=e)

@app.route('/api/tasks/<task_id>/secrets', methods=['POST'])
@auth_required
def upload_task_secrets(task_id):
    """Upload secret files or env dict for a task. Files are saved under workspace/tasks/<id>/secrets with restrictive perms.
    Accepts multipart/form-data files or JSON {"env": {"KEY": "value", ...}}."""
    d = task_path(task_id)
    if not os.path.exists(d):
        return jsonify({'error': 'task not found'}), 404
    secrets_dir = os.path.join(d, 'secrets')
    os.makedirs(secrets_dir, exist_ok=True)
    updated_files = []
    # Handle JSON env payload
    if request.is_json:
        payload = request.get_json() or {}
        env = payload.get('env')
        if isinstance(env, dict):
            env_path = os.path.join(secrets_dir, '.env')
            try:
                with open(env_path, 'w') as ef:
                    for k, v in env.items():
                        ef.write(f"{k}={v}\n")
                try:
                    os.chmod(env_path, 0o600)
                except Exception:
                    pass
                updated_files.append('.env')
            except Exception as e:
                return jsonify({'error': 'failed to write env file', 'message': str(e)}), 500
    # Handle file uploads
    if request.files:
        for key in request.files:
            f = request.files.get(key)
            if f:
                filename = secure_filename(f.filename)
                if not filename:
                    continue
                dest = os.path.join(secrets_dir, filename)
                try:
                    f.save(dest)
                    try:
                        os.chmod(dest, 0o600)
                    except Exception:
                        pass
                    updated_files.append(filename)
                except Exception as e:
                    return jsonify({'error': 'failed to save file', 'file': filename, 'message': str(e)}), 500
    # Update meta
    meta_file = os.path.join(d, 'meta.json')
    try:
        if os.path.exists(meta_file):
            with open(meta_file) as mf:
                meta = json.load(mf)
        else:
            meta = {'id': task_id}
        meta['secrets'] = True
        meta['secret_files'] = sorted(list(set(meta.get('secret_files', []) + updated_files)))
        with open(meta_file, 'w') as mf:
            json.dump(meta, mf)
    except Exception as e:
        return jsonify({'error': 'failed to update meta', 'message': str(e)}), 500
    return jsonify({'result': 'ok', 'files': updated_files}), 201


@app.route('/api/tasks/<task_id>/secrets', methods=['GET'])
def list_task_secrets(task_id):
    d = task_path(task_id)
    if not os.path.exists(d):
        return jsonify({'error': 'task not found'}), 404
    secrets_dir = os.path.join(d, 'secrets')
    if not os.path.exists(secrets_dir):
        return jsonify({'files': []})
    files = [f for f in os.listdir(secrets_dir) if os.path.isfile(os.path.join(secrets_dir, f))]
    return jsonify({'files': files})


@app.route('/api/tasks', methods=['GET'])
def list_tasks():
    ensure_workspace()  # Lazy initialization
    tasks = []
    if os.path.exists(TASKS_DIR):
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
