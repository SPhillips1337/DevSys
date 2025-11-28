"""
Comprehensive test suite for the improved manager service.
Tests the new error handling, logging, and configuration features.
"""
import os
import sys
import json
import tempfile
import shutil
import pytest
from unittest.mock import patch, MagicMock

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set test environment variables before importing
os.environ['TESTING'] = 'true'
os.environ['LOG_LEVEL'] = 'DEBUG'

from manager.app import app
from utils.exceptions import ValidationError, AuthenticationError, FilesystemError
from utils.config import DevSysConfig


class TestManagerImproved:
    """Test suite for the improved manager service."""
    
    @pytest.fixture
    def client(self):
        """Create a test client with temporary workspace."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Set up test environment
            os.environ['WORKSPACE'] = temp_dir
            os.environ['MANAGER_API_TOKEN'] = 'test-token-123'
            
            app.config['TESTING'] = True
            app.config['WORKSPACE'] = temp_dir
            
            with app.test_client() as client:
                yield client
    
    @pytest.fixture
    def auth_headers(self):
        """Authentication headers for API requests."""
        return {'Authorization': 'Bearer test-token-123'}
    
    def test_create_task_success(self, client, auth_headers):
        """Test successful task creation."""
        task_data = {
            'id': 'test-task-001',
            'title': 'Test Task',
            'spec': {
                'description': 'A test task',
                'owner': 'test-user',
                'kind': 'deployment',
                'deploy': True
            }
        }
        
        response = client.post('/api/tasks', 
                             json=task_data, 
                             headers=auth_headers)
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['id'] == 'test-task-001'
        assert data['title'] == 'Test Task'
        assert data['status'] == 'created'
        assert 'created_at' in data
    
    def test_create_task_invalid_id(self, client, auth_headers):
        """Test task creation with invalid ID."""
        task_data = {
            'id': '../invalid-id',
            'title': 'Invalid Task'
        }
        
        response = client.post('/api/tasks', 
                             json=task_data, 
                             headers=auth_headers)
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'error_type' in data
        assert data['error_type'] == 'ValidationError'
    
    def test_create_task_duplicate_id(self, client, auth_headers):
        """Test creating task with duplicate ID."""
        task_data = {
            'id': 'duplicate-task',
            'title': 'First Task'
        }
        
        # Create first task
        response1 = client.post('/api/tasks', 
                              json=task_data, 
                              headers=auth_headers)
        assert response1.status_code == 201
        
        # Try to create duplicate
        response2 = client.post('/api/tasks', 
                              json=task_data, 
                              headers=auth_headers)
        assert response2.status_code == 400
        data = response2.get_json()
        assert 'already exists' in data['message']
    
    def test_authentication_required(self, client):
        """Test that authentication is required when token is set."""
        task_data = {'title': 'Unauthorized Task'}
        
        response = client.post('/api/tasks', json=task_data)
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['error_type'] == 'AuthenticationError'
    
    def test_authentication_with_x_api_token(self, client):
        """Test authentication using X-Api-Token header."""
        task_data = {'title': 'Test Task'}
        headers = {'X-Api-Token': 'test-token-123'}
        
        response = client.post('/api/tasks', 
                             json=task_data, 
                             headers=headers)
        
        assert response.status_code == 201
    
    def test_get_task_success(self, client, auth_headers):
        """Test retrieving an existing task."""
        # Create task first
        task_data = {
            'id': 'get-test-task',
            'title': 'Get Test Task'
        }
        client.post('/api/tasks', json=task_data, headers=auth_headers)
        
        # Retrieve task
        response = client.get('/api/tasks/get-test-task')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['id'] == 'get-test-task'
        assert data['title'] == 'Get Test Task'
    
    def test_get_task_not_found(self, client):
        """Test retrieving non-existent task."""
        response = client.get('/api/tasks/non-existent-task')
        
        assert response.status_code == 404
        data = response.get_json()
        assert 'not found' in data['error']
    
    def test_list_tasks(self, client, auth_headers):
        """Test listing all tasks."""
        # Create multiple tasks
        for i in range(3):
            task_data = {
                'id': f'list-task-{i}',
                'title': f'List Task {i}'
            }
            client.post('/api/tasks', json=task_data, headers=auth_headers)
        
        # List tasks
        response = client.get('/api/tasks')
        
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 3
        assert all('id' in task for task in data)
    
    def test_update_task_status(self, client, auth_headers):
        """Test updating task status."""
        # Create task
        task_data = {
            'id': 'status-test-task',
            'title': 'Status Test Task'
        }
        client.post('/api/tasks', json=task_data, headers=auth_headers)
        
        # Update status
        response = client.post('/api/tasks/status-test-task/status',
                             json={'status': 'in_progress'},
                             headers=auth_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'in_progress'
        assert 'updated_at' in data
    
    def test_trigger_deploy(self, client, auth_headers):
        """Test triggering deployment."""
        # Create task
        task_data = {
            'id': 'deploy-test-task',
            'title': 'Deploy Test Task'
        }
        client.post('/api/tasks', json=task_data, headers=auth_headers)
        
        # Trigger deploy
        response = client.post('/api/tasks/deploy-test-task/deploy',
                             headers=auth_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'ready_for_deploy'
    
    def test_deployment_secrets_handling(self, client, auth_headers):
        """Test handling of deployment secrets."""
        task_data = {
            'id': 'secrets-test-task',
            'title': 'Secrets Test Task',
            'spec': {
                'deployment': {
                    'env': {
                        'API_KEY': 'test-key',
                        'DATABASE_URL': 'test-db-url'
                    },
                    'secrets': ['private-key.pem', 'config.json']
                }
            }
        }
        
        response = client.post('/api/tasks',
                             json=task_data,
                             headers=auth_headers)
        
        assert response.status_code == 201
        data = response.get_json()
        assert data.get('secrets') is True
    
    def test_upload_secrets(self, client, auth_headers):
        """Test uploading secrets for a task."""
        # Create task first
        task_data = {
            'id': 'upload-secrets-task',
            'title': 'Upload Secrets Task'
        }
        client.post('/api/tasks', json=task_data, headers=auth_headers)
        
        # Upload secrets
        secrets_data = {
            'env': {
                'SECRET_KEY': 'super-secret',
                'API_TOKEN': 'api-token-123'
            }
        }
        
        response = client.post('/api/tasks/upload-secrets-task/secrets',
                             json=secrets_data,
                             headers=auth_headers)
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['result'] == 'ok'
        assert '.env' in data['files']
    
    def test_list_secrets(self, client, auth_headers):
        """Test listing secrets for a task."""
        # Create task and upload secrets
        task_data = {
            'id': 'list-secrets-task',
            'title': 'List Secrets Task'
        }
        client.post('/api/tasks', json=task_data, headers=auth_headers)
        
        secrets_data = {'env': {'TEST_KEY': 'test-value'}}
        client.post('/api/tasks/list-secrets-task/secrets',
                   json=secrets_data,
                   headers=auth_headers)
        
        # List secrets
        response = client.get('/api/tasks/list-secrets-task/secrets')
        
        assert response.status_code == 200
        data = response.get_json()
        assert '.env' in data['files']
    
    def test_configuration_validation(self):
        """Test configuration validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.environ['WORKSPACE'] = temp_dir
            
            # This should not raise an exception
            from utils.config import get_config
            config = get_config('manager')
            assert config.service_name == 'manager'
            assert config.agent.workspace == temp_dir


class TestManagerSecurity:
    """Security-focused tests for the manager service."""
    
    @pytest.fixture
    def client(self):
        """Create a test client with security settings."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.environ['WORKSPACE'] = temp_dir
            os.environ['MANAGER_API_TOKEN'] = 'secure-token-456'
            
            app.config['TESTING'] = True
            with app.test_client() as client:
                yield client
    
    def test_path_traversal_protection(self, client):
        """Test protection against path traversal attacks."""
        headers = {'Authorization': 'Bearer secure-token-456'}
        
        # Try to access parent directory
        response = client.get('/api/tasks/../../../etc/passwd')
        assert response.status_code == 404
        
        # Try to create task with path traversal in ID
        task_data = {
            'id': '../../../malicious-task',
            'title': 'Malicious Task'
        }
        response = client.post('/api/tasks', json=task_data, headers=headers)
        assert response.status_code == 400
    
    def test_input_sanitization(self, client):
        """Test input sanitization."""
        headers = {'Authorization': 'Bearer secure-token-456'}
        
        # Test with potentially dangerous characters
        task_data = {
            'id': 'test<script>alert("xss")</script>',
            'title': 'XSS Test Task'
        }
        
        response = client.post('/api/tasks', json=task_data, headers=headers)
        assert response.status_code == 400
    
    def test_token_validation(self, client):
        """Test API token validation."""
        task_data = {'title': 'Test Task'}
        
        # No token
        response = client.post('/api/tasks', json=task_data)
        assert response.status_code == 400
        
        # Invalid token
        headers = {'Authorization': 'Bearer invalid-token'}
        response = client.post('/api/tasks', json=task_data, headers=headers)
        assert response.status_code == 400
        
        # Valid token
        headers = {'Authorization': 'Bearer secure-token-456'}
        response = client.post('/api/tasks', json=task_data, headers=headers)
        assert response.status_code == 201


if __name__ == '__main__':
    pytest.main([__file__, '-v'])