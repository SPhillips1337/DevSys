#!/usr/bin/env python3
"""
Minimal test to check if the imports work
"""
import os
import sys

# Set up environment like CI
os.environ['WORKSPACE'] = '/tmp'
os.environ['LOG_LEVEL'] = 'INFO'
os.environ['TESTING'] = 'true'
sys.path.insert(0, '/workspace')

print("Testing imports step by step...")

# Step 1: Test utils.config
try:
    print("1. Importing utils.config...")
    from utils.config import ConfigurationError, get_config
    print("   ✓ utils.config imported successfully")
except Exception as e:
    print(f"   ✗ Failed to import utils.config: {e}")
    sys.exit(1)

# Step 2: Test utils.exceptions  
try:
    print("2. Importing utils.exceptions...")
    from utils.exceptions import DevSysError, ValidationError
    print("   ✓ utils.exceptions imported successfully")
except Exception as e:
    print(f"   ✗ Failed to import utils.exceptions: {e}")
    sys.exit(1)

# Step 3: Test manager.app
try:
    print("3. Importing manager.app...")
    from manager.app import app
    print("   ✓ manager.app imported successfully")
except Exception as e:
    print(f"   ✗ Failed to import manager.app: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 4: Test the test file itself
try:
    print("4. Importing test file...")
    from tests.test_manager_improved import TestManagerImproved
    print("   ✓ test_manager_improved imported successfully")
except Exception as e:
    print(f"   ✗ Failed to import test_manager_improved: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n🎉 All imports successful! The CI error should be resolved.")

# Try to run one simple test
try:
    print("\n5. Testing basic functionality...")
    import tempfile
    with tempfile.TemporaryDirectory() as temp_dir:
        os.environ['WORKSPACE'] = temp_dir
        os.environ['MANAGER_API_TOKEN'] = 'test-token'
        
        # Create a test client
        app.config['TESTING'] = True
        with app.test_client() as client:
            response = client.get('/api/tasks')
            print(f"   ✓ GET /api/tasks returned status {response.status_code}")
            
except Exception as e:
    print(f"   ✗ Basic functionality test failed: {e}")
    import traceback
    traceback.print_exc()

print("\n✅ Tests completed!")