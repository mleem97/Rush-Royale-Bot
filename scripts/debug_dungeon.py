"""
Debug script for dungeon loading issues.
Run this to diagnose why the bot has difficulty loading dungeons.

Usage:
    python scripts/debug_dungeon.py
"""
import sys
import os
import time

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
os.chdir(project_root)

import logging
import cv2
import numpy as np
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_icons():
    """Check if required icons exist and are valid."""
    print("\n" + "="*60)
    print("ICON VERIFICATION")
    print("="*60)
    
    icons_dir = Path("icons")
    required_icons = [
        "dungeon_page.png",
        "home_screen.png", 
        "battle_icon.png",
        "chapter_1.png",
        "chapter_2.png",
        "fighting.png",
        "back_button.png"
    ]
    
    missing = []
    invalid = []
    
    for icon in required_icons:
        icon_path = icons_dir / icon
        if not icon_path.exists():
            missing.append(icon)
            print(f"  ❌ MISSING: {icon}")
        else:
            img = cv2.imread(str(icon_path), 0)
            if img is None:
                invalid.append(icon)
                print(f"  ⚠️  INVALID (can't read): {icon}")
            else:
                print(f"  ✅ OK: {icon} ({img.shape[1]}x{img.shape[0]})")
    
    # List all chapter icons
    print("\n  Chapter icons found:")
    for f in sorted(icons_dir.glob("chapter_*.png")):
        img = cv2.imread(str(f), 0)
        if img is not None:
            print(f"    - {f.name} ({img.shape[1]}x{img.shape[0]})")
    
    return len(missing) == 0 and len(invalid) == 0


def test_template_matching():
    """Test template matching with a sample screenshot."""
    print("\n" + "="*60)
    print("TEMPLATE MATCHING TEST")
    print("="*60)
    
    # Try to take a screenshot
    try:
        from Src.bot_core import Bot
        print("  Initializing bot for screenshot...")
        bot = Bot()
        
        # Take screenshot
        print("  Taking screenshot...")
        bot.getScreen()
        
        if bot.screenRGB is None:
            print("  ❌ Failed to capture screenshot!")
            print("  Possible causes:")
            print("    - BlueStacks not running")
            print("    - ADB not connected")
            print("    - Scrcpy not installed")
            return False
        
        print(f"  ✅ Screenshot captured: {bot.screenRGB.shape}")
        
        # Save screenshot for manual inspection
        debug_dir = Path("reports/debug")
        debug_dir.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(debug_dir / "current_screen.png"), bot.screenRGB)
        print(f"  📷 Screenshot saved to: {debug_dir / 'current_screen.png'}")
        
        # Test icon detection
        print("\n  Testing icon detection:")
        icons_found = bot.get_current_icons(new=False, available=True)
        
        if icons_found.empty:
            print("  ⚠️  No icons detected on screen!")
        else:
            print(f"  Found {len(icons_found)} icons:")
            for _, row in icons_found.iterrows():
                print(f"    - {row['icon']}: pos={row['pos [X,Y]']}")
        
        # Test specific chapter detection
        print("\n  Testing chapter icon detection with relaxed threshold:")
        img_gray = cv2.cvtColor(bot.screenRGB, cv2.COLOR_BGR2GRAY)
        
        for chapter_num in range(1, 7):
            chapter_file = f"icons/chapter_{chapter_num}.png"
            if os.path.exists(chapter_file):
                template = cv2.imread(chapter_file, 0)
                if template is not None:
                    # Try different thresholds
                    res = cv2.matchTemplate(img_gray, template, cv2.TM_CCOEFF_NORMED)
                    _, max_val, _, max_loc = cv2.minMaxLoc(res)
                    status = "✅" if max_val >= 0.7 else "❌"
                    print(f"    chapter_{chapter_num}.png: max_val={max_val:.3f} {status}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_dungeon_navigation():
    """Test dungeon navigation step by step."""
    print("\n" + "="*60)
    print("DUNGEON NAVIGATION TEST")
    print("="*60)
    
    try:
        from Src.bot_core import Bot
        from Src.bot_perception import get_button_pos
        
        bot = Bot()
        bot.logger = logger
        
        print("\n  Step 1: Check current screen state")
        avail_buttons = bot.get_current_icons(available=True)
        
        if avail_buttons.empty:
            print("    ❌ No buttons detected!")
            print("    Make sure Rush Royale is open on the home screen or dungeon page")
            return False
        
        print(f"    Found buttons: {list(avail_buttons['icon'])}")
        
        # Check if on dungeon page
        on_dungeon = (avail_buttons['icon'] == 'dungeon_page.png').any()
        on_home = (avail_buttons['icon'] == 'home_screen.png').any()
        
        print(f"    On dungeon page: {on_dungeon}")
        print(f"    On home screen: {on_home}")
        
        if not on_dungeon and not on_home:
            print("    ⚠️  Not on home or dungeon page!")
            print("    Navigate to the home screen first")
            return False
        
        print("\n  Step 2: Test swipe coordinates")
        from Src.bot_perception import get_grid
        boxes, box_size = get_grid()
        
        offset = 60
        start_pos = boxes[0, 0] + offset
        end_pos = boxes[2, 0] + offset
        
        print(f"    Swipe UP: ({start_pos[0]}, {start_pos[1]}) -> ({end_pos[0]}, {end_pos[1]})")
        print(f"    Box size: {box_size}")
        print(f"    Grid shape: {boxes.shape}")
        
        # Calculate expected floor 5 chapter
        floor = 5
        target_chapter = f'chapter_{int(np.ceil((floor)/3))}.png'
        print(f"\n  Step 3: For floor {floor}, looking for {target_chapter}")
        
        if (avail_buttons['icon'] == target_chapter).any():
            pos = get_button_pos(avail_buttons, target_chapter)
            print(f"    ✅ Found {target_chapter} at position: {pos}")
        else:
            print(f"    ❌ {target_chapter} not found on current screen")
            print(f"    Available chapters: {[i for i in avail_buttons['icon'] if 'chapter_' in i]}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_resolution():
    """Check if resolution matches expected 1600x900."""
    print("\n" + "="*60)
    print("RESOLUTION CHECK")
    print("="*60)
    
    try:
        from Src.bot_core import Bot
        bot = Bot()
        bot.getScreen()
        
        if bot.screenRGB is not None:
            height, width = bot.screenRGB.shape[:2]
            expected = (900, 1600)
            
            print(f"  Current resolution: {width}x{height}")
            print(f"  Expected resolution: 1600x900")
            
            if (width, height) == (1600, 900):
                print("  ✅ Resolution matches!")
                return True
            else:
                print("  ⚠️  Resolution mismatch!")
                print("  The bot expects BlueStacks to run at 1600x900")
                print("  Icon positions and coordinates may be wrong")
                return False
        else:
            print("  ❌ Could not capture screenshot")
            return False
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def main():
    print("="*60)
    print("RUSH ROYALE BOT - DUNGEON DEBUG TOOL")
    print("="*60)
    print("\nThis tool will diagnose dungeon loading issues.\n")
    
    # Run checks
    results = {
        "Icons": check_icons(),
        "Resolution": check_resolution(),
        "Template Matching": test_template_matching(),
        "Dungeon Navigation": test_dungeon_navigation(),
    }
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    all_passed = True
    for test, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {test}: {status}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n  All tests passed! The issue might be:")
        print("    - Timing (try increasing delays)")
        print("    - Game state (wrong screen)")
        print("    - Game UI update (icons changed)")
    else:
        print("\n  Some tests failed. Check the output above for details.")
    
    print("\n  Check 'reports/debug/current_screen.png' to see what the bot sees")


if __name__ == "__main__":
    main()
