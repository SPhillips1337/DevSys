#!/usr/bin/env python3
import sys
import os

# Set up environment
os.environ['WORKSPACE'] = '/workspace'
os.environ['LOG_LEVEL'] = 'DEBUG'
sys.path.insert(0, '/workspace')

print("Testing imports...")

try:
    print("1. Importing utils.config...")
    from utils.config import get_config, ConfigurationError
    print("   ✓ Success")
    
    print("2. Importing utils.exceptions...")
    from utils.exceptions import DevSysError, ValidationError, AuthenticationError
    print("   ✓ Success")
    
    print("3. Importing utils.logging_config...")
    from utils.logging_config import setup_logging, get_logger
    print("   ✓ Success")
    
    print("4. Importing utils.http_client...")
    from utils.http_client import create_manager_client
    print("   ✓ Success")
    
    print("5. Importing manager.app...")
    from manager.app import app
    print("   ✓ Success")
    
    print("\n✅ All imports successful!")
    
    # Test basic functionality
    print("\n6. Testing configuration...")
    config = get_config('test')
    print(f"   ✓ Config created: {config.service_name}")
    
    print("\n7. Testing logger...")
    logger = setup_logging('test')
    print(f"   ✓ Logger created: {logger.name}")
    
    print("\n🎉 All tests passed!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)