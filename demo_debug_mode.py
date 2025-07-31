#!/usr/bin/env python3
"""
Debug Mode Demonstration Script
Shows debug system features without running the full bot
"""

import os
import sys
import time
import configparser
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'Src'))

from debug_system import get_debug_system
from performance_monitor import get_performance_monitor


def demonstrate_debug_features():
    """Demonstrate key debug features"""
    print("🎮 Rush Royale Bot - Debug Mode Demonstration")
    print("=" * 60)
    
    # Initialize systems
    debug_sys = get_debug_system()
    perf_monitor = get_performance_monitor()
    
    # Check current config
    config = configparser.ConfigParser()
    config.read('config.ini')
    
    current_debug = config.getboolean('debug', 'enabled', fallback=False)
    print(f"📋 Current debug status: {'ENABLED' if current_debug else 'DISABLED'}")
    
    # Enable debug mode for demonstration
    debug_sys.set_enabled(True)
    print("✅ Debug mode enabled for demonstration")
    
    print("\n🔍 Debug Feature Demonstration:")
    print("-" * 40)
    
    # 1. Basic Event Logging
    print("1. Event Logging:")
    debug_sys.log_event("DEMO", "feature_showcase", {
        "feature": "event_logging",
        "user": "demonstration"
    })
    print("   ✓ Event logged to debug system")
    
    # 2. Performance Monitoring
    print("\n2. Performance Monitoring:")
    with debug_sys.time_operation('demo_operation') as timer:
        time.sleep(0.1)  # Simulate work
        timer.add_detail('simulated_work', 'sleep_0.1s')
    print("   ✓ Performance data captured")
    
    # 3. Decision Making Logging
    print("\n3. Decision Making:")
    debug_sys.debug_decision_making(None, {
        "board_state": "early_game",
        "units_available": ["demon_hunter", "chemist"],
        "mana": 5
    }, "spawn_unit", "Early game strategy: prioritize DPS units")
    print("   ✓ Decision logic logged")
    
    # 4. Action Planning and Execution
    print("\n4. Action Planning:")
    debug_sys.debug_action_plan(None, "spawn_unit", {
        "position": "grid_slot_5",
        "unit_type": "demon_hunter"
    }, "Unit spawned on board")
    
    debug_sys.debug_action_execution(None, "spawn_unit", True, "unit_spawned")
    print("   ✓ Action planning and execution logged")
    
    # 5. Error Handling
    print("\n5. Error Recovery:")
    debug_sys.debug_error_recovery(None, Exception("Demo error"), "retry_operation", True)
    print("   ✓ Error recovery scenario logged")
    
    # 6. Performance Warning
    print("\n6. Performance Monitoring:")
    debug_sys.debug_performance_issue(None, "demo_slow_operation", 0.5, 0.1, {
        "operation_type": "demonstration",
        "complexity": "simulated"
    })
    print("   ✓ Performance warning generated")
    
    # Show debug summary
    print("\n📊 Debug Session Summary:")
    summary = debug_sys.get_debug_summary(5)
    print(f"   Events Logged: {summary.get('recent_events', 0)}")
    print(f"   Event Types: {list(summary.get('event_types', {}).keys())}")
    print(f"   Warnings: {summary.get('warnings_count', 0)}")
    print(f"   Errors: {summary.get('errors_count', 0)}")
    
    # Export debug data
    print("\n💾 Exporting Debug Data:")
    export_path = debug_sys.export_debug_session("demo_debug_session.json")
    if os.path.exists(export_path):
        file_size = os.path.getsize(export_path)
        print(f"   ✓ Debug data exported: {export_path} ({file_size} bytes)")
    
    return debug_sys


def show_debug_files():
    """Show created debug files"""
    print("\n📁 Debug Files Created:")
    print("-" * 40)
    
    debug_files = []
    
    # Check for debug output directory
    debug_output = Path("debug_output")
    if debug_output.exists():
        for subdir in ["screenshots", "annotated", "grids", "units"]:
            subpath = debug_output / subdir
            if subpath.exists():
                files = list(subpath.glob("*"))
                if files:
                    debug_files.extend(files)
                    print(f"   {subdir}/: {len(files)} files")
    
    # Check for debug logs
    if os.path.exists("debug.log"):
        size = os.path.getsize("debug.log")
        debug_files.append("debug.log")
        print(f"   debug.log: {size} bytes")
    
    # Check for exports
    export_files = list(Path(".").glob("*debug*.json"))
    if export_files:
        debug_files.extend(export_files)
        print(f"   Export files: {[f.name for f in export_files]}")
    
    print(f"\n   Total debug files: {len(debug_files)}")
    return debug_files


def show_config_info():
    """Show debug configuration information"""
    print("\n⚙️  Debug Configuration:")
    print("-" * 40)
    
    config = configparser.ConfigParser()
    config.read('config.ini')
    
    if config.has_section('debug'):
        for key, value in config['debug'].items():
            print(f"   {key}: {value}")
    else:
        print("   No [debug] section found in config.ini")
        print("   Using default settings")
    
    print("\n📋 Available Debug Settings:")
    print("   enabled: Enable/disable debug mode")
    print("   save_screenshots: Save raw screenshots")
    print("   save_grid_states: Save grid visualizations") 
    print("   save_unit_crops: Save individual unit images")
    print("   log_file: Debug log file location")


def show_usage_tips():
    """Show tips for using debug mode"""
    print("\n💡 Debug Mode Usage Tips:")
    print("-" * 40)
    print("1. Enable debug mode only when troubleshooting")
    print("2. Check debug_output/ folder for visual debugging")
    print("3. Review debug.log for detailed operation logs")
    print("4. Use 'Export Debug' button in GUI for comprehensive data")
    print("5. Clean old debug files periodically to save disk space")
    
    print("\n🔧 Common Debug Scenarios:")
    print("• Bot not recognizing units → Check grid visualizations")
    print("• Bot clicking wrong spots → Check annotated screenshots")
    print("• Poor merge decisions → Review decision making logs")
    print("• Performance issues → Check timing warnings")
    print("• Crashes or errors → Review error recovery logs")
    
    print("\n📖 For complete documentation, see: DEBUG_MODE_GUIDE.md")


def main():
    """Main demonstration function"""
    try:
        # Run demonstration
        debug_sys = demonstrate_debug_features()
        
        # Show created files
        debug_files = show_debug_files()
        
        # Show configuration
        show_config_info()
        
        # Show usage tips
        show_usage_tips()
        
        print("\n" + "=" * 60)
        print("🎉 Debug Mode Demonstration Complete!")
        print("\nTo use debug mode with the actual bot:")
        print("1. Set 'enabled = True' in config.ini [debug] section")
        print("2. Or use the debug toggle in the bot GUI") 
        print("3. Run the bot and observe detailed debug output")
        print("\n🚀 Ready to debug your Rush Royale Bot!")
        
    except Exception as e:
        print(f"❌ Demonstration failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
