#!/usr/bin/env python3
"""
Check syntax of Python files
"""
import ast
import os

def check_file_syntax(filepath):
    """Check if a Python file has valid syntax."""
    try:
        with open(filepath, 'r') as f:
            content = f.read()
        
        # Try to parse the AST
        ast.parse(content, filename=filepath)
        print(f"✓ {filepath} - syntax OK")
        return True
        
    except SyntaxError as e:
        print(f"✗ {filepath} - syntax error: {e}")
        print(f"  Line {e.lineno}: {e.text}")
        return False
    except Exception as e:
        print(f"✗ {filepath} - error: {e}")
        return False

print("Checking syntax of Python files...")

files_to_check = [
    'utils/config.py',
    'utils/exceptions.py', 
    'utils/logging_config.py',
    'utils/http_client.py',
    'manager/app.py',
    'tests/test_manager_improved.py'
]

all_good = True
for filepath in files_to_check:
    if os.path.exists(filepath):
        if not check_file_syntax(filepath):
            all_good = False
    else:
        print(f"✗ {filepath} - file not found")
        all_good = False

if all_good:
    print("\n🎉 All files have valid syntax!")
else:
    print("\n❌ Some files have syntax errors!")