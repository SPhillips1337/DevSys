#!/usr/bin/env python3
"""Test script to verify that the utility modules can be imported correctly."""

import sys
import os

# Set up environment
os.environ['WORKSPACE'] = '/tmp'
os.environ['LOG_LEVEL'] = 'DEBUG'
os.environ['TESTING'] = 'true'

print("Testing imports...")

try:
    # Test utils imports
    print("1. Testing utils.config...")
    from utils.config import get_config, ConfigurationError
    print("   ✓ utils.config imported successfully")
    
    print("2. Testing utils.exceptions...")
    from utils.exceptions import DevSysError, ValidationError, AuthenticationError
    print("   ✓ utils.exceptions imported successfully")
    
    print("3. Testing utils.logging_config...")
    from utils.logging_config import setup_logging, get_logger
    print("   ✓ utils.logging_config imported successfully")
    
    print("4. Testing utils.http_client...")
    from utils.http_client import create_manager_client
    print("   ✓ utils.http_client imported successfully")
    
    print("5. Testing manager.app...")
    from manager.app import app
    print("   ✓ manager.app imported successfully")
    
    print("\n✅ All imports successful!")
    
    # Test basic configuration
    print("\n6. Testing configuration...")
    config = get_config('test')
    print(f"   ✓ Configuration created for service: {config.service_name}")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Other error: {e}")
    sys.exit(1)

print("\n🎉 All tests passed!")