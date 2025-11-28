#!/usr/bin/env python3
import subprocess
import sys
import os

# Set up environment
os.environ['WORKSPACE'] = '/workspace'
os.environ['LOG_LEVEL'] = 'DEBUG'

# Change to workspace directory
os.chdir('/workspace')

# First test just imports
print("=== Testing imports ===")
try:
    result = subprocess.run([
        sys.executable, '-c', 
        """
import sys
import os
sys.path.insert(0, '/workspace')
os.environ['WORKSPACE'] = '/workspace'

from utils.config import get_config, ConfigurationError
from utils.exceptions import DevSysError, ValidationError
from utils.logging_config import setup_logging
from utils.http_client import create_manager_client
from manager.app import app
print("All imports successful!")
"""
    ], capture_output=True, text=True, timeout=30)
    
    print("STDOUT:")
    print(result.stdout)
    if result.stderr:
        print("STDERR:")
        print(result.stderr)
    print(f"Return code: {result.returncode}")
    
    if result.returncode == 0:
        print("✅ Import test passed!")
    else:
        print("❌ Import test failed!")
        sys.exit(1)
        
except Exception as e:
    print(f"Error running import test: {e}")
    sys.exit(1)

# Now try running the actual tests
print("\n=== Running pytest ===")
try:
    result = subprocess.run([
        sys.executable, '-m', 'pytest', 
        'tests/test_manager_improved.py::TestManagerImproved::test_create_task_success',
        '-v', '--tb=short'
    ], capture_output=True, text=True, timeout=60)
    
    print("STDOUT:")
    print(result.stdout)
    if result.stderr:
        print("STDERR:")
        print(result.stderr)
    print(f"Return code: {result.returncode}")
    
except Exception as e:
    print(f"Error running pytest: {e}")