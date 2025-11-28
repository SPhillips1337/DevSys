#!/usr/bin/env python3
import subprocess
import sys
import os

# Set up environment
os.environ['WORKSPACE'] = '/workspace'
os.environ['LOG_LEVEL'] = 'DEBUG'

# Change to workspace directory
os.chdir('/workspace')

# Run the specific test that was failing
try:
    result = subprocess.run([
        sys.executable, '-m', 'pytest', 
        'tests/test_manager_improved.py', 
        '-v', '--tb=short'
    ], capture_output=True, text=True, timeout=60)
    
    print("STDOUT:")
    print(result.stdout)
    print("\nSTDERR:")
    print(result.stderr)
    print(f"\nReturn code: {result.returncode}")
    
except subprocess.TimeoutExpired:
    print("Test timed out after 60 seconds")
except Exception as e:
    print(f"Error running test: {e}")