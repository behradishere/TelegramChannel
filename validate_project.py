#!/usr/bin/env python3
"""Project validation and status check script."""
import os
import sys
from pathlib import Path


def check_file_exists(filepath: str, required: bool = True) -> bool:
    """Check if a file exists."""
    exists = Path(filepath).exists()
    status = "✅" if exists else ("❌" if required else "⚠️")
    req_text = "(required)" if required else "(optional)"
    print(f"{status} {filepath} {req_text}")
    return exists


def check_python_syntax(filepath: str) -> bool:
    """Check Python file for syntax errors."""
    try:
        with open(filepath, 'r') as f:
            compile(f.read(), filepath, 'exec')
        return True
    except SyntaxError as e:
        print(f"  ❌ Syntax error: {e}")
        return False


def main():
    """Run project validation checks."""
    print("🔍 Telegram Trading Bot - Project Validation")
    print("=" * 50)
    print()

    # Check required files
    print("📁 Checking required files...")
    required_files = [
        'main.py',
        'signal_parser.py',
        'order_manager.py',
        'config.py',
        'risk_manager.py',
        'utils.py',
        'requirements.txt',
        'README.md',
        '.env.example',
        '.gitignore'
    ]

    all_required_exist = all(check_file_exists(f) for f in required_files)
    print()

    # Check optional files
    print("📁 Checking optional files...")
    optional_files = [
        '.env',
        'health.txt',
        'bot.log',
        'signals_session.session'
    ]

    for f in optional_files:
        check_file_exists(f, required=False)
    print()

    # Check Python syntax
    print("🐍 Checking Python syntax...")
    python_files = [
        'main.py',
        'signal_parser.py',
        'order_manager.py',
        'config.py',
        'risk_manager.py',
        'utils.py',
        'health_check.py',
        'GetChannelId.py',
        'signal_bot.py'
    ]

    syntax_ok = True
    for f in python_files:
        if Path(f).exists():
            if not check_python_syntax(f):
                syntax_ok = False

    if syntax_ok:
        print("✅ All Python files have valid syntax")
    print()

    # Check test files
    print("🧪 Checking test files...")
    test_files = [
        'tests/test_signal_parser.py',
        'tests/test_signal_parser_extended.py',
        'tests/test_risk_manager.py',
        'tests/test_utils.py'
    ]

    all_tests_exist = all(check_file_exists(f) for f in test_files)
    print()

    # Check Docker files
    print("🐳 Checking Docker files...")
    docker_files = ['Dockerfile', 'docker-compose.yml']
    for f in docker_files:
        check_file_exists(f, required=False)
    print()

    # Check scripts
    print("📜 Checking scripts...")
    scripts = ['setup.sh', 'Makefile']
    for f in scripts:
        check_file_exists(f, required=False)
    print()

    # Run tests if pytest available
    print("🧪 Running tests...")
    try:
        import pytest
        exit_code = pytest.main(['-v', '--tb=short', 'tests/'])
        if exit_code == 0:
            print("✅ All tests passed!")
        else:
            print(f"⚠️ Some tests failed (exit code: {exit_code})")
    except ImportError:
        print("⚠️ pytest not installed, skipping tests")
    print()

    # Final summary
    print("=" * 50)
    print("📊 VALIDATION SUMMARY")
    print("=" * 50)

    if all_required_exist and syntax_ok:
        print("✅ Project structure is valid")
        print("✅ All required files present")
        print("✅ Python syntax is correct")
        print()
        print("🚀 Next steps:")
        print("   1. Copy .env.example to .env and configure")
        print("   2. Run: python GetChannelId.py")
        print("   3. Test with DRY_RUN=true")
        print("   4. Deploy and monitor")
        return 0
    else:
        print("❌ Project validation failed")
        print("   Fix the issues above and run again")
        return 1


if __name__ == "__main__":
    sys.exit(main())

