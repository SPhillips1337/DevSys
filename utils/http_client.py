"""
Centralized HTTP client for DevSys services.
Provides consistent error handling, retries, and authentication.
"""
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Optional, Dict, Any, Union
import json
from .exceptions import NetworkError, AuthenticationError, retry
from .logging_config import get_logger


class DevSysHTTPClient:
    """HTTP client with built-in error handling and retries."""
    
    def __init__(
        self,
        base_url: str,
        api_token: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
        backoff_factor: float = 0.3
    ):
        self.base_url = base_url.rstrip('/')
        self.api_token = api_token
        self.timeout = timeout
        self.logger = get_logger()
        
        # Create session with retry strategy
        self.session = requests.Session()
        
        retry_strategy = Retry(
            total=max_retries,
            status_forcelist=[429, 500, 502, 503, 504],
            method_whitelist=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE"],
            backoff_factor=backoff_factor
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set default headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'DevSys-Agent/1.0'
        })
        
        # Set authentication if provided
        if self.api_token:
            self.session.headers['Authorization'] = f'Bearer {self.api_token}'
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None
    ) -> requests.Response:
        """Make HTTP request with error handling."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        request_timeout = timeout or self.timeout
        
        # Prepare request data
        json_data = None
        if data is not None:
            json_data = data if isinstance(data, str) else json.dumps(data)
        
        # Merge headers
        request_headers = self.session.headers.copy()
        if headers:
            request_headers.update(headers)
        
        self.logger.debug(f"Making {method} request to {url}", extra={
            'method': method,
            'url': url,
            'has_data': data is not None,
            'timeout': request_timeout
        })
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                data=json_data,
                params=params,
                headers=request_headers,
                timeout=request_timeout
            )
            
            self.logger.debug(f"Received response: {response.status_code}", extra={
                'method': method,
                'url': url,
                'status_code': response.status_code,
                'response_size': len(response.content)
            })
            
            return response
            
        except requests.exceptions.Timeout as e:
            raise NetworkError(
                f"Request timeout after {request_timeout}s",
                url=url,
                cause=e
            )
        except requests.exceptions.ConnectionError as e:
            raise NetworkError(
                f"Connection error to {url}",
                url=url,
                cause=e
            )
        except requests.exceptions.RequestException as e:
            raise NetworkError(
                f"Request failed: {str(e)}",
                url=url,
                cause=e
            )
    
    def _handle_response(self, response: requests.Response, endpoint: str) -> Dict[str, Any]:
        """Handle response and extract JSON data."""
        if response.status_code == 401:
            raise AuthenticationError(
                "Authentication failed",
                details={'endpoint': endpoint, 'status_code': response.status_code}
            )
        
        if response.status_code == 403:
            raise AuthenticationError(
                "Access forbidden",
                details={'endpoint': endpoint, 'status_code': response.status_code}
            )
        
        if not response.ok:
            error_msg = f"HTTP {response.status_code}"
            try:
                error_data = response.json()
                if 'error' in error_data:
                    error_msg = error_data['error']
                elif 'message' in error_data:
                    error_msg = error_data['message']
            except (ValueError, KeyError):
                error_msg = response.text or error_msg
            
            raise NetworkError(
                f"Request failed: {error_msg}",
                url=response.url,
                status_code=response.status_code
            )
        
        # Try to parse JSON response
        try:
            return response.json()
        except ValueError:
            # Return empty dict for non-JSON responses
            return {}
    
    def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Make GET request."""
        response = self._make_request('GET', endpoint, params=params, **kwargs)
        return self._handle_response(response, endpoint)
    
    def post(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Make POST request."""
        response = self._make_request('POST', endpoint, data=data, **kwargs)
        return self._handle_response(response, endpoint)
    
    def put(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Make PUT request."""
        response = self._make_request('PUT', endpoint, data=data, **kwargs)
        return self._handle_response(response, endpoint)
    
    def delete(
        self,
        endpoint: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Make DELETE request."""
        response = self._make_request('DELETE', endpoint, **kwargs)
        return self._handle_response(response, endpoint)
    
    def patch(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Make PATCH request."""
        response = self._make_request('PATCH', endpoint, data=data, **kwargs)
        return self._handle_response(response, endpoint)


class ManagerClient(DevSysHTTPClient):
    """Specialized client for Manager API operations."""
    
    def create_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new task."""
        return self.post('/api/tasks', data=task_data)
    
    def get_task(self, task_id: str) -> Dict[str, Any]:
        """Get task details."""
        return self.get(f'/api/tasks/{task_id}')
    
    def list_tasks(self) -> Dict[str, Any]:
        """List all tasks."""
        return self.get('/api/tasks')
    
    def update_task_status(self, task_id: str, status: str) -> Dict[str, Any]:
        """Update task status."""
        return self.post(f'/api/tasks/{task_id}/status', data={'status': status})
    
    def trigger_deploy(self, task_id: str) -> Dict[str, Any]:
        """Trigger task deployment."""
        return self.post(f'/api/tasks/{task_id}/deploy')
    
    def get_deploy_history(self, task_id: str) -> Dict[str, Any]:
        """Get deployment history for task."""
        return self.get(f'/api/tasks/{task_id}/deploys')
    
    def rollback_deploy(self, task_id: str, revision: Optional[str] = None) -> Dict[str, Any]:
        """Rollback task deployment."""
        data = {}
        if revision:
            data['revision'] = revision
        return self.post(f'/api/tasks/{task_id}/rollback', data=data)
    
    def get_test_report(self, task_id: str) -> Dict[str, Any]:
        """Get latest test report for task."""
        return self.get(f'/api/tasks/{task_id}/tests/latest')
    
    def upload_secrets(self, task_id: str, secrets: Dict[str, Any]) -> Dict[str, Any]:
        """Upload secrets for task."""
        return self.post(f'/api/tasks/{task_id}/secrets', data=secrets)
    
    def list_secrets(self, task_id: str) -> Dict[str, Any]:
        """List secrets for task."""
        return self.get(f'/api/tasks/{task_id}/secrets')


def create_manager_client(manager_url: str, api_token: Optional[str] = None) -> ManagerClient:
    """Create a configured manager client."""
    return ManagerClient(
        base_url=manager_url,
        api_token=api_token,
        timeout=30,
        max_retries=3
    )


@retry(max_attempts=3, delay=1.0, exceptions=(NetworkError,))
def safe_api_call(client: DevSysHTTPClient, method: str, *args, **kwargs) -> Optional[Dict[str, Any]]:
    """
    Make a safe API call with retries and error handling.
    
    Args:
        client: HTTP client instance
        method: HTTP method name ('get', 'post', etc.)
        *args: Arguments to pass to the method
        **kwargs: Keyword arguments to pass to the method
        
    Returns:
        API response data or None if call fails
    """
    try:
        method_func = getattr(client, method.lower())
        return method_func(*args, **kwargs)
    except (NetworkError, AuthenticationError) as e:
        logger = get_logger()
        logger.error(f"API call failed: {e}", extra={
            'method': method,
            'error_type': type(e).__name__,
            'error_details': e.to_dict() if hasattr(e, 'to_dict') else str(e)
        })
        return None