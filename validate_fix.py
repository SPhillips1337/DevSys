#!/usr/bin/env python3
"""
Comprehensive validation script to ensure the CI fix is working
"""
import os
import sys
import ast
import tempfile

def check_syntax(filepath):
    """Check if a Python file has valid syntax."""
    try:
        with open(filepath, 'r') as f:
            content = f.read()
        ast.parse(content, filename=filepath)
        return True, None
    except SyntaxError as e:
        return False, f"Syntax error at line {e.lineno}: {e.msg}"
    except Exception as e:
        return False, str(e)

def test_imports():
    """Test that all modules can be imported without errors."""
    # Set up test environment
    os.environ['WORKSPACE'] = '/tmp'
    os.environ['TESTING'] = 'true'
    os.environ['LOG_LEVEL'] = 'ERROR'  # Reduce noise
    
    try:
        # Test utility imports
        from utils.config import get_config, ConfigurationError
        from utils.exceptions import DevSysError, ValidationError
        from utils.logging_config import setup_logging
        from utils.http_client import create_manager_client
        
        # Test manager import (this was the failing point)
        from manager.app import app
        
        # Test that we can create a config without errors
        config = get_config('test')
        
        return True, "All imports successful"
    except Exception as e:
        return False, f"Import error: {e}"

def test_manager_functionality():
    """Test basic manager functionality."""
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            os.environ['WORKSPACE'] = temp_dir
            os.environ['MANAGER_API_TOKEN'] = 'test-token'
            
            from manager.app import app
            app.config['TESTING'] = True
            
            with app.test_client() as client:
                # Test basic endpoint
                response = client.get('/api/tasks')
                if response.status_code != 200:
                    return False, f"API test failed with status {response.status_code}"
                
                return True, "Basic functionality test passed"
    except Exception as e:
        return False, f"Functionality test error: {e}"

def main():
    print("🔍 Validating CI fix...")
    
    # Check if all required files exist
    required_files = [
        'utils/config.py',
        'utils/exceptions.py',
        'utils/logging_config.py',
        'utils/http_client.py',
        'manager/app.py',
        'tests/test_manager_improved.py',
        '.github/workflows/ci.yml'
    ]
    
    print("\n📁 Checking file existence...")
    missing_files = []
    for filepath in required_files:
        if os.path.exists(filepath):
            print(f"   ✓ {filepath}")
        else:
            print(f"   ✗ {filepath} - MISSING")
            missing_files.append(filepath)
    
    if missing_files:
        print(f"\n❌ Missing files: {missing_files}")
        return False
    
    # Check syntax of Python files
    print("\n🔧 Checking syntax...")
    python_files = [f for f in required_files if f.endswith('.py')]
    syntax_errors = []
    
    for filepath in python_files:
        is_valid, error = check_syntax(filepath)
        if is_valid:
            print(f"   ✓ {filepath}")
        else:
            print(f"   ✗ {filepath} - {error}")
            syntax_errors.append((filepath, error))
    
    if syntax_errors:
        print(f"\n❌ Syntax errors found: {syntax_errors}")
        return False
    
    # Test imports
    print("\n📦 Testing imports...")
    import_success, import_msg = test_imports()
    if import_success:
        print(f"   ✓ {import_msg}")
    else:
        print(f"   ✗ {import_msg}")
        return False
    
    # Test basic functionality
    print("\n🧪 Testing functionality...")
    func_success, func_msg = test_manager_functionality()
    if func_success:
        print(f"   ✓ {func_msg}")
    else:
        print(f"   ✗ {func_msg}")
        return False
    
    print("\n🎉 All validations passed! CI fix should be working.")
    print("\nKey improvements:")
    print("  • No more import-time directory creation")
    print("  • Lazy workspace initialization")
    print("  • Test environment compatibility")
    print("  • Structured error handling")
    print("  • Comprehensive logging")
    
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)