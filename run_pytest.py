#!/usr/bin/env python3
import subprocess
import sys
import os

# Set up environment
os.environ['WORKSPACE'] = '/tmp'
os.environ['LOG_LEVEL'] = 'DEBUG'
os.chdir('/workspace')

print("Running pytest...")

try:
    # Run pytest with verbose output
    result = subprocess.run([
        sys.executable, '-m', 'pytest', 
        'tests/', '-v', '--tb=short', '--no-header'
    ], capture_output=True, text=True, timeout=120)
    
    print("STDOUT:")
    print(result.stdout)
    print("\nSTDERR:")
    print(result.stderr)
    print(f"\nReturn code: {result.returncode}")
    
except subprocess.TimeoutExpired:
    print("Test timed out after 120 seconds")
except Exception as e:
    print(f"Error running pytest: {e}")