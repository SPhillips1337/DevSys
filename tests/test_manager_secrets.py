import os
import json
import importlib
import sys

import pytest


def test_upload_env_writes_env_file(tmp_path, monkeypatch):
    # set workspace
    monkeypatch.setenv('WORKSPACE', str(tmp_path))
    # ensure fresh import
    if 'manager.app' in sys.modules:
        del sys.modules['manager.app']
    manager = importlib.import_module('manager.app')
    client = manager.app.test_client()

    # create a task via POST using sample manifest
    repo_root = os.path.dirname(manager.__file__)
    specs_path = os.path.normpath(os.path.join(repo_root, '..', 'specs', 'create-blog.json'))
    with open(specs_path) as f:
        payload = json.load(f)
    headers = {}
    token = os.environ.get('MANAGER_API_TOKEN')
    if token:
        headers['Authorization'] = f"Bearer {token}"
    resp = client.post('/api/tasks', json=payload, headers=headers)
    assert resp.status_code == 201
    meta = resp.get_json()
    task_id = meta['id']

    # upload env JSON
    env_payload = {'env': {'OLLAMA_URL': 'https://example/', 'OLLAMA_KEY': 'secret'}}
    resp = client.post(f'/api/tasks/{task_id}/secrets', json=env_payload, headers=headers)
    assert resp.status_code == 201
    data = resp.get_json()
    assert '.env' in data['files']

    # check file exists and contents
    secrets_dir = tmp_path / 'tasks' / task_id / 'secrets'
    env_file = secrets_dir / '.env'
    assert env_file.exists()
    content = env_file.read_text()
    assert 'OLLAMA_URL=https://example/' in content
    assert 'OLLAMA_KEY=secret' in content

    # meta updated
    meta_file = tmp_path / 'tasks' / task_id / 'meta.json'
    assert meta_file.exists()
    m = json.loads(meta_file.read_text())
    assert m.get('secrets') is True
    assert '.env' in m.get('secret_files', [])


def test_file_upload_saves_file(tmp_path, monkeypatch):
    monkeypatch.setenv('WORKSPACE', str(tmp_path))
    if 'manager.app' in sys.modules:
        del sys.modules['manager.app']
    manager = importlib.import_module('manager.app')
    client = manager.app.test_client()

    # create a task
    repo_root = os.path.dirname(manager.__file__)
    specs_path = os.path.normpath(os.path.join(repo_root, '..', 'specs', 'create-blog.json'))
    with open(specs_path) as f:
        payload = json.load(f)
    headers = {}
    token = os.environ.get('MANAGER_API_TOKEN')
    if token:
        headers['Authorization'] = f"Bearer {token}"
    resp = client.post('/api/tasks', json=payload, headers=headers)
    assert resp.status_code == 201
    meta = resp.get_json()
    task_id = meta['id']

    import io
    data = {'file1': (io.BytesIO(b'secret-data'), 'mykey.pem')}
    # Flask test client expects content_type multipart/form-data when sending files
    resp = client.post(f'/api/tasks/{task_id}/secrets', data=data, content_type='multipart/form-data', headers=headers)
    assert resp.status_code == 201
    res = resp.get_json()
    assert 'mykey.pem' in res['files']
    secrets_dir = tmp_path / 'tasks' / task_id / 'secrets'
    assert (secrets_dir / 'mykey.pem').exists()
    assert (secrets_dir / 'mykey.pem').read_bytes() == b'secret-data'
