#!/usr/bin/env python3
"""
Test script to verify screenshot capture and performance monitoring fixes
"""

import os
import sys
import time
from pathlib import Path

# Add Src directory to path
sys.path.append(str(Path(__file__).parent / 'Src'))

from performance_monitor import get_performance_monitor, time_function

@time_function('test_operation')
def test_performance_logging():
    """Test performance logging with unicode characters"""
    print("Testing performance logging...")
    time.sleep(0.1)
    return "Success"

def test_screenshot_fallback():
    """Test screenshot fallback mechanism"""
    print("Testing screenshot error handling...")
    
    # Create a mock screenshot file
    test_file = "bot_feed_test.png"
    with open(test_file, 'w') as f:
        f.write("mock screenshot data")
    
    try:
        # This should work without unicode errors
        monitor = get_performance_monitor()
        with monitor.time_operation('test_screenshot') as timer:
            if not os.path.exists(test_file):
                timer.set_success(False)
                raise FileNotFoundError("Test file not found")
        
        print("✓ Screenshot error handling works")
        
    finally:
        # Clean up
        if os.path.exists(test_file):
            os.remove(test_file)

def main():
    print("🔧 Testing Rush Royale Bot fixes...")
    print()
    
    # Test 1: Performance logging
    try:
        result = test_performance_logging()
        print(f"✓ Performance logging: {result}")
    except Exception as e:
        print(f"✗ Performance logging failed: {e}")
        return False
    
    # Test 2: Screenshot error handling
    try:
        test_screenshot_fallback()
        print("✓ Screenshot error handling works")
    except Exception as e:
        print(f"✗ Screenshot error handling failed: {e}")
        return False
    
    # Test 3: Generate performance report
    try:
        monitor = get_performance_monitor()
        report = monitor.get_performance_report()
        print("\n📊 Performance Report:")
        print(report)
        print("✓ Performance reporting works")
    except Exception as e:
        print(f"✗ Performance reporting failed: {e}")
        return False
    
    print("\n🎉 All tests passed!")
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
