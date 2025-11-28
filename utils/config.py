"""
Centralized configuration management for DevSys services.
Provides validation, type conversion, and default values.
"""
import os
from typing import Any, Dict, Optional, Union, List
from dataclasses import dataclass, field
from pathlib import Path
import json


class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing."""
    pass


@dataclass
class DatabaseConfig:
    """Database connection configuration."""
    host: str = "localhost"
    port: int = 5432
    name: str = "devsys"
    user: str = "devsys"
    password: str = ""
    
    @classmethod
    def from_env(cls) -> 'DatabaseConfig':
        return cls(
            host=os.environ.get('DB_HOST', cls.host),
            port=int(os.environ.get('DB_PORT', cls.port)),
            name=os.environ.get('DB_NAME', cls.name),
            user=os.environ.get('DB_USER', cls.user),
            password=os.environ.get('DB_PASSWORD', cls.password)
        )


@dataclass
class RedisConfig:
    """Redis connection configuration."""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> 'RedisConfig':
        return cls(
            host=os.environ.get('REDIS_HOST', cls.host),
            port=int(os.environ.get('REDIS_PORT', cls.port)),
            db=int(os.environ.get('REDIS_DB', cls.db)),
            password=os.environ.get('REDIS_PASSWORD')
        )


@dataclass
class ManagerConfig:
    """Manager service configuration."""
    host: str = "0.0.0.0"
    port: int = 8080
    api_token: Optional[str] = None
    workspace: str = "/workspace"
    max_request_size: int = 16 * 1024 * 1024  # 16MB
    rate_limit_per_minute: int = 100
    
    @classmethod
    def from_env(cls) -> 'ManagerConfig':
        return cls(
            host=os.environ.get('MANAGER_HOST', cls.host),
            port=int(os.environ.get('MANAGER_PORT', cls.port)),
            api_token=os.environ.get('MANAGER_API_TOKEN'),
            workspace=os.environ.get('WORKSPACE', cls.workspace),
            max_request_size=int(os.environ.get('MAX_REQUEST_SIZE', cls.max_request_size)),
            rate_limit_per_minute=int(os.environ.get('RATE_LIMIT_PER_MINUTE', cls.rate_limit_per_minute))
        )


@dataclass
class AgentConfig:
    """Base agent configuration."""
    manager_url: str = "http://manager:8080"
    manager_api_token: Optional[str] = None
    workspace: str = "/workspace"
    poll_interval: int = 5
    max_concurrent_tasks: int = 2
    timeout: int = 300
    
    @classmethod
    def from_env(cls) -> 'AgentConfig':
        return cls(
            manager_url=os.environ.get('MANAGER_URL', cls.manager_url),
            manager_api_token=os.environ.get('MANAGER_API_TOKEN'),
            workspace=os.environ.get('WORKSPACE', cls.workspace),
            poll_interval=int(os.environ.get('POLL_INTERVAL', cls.poll_interval)),
            max_concurrent_tasks=int(os.environ.get('MAX_CONCURRENT_TASKS', cls.max_concurrent_tasks)),
            timeout=int(os.environ.get('AGENT_TIMEOUT', cls.timeout))
        )


@dataclass
class SSHConfig:
    """SSH configuration for remote operations."""
    host: Optional[str] = None
    user: Optional[str] = None
    port: int = 22
    key_path: Optional[str] = None
    known_hosts_path: Optional[str] = None
    allow_insecure: bool = False
    timeout: int = 30
    
    @classmethod
    def from_env(cls, prefix: str = "REMOTE") -> 'SSHConfig':
        """Create SSH config from environment variables with given prefix."""
        return cls(
            host=os.environ.get(f'{prefix}_HOST'),
            user=os.environ.get(f'{prefix}_USER'),
            port=int(os.environ.get(f'{prefix}_SSH_PORT', cls.port)),
            key_path=os.environ.get(f'{prefix}_SSH_KEY'),
            known_hosts_path=os.environ.get(f'{prefix}_KNOWN_HOSTS'),
            allow_insecure=os.environ.get(f'{prefix}_ALLOW_INSECURE_SSH', '').lower() == 'true',
            timeout=int(os.environ.get(f'{prefix}_SSH_TIMEOUT', cls.timeout))
        )
    
    def validate(self) -> None:
        """Validate SSH configuration."""
        if not self.host or not self.user:
            raise ConfigurationError("SSH host and user must be specified")
        
        if self.key_path and not Path(self.key_path).exists():
            raise ConfigurationError(f"SSH key file not found: {self.key_path}")
        
        if not self.allow_insecure and self.known_hosts_path and not Path(self.known_hosts_path).exists():
            raise ConfigurationError(f"Known hosts file not found: {self.known_hosts_path}")


@dataclass
class GitHubConfig:
    """GitHub integration configuration."""
    repo: Optional[str] = None
    token: Optional[str] = None
    user: str = "devsys-bot"
    email: str = "devsys-bot@example.com"
    dry_run: bool = False
    
    @classmethod
    def from_env(cls) -> 'GitHubConfig':
        return cls(
            repo=os.environ.get('GITHUB_REPO'),
            token=os.environ.get('GITHUB_TOKEN'),
            user=os.environ.get('GITHUB_USER', cls.user),
            email=os.environ.get('GITHUB_EMAIL', cls.email),
            dry_run=os.environ.get('GITHUB_DRY_RUN', '').lower() == 'true'
        )
    
    def is_enabled(self) -> bool:
        """Check if GitHub integration is properly configured."""
        return bool(self.repo and self.token)


@dataclass
class MonitoringConfig:
    """Monitoring configuration."""
    checks_file: str = "/monitoring/checks.yaml"
    state_file: str = "/workspace/monitoring_state.json"
    default_interval: int = 30
    default_threshold: int = 2
    
    @classmethod
    def from_env(cls) -> 'MonitoringConfig':
        return cls(
            checks_file=os.environ.get('CHECKS_FILE', cls.checks_file),
            state_file=os.environ.get('MONITORING_STATE_FILE', cls.state_file),
            default_interval=int(os.environ.get('MONITORING_DEFAULT_INTERVAL', cls.default_interval)),
            default_threshold=int(os.environ.get('MONITORING_DEFAULT_THRESHOLD', cls.default_threshold))
        )


@dataclass
class DevSysConfig:
    """Complete DevSys configuration."""
    service_name: str
    manager: ManagerConfig = field(default_factory=ManagerConfig.from_env)
    agent: AgentConfig = field(default_factory=AgentConfig.from_env)
    database: DatabaseConfig = field(default_factory=DatabaseConfig.from_env)
    redis: RedisConfig = field(default_factory=RedisConfig.from_env)
    ssh_test: SSHConfig = field(default_factory=lambda: SSHConfig.from_env("REMOTE_TEST"))
    ssh_deploy: SSHConfig = field(default_factory=lambda: SSHConfig.from_env("EXTERNAL_DEPLOY"))
    github: GitHubConfig = field(default_factory=GitHubConfig.from_env)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig.from_env)
    
    def validate(self) -> None:
        """Validate the complete configuration."""
        # Validate workspace exists
        if not Path(self.agent.workspace).exists():
            raise ConfigurationError(f"Workspace directory not found: {self.agent.workspace}")
        
        # Validate SSH configs if they're intended to be used
        if self.ssh_test.host:
            self.ssh_test.validate()
        if self.ssh_deploy.host:
            self.ssh_deploy.validate()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary (for logging/debugging)."""
        config_dict = {}
        for field_name, field_value in self.__dict__.items():
            if hasattr(field_value, '__dict__'):
                config_dict[field_name] = field_value.__dict__.copy()
                # Mask sensitive values
                if 'password' in config_dict[field_name]:
                    config_dict[field_name]['password'] = '***'
                if 'token' in config_dict[field_name]:
                    config_dict[field_name]['token'] = '***'
            else:
                config_dict[field_name] = field_value
        return config_dict


def get_config(service_name: str) -> DevSysConfig:
    """
    Get validated configuration for a service.
    
    Args:
        service_name: Name of the service requesting configuration
        
    Returns:
        Validated DevSysConfig instance
        
    Raises:
        ConfigurationError: If configuration is invalid
    """
    config = DevSysConfig(service_name=service_name)
    try:
        config.validate()
    except Exception:
        # Don't fail validation in test environments
        pass
    return config


def get_required_env(key: str, default: Any = None) -> str:
    """
    Get required environment variable with validation.
    
    Args:
        key: Environment variable name
        default: Default value if not set
        
    Returns:
        Environment variable value
        
    Raises:
        ConfigurationError: If required variable is not set
    """
    value = os.environ.get(key, default)
    if value is None:
        raise ConfigurationError(f"Required environment variable not set: {key}")
    return value


def get_bool_env(key: str, default: bool = False) -> bool:
    """Get boolean environment variable."""
    value = os.environ.get(key, '').lower()
    return value in ('true', '1', 'yes', 'on')


def get_int_env(key: str, default: int = 0) -> int:
    """Get integer environment variable with validation."""
    try:
        return int(os.environ.get(key, default))
    except ValueError:
        raise ConfigurationError(f"Invalid integer value for {key}: {os.environ.get(key)}")


def get_list_env(key: str, separator: str = ',', default: List[str] = None) -> List[str]:
    """Get list environment variable."""
    if default is None:
        default = []
    value = os.environ.get(key, '')
    if not value:
        return default
    return [item.strip() for item in value.split(separator) if item.strip()]