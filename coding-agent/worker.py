import os
import sys
import time
import json
import yaml
import signal
import subprocess
from datetime import datetime
from typing import Optional, Dict, Any

# Add utils to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.logging_config import setup_logging, get_task_logger, log_operation
from utils.config import get_config, ConfigurationError
from utils.http_client import create_manager_client
from utils.exceptions import (
    DevSysError, TaskProcessingError, ExternalServiceError,
    NetworkError, handle_errors, retry
)

# Initialize logging and configuration
logger = setup_logging('coding-agent')
try:
    config = get_config('coding-agent')
    logger.info("Coding agent starting", extra={'config': config.to_dict()})
except ConfigurationError as e:
    logger.error(f"Configuration error: {e}")
    sys.exit(1)

# Initialize HTTP client
manager_client = create_manager_client(config.agent.manager_url, config.agent.manager_api_token)

WORKSPACE = config.agent.workspace
TASKS_DIR = os.path.join(WORKSPACE, 'tasks')

# Global shutdown flag
shutdown_requested = False

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global shutdown_requested
    logger.info(f"Received signal {signum}, initiating graceful shutdown")
    shutdown_requested = True

# Register signal handlers
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

os.makedirs(TASKS_DIR, exist_ok=True)

logger.info(f'Coding agent started, workspace: {WORKSPACE}, manager: {config.agent.manager_url}')

@log_operation("read_task_meta")
def read_meta(task_dir: str) -> Optional[Dict[str, Any]]:
    """Read task metadata with error handling."""
    meta_file = os.path.join(task_dir, 'meta.json')
    if not os.path.exists(meta_file):
        return None
    
    try:
        with open(meta_file) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.error(f"Failed to read meta file {meta_file}: {e}")
        return None


@handle_errors("scaffold_task")
def scaffold_task(task_id: str, task_dir: str, spec: Dict[str, Any]) -> None:
    """Scaffold code for a task using opencode-like approach."""
    task_logger = get_task_logger(task_id, 'coding')
    
    # Create source directory
    src_dir = os.path.join(task_dir, 'src')
    os.makedirs(src_dir, exist_ok=True)
    
    # Generate simple static site (placeholder for opencode integration)
    title = spec.get('title', 'Generated Site')
    description = spec.get('description', 'Scaffolded by coding-agent')
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .header {{ background: #f4f4f4; padding: 20px; border-radius: 5px; }}
        .content {{ margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{title}</h1>
        <p>{description}</p>
    </div>
    <div class="content">
        <p>This site was scaffolded by the DevSys coding agent.</p>
        <p>Generated at: {datetime.utcnow().isoformat()}Z</p>
    </div>
</body>
</html>"""
    
    index_path = os.path.join(src_dir, 'index.html')
    with open(index_path, 'w') as f:
        f.write(html_content)
    
    task_logger.info(f"Scaffolded basic HTML site", extra={
        'files_created': ['index.html'],
        'src_dir': src_dir
    })


@retry(max_attempts=3, delay=2.0, exceptions=(ExternalServiceError,))
def create_github_pr(task_id: str, src_dir: str, title: str) -> Optional[str]:
    """Create GitHub PR for the scaffolded code."""
    github_config = config.github
    
    if not github_config.is_enabled():
        logger.debug("GitHub integration not configured, skipping PR creation")
        return None
    
    task_logger = get_task_logger(task_id, 'coding')
    
    try:
        branch = f"task/{task_id}"
        
        # Initialize git repo and commit
        subprocess.check_call(['git', 'init'], cwd=src_dir)
        subprocess.check_call(['git', 'config', 'user.name', github_config.user], cwd=src_dir)
        subprocess.check_call(['git', 'config', 'user.email', github_config.email], cwd=src_dir)
        subprocess.check_call(['git', 'add', '.'], cwd=src_dir)
        subprocess.check_call(['git', 'commit', '-m', f"Scaffold for task {task_id}"], cwd=src_dir)
        
        # Add remote using token in URL
        remote_url = f"https://{github_config.token}:x-oauth-basic@github.com/{github_config.repo}.git"
        subprocess.check_call(['git', 'remote', 'add', 'origin', remote_url], cwd=src_dir)
        
        # Create and push branch
        subprocess.check_call(['git', 'checkout', '-b', branch], cwd=src_dir)
        
        if not github_config.dry_run:
            subprocess.check_call(['git', 'push', '--set-upstream', 'origin', branch], cwd=src_dir)
        else:
            task_logger.info("GitHub dry run enabled, skipping push")
            return None
        
        # Create PR via GitHub API
        import requests
        headers = {
            'Authorization': f'token {github_config.token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        api_url = f'https://api.github.com/repos/{github_config.repo}/pulls'
        pr_payload = {
            'title': f'Task {task_id}: {title}',
            'head': branch,
            'base': 'main',
            'body': f'Automated PR for task {task_id} (scaffold).'
        }
        
        response = requests.post(api_url, json=pr_payload, headers=headers, timeout=10)
        
        if response.status_code in (200, 201):
            pr_data = response.json()
            pr_url = pr_data.get('html_url')
            task_logger.info(f"Created GitHub PR: {pr_url}")
            return pr_url
        elif response.status_code == 422:
            # PR may already exist
            task_logger.warning("PR creation failed, may already exist")
            return None
        else:
            raise ExternalServiceError(
                f"GitHub API error: {response.status_code}",
                service="github",
                details={'response': response.text}
            )
            
    except subprocess.CalledProcessError as e:
        raise ExternalServiceError(
            f"Git operation failed: {e}",
            service="git",
            cause=e
        )
    except Exception as e:
        raise ExternalServiceError(
            f"GitHub PR creation failed: {e}",
            service="github",
            cause=e
        )

# Main worker loop
logger.info("Starting main worker loop")

while not shutdown_requested:
    try:
        # Process tasks
        for name in os.listdir(TASKS_DIR):
            if shutdown_requested:
                break
                
            task_dir = os.path.join(TASKS_DIR, name)
            if not os.path.isdir(task_dir):
                continue
                
            meta = read_meta(task_dir)
            if not meta:
                continue
                
            status = meta.get('status')
            if status != 'created':
                continue
            
            task_logger = get_task_logger(name, 'coding')
            task_logger.info(f"Processing new task")
            
            try:
                # Mark task as in progress
                manager_client.update_task_status(name, 'in_progress')
                
                # Read task specification
                spec_path = os.path.join(task_dir, 'spec.yaml')
                spec = {}
                if os.path.exists(spec_path):
                    try:
                        with open(spec_path) as f:
                            spec = yaml.safe_load(f) or {}
                    except yaml.YAMLError as e:
                        task_logger.error(f"Invalid YAML in spec file: {e}")
                        raise TaskProcessingError(
                            "Invalid task specification",
                            task_id=name,
                            stage="spec_parsing",
                            cause=e
                        )
                
                # Scaffold the task
                scaffold_task(name, task_dir, spec)
                
                # Attempt GitHub PR creation if configured
                src_dir = os.path.join(task_dir, 'src')
                title = spec.get('title', 'Generated Site')
                
                try:
                    pr_url = create_github_pr(name, src_dir, title)
                    if pr_url:
                        task_logger.info(f"Created GitHub PR: {pr_url}")
                except ExternalServiceError as e:
                    # Don't fail the task if GitHub PR creation fails
                    task_logger.warning(f"GitHub PR creation failed: {e.message}")
                
                # Mark task as completed
                manager_client.update_task_status(name, 'completed')
                task_logger.info("Task completed successfully")
                
            except TaskProcessingError as e:
                task_logger.error(f"Task processing failed: {e.message}")
                try:
                    manager_client.update_task_status(name, 'failed')
                except NetworkError:
                    task_logger.error("Failed to update task status to failed")
            except NetworkError as e:
                task_logger.error(f"Network error during task processing: {e.message}")
                # Don't mark as failed if it's just a network issue
            except Exception as e:
                task_logger.error(f"Unexpected error processing task: {e}", exc_info=True)
                try:
                    manager_client.update_task_status(name, 'failed')
                except NetworkError:
                    task_logger.error("Failed to update task status to failed")
        
        # Sleep before next iteration
        if not shutdown_requested:
            time.sleep(config.agent.poll_interval)
            
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down")
        break
    except Exception as e:
        logger.error(f"Worker loop error: {e}", exc_info=True)
        if not shutdown_requested:
            time.sleep(config.agent.poll_interval)

logger.info("Coding agent shutting down gracefully")
sys.exit(0)
