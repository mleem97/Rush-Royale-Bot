#!/usr/bin/env python
"""
Extract Templates from Screenshots - Use existing screenshots to capture templates.

This tool loads screenshots from debug_screenshots folder and lets you
extract templates from them without needing a live game connection.

Usage:
    python scripts/extract_from_screenshots.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import numpy as np
from pathlib import Path
from datetime import datetime
import shutil

# Selection globals
g_selection = None
g_selecting = False
g_start = None
g_end = None


def mouse_callback(event, x, y, flags, param):
    global g_selection, g_selecting, g_start, g_end
    if event == cv2.EVENT_LBUTTONDOWN:
        g_start = (x, y)
        g_selecting = True
    elif event == cv2.EVENT_MOUSEMOVE and g_selecting:
        g_end = (x, y)
    elif event == cv2.EVENT_LBUTTONUP:
        g_end = (x, y)
        g_selecting = False
        if g_start and g_end:
            x1, y1 = g_start
            x2, y2 = g_end
            if abs(x2-x1) > 5 and abs(y2-y1) > 5:
                g_selection = (min(x1,x2), min(y1,y2), max(x1,x2), max(y1,y2))


# All templates to capture
ALL_TEMPLATES = [
    # Navigation
    ('home_screen.png', 'Home-Icon (kleines Haus unten)'),
    ('battle_icon.png', 'Großer BATTLE Button'),
    ('pve_button.png', 'PvE Button'),
    ('pvp_button.png', 'PvP Button'),
    ('pvp_button2.png', 'PvP Button Alternative'),
    ('back_button.png', 'Zurück-Pfeil'),
    ('x_mark.png', 'Schließen X'),
    
    # Dungeon
    ('dungeon_page.png', 'Dungeon Header/Überschrift'),
    ('chapter_1.png', 'Kapitel 1'),
    ('chapter_2.png', 'Kapitel 2'),
    ('chapter_3.png', 'Kapitel 3'),
    ('chapter_4.png', 'Kapitel 4'),
    ('chapter_5.png', 'Kapitel 5'),
    ('chapter_6.png', 'Kapitel 6'),
    
    # Battle
    ('fighting.png', 'Kampf-Indikator'),
    ('0cont_button.png', 'Continue/Weiter Button'),
    ('1quit.png', 'Quit/Beenden Button'),
    
    # Shop
    ('store_refresh.png', 'Shop Refresh'),
    ('refresh_button.png', 'Refresh Button'),
    
    # Quests
    ('quest_done.png', 'Quest erledigt'),
    ('quest_collect.png', 'Quest abholen'),
    
    # Ads
    ('ad_pve.png', 'PvE Werbung'),
    ('ad_season.png', 'Season Werbung'),
    
    # Other
    ('friend_menu.png', 'Freundesmenü'),
]


class ScreenshotTemplateExtractor:
    def __init__(self):
        self.screenshots_dir = Path("screenshots")
        self.icons_dir = Path("icons")
        self.backup_dir = Path("icons_backup_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
        self.screenshots = []
        self.current_idx = 0
        self.captured = []
        self.scale = 1.0
        
    def load_screenshots(self):
        """Load all screenshots from debug_screenshots folder."""
        if not self.screenshots_dir.exists():
            print(f"❌ Ordner nicht gefunden: {self.screenshots_dir}")
            return False
        
        self.screenshots = sorted(
            self.screenshots_dir.glob("*.png"),
            key=lambda p: p.stat().st_mtime
        )
        
        if not self.screenshots:
            print("❌ Keine Screenshots gefunden!")
            return False
        
        print(f"✓ {len(self.screenshots)} Screenshots gefunden")
        return True
    
    def backup_existing(self):
        """Backup existing templates."""
        if self.icons_dir.exists() and any(self.icons_dir.glob("*.png")):
            print(f"\n📦 Sichere bestehende Templates...")
            shutil.copytree(self.icons_dir, self.backup_dir)
            count = len(list(self.backup_dir.glob("*.png")))
            print(f"   {count} Templates gesichert nach: {self.backup_dir}")
    
    def get_current_screenshot(self):
        """Get current screenshot."""
        if 0 <= self.current_idx < len(self.screenshots):
            path = self.screenshots[self.current_idx]
            img = cv2.imread(str(path))
            return img, path.name
        return None, None
    
    def run(self):
        """Main extraction loop."""
        global g_selection, g_selecting, g_start, g_end
        
        print("\n" + "="*60)
        print("📸 TEMPLATE-EXTRAKTION AUS SCREENSHOTS")
        print("="*60)
        
        if not self.load_screenshots():
            return
        
        self.backup_existing()
        
        # Show preview of all screenshots
        print("\n📋 Verfügbare Screenshots:")
        for i, path in enumerate(self.screenshots):
            print(f"   {i+1:2}. {path.name}")
        
        print("\n" + "-"*60)
        print("STEUERUNG:")
        print("  [Maus ziehen]  = Region auswählen")
        print("  [ENTER]        = Template speichern")
        print("  [S]            = Template überspringen")
        print("  [←/→ oder A/D] = Screenshot wechseln")
        print("  [N]            = Nächstes Template")
        print("  [ESC]          = Beenden")
        print("-"*60)
        
        input("\nDrücke ENTER zum Starten...")
        
        template_idx = 0
        
        window = "Template Extraktion"
        # Fixed 9:16 aspect ratio window (900x1600 scaled down)
        cv2.namedWindow(window, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window, 506, 900)  # 900:1600 aspect ratio, fitting screen
        cv2.setMouseCallback(window, mouse_callback)
        
        while template_idx < len(ALL_TEMPLATES):
            template_name, hint = ALL_TEMPLATES[template_idx]
            
            # Skip if already captured
            if template_name in self.captured:
                template_idx += 1
                continue
            
            screenshot, screenshot_name = self.get_current_screenshot()
            if screenshot is None:
                print("❌ Kein Screenshot verfügbar!")
                break
            
            h, w = screenshot.shape[:2]
            # Fixed scale to fit 9:16 window (506x900)
            self.scale = min(506/w, 900/h)
            display_w = int(w * self.scale)
            display_h = int(h * self.scale)
            
            g_selection = None
            
            print(f"\n[{template_idx+1}/{len(ALL_TEMPLATES)}] 📍 {template_name}")
            print(f"   Hinweis: {hint}")
            print(f"   Screenshot: {screenshot_name} ({self.current_idx+1}/{len(self.screenshots)})")
            
            while True:
                # Display with fixed aspect ratio
                display = cv2.resize(screenshot.copy(), (display_w, display_h))
                
                # Draw selection
                if g_selecting and g_start and g_end:
                    cv2.rectangle(display, g_start, g_end, (0, 255, 0), 2)
                elif g_selection:
                    x1, y1, x2, y2 = g_selection
                    cv2.rectangle(display, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    sw, sh = x2-x1, y2-y1
                    cv2.putText(display, f"{int(sw/self.scale)}x{int(sh/self.scale)}", 
                               (x1, y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                
                # Info overlay
                cv2.rectangle(display, (5, 5), (600, 70), (0, 0, 0), -1)
                cv2.putText(display, f"Template: {template_name}", (10, 25),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)
                cv2.putText(display, f"Screenshot {self.current_idx+1}/{len(self.screenshots)}: {screenshot_name}", 
                           (10, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                cv2.putText(display, "ENTER=Save | S=Skip | A/D=Prev/Next Screenshot | N=Next Template | ESC=Quit", 
                           (10, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
                
                cv2.imshow(window, display)
                key = cv2.waitKey(30) & 0xFF
                
                if key == 27:  # ESC
                    cv2.destroyAllWindows()
                    self._print_summary()
                    return
                
                elif key == ord('s') or key == ord('S'):
                    print(f"   ⏭️ Übersprungen")
                    template_idx += 1
                    break
                
                elif key == ord('n') or key == ord('N'):
                    print(f"   ⏭️ Nächstes Template")
                    template_idx += 1
                    break
                
                elif key == ord('a') or key == ord('A') or key == 81:  # A or Left
                    self.current_idx = (self.current_idx - 1) % len(self.screenshots)
                    screenshot, screenshot_name = self.get_current_screenshot()
                    h, w = screenshot.shape[:2]
                    self.scale = min(506/w, 900/h)
                    display_w = int(w * self.scale)
                    display_h = int(h * self.scale)
                    g_selection = None
                    print(f"   📸 Screenshot: {screenshot_name}")
                
                elif key == ord('d') or key == ord('D') or key == 83:  # D or Right
                    self.current_idx = (self.current_idx + 1) % len(self.screenshots)
                    screenshot, screenshot_name = self.get_current_screenshot()
                    h, w = screenshot.shape[:2]
                    self.scale = min(506/w, 900/h)
                    display_w = int(w * self.scale)
                    display_h = int(h * self.scale)
                    g_selection = None
                    print(f"   📸 Screenshot: {screenshot_name}")
                
                elif key == 13 and g_selection:  # ENTER
                    x1, y1, x2, y2 = g_selection
                    # Scale back
                    x1 = int(x1 / self.scale)
                    y1 = int(y1 / self.scale)
                    x2 = int(x2 / self.scale)
                    y2 = int(y2 / self.scale)
                    
                    template = screenshot[y1:y2, x1:x2]
                    
                    # Save
                    save_path = self.icons_dir / template_name
                    cv2.imwrite(str(save_path), template)
                    self.captured.append(template_name)
                    
                    print(f"   ✓ Gespeichert: {template_name} ({template.shape[1]}x{template.shape[0]})")
                    template_idx += 1
                    break
        
        cv2.destroyAllWindows()
        self._print_summary()
    
    def _print_summary(self):
        """Print summary."""
        print("\n" + "="*60)
        print("📊 ZUSAMMENFASSUNG")
        print("="*60)
        
        print(f"\n✓ Erfasst: {len(self.captured)} Templates")
        
        if self.captured:
            print("\nNeue Templates:")
            for name in sorted(self.captured):
                path = self.icons_dir / name
                if path.exists():
                    img = cv2.imread(str(path))
                    if img is not None:
                        print(f"   ✓ {name}: {img.shape[1]}x{img.shape[0]}")
        
        missing = [t[0] for t in ALL_TEMPLATES if t[0] not in self.captured]
        if missing:
            print(f"\n⚠️ Nicht erfasst: {len(missing)} Templates")
            for name in missing[:10]:
                print(f"   - {name}")
            if len(missing) > 10:
                print(f"   ... und {len(missing)-10} weitere")
        
        if self.backup_dir.exists():
            print(f"\n📦 Backup: {self.backup_dir}")
        
        print("\n💡 Teste mit: python scripts/debug_dungeon_detection.py")


def main():
    extractor = ScreenshotTemplateExtractor()
    extractor.run()


if __name__ == "__main__":
    main()
