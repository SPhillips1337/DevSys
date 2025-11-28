#!/usr/bin/env python3
import sys
import os

# Set up environment
os.environ['WORKSPACE'] = '/tmp'  # Use /tmp for testing
os.environ['LOG_LEVEL'] = 'DEBUG'
os.environ['TESTING'] = 'true'
sys.path.insert(0, '/workspace')

print("Testing basic imports...")

try:
    # Test individual imports
    print("1. Testing utils.config...")
    from utils.config import ConfigurationError
    print("   ✓ ConfigurationError imported")
    
    print("2. Testing utils.exceptions...")
    from utils.exceptions import DevSysError
    print("   ✓ DevSysError imported")
    
    print("3. Testing manager.app...")
    from manager.app import app
    print("   ✓ manager.app imported")
    
    print("\n✅ Basic imports successful!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)