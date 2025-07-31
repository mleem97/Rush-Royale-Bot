#!/usr/bin/env python3
"""
Test PvE Dungeon Navigation
Tests the improved dungeon selection and navigation logic.
"""

import sys
import os
import time
import configparser
from pathlib import Path

# Add Src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'Src'))

from bot_core import Bot
from debug_system import get_debug_system
from warning_suppressor import configure_warnings

# Configure warnings
configure_warnings()

def test_pve_navigation():
    """Test PvE dungeon navigation with debug logging."""
    print("🧪 Testing PvE Dungeon Navigation")
    print("=" * 50)
    
    # Initialize debug system
    debug_system = get_debug_system()
    debug_system.set_enabled(True)
    print("✅ Debug system enabled")
    
    # Read config
    config = configparser.ConfigParser()
    config.read('config.ini')
    
    floor = int(config.get('bot', 'floor', fallback=7))
    print(f"🎯 Target floor: {floor}")
    
    # Initialize bot
    try:
        print("🤖 Initializing bot...")
        bot = Bot()
        bot.debug = debug_system
        
        # Test 1: Take screenshot and analyze current state
        print("\n📸 Test 1: Analyzing current screen state")
        current_icons = bot.get_current_icons(available=True)
        if not current_icons.empty:
            icons = current_icons['icon'].tolist()
            print(f"✅ Detected icons: {icons}")
        else:
            print("⚠️ No icons detected - check device connection")
            return False
            
        # Test 2: Check if we can navigate to battle screen
        print("\n🔍 Test 2: Testing battle screen navigation")
        df, status = bot.battle_screen(start=False)
        print(f"Current status: {status}")
        
        if status == 'home':
            print("✅ On home screen, testing PvE navigation...")
            
            # Test 3: Try to start PvE dungeon
            print(f"\n🏰 Test 3: Starting PvE dungeon floor {floor}")
            df, result = bot.battle_screen(start=True, pve=True, floor=floor)
            print(f"Battle screen result: {result}")
            
            # Wait a bit and check if we successfully entered dungeon
            time.sleep(5)
            df, final_status = bot.battle_screen(start=False)
            print(f"Final status after dungeon attempt: {final_status}")
            
            if final_status == 'fighting':
                print("🎉 SUCCESS: Successfully entered dungeon battle!")
                return True
            else:
                print(f"❌ FAILED: Expected 'fighting' but got '{final_status}'")
                return False
        else:
            print(f"ℹ️ Not on home screen (status: {status}), cannot test PvE navigation")
            return False
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
        return False
    finally:
        # Export debug session for analysis
        try:
            session_file = debug_system.export_debug_session()
            print(f"📋 Debug session exported to: {session_file}")
        except Exception as e:
            print(f"⚠️ Could not export debug session: {e}")

def analyze_debug_logs():
    """Analyze recent debug logs for PvE navigation patterns."""
    print("\n🔍 Analyzing Debug Logs")
    print("=" * 30)
    
    debug_files = list(Path('.').glob('debug_session_*.json'))
    if not debug_files:
        print("ℹ️ No debug session files found")
        return
    
    # Get most recent debug file
    latest_debug = max(debug_files, key=lambda x: x.stat().st_mtime)
    print(f"📄 Analyzing: {latest_debug}")
    
    try:
        import json
        with open(latest_debug, 'r') as f:
            session_data = json.load(f)
        
        # Count PvE start attempts
        pve_starts = [event for event in session_data.get('events', []) 
                      if event.get('operation') == 'starting_pve']
        
        # Count dungeon calls
        dungeon_calls = [event for event in session_data.get('events', [])
                        if event.get('event_type') == 'DUNGEON_START']
        
        # Count fighting states
        fighting_states = [event for event in session_data.get('events', [])
                          if event.get('operation') == 'combat_detected']
        
        print(f"📊 Analysis Results:")
        print(f"   PvE start attempts: {len(pve_starts)}")
        print(f"   Dungeon function calls: {len(dungeon_calls)}")
        print(f"   Combat states reached: {len(fighting_states)}")
        
        if len(pve_starts) > 0 and len(fighting_states) == 0:
            print("⚠️ ISSUE: PvE starts detected but no combat reached")
            print("   This suggests dungeon navigation is failing")
        elif len(fighting_states) > 0:
            print("✅ SUCCESS: Combat states detected - navigation working")
        else:
            print("ℹ️ No PvE activity detected in this session")
            
    except Exception as e:
        print(f"❌ Error analyzing debug logs: {e}")

if __name__ == "__main__":
    print("🚀 PvE Navigation Test Suite")
    print("=" * 40)
    
    # Check if we're in the right directory
    if not os.path.exists('config.ini'):
        print("❌ Error: config.ini not found. Please run from Rush-Royale-Bot directory.")
        sys.exit(1)
    
    # Run tests
    success = test_pve_navigation()
    
    # Analyze logs
    analyze_debug_logs()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 PvE Navigation Test: PASSED")
    else:
        print("❌ PvE Navigation Test: FAILED")
        print("💡 Check the debug logs above for details")
    
    print("🔧 Suggested next steps:")
    print("   1. Enable debug mode in config.ini")
    print("   2. Run the bot normally and check debug output")
    print("   3. Use 'python test_pve_navigation.py' to test navigation")
    print("=" * 50)
