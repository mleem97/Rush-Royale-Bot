#!/usr/bin/env python
"""
Full Template Refresh - Automatically captures all UI templates from the game.

This tool navigates through all game screens and captures fresh templates
for every UI element, replacing all existing templates.

Usage:
    python scripts/full_template_refresh.py

Requirements:
    - BlueStacks running with Rush Royale open
    - Game should be on the home screen
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import numpy as np
from pathlib import Path
from datetime import datetime
import time
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


class FullTemplateRefresh:
    """Complete template refresh system."""
    
    # All templates organized by screen
    TEMPLATE_SCREENS = [
        {
            'name': 'Home Screen',
            'instruction': 'Gehe zum HAUPTMENÜ (Home Screen)',
            'templates': [
                ('home_screen.png', 'Home-Icon (kleines Haus-Symbol unten)'),
                ('battle_icon.png', 'Großer BATTLE/KAMPF Button'),
                ('pve_button.png', 'PvE Button (falls sichtbar)'),
                ('pvp_button.png', 'PvP Button'),
                ('pvp_button2.png', 'PvP Button Alternative (falls anders)'),
            ]
        },
        {
            'name': 'Dungeon/PvE Selection',
            'instruction': 'Gehe zur DUNGEON/PvE Auswahl (Kapitel-Liste)',
            'templates': [
                ('dungeon_page.png', 'Dungeon Überschrift/Header'),
                ('chapter_1.png', 'Kapitel 1 Banner'),
                ('chapter_2.png', 'Kapitel 2 Banner'),
                ('chapter_3.png', 'Kapitel 3 Banner'),
                ('chapter_4.png', 'Kapitel 4 Banner'),
                ('chapter_5.png', 'Kapitel 5 Banner'),
                ('chapter_6.png', 'Kapitel 6 Banner'),
            ]
        },
        {
            'name': 'General Navigation',
            'instruction': 'Bleib auf aktuellem Screen für Navigation-Elemente',
            'templates': [
                ('back_button.png', 'Zurück-Pfeil (oben links)'),
                ('x_mark.png', 'Schließen X (falls sichtbar)'),
            ]
        },
        {
            'name': 'Battle/Fight',
            'instruction': 'Starte einen Kampf und warte bis er läuft',
            'templates': [
                ('fighting.png', 'Kampf-Indikator (Schwerter o.ä.)'),
            ]
        },
        {
            'name': 'Battle End',
            'instruction': 'Beende einen Kampf (Sieg oder Niederlage)',
            'templates': [
                ('0cont_button.png', 'Weiter/Continue Button'),
                ('1quit.png', 'Beenden/Quit Button'),
            ]
        },
        {
            'name': 'Store/Shop',
            'instruction': 'Gehe zum SHOP/LADEN',
            'templates': [
                ('store_refresh.png', 'Shop Refresh Button'),
                ('refresh_button.png', 'Refresh Button im Shop'),
            ]
        },
        {
            'name': 'Quests',
            'instruction': 'Gehe zu den QUESTS/AUFGABEN',
            'templates': [
                ('quest_done.png', 'Erledigte Quest Markierung'),
                ('quest_collect.png', 'Quest Belohnung abholen'),
            ]
        },
        {
            'name': 'Ads & Popups',
            'instruction': 'Wenn Werbung/Popups erscheinen',
            'templates': [
                ('ad_pve.png', 'Werbung im PvE'),
                ('ad_season.png', 'Season Werbung'),
            ]
        },
        {
            'name': 'Friend Menu',
            'instruction': 'Wenn Freundesliste erscheint',
            'templates': [
                ('friend_menu.png', 'Freundesmenü'),
            ]
        },
        {
            'name': 'Opponents',
            'instruction': 'Im Kampf wenn Gegner sichtbar (optional)',
            'templates': [
                ('shaman_opponent.png', 'Shaman Gegner'),
                ('witch_opponent.png', 'Witch/Hexe Gegner'),
                ('robot_1.png', 'Robot Gegner Typ 1'),
                ('robot_3.png', 'Robot Gegner Typ 3'),
                ('robot_4.png', 'Robot Gegner Typ 4'),
                ('robot_6.png', 'Robot Gegner Typ 6'),
            ]
        },
    ]
    
    def __init__(self):
        self.bot = None
        self.icons_dir = Path("icons")
        self.backup_dir = Path("icons_backup_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
        self.captured = []
        self.skipped = []
        self.scale = 1.0
        
    def init_bot(self):
        """Initialize bot connection."""
        try:
            from Src.bot_core import Bot
            self.bot = Bot()
            print("✓ Bot verbunden")
            return True
        except Exception as e:
            print(f"✗ Bot-Verbindung fehlgeschlagen: {e}")
            return False
    
    def backup_existing(self):
        """Backup all existing templates."""
        if self.icons_dir.exists():
            print(f"\n📦 Sichere bestehende Templates nach: {self.backup_dir}")
            shutil.copytree(self.icons_dir, self.backup_dir)
            print(f"   {len(list(self.backup_dir.glob('*.png')))} Templates gesichert")
    
    def get_screenshot(self):
        """Get current screenshot."""
        if self.bot:
            self.bot.getScreen()
            if self.bot.screenRGB is not None:
                return cv2.cvtColor(self.bot.screenRGB, cv2.COLOR_RGB2BGR)
        return None
    
    def capture_region(self, screenshot, template_name, hint):
        """Let user select a region for a template."""
        global g_selection, g_selecting, g_start, g_end
        g_selection = None
        g_selecting = False
        g_start = None
        g_end = None
        
        window = f"Markiere: {template_name}"
        cv2.namedWindow(window, cv2.WINDOW_NORMAL)
        cv2.setMouseCallback(window, mouse_callback)
        
        h, w = screenshot.shape[:2]
        self.scale = min(1.0, 1400/w, 900/h)
        display_size = (int(w * self.scale), int(h * self.scale))
        
        print(f"\n  📍 {template_name}")
        print(f"     Hinweis: {hint}")
        print(f"     [Maus ziehen] = Auswählen | [ENTER] = Speichern | [S] = Überspringen")
        print(f"     [R] = Neuer Screenshot | [ESC] = Abbrechen")
        
        current_screenshot = screenshot
        
        while True:
            h, w = current_screenshot.shape[:2]
            display_size = (int(w * self.scale), int(h * self.scale))
            display = cv2.resize(current_screenshot.copy(), display_size)
            
            # Draw selection
            if g_selecting and g_start and g_end:
                cv2.rectangle(display, g_start, g_end, (0, 255, 0), 2)
            elif g_selection:
                x1, y1, x2, y2 = g_selection
                cv2.rectangle(display, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(display, f"{x2-x1}x{y2-y1}", (x1, y1-5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            
            # Instructions overlay
            cv2.rectangle(display, (5, 5), (500, 25), (0, 0, 0), -1)
            cv2.putText(display, "ENTER=Speichern | S=Skip | R=Neuer Screenshot | ESC=Abbruch", (10, 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
            
            cv2.imshow(window, display)
            key = cv2.waitKey(30) & 0xFF
            
            if key == 27:  # ESC
                cv2.destroyWindow(window)
                return None, 'abort', current_screenshot
            elif key == ord('s') or key == ord('S'):
                cv2.destroyWindow(window)
                return None, 'skip', current_screenshot
            elif key == ord('r') or key == ord('R'):
                # Take new screenshot
                print("     📸 Neuer Screenshot...")
                new_screenshot = self.get_screenshot()
                if new_screenshot is not None:
                    current_screenshot = new_screenshot
                    g_selection = None  # Reset selection
                    print("     ✓ Screenshot aktualisiert!")
                else:
                    print("     ❌ Screenshot fehlgeschlagen!")
            elif key == 13 and g_selection:  # ENTER
                x1, y1, x2, y2 = g_selection
                # Scale back to original
                x1 = int(x1 / self.scale)
                y1 = int(y1 / self.scale)
                x2 = int(x2 / self.scale)
                y2 = int(y2 / self.scale)
                template = current_screenshot[y1:y2, x1:x2]
                cv2.destroyWindow(window)
                return template, 'ok', current_screenshot
        
        cv2.destroyWindow(window)
        return None, 'skip', current_screenshot
    
    def save_template(self, name, template):
        """Save a template."""
        if template is None or template.size == 0:
            return False
        path = self.icons_dir / name
        cv2.imwrite(str(path), template)
        self.captured.append(name)
        return True
    
    def run(self):
        """Run the full template refresh."""
        print("\n" + "="*60)
        print("🔄 VOLLSTÄNDIGE TEMPLATE-AKTUALISIERUNG")
        print("="*60)
        
        print("\nDieses Tool führt dich durch ALLE Screens und erfasst")
        print("frische Templates für jeden UI-Element.")
        print("\n⚠️  Alle bestehenden Templates werden gesichert!")
        
        input("\nDrücke ENTER zum Starten (oder Strg+C zum Abbrechen)...")
        
        # Backup
        self.backup_existing()
        
        total_templates = sum(len(s['templates']) for s in self.TEMPLATE_SCREENS)
        current = 0
        
        for screen in self.TEMPLATE_SCREENS:
            print(f"\n{'='*60}")
            print(f"📱 SCREEN: {screen['name']}")
            print(f"{'='*60}")
            print(f"\n👉 {screen['instruction']}")
            print("\nDrücke ENTER wenn bereit (oder 'skip' um diesen Screen zu überspringen)...")
            
            user_input = input().strip().lower()
            if user_input == 'skip':
                for name, _ in screen['templates']:
                    self.skipped.append(name)
                    current += 1
                print(f"⏭️  Screen übersprungen")
                continue
            
            # Get screenshot
            print("\n📸 Erfasse Screenshot...")
            screenshot = self.get_screenshot()
            
            if screenshot is None:
                print("❌ Kein Screenshot möglich!")
                for name, _ in screen['templates']:
                    self.skipped.append(name)
                continue
            
            print(f"✓ Screenshot: {screenshot.shape[1]}x{screenshot.shape[0]}")
            
            # Capture each template
            for name, hint in screen['templates']:
                current += 1
                print(f"\n[{current}/{total_templates}]", end="")
                
                template, status, screenshot = self.capture_region(screenshot, name, hint)
                
                if status == 'abort':
                    print("\n\n⚠️ Abgebrochen durch Benutzer")
                    self._print_summary()
                    return
                elif status == 'skip':
                    self.skipped.append(name)
                    print(f"  ⏭️  Übersprungen: {name}")
                elif template is not None:
                    if self.save_template(name, template):
                        print(f"  ✓ Gespeichert: {name} ({template.shape[1]}x{template.shape[0]})")
            
            # Screenshot wird jetzt automatisch in capture_region aktualisiert
            # Kein separater Prompt mehr nötig
        
        cv2.destroyAllWindows()
        self._print_summary()
    
    def _print_summary(self):
        """Print final summary."""
        print("\n" + "="*60)
        print("📊 ZUSAMMENFASSUNG")
        print("="*60)
        
        print(f"\n✓ Erfasst:    {len(self.captured)} Templates")
        print(f"⏭️  Übersprungen: {len(self.skipped)} Templates")
        
        if self.captured:
            print("\n✓ Neue Templates:")
            for name in sorted(self.captured):
                path = self.icons_dir / name
                if path.exists():
                    img = cv2.imread(str(path))
                    if img is not None:
                        print(f"   {name}: {img.shape[1]}x{img.shape[0]}")
        
        if self.skipped:
            print("\n⏭️ Übersprungen (behalten alte Version falls vorhanden):")
            for name in sorted(self.skipped):
                # Check if backup exists
                backup_path = self.backup_dir / name if self.backup_dir.exists() else None
                if backup_path and backup_path.exists():
                    # Restore from backup
                    shutil.copy(backup_path, self.icons_dir / name)
                    print(f"   {name} (wiederhergestellt aus Backup)")
                else:
                    print(f"   {name} (kein Backup)")
        
        print(f"\n📦 Backup gespeichert in: {self.backup_dir}")
        print("\n💡 Teste mit: python scripts/debug_dungeon_detection.py")


def quick_mode():
    """Quick mode - just capture the most important templates."""
    print("\n" + "="*60)
    print("⚡ SCHNELL-MODUS - Nur wichtigste Templates")
    print("="*60)
    
    essential = [
        ('Home Screen', [
            ('home_screen.png', 'Home-Icon'),
            ('battle_icon.png', 'Battle Button'),
        ]),
        ('Dungeon', [
            ('dungeon_page.png', 'Dungeon Header'),
            ('chapter_1.png', 'Kapitel 1'),
            ('chapter_2.png', 'Kapitel 2'),
            ('back_button.png', 'Zurück-Pfeil'),
        ]),
        ('Battle', [
            ('fighting.png', 'Kampf-Indikator'),
            ('0cont_button.png', 'Continue Button'),
        ]),
    ]
    
    refresher = FullTemplateRefresh()
    if not refresher.init_bot():
        return
    
    refresher.backup_existing()
    
    for screen_name, templates in essential:
        print(f"\n📱 {screen_name}")
        print(f"   Navigiere zum Screen und drücke ENTER...")
        input()
        
        screenshot = refresher.get_screenshot()
        if screenshot is None:
            print("   ❌ Kein Screenshot!")
            continue
        
        for name, hint in templates:
            template, status, screenshot = refresher.capture_region(screenshot, name, hint)
            if status == 'abort':
                cv2.destroyAllWindows()
                return
            elif status == 'ok' and template is not None:
                refresher.save_template(name, template)
                print(f"   ✓ {name}")
    
    cv2.destroyAllWindows()
    refresher._print_summary()


def main():
    print("\n" + "="*60)
    print("🎮 RUSH ROYALE TEMPLATE REFRESH")
    print("="*60)
    
    print("\nOptionen:")
    print("  1. Vollständig - Alle Templates neu erfassen")
    print("  2. Schnell - Nur wichtigste Templates")
    print("  3. Beenden")
    
    choice = input("\nWahl (1-3): ").strip()
    
    if choice == '1':
        refresher = FullTemplateRefresh()
        if refresher.init_bot():
            refresher.run()
    elif choice == '2':
        quick_mode()
    else:
        print("Beendet.")


if __name__ == "__main__":
    main()
