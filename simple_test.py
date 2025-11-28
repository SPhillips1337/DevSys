import os
import sys

# Set test environment
os.environ['WORKSPACE'] = '/tmp'
os.environ['TESTING'] = 'true'
os.environ['LOG_LEVEL'] = 'DEBUG'

print("Testing basic imports...")

try:
    print("Testing utils.config...")
    from utils.config import ConfigurationError
    print("✓ ConfigurationError imported")
    
    print("Testing utils.exceptions...")
    from utils.exceptions import DevSysError
    print("✓ DevSysError imported")
    
    print("Testing manager.app...")
    from manager.app import app
    print("✓ manager.app imported")
    
    print("\n✅ Basic imports successful!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)