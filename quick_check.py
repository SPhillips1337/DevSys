import ast

# Check utils/config.py
try:
    with open('utils/config.py') as f:
        ast.parse(f.read())
    print("✓ utils/config.py syntax OK")
except Exception as e:
    print(f"✗ utils/config.py error: {e}")

# Check manager/app.py  
try:
    with open('manager/app.py') as f:
        ast.parse(f.read())
    print("✓ manager/app.py syntax OK")
except Exception as e:
    print(f"✗ manager/app.py error: {e}")

# Try basic import
try:
    import sys
    sys.path.insert(0, '/workspace')
    from utils.config import ConfigurationError
    print("✓ ConfigurationError import OK")
except Exception as e:
    print(f"✗ ConfigurationError import error: {e}")