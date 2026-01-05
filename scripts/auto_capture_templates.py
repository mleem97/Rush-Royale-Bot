#!/usr/bin/env python
"""
Automated Template Capture Tool - Automatically navigates through game menus
and captures all necessary icon templates.

This tool:
1. Navigates through all game screens automatically
2. Captures screenshots at each location
3. Uses edge detection to find UI elements
4. Saves templates with proper naming

Usage:
    python scripts/auto_capture_templates.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import numpy as np
from pathlib import Path
from datetime import datetime
import time
import json

# Template regions - approximate locations in 1600x900 resolution
# Format: (name, x, y, width, height, screen_type)
TEMPLATE_DEFINITIONS = {
    'home': [
        # Bottom navigation bar icons
        ('home_screen.png', 70, 850, 70, 70, 'Home button - bottom left area'),
        ('battle_icon.png', 800, 70, 180, 180, 'Battle button - top center'),
        ('pve_button.png', 1400, 800, 141, 48, 'PvE button - bottom right'),
        ('pvp_button.png', 100, 800, 200, 80, 'PvP button - bottom left'),
    ],
    'dungeon': [
        ('dungeon_page.png', 750, 50, 100, 50, 'Dungeon header text'),
        ('chapter_1.png', 200, 300, 350, 90, 'Chapter 1 banner'),
        ('chapter_2.png', 200, 450, 370, 90, 'Chapter 2 banner'),
        ('back_button.png', 50, 50, 70, 70, 'Back button - top left'),
    ],
    'battle': [
        ('fighting.png', 750, 50, 60, 60, 'Fighting indicator'),
        ('0cont_button.png', 800, 700, 70, 70, 'Continue button'),
        ('1quit.png', 800, 800, 66, 59, 'Quit button'),
    ],
    'general': [
        ('back_button.png', 50, 50, 70, 70, 'Back button'),
        ('x_mark.png', 1500, 100, 30, 30, 'Close X button'),
    ]
}


class AutoTemplateCapture:
    """Automated template capture system."""
    
    def __init__(self):
        self.bot = None
        self.screenshots = {}
        self.captured_templates = []
        self.icons_dir = Path("icons")
        self.backup_dir = self.icons_dir / "backup"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
    def init_bot(self):
        """Initialize bot connection."""
        try:
            from Src.bot_core import Bot
            self.bot = Bot()
            print("✓ Bot connected")
            return True
        except Exception as e:
            print(f"✗ Bot connection failed: {e}")
            return False
    
    def get_screenshot(self):
        """Capture current screen."""
        if self.bot is None:
            return None
        self.bot.getScreen()
        if self.bot.screenRGB is not None:
            return cv2.cvtColor(self.bot.screenRGB, cv2.COLOR_RGB2BGR)
        return None
    
    def click(self, x, y):
        """Click at position."""
        if self.bot:
            self.bot.click(x, y)
            time.sleep(0.5)
    
    def back(self):
        """Press back button."""
        if self.bot:
            self.bot.key_input(4)  # KEYCODE_BACK
            time.sleep(0.5)
    
    def detect_screen_type(self, screenshot):
        """Try to detect which screen we're on."""
        if screenshot is None:
            return 'unknown'
        
        gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
        
        # Check existing templates
        for template_name in ['home_screen.png', 'dungeon_page.png', 'fighting.png']:
            template_path = self.icons_dir / template_name
            if template_path.exists():
                template = cv2.imread(str(template_path), 0)
                if template is not None:
                    res = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)
                    if res.max() > 0.6:
                        if 'home' in template_name:
                            return 'home'
                        elif 'dungeon' in template_name:
                            return 'dungeon'
                        elif 'fighting' in template_name:
                            return 'battle'
        
        return 'unknown'
    
    def find_ui_elements(self, screenshot):
        """Use edge detection to find potential UI elements."""
        gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
        
        # Edge detection
        edges = cv2.Canny(gray, 50, 150)
        
        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter for button-like shapes
        buttons = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = w * h
            aspect = w / max(h, 1)
            
            # Filter by size and aspect ratio
            if 1000 < area < 50000 and 0.3 < aspect < 5:
                buttons.append((x, y, w, h))
        
        return buttons
    
    def extract_template(self, screenshot, x, y, w, h, padding=5):
        """Extract a template region from screenshot."""
        # Add padding
        x1 = max(0, x - padding)
        y1 = max(0, y - padding)
        x2 = min(screenshot.shape[1], x + w + padding)
        y2 = min(screenshot.shape[0], y + h + padding)
        
        return screenshot[y1:y2, x1:x2]
    
    def backup_template(self, name):
        """Backup existing template."""
        old_path = self.icons_dir / name
        if old_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.backup_dir / f"{name.replace('.png', '')}_{timestamp}.png"
            old_template = cv2.imread(str(old_path))
            if old_template is not None:
                cv2.imwrite(str(backup_path), old_template)
                return backup_path
        return None
    
    def save_template(self, name, template):
        """Save template with backup."""
        if template is None or template.size == 0:
            return False
        
        self.backup_template(name)
        save_path = self.icons_dir / name
        cv2.imwrite(str(save_path), template)
        self.captured_templates.append(name)
        return True
    
    def interactive_capture(self, screenshot, name, hint=""):
        """Let user select region interactively."""
        print(f"\n  Capturing: {name}")
        if hint:
            print(f"  Hint: {hint}")
        
        # Selection state
        selecting = False
        start = None
        end = None
        selection = None
        
        def mouse_cb(event, x, y, flags, param):
            nonlocal selecting, start, end, selection
            if event == cv2.EVENT_LBUTTONDOWN:
                start = (x, y)
                selecting = True
            elif event == cv2.EVENT_MOUSEMOVE and selecting:
                end = (x, y)
            elif event == cv2.EVENT_LBUTTONUP:
                end = (x, y)
                selecting = False
                if start and end:
                    x1, y1 = start
                    x2, y2 = end
                    selection = (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
        
        window = f"Select: {name}"
        cv2.namedWindow(window, cv2.WINDOW_NORMAL)
        cv2.setMouseCallback(window, mouse_cb)
        
        # Scale for display
        h, w = screenshot.shape[:2]
        scale = min(1.0, 1400 / w, 900 / h)
        
        print("  → Draw rectangle, ENTER=save, S=skip, ESC=abort all")
        
        while True:
            display = cv2.resize(screenshot.copy(), (int(w * scale), int(h * scale)))
            
            if selecting and start and end:
                cv2.rectangle(display, start, end, (0, 255, 0), 2)
            elif selection:
                x1, y1, x2, y2 = selection
                cv2.rectangle(display, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(display, f"{x2-x1}x{y2-y1}", (x1, y1-5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            
            cv2.imshow(window, display)
            key = cv2.waitKey(30) & 0xFF
            
            if key == 27:  # ESC - abort all
                cv2.destroyWindow(window)
                return None, 'abort'
            elif key == ord('s'):  # Skip this one
                cv2.destroyWindow(window)
                return None, 'skip'
            elif key == 13 and selection:  # ENTER - save
                x1, y1, x2, y2 = selection
                # Scale back
                x1, y1 = int(x1 / scale), int(y1 / scale)
                x2, y2 = int(x2 / scale), int(y2 / scale)
                template = screenshot[y1:y2, x1:x2]
                cv2.destroyWindow(window)
                return template, 'ok'
        
        cv2.destroyWindow(window)
        return None, 'skip'
    
    def run_guided_capture(self):
        """Run guided capture through all screens."""
        print("\n" + "="*60)
        print("GUIDED TEMPLATE CAPTURE")
        print("="*60)
        
        # Define capture sequence
        screens = [
            {
                'name': 'Home Screen',
                'instruction': 'Navigate to the MAIN HOME SCREEN (where you see Battle button)',
                'templates': [
                    ('home_screen.png', 'Small home icon in bottom navigation'),
                    ('battle_icon.png', 'Large BATTLE button'),
                    ('pve_button.png', 'PvE text/button (if visible)'),
                    ('pvp_button.png', 'PvP button'),
                ]
            },
            {
                'name': 'Dungeon Selection',
                'instruction': 'Navigate to DUNGEON/PvE selection screen (chapter list)',
                'templates': [
                    ('dungeon_page.png', 'Dungeon/PvE header or identifier'),
                    ('chapter_1.png', 'Chapter 1 banner/text'),
                    ('chapter_2.png', 'Chapter 2 banner/text'),
                    ('chapter_3.png', 'Chapter 3 banner/text'),
                    ('chapter_4.png', 'Chapter 4 banner/text'),
                    ('chapter_5.png', 'Chapter 5 banner/text'),
                    ('chapter_6.png', 'Chapter 6 banner/text'),
                ]
            },
            {
                'name': 'General UI',
                'instruction': 'Stay on current screen for general UI elements',
                'templates': [
                    ('back_button.png', 'Back arrow button (top-left usually)'),
                ]
            },
        ]
        
        total_captured = 0
        total_skipped = 0
        
        for screen in screens:
            print(f"\n{'='*60}")
            print(f"SCREEN: {screen['name']}")
            print(f"{'='*60}")
            print(f"\n📍 {screen['instruction']}")
            print("\nPress ENTER when ready (or 'q' to quit)...")
            
            user_input = input().strip().lower()
            if user_input == 'q':
                break
            
            # Get screenshot
            print("📸 Capturing screenshot...")
            screenshot = self.get_screenshot()
            
            if screenshot is None:
                print("✗ Could not get screenshot!")
                continue
            
            print(f"✓ Screenshot: {screenshot.shape[1]}x{screenshot.shape[0]}")
            
            # Capture each template
            for template_name, hint in screen['templates']:
                template, status = self.interactive_capture(screenshot, template_name, hint)
                
                if status == 'abort':
                    print("\n⚠ Capture aborted by user")
                    cv2.destroyAllWindows()
                    return
                elif status == 'skip':
                    print(f"  ⏭ Skipped: {template_name}")
                    total_skipped += 1
                elif template is not None:
                    if self.save_template(template_name, template):
                        print(f"  ✓ Saved: {template_name} ({template.shape[1]}x{template.shape[0]})")
                        total_captured += 1
                    else:
                        print(f"  ✗ Failed to save: {template_name}")
        
        cv2.destroyAllWindows()
        
        # Summary
        print("\n" + "="*60)
        print("CAPTURE COMPLETE")
        print("="*60)
        print(f"✓ Captured: {total_captured} templates")
        print(f"⏭ Skipped:  {total_skipped} templates")
        
        if self.captured_templates:
            print("\nNew/updated templates:")
            for name in self.captured_templates:
                print(f"  - {name}")
        
        print("\n💡 Run 'python scripts/debug_dungeon_detection.py' to verify")
    
    def run_auto_scan(self):
        """Automatically scan current screen and suggest captures."""
        print("\n" + "="*60)
        print("AUTO-SCAN MODE")
        print("="*60)
        
        screenshot = self.get_screenshot()
        if screenshot is None:
            print("✗ Could not get screenshot")
            return
        
        print(f"Screenshot: {screenshot.shape[1]}x{screenshot.shape[0]}")
        
        # Detect UI elements
        print("\nDetecting UI elements...")
        elements = self.find_ui_elements(screenshot)
        print(f"Found {len(elements)} potential UI elements")
        
        # Show detected elements
        display = screenshot.copy()
        for i, (x, y, w, h) in enumerate(elements[:20]):  # Limit to 20
            cv2.rectangle(display, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.putText(display, str(i+1), (x, y-5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        # Show
        cv2.namedWindow("Detected Elements", cv2.WINDOW_NORMAL)
        h, w = display.shape[:2]
        scale = min(1.0, 1400 / w, 900 / h)
        cv2.imshow("Detected Elements", cv2.resize(display, (int(w*scale), int(h*scale))))
        print("\nPress any key to continue...")
        cv2.waitKey(0)
        cv2.destroyAllWindows()


def main():
    print("\n" + "="*60)
    print("RUSH ROYALE AUTO TEMPLATE CAPTURE")
    print("="*60)
    
    capturer = AutoTemplateCapture()
    
    print("\nConnecting to BlueStacks...")
    if not capturer.init_bot():
        print("\n⚠ Could not connect to BlueStacks")
        print("Make sure:")
        print("  1. BlueStacks is running")
        print("  2. Rush Royale is open")
        print("  3. ADB is enabled")
        return
    
    while True:
        print("\n" + "-"*40)
        print("Options:")
        print("  1. Guided capture (recommended)")
        print("  2. Auto-scan current screen")
        print("  3. Quick capture single template")
        print("  4. Exit")
        
        choice = input("\nChoice: ").strip()
        
        if choice == '1':
            capturer.run_guided_capture()
        elif choice == '2':
            capturer.run_auto_scan()
        elif choice == '3':
            name = input("Template name (e.g., home_screen.png): ").strip()
            if not name.endswith('.png'):
                name += '.png'
            screenshot = capturer.get_screenshot()
            if screenshot is not None:
                template, status = capturer.interactive_capture(screenshot, name)
                if template is not None:
                    capturer.save_template(name, template)
                    print(f"✓ Saved: {name}")
            cv2.destroyAllWindows()
        elif choice == '4':
            print("\nGoodbye!")
            break


if __name__ == "__main__":
    main()
