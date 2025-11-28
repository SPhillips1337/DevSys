#!/usr/bin/env python3
"""
Mimic the CI environment to reproduce the error
"""
import subprocess
import sys
import os

# Set up CI-like environment
os.environ['WORKSPACE'] = '/workspace'
os.environ['LOG_LEVEL'] = 'INFO'

# Change to workspace directory
os.chdir('/workspace')

print("=== Mimicking CI Environment ===")
print(f"Working directory: {os.getcwd()}")
print(f"Python version: {sys.version}")
print(f"WORKSPACE: {os.environ.get('WORKSPACE')}")

# Step 1: Try to import the problematic module directly
print("\n=== Step 1: Direct Import Test ===")
try:
    result = subprocess.run([
        sys.executable, '-c', 
        """
import sys
sys.path.insert(0, '/workspace')
print('Attempting to import utils.config...')
from utils.config import ConfigurationError
print('SUCCESS: ConfigurationError imported')
print('Attempting to import manager.app...')
from manager.app import app
print('SUCCESS: manager.app imported')
"""
    ], capture_output=True, text=True, cwd='/workspace')
    
    print("Return code:", result.returncode)
    if result.stdout:
        print("STDOUT:", result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
        
except Exception as e:
    print(f"Error in direct import test: {e}")

# Step 2: Try pytest collection (what CI does first)
print("\n=== Step 2: Pytest Collection Test ===")
try:
    result = subprocess.run([
        sys.executable, '-m', 'pytest', 
        '--collect-only', '-q'
    ], capture_output=True, text=True, cwd='/workspace')
    
    print("Return code:", result.returncode)
    if result.stdout:
        print("STDOUT:", result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
        
except Exception as e:
    print(f"Error in pytest collection: {e}")

# Step 3: Try running just the problematic test file
print("\n=== Step 3: Single Test File ===")
try:
    result = subprocess.run([
        sys.executable, '-m', 'pytest', 
        'tests/test_manager_improved.py', '--collect-only', '-q'
    ], capture_output=True, text=True, cwd='/workspace')
    
    print("Return code:", result.returncode)
    if result.stdout:
        print("STDOUT:", result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
        
except Exception as e:
    print(f"Error in single test file: {e}")

print("\n=== Test Complete ===")