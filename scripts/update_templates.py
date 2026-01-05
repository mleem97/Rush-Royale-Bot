#!/usr/bin/env python
"""
Template Update Tool - Capture new icon templates from the game.

This tool helps you update outdated icon templates by:
1. Taking a screenshot from the game
2. Letting you select regions for each icon
3. Saving the new templates

Usage:
    python scripts/update_templates.py

Instructions:
1. Open Rush Royale in BlueStacks
2. Navigate to the screen with the icon you want to capture
3. Run this script
4. Follow the prompts to select and save icon regions
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import numpy as np
from pathlib import Path
from datetime import datetime

# Selection state
selection_start = None
selection_end = None
selecting = False
current_selection = None


def mouse_callback(event, x, y, flags, param):
    """Handle mouse events for region selection."""
    global selection_start, selection_end, selecting, current_selection
    
    if event == cv2.EVENT_LBUTTONDOWN:
        selection_start = (x, y)
        selecting = True
    elif event == cv2.EVENT_MOUSEMOVE and selecting:
        selection_end = (x, y)
    elif event == cv2.EVENT_LBUTTONUP:
        selection_end = (x, y)
        selecting = False
        if selection_start and selection_end:
            x1, y1 = selection_start
            x2, y2 = selection_end
            current_selection = (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))


def capture_template(screenshot, window_name="Select Template Region"):
    """Let user select a region and return the cropped template."""
    global selection_start, selection_end, selecting, current_selection
    
    # Reset selection state
    selection_start = None
    selection_end = None
    selecting = False
    current_selection = None
    
    # Create window
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(window_name, mouse_callback)
    
    # Scale for display if too large
    h, w = screenshot.shape[:2]
    scale = min(1.0, 1400 / w, 900 / h)
    display_size = (int(w * scale), int(h * scale))
    
    print("\n  Instructions:")
    print("  - Click and drag to select the icon region")
    print("  - Press ENTER to confirm selection")
    print("  - Press ESC to cancel")
    print("  - Press R to reset selection")
    
    while True:
        # Create display image
        display = cv2.resize(screenshot.copy(), display_size)
        
        # Draw current selection
        if selecting and selection_start and selection_end:
            cv2.rectangle(display, selection_start, selection_end, (0, 255, 0), 2)
        elif current_selection:
            x1, y1, x2, y2 = current_selection
            cv2.rectangle(display, (x1, y1), (x2, y2), (0, 255, 0), 2)
            # Show dimensions
            sel_w, sel_h = x2 - x1, y2 - y1
            cv2.putText(display, f"{sel_w}x{sel_h}", (x1, y1 - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        cv2.imshow(window_name, display)
        key = cv2.waitKey(30) & 0xFF
        
        if key == 27:  # ESC
            cv2.destroyWindow(window_name)
            return None
        elif key == 13:  # ENTER
            if current_selection:
                # Scale selection back to original size
                x1, y1, x2, y2 = current_selection
                x1 = int(x1 / scale)
                y1 = int(y1 / scale)
                x2 = int(x2 / scale)
                y2 = int(y2 / scale)
                template = screenshot[y1:y2, x1:x2]
                cv2.destroyWindow(window_name)
                return template
        elif key == ord('r'):  # Reset
            current_selection = None
            selection_start = None
            selection_end = None
    
    cv2.destroyWindow(window_name)
    return None


def get_screenshot():
    """Get screenshot from BlueStacks via ADB."""
    try:
        from Src.bot_core import Bot
        bot = Bot()
        bot.getScreen()
        if bot.screenRGB is not None:
            # Convert RGB to BGR for OpenCV
            return cv2.cvtColor(bot.screenRGB, cv2.COLOR_RGB2BGR)
    except Exception as e:
        print(f"Could not get live screenshot: {e}")
    
    # Fallback: check for debug screenshots
    debug_dir = Path("screenshots")
    if debug_dir.exists():
        screenshots = list(debug_dir.glob("*.png"))
        if screenshots:
            latest = max(screenshots, key=lambda p: p.stat().st_mtime)
            print(f"Using cached screenshot: {latest}")
            return cv2.imread(str(latest))
    
    return None


def list_templates():
    """List all existing templates with their sizes."""
    icons_dir = Path("icons")
    templates = []
    
    for icon_path in sorted(icons_dir.glob("*.png")):
        img = cv2.imread(str(icon_path))
        if img is not None:
            h, w = img.shape[:2]
            templates.append((icon_path.name, w, h))
    
    return templates


def main():
    print("\n" + "="*60)
    print("RUSH ROYALE TEMPLATE UPDATE TOOL")
    print("="*60)
    
    # List existing templates
    print("\nExisting templates:")
    print("-"*40)
    templates = list_templates()
    
    # Categorize templates
    navigation = []
    chapters = []
    other = []
    
    for name, w, h in templates:
        if 'chapter_' in name:
            chapters.append((name, w, h))
        elif name in ['home_screen.png', 'battle_icon.png', 'pve_button.png', 
                      'pvp_button.png', 'dungeon_page.png', 'back_button.png']:
            navigation.append((name, w, h))
        else:
            other.append((name, w, h))
    
    print("\n📍 Navigation icons:")
    for name, w, h in navigation:
        print(f"   {name:<25} {w:>3}x{h:<3}")
    
    print("\n📖 Chapter icons:")
    for name, w, h in chapters:
        print(f"   {name:<25} {w:>3}x{h:<3}")
    
    print("\n🔧 Other icons:")
    for name, w, h in other:
        print(f"   {name:<25} {w:>3}x{h:<3}")
    
    # Get screenshot
    print("\n" + "-"*40)
    print("Getting screenshot from BlueStacks...")
    screenshot = get_screenshot()
    
    if screenshot is None:
        print("ERROR: Could not get screenshot!")
        print("\nOptions:")
        print("  1. Make sure BlueStacks is running with Rush Royale")
        print("  2. Run debug_dungeon_detection.py first to create a cached screenshot")
        return
    
    print(f"Screenshot size: {screenshot.shape[1]}x{screenshot.shape[0]}")
    
    # Main loop
    while True:
        print("\n" + "-"*40)
        print("Options:")
        print("  1. Capture new template")
        print("  2. Update existing template")
        print("  3. Take new screenshot")
        print("  4. View current screenshot")
        print("  5. Exit")
        
        choice = input("\nChoice (1-5): ").strip()
        
        if choice == '1':
            name = input("Enter template name (e.g., 'my_icon.png'): ").strip()
            if not name.endswith('.png'):
                name += '.png'
            
            print(f"\nCapturing template: {name}")
            template = capture_template(screenshot, f"Select region for: {name}")
            
            if template is not None and template.size > 0:
                save_path = Path("icons") / name
                cv2.imwrite(str(save_path), template)
                print(f"✓ Saved: {save_path} ({template.shape[1]}x{template.shape[0]})")
            else:
                print("✗ Capture cancelled")
        
        elif choice == '2':
            print("\nExisting templates:")
            all_templates = [t[0] for t in templates]
            for i, name in enumerate(all_templates, 1):
                print(f"  {i:2}. {name}")
            
            idx = input("\nEnter number to update: ").strip()
            try:
                idx = int(idx) - 1
                if 0 <= idx < len(all_templates):
                    name = all_templates[idx]
                    
                    # Show old template
                    old_path = Path("icons") / name
                    old_template = cv2.imread(str(old_path))
                    if old_template is not None:
                        cv2.imshow(f"Old: {name}", old_template)
                        cv2.waitKey(500)
                    
                    print(f"\nUpdating: {name}")
                    template = capture_template(screenshot, f"Select new region for: {name}")
                    
                    cv2.destroyAllWindows()
                    
                    if template is not None and template.size > 0:
                        # Backup old
                        backup_dir = Path("icons/backup")
                        backup_dir.mkdir(exist_ok=True)
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        backup_path = backup_dir / f"{name.replace('.png', '')}_{timestamp}.png"
                        if old_template is not None:
                            cv2.imwrite(str(backup_path), old_template)
                            print(f"  Backed up old template to: {backup_path}")
                        
                        # Save new
                        cv2.imwrite(str(old_path), template)
                        print(f"✓ Updated: {old_path} ({template.shape[1]}x{template.shape[0]})")
                    else:
                        print("✗ Update cancelled")
            except (ValueError, IndexError):
                print("Invalid selection")
        
        elif choice == '3':
            print("\nTaking new screenshot...")
            new_screenshot = get_screenshot()
            if new_screenshot is not None:
                screenshot = new_screenshot
                print(f"✓ New screenshot: {screenshot.shape[1]}x{screenshot.shape[0]}")
            else:
                print("✗ Could not get new screenshot")
        
        elif choice == '4':
            cv2.namedWindow("Current Screenshot", cv2.WINDOW_NORMAL)
            h, w = screenshot.shape[:2]
            scale = min(1.0, 1400 / w, 900 / h)
            display = cv2.resize(screenshot, (int(w * scale), int(h * scale)))
            cv2.imshow("Current Screenshot", display)
            print("Press any key to close...")
            cv2.waitKey(0)
            cv2.destroyAllWindows()
        
        elif choice == '5':
            print("\nGoodbye!")
            break
        
        else:
            print("Invalid choice")
    
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
