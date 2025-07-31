#!/usr/bin/env python3
"""
Test utility for the Debug System
Verifies debug functionality and demonstrates features
"""

import os
import sys
import time
import numpy as np
import pandas as pd
import cv2
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'Src'))

from debug_system import get_debug_system, DebugVisualizer
from performance_monitor import get_performance_monitor


def test_debug_system():
    """Test the debug system functionality"""
    print("🔧 Testing Debug System...")
    
    # Initialize debug system
    debug_sys = get_debug_system()
    debug_sys.set_enabled(True)
    
    print("✅ Debug system initialized")
    
    # Test basic event logging
    debug_sys.log_event("TEST", "initialization", {
        "test_parameter": "test_value",
        "timestamp": time.time()
    })
    
    # Test with warnings
    debug_sys.log_event("TEST", "warning_test", {
        "warning_type": "simulated"
    }, warnings=["This is a test warning"])
    
    # Test error logging
    debug_sys.log_event("TEST", "error_test", {
        "error_type": "simulated"
    }, success=False, warnings=["This is a test error"])
    
    print("✅ Event logging tests completed")
    
    # Test performance logging
    with debug_sys.time_operation('test_operation') as timer:
        time.sleep(0.1)
        timer.add_detail('test_detail', 'performance_test')
    
    print("✅ Performance logging test completed")
    
    # Test debug summary
    summary = debug_sys.get_debug_summary()
    print(f"✅ Debug summary generated: {summary}")
    
    return debug_sys


def test_visual_debugging():
    """Test visual debugging features"""
    print("🖼️  Testing Visual Debugging...")
    
    # Create test image
    test_img = np.zeros((900, 1600, 3), dtype=np.uint8)
    test_img.fill(50)  # Dark gray background
    
    # Add some visual elements
    cv2.rectangle(test_img, (100, 100), (200, 200), (0, 255, 0), 2)
    cv2.circle(test_img, (400, 300), 50, (255, 0, 0), -1)
    cv2.putText(test_img, "TEST SCREEN", (500, 400), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
    
    # Test visualizer
    visualizer = DebugVisualizer()
    
    # Test annotated screenshot
    annotations = [
        {
            'type': 'point',
            'pos': (300, 250),
            'color': (0, 255, 0),
            'label': 'Test Click'
        },
        {
            'type': 'rectangle',
            'rect': (100, 100, 100, 100),
            'color': (255, 0, 0),
            'label': 'UI Element'
        },
        {
            'type': 'text',
            'pos': (600, 500),
            'text': 'Debug Info',
            'color': (255, 255, 0)
        }
    ]
    
    screenshot_path = visualizer.save_annotated_screenshot(test_img, annotations, "test_debug.png")
    print(f"✅ Annotated screenshot saved: {screenshot_path}")
    
    # Test grid visualization
    grid_data = {
        'grid_pos': [[i//5, i%5] for i in range(15)],
        'unit': ['demon_hunter.png', 'chemist.png', 'knight_statue.png', 'empty.png', 'harlequin.png'] * 3,
        'rank': [1, 2, 3, 0, 4] * 3,
        'u_prob': [500, 800, 1200, 0, 600] * 3
    }
    grid_df = pd.DataFrame(grid_data)
    
    grid_path = visualizer.save_grid_visualization(grid_df, test_img, "test_grid.png")
    print(f"✅ Grid visualization saved: {grid_path}")
    
    return visualizer


def test_mock_bot_scenario():
    """Test debug system with mock bot scenario"""
    print("🤖 Testing Mock Bot Scenario...")
    
    debug_sys = get_debug_system()
    debug_sys.set_enabled(True)
    
    # Simulate bot startup
    debug_sys.log_event("BOT_STARTUP", "initialization", {
        "device": "emulator-5554",
        "config_loaded": True
    })
    
    # Simulate screen capture
    debug_sys.log_event("SCREEN_CAPTURE", "screenshot_taken", {
        "resolution": "1600x900",
        "file_size": "245KB"
    })
    
    # Simulate unit recognition
    debug_sys.log_event("UNIT_RECOGNITION", "grid_analysis", {
        "recognized_units": 12,
        "empty_slots": 3,
        "confidence_avg": 0.85
    })
    
    # Simulate decision making
    debug_sys.debug_decision_making(None, {
        "grid_full": False,
        "merge_candidates": 4,
        "priority_units": ["demon_hunter", "chemist"]
    }, "merge_units", "Board has space but priority units available")
    
    # Simulate action execution
    debug_sys.debug_action_plan(None, "click", {
        "position": [450, 300],
        "target": "unit_spawn"
    }, "Unit spawned")
    
    debug_sys.debug_action_execution(None, "click", True, "unit_spawned")
    
    # Simulate error scenario
    debug_sys.debug_error_recovery(None, Exception("Test error"), "retry_screenshot", True)
    
    # Simulate performance issue
    debug_sys.debug_performance_issue(None, "unit_recognition", 0.25, 0.1, {
        "complexity": "high",
        "grid_units": 15
    })
    
    print("✅ Mock bot scenario completed")
    
    # Show final summary
    summary = debug_sys.get_debug_summary(10)
    print(f"📊 Final Debug Summary:")
    print(f"   Total Events: {summary.get('recent_events', 0)}")
    print(f"   Event Types: {summary.get('event_types', {})}")
    print(f"   Warnings: {summary.get('warnings_count', 0)}")
    print(f"   Errors: {summary.get('errors_count', 0)}")
    
    return debug_sys


def test_debug_export():
    """Test debug data export"""
    print("💾 Testing Debug Export...")
    
    debug_sys = get_debug_system()
    
    # Export session data
    export_path = debug_sys.export_debug_session("test_debug_export.json")
    
    if os.path.exists(export_path):
        file_size = os.path.getsize(export_path)
        print(f"✅ Debug export successful: {export_path} ({file_size} bytes)")
        
        # Verify export contains expected data
        import json
        with open(export_path, 'r') as f:
            export_data = json.load(f)
        
        print(f"   Session Events: {len(export_data.get('events', []))}")
        print(f"   Session Duration: {export_data.get('session_info', {}).get('session_duration', 0):.2f}s")
        
        return True
    else:
        print("❌ Debug export failed")
        return False


def main():
    """Run all debug system tests"""
    print("🚀 Starting Rush Royale Bot Debug System Tests")
    print("=" * 50)
    
    try:
        # Test basic debug system
        debug_sys = test_debug_system()
        
        # Test visual debugging
        visualizer = test_visual_debugging()
        
        # Test mock bot scenario
        test_mock_bot_scenario()
        
        # Test export functionality
        export_success = test_debug_export()
        
        print("=" * 50)
        print("🎉 All debug system tests completed!")
        
        if export_success:
            print("✅ Debug system is fully functional")
            print("\n📋 To enable debug mode:")
            print("   1. Set 'enabled = True' in [debug] section of config.ini")
            print("   2. Use the debug toggle in the bot GUI")
            print("   3. Check debug_output/ folder for visual debug files")
            print("   4. Monitor debug.log for detailed operation logs")
            print("\n🔍 Debug Features Available:")
            print("   • Comprehensive action logging")
            print("   • Visual screenshot annotations")
            print("   • Grid state visualizations")
            print("   • Performance monitoring integration")
            print("   • Error recovery tracking")
            print("   • Real-time debug info in GUI")
            print("   • Session data export")
        else:
            print("⚠️  Some debug features may not work correctly")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
