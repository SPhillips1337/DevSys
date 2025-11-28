#!/usr/bin/env python3
import subprocess
import sys
import os

# Set up environment
os.environ['WORKSPACE'] = '/workspace'
os.chdir('/workspace')

print("Running existing tests to see current status...")

try:
    # Run pytest on existing tests only (not the new one)
    result = subprocess.run([
        sys.executable, '-m', 'pytest', 
        'tests/test_create_blog.py', 
        'tests/test_manager_secrets.py',
        'tests/test_vocaloid_smoke.py',
        '-v'
    ], capture_output=True, text=True, timeout=60)
    
    print("STDOUT:")
    print(result.stdout)
    print("\nSTDERR:")  
    print(result.stderr)
    print(f"\nReturn code: {result.returncode}")
    
except Exception as e:
    print(f"Error: {e}")

print("\n" + "="*50)
print("Now testing the new improved test file...")

try:
    # Run pytest on the new test file
    result = subprocess.run([
        sys.executable, '-m', 'pytest', 
        'tests/test_manager_improved.py',
        '--collect-only', '-v'
    ], capture_output=True, text=True, timeout=60)
    
    print("STDOUT:")
    print(result.stdout)
    print("\nSTDERR:")
    print(result.stderr)
    print(f"\nReturn code: {result.returncode}")
    
except Exception as e:
    print(f"Error: {e}")