#!/usr/bin/env python3
"""
Test runner for Rush Royale Bot test suite
Runs all tests with proper configuration and reporting
"""

import unittest
import sys
import os
import warnings
from pathlib import Path

# Suppress known warnings during testing
warnings.filterwarnings("ignore", message="pkg_resources is deprecated", category=UserWarning)
warnings.filterwarnings("ignore", category=ResourceWarning)


def setup_test_environment():
    """Set up the test environment"""
    # Add project root to path
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))
    sys.path.insert(0, str(project_root / 'Src'))
    
    # Change to project directory
    os.chdir(project_root)
    
    print(f"🧪 Running tests from: {project_root}")
    print(f"🐍 Python version: {sys.version}")
    print("=" * 60)


def run_test_suite():
    """Run the complete test suite"""
    # Discover and run all tests
    loader = unittest.TestLoader()
    test_dir = Path(__file__).parent
    
    # Load tests from test directory
    suite = loader.discover(str(test_dir), pattern='test_*.py')
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(
        verbosity=2,
        buffer=True,
        stream=sys.stdout
    )
    
    print("🚀 Starting Rush Royale Bot Test Suite")
    print("=" * 60)
    
    result = runner.run(suite)
    
    print("\n" + "=" * 60)
    print("📊 Test Results Summary:")
    print(f"✅ Tests run: {result.testsRun}")
    print(f"❌ Failures: {len(result.failures)}")
    print(f"💥 Errors: {len(result.errors)}")
    print(f"⏭️  Skipped: {len(result.skipped) if hasattr(result, 'skipped') else 0}")
    
    if result.failures:
        print("\n🔴 Failures:")
        for test, traceback in result.failures:
            print(f"  • {test}: {traceback.split(chr(10))[-2] if chr(10) in traceback else traceback}")
    
    if result.errors:
        print("\n💥 Errors:")
        for test, traceback in result.errors:
            print(f"  • {test}: {traceback.split(chr(10))[-2] if chr(10) in traceback else traceback}")
    
    success = len(result.failures) == 0 and len(result.errors) == 0
    
    if success:
        print("\n🎉 All tests passed! Bot is ready for deployment.")
    else:
        print("\n⚠️  Some tests failed. Please review and fix issues.")
    
    return success


def run_specific_test(test_name):
    """Run a specific test module"""
    try:
        module = unittest.import_module(f'tests.{test_name}')
        suite = unittest.TestLoader().loadTestsFromModule(module)
        runner = unittest.TextTestRunner(verbosity=2, buffer=True)
        result = runner.run(suite)
        return len(result.failures) == 0 and len(result.errors) == 0
    except ImportError:
        print(f"❌ Test module '{test_name}' not found")
        return False


def main():
    """Main test runner function"""
    setup_test_environment()
    
    if len(sys.argv) > 1:
        # Run specific test
        test_name = sys.argv[1]
        if test_name.startswith('test_'):
            test_name = test_name[5:]  # Remove 'test_' prefix
        
        print(f"🎯 Running specific test: {test_name}")
        success = run_specific_test(f'test_{test_name}')
    else:
        # Run all tests
        success = run_test_suite()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
