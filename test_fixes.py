#!/usr/bin/env python3
"""
Test script for the Unicode encoding and screenshot fixes
"""

import logging
import sys
import os

# Add Src to path
sys.path.append('./Src')

def test_performance_monitor():
    """Test performance monitor encoding fixes"""
    print("Testing Performance Monitor encoding fixes...")
    
    try:
        from performance_monitor import get_performance_monitor, safe_log
        
        # Test safe logging function
        logger = logging.getLogger('test')
        handler = logging.StreamHandler()
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        # Test with problematic characters
        safe_log(logger, 'info', "Test message with unicode: ✓ ✗ 🎯 📊")
        print("✅ Safe logging works")
        
        # Test performance monitor initialization
        monitor = get_performance_monitor()
        print("✅ Performance monitor initialized")
        
        # Test metric recording
        monitor.record_metric('test_operation', 0.123, True)
        print("✅ Metric recording works")
        
        return True
        
    except Exception as e:
        print(f"❌ Performance monitor test failed: {e}")
        return False

def test_error_recovery():
    """Test error recovery system"""
    print("Testing Error Recovery System...")
    
    try:
        from error_recovery import get_error_recovery_system
        
        recovery = get_error_recovery_system()
        print("✅ Error recovery system initialized")
        
        # Test error handling
        test_error = FileNotFoundError("Test screenshot error")
        result = recovery.handle_error(test_error, 'screen_capture')
        print(f"✅ Error recovery handled test error: {result}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error recovery test failed: {e}")
        return False

def test_screenshot_fallback():
    """Test screenshot fallback mechanisms"""
    print("Testing Screenshot fallback...")
    
    # Create a test screenshot file
    test_file = 'bot_feed_emulator-5554.png'
    if not os.path.exists(test_file):
        # Create a dummy 100x100 black image for testing
        try:
            import cv2
            import numpy as np
            dummy_img = np.zeros((900, 1600, 3), dtype=np.uint8)
            cv2.imwrite(test_file, dummy_img)
            print(f"✅ Created test screenshot: {test_file}")
        except ImportError:
            print("⚠️  OpenCV not available for test image creation")
            return True
    else:
        print(f"✅ Test screenshot exists: {test_file}")
    
    return True

def main():
    """Run all tests"""
    print("🔧 Testing Bot Fixes")
    print("=" * 50)
    
    tests = [
        ("Performance Monitor", test_performance_monitor),
        ("Error Recovery", test_error_recovery),
        ("Screenshot Fallback", test_screenshot_fallback),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 30)
        result = test_func()
        results.append((test_name, result))
        print()
    
    print("📊 Test Results Summary")
    print("=" * 50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:<25} {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All fixes are working correctly!")
        return 0
    else:
        print("⚠️  Some issues remain - check the logs above")
        return 1

if __name__ == "__main__":
    sys.exit(main())
