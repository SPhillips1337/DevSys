import os
import json
import importlib
import sys
import tempfile

import yaml
import pytest


def test_post_project_manifest_creates_task(tmp_path, monkeypatch):
    # Set WORKSPACE to a fresh temporary directory before importing the manager app
    monkeypatch.setenv('WORKSPACE', str(tmp_path))

    # Ensure fresh import of the manager app so it picks up the env var
    if 'manager.app' in sys.modules:
        del sys.modules['manager.app']
    manager = importlib.import_module('manager.app')

    client = manager.app.test_client()

    # Load the sample project manifest (JSON) from specs/create-blog.json
    repo_root = os.path.dirname(manager.__file__)
    specs_path = os.path.normpath(os.path.join(repo_root, '..', 'specs', 'create-blog.json'))
    assert os.path.exists(specs_path), f"spec file not found: {specs_path}"
    with open(specs_path) as f:
        payload = json.load(f)

    # If the manager requires API token auth, include it in headers
    headers = {}
    token = os.environ.get('MANAGER_API_TOKEN')
    if token:
        headers['Authorization'] = f"Bearer {token}"
    resp = client.post('/api/tasks', json=payload, headers=headers)
    assert resp.status_code == 201, resp.get_data(as_text=True)
    meta = resp.get_json()
    assert 'id' in meta

    task_dir = os.path.join(str(tmp_path), 'tasks', meta['id'])
    spec_file = os.path.join(task_dir, 'spec.yaml')
    meta_file = os.path.join(task_dir, 'meta.json')

    assert os.path.isdir(task_dir), 'task directory was not created'
    assert os.path.exists(spec_file), 'spec.yaml not written'
    assert os.path.exists(meta_file), 'meta.json not written'

    # Load written spec and check it contains embedded project manifest
    with open(spec_file) as f:
        written = yaml.safe_load(f)
    assert 'project' in written, 'original project manifest not embedded in saved spec'
    assert written['project']['slug'] == payload['slug']
