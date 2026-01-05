#!/usr/bin/env python
"""
Debug script to test dungeon detection.
Run this while Rush Royale is open in BlueStacks on the dungeon selection screen.

Usage:
    python scripts/debug_dungeon_detection.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import numpy as np
from pathlib import Path
from datetime import datetime

# Try to import bot modules
try:
    from Src.bot_core import Bot, _load_config
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running from the project root directory")
    sys.exit(1)


def analyze_icons(bot, save_debug=True):
    """Analyze all icons on current screen with detailed output."""
    print("\n" + "="*60)
    print("ICON DETECTION ANALYSIS")
    print("="*60)
    
    # Get screenshot
    print("\n[1] Getting screenshot...")
    bot.getScreen()
    
    if bot.screenRGB is None:
        print("ERROR: Could not get screenshot!")
        print("  - Is BlueStacks running?")
        print("  - Is Rush Royale open?")
        print("  - Is ADB connection working?")
        return
    
    print(f"  Screenshot shape: {bot.screenRGB.shape}")
    
    # Save screenshot for debugging
    if save_debug:
        debug_dir = Path("screenshots")
        debug_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = debug_dir / f"debug_screen_{timestamp}.png"
        cv2.imwrite(str(screenshot_path), cv2.cvtColor(bot.screenRGB, cv2.COLOR_RGB2BGR))
        print(f"  Saved screenshot: {screenshot_path}")
    
    # Analyze each icon
    print("\n[2] Testing icon templates...")
    print("-"*60)
    
    img_gray = cv2.cvtColor(bot.screenRGB, cv2.COLOR_BGR2GRAY)
    img_blur = cv2.GaussianBlur(img_gray, (3, 3), 0)
    
    # Load config thresholds
    config = _load_config()
    icon_thresh = config.getfloat('detection', 'icon_threshold', fallback=0.78)
    chapter_thresh = config.getfloat('detection', 'chapter_threshold', fallback=0.70)
    dungeon_thresh = config.getfloat('detection', 'dungeon_page_threshold', fallback=0.72)
    
    # Priority icons for dungeon navigation
    priority_icons = [
        'home_screen.png',
        'battle_icon.png',
        'pve_button.png',
        'pvp_button.png',
        'dungeon_page.png',
        'chapter_1.png', 'chapter_2.png', 'chapter_3.png',
        'chapter_4.png', 'chapter_5.png', 'chapter_6.png',
        'back_button.png',
        'fighting.png',
    ]
    
    icon_dir = Path("icons")
    results = []
    
    for icon_name in os.listdir(icon_dir):
        if not icon_name.endswith('.png'):
            continue
            
        template_path = icon_dir / icon_name
        template = cv2.imread(str(template_path), 0)
        if template is None:
            continue
        
        template_blur = cv2.GaussianBlur(template, (3, 3), 0)
        
        # Determine threshold
        is_chapter = 'chapter_' in icon_name
        threshold = icon_thresh
        if is_chapter:
            threshold = chapter_thresh
        elif icon_name == 'dungeon_page.png':
            threshold = dungeon_thresh
        
        # Try multi-scale matching
        best_val = 0.0
        best_loc = (0, 0)
        best_scale = 1.0
        
        scales = [0.85, 0.9, 0.95, 1.0, 1.05, 1.1, 1.15] if is_chapter else [0.9, 1.0, 1.1]
        
        for scale in scales:
            new_w = max(1, int(template_blur.shape[1] * scale))
            new_h = max(1, int(template_blur.shape[0] * scale))
            tmpl = cv2.resize(template_blur, (new_w, new_h), interpolation=cv2.INTER_AREA)
            
            if img_blur.shape[0] < tmpl.shape[0] or img_blur.shape[1] < tmpl.shape[1]:
                continue
            
            res = cv2.matchTemplate(img_blur, tmpl, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(res)
            
            if max_val > best_val:
                best_val = max_val
                best_loc = max_loc
                best_scale = scale
        
        found = best_val >= threshold
        is_priority = icon_name in priority_icons
        
        results.append({
            'icon': icon_name,
            'best_val': best_val,
            'threshold': threshold,
            'found': found,
            'location': best_loc,
            'scale': best_scale,
            'priority': is_priority
        })
    
    # Sort by priority and confidence
    results.sort(key=lambda x: (-x['priority'], -x['best_val']))
    
    print(f"{'Icon':<25} {'Match':>7} {'Thresh':>7} {'Found':>6} {'Scale':>6} {'Location'}")
    print("-"*80)
    
    for r in results:
        indicator = "✓" if r['found'] else "✗"
        priority = "★" if r['priority'] else " "
        color = "" if not r['found'] else "\033[92m" if r['found'] else ""
        end_color = "\033[0m" if color else ""
        
        if r['priority'] or r['best_val'] >= r['threshold'] * 0.9:  # Show near-matches too
            print(f"{priority}{r['icon']:<24} {r['best_val']:>6.3f} {r['threshold']:>6.2f} {indicator:>5} {r['scale']:>5.2f}  {r['location']}")
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    found_icons = [r for r in results if r['found']]
    found_priority = [r for r in found_icons if r['priority']]
    
    print(f"Total icons found: {len(found_icons)}/{len(results)}")
    print(f"Priority icons found: {len(found_priority)}/{len([r for r in results if r['priority']])}")
    
    print("\nDetected priority icons:")
    for r in found_priority:
        print(f"  - {r['icon']} (confidence: {r['best_val']:.3f})")
    
    # Screen state interpretation
    print("\n[3] Screen State Interpretation:")
    print("-"*40)
    
    found_names = {r['icon'] for r in found_icons}
    
    if 'home_screen.png' in found_names and 'battle_icon.png' in found_names:
        print("  → HOME SCREEN detected")
        print("    Action: Click PvE button to navigate to dungeon")
    elif 'dungeon_page.png' in found_names or any(f'chapter_{i}.png' in found_names for i in range(1, 7)):
        print("  → DUNGEON PAGE detected")
        print("    Action: Ready to select floor")
    elif 'fighting.png' in found_names:
        print("  → IN BATTLE detected")
        print("    Action: Currently fighting")
    elif 'pve_button.png' in found_names:
        print("  → PVE BUTTON visible")
        print("    Action: Click to enter dungeon selection")
    else:
        print("  → UNKNOWN SCREEN")
        print("    Suggestion: Check if templates are outdated")
    
    # Check template freshness
    print("\n[4] Template Quality Check:")
    print("-"*40)
    
    low_match = [r for r in results if r['priority'] and r['best_val'] < 0.5]
    if low_match:
        print("  ⚠ These priority icons have very low match scores:")
        for r in low_match:
            print(f"    - {r['icon']}: {r['best_val']:.3f} (may need updating)")
    else:
        print("  ✓ All priority icon templates seem reasonable")
    
    near_threshold = [r for r in results if r['priority'] and not r['found'] and r['best_val'] >= r['threshold'] * 0.85]
    if near_threshold:
        print("\n  ⚠ These icons are close to threshold (consider lowering):")
        for r in near_threshold:
            print(f"    - {r['icon']}: {r['best_val']:.3f} vs threshold {r['threshold']:.2f}")


def main():
    print("\n" + "="*60)
    print("RUSH ROYALE DUNGEON DETECTION DEBUGGER")
    print("="*60)
    
    print("\nInitializing bot...")
    try:
        bot = Bot()
        print("Bot initialized successfully!")
    except Exception as e:
        print(f"ERROR initializing bot: {e}")
        print("\nTroubleshooting:")
        print("  1. Make sure BlueStacks is running")
        print("  2. Verify ADB is enabled in BlueStacks settings")
        print("  3. Check config.ini for correct port settings")
        return
    
    print("\nStarting analysis... (make sure Rush Royale is visible)")
    input("Press Enter when ready...")
    
    analyze_icons(bot, save_debug=True)
    
    print("\n" + "="*60)
    print("Done! Check screenshots folder for captured screen.")
    print("="*60)


if __name__ == "__main__":
    main()
