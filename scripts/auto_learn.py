"""
Rush Royale Bot - Auto-Learn from Screenshots
Python 3.13 Compatible

Lernt automatisch Farbsignaturen aus vorhandenen Screenshots.
Nach dem Lernen werden KEINE Templates/Icons mehr benoetigt!

Sucht Screenshots in:
- screenshots/ (zentraler Ordner - primaer)
- debug_screenshots/ (legacy)
- icons/ (alle Unterordner, legacy)
- icons_backup_*/
- Hauptverzeichnis (bot_feed_*.png)
"""
from __future__ import annotations

import os
import sys
import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict

import cv2
import numpy as np

# Projektpfade
PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_FILE = PROJECT_ROOT / "Src" / "utils" / "learned_signatures.json"
ICONS_DIR = PROJECT_ROOT / "icons"
DEBUG_SCREENSHOTS_DIR = PROJECT_ROOT / "screenshots"


@dataclass
class LearnedSignature:
    """Eine gelernte Farbsignatur."""
    screen_name: str
    sample_points: List[Dict]  # [{x, y, r, g, b, tolerance}]
    min_matches: int
    source_files: List[str]


class AutoLearner:
    """
    Lernt Farbsignaturen automatisch aus Screenshots.
    """
    
    # Feste Sample-Positionen fuer verschiedene Screen-Bereiche
    SAMPLE_GRID = [
        # Top-Bereich
        (100, 50), (450, 50), (800, 50),
        # Oberes Drittel
        (100, 300), (450, 300), (800, 300),
        # Mitte
        (100, 600), (450, 600), (800, 600),
        # Unteres Drittel
        (100, 1000), (450, 1000), (800, 1000),
        # Bottom-Navigation
        (140, 1259), (450, 1259), (750, 1259),
        # Ganz unten
        (100, 1450), (450, 1450), (800, 1450),
    ]
    
    # Screen-Typ Erkennung basierend auf Ordnernamen
    FOLDER_TO_SCREEN = {
        'home': 'home',
        'pve': 'dungeon',
        'pvp': 'pvp',
        'shop': 'store',
        'quest': 'quest',
        'heroes': 'heroes',
        'expedition': 'expedition',
        'events': 'events',
    }
    
    def __init__(self):
        self.screenshots: Dict[str, Tuple[np.ndarray, str]] = {}  # name -> (img, screen_type)
        
    def find_all_screenshots(self) -> int:
        """Findet ALLE Screenshots im Projekt."""
        count = 0
        
        # 1. screenshots/ (zentraler Ordner - primaere Quelle)
        screenshots_dir = PROJECT_ROOT / "screenshots"
        if screenshots_dir.exists():
            for f in screenshots_dir.glob("*.png"):
                if self._is_screenshot(f):
                    count += self._load_screenshot(f, "unknown")
        
        # 2. debug_screenshots/ (legacy)
        debug_dir = PROJECT_ROOT / "debug_screenshots"
        if debug_dir.exists():
            for f in debug_dir.glob("*.png"):
                if self._is_screenshot(f):
                    count += self._load_screenshot(f, "unknown")
        
        # 3. icons/ und alle Unterordner (legacy)
        icons_dir = PROJECT_ROOT / "icons"
        if icons_dir.exists():
            for subdir in icons_dir.iterdir():
                if subdir.is_dir():
                    screen_type = self.FOLDER_TO_SCREEN.get(subdir.name, subdir.name)
                    for f in subdir.glob("*.png"):
                        if self._is_screenshot(f):
                            count += self._load_screenshot(f, screen_type)
                elif subdir.suffix == '.png' and self._is_screenshot(subdir):
                    count += self._load_screenshot(subdir, "unknown")
        
        # 4. icons_backup_*/ Ordner
        for backup_dir in PROJECT_ROOT.glob("icons_backup_*"):
            if backup_dir.is_dir():
                for f in backup_dir.glob("*.png"):
                    if self._is_screenshot(f):
                        count += self._load_screenshot(f, "unknown")
        
        # 5. Hauptverzeichnis (bot_feed_*.png)
        for f in PROJECT_ROOT.glob("bot_feed_*.png"):
            count += self._load_screenshot(f, "unknown")
        
        # 5. OCR_inputs/ falls vorhanden (Unit-Bilder, ueberspringen)
        # Diese sind zu klein fuer Screen-Erkennung
        
        print(f"Gefunden: {count} Screenshots")
        return count
    
    def _is_screenshot(self, path: Path) -> bool:
        """Prueft ob Datei ein vollstaendiger Screenshot ist (nicht nur Icon)."""
        # Screenshots haben typisch "Screenshot" im Namen oder sind gross
        name = path.name.lower()
        if 'screenshot' in name:
            return True
        if 'debug_screen' in name:
            return True
        if 'bot_feed' in name:
            return True
        
        # Pruefe Dateigroesse (Screenshots > 100KB, Icons < 50KB)
        try:
            size = path.stat().st_size
            return size > 100000  # > 100KB
        except:
            return False
    
    def _load_screenshot(self, path: Path, screen_type: str) -> int:
        """Laedt einen Screenshot."""
        try:
            img = cv2.imread(str(path))
            if img is None:
                return 0
            
            # Nur grosse Bilder (echte Screenshots)
            h, w = img.shape[:2]
            if h < 500 or w < 400:
                return 0
            
            self.screenshots[path.name] = (img, screen_type)
            return 1
        except Exception as e:
            print(f"  Fehler bei {path.name}: {e}")
            return 0
    
    def sample_colors(self, img: np.ndarray) -> Dict[Tuple[int, int], Tuple[int, int, int]]:
        """Extrahiert Farben an Sample-Positionen."""
        h, w = img.shape[:2]
        colors = {}
        
        for x, y in self.SAMPLE_GRID:
            if y < h and x < w:
                # BGR -> RGB
                pixel = img[y, x]
                colors[(x, y)] = (int(pixel[2]), int(pixel[1]), int(pixel[0]))
        
        return colors
    
    def cluster_screenshots(self) -> Dict[str, List[str]]:
        """
        Gruppiert Screenshots nach Screen-Typ (aus Ordner) und Aehnlichkeit.
        """
        if not self.screenshots:
            return {}
        
        # Zuerst nach bekanntem Screen-Typ gruppieren
        type_clusters = defaultdict(list)
        unknown_screenshots = []
        
        for name, (img, screen_type) in self.screenshots.items():
            if screen_type != "unknown":
                type_clusters[screen_type].append(name)
            else:
                unknown_screenshots.append(name)
        
        # Unbekannte nach Farbaehnlichkeit clustern
        if unknown_screenshots:
            profiles = {}
            for name in unknown_screenshots:
                img, _ = self.screenshots[name]
                colors = self.sample_colors(img)
                profile = []
                for pos in self.SAMPLE_GRID:
                    if pos in colors:
                        profile.extend(colors[pos])
                    else:
                        profile.extend([0, 0, 0])
                profiles[name] = np.array(profile)
            
            # Clustering
            assigned = set()
            cluster_num = 0
            
            for name1 in unknown_screenshots:
                if name1 in assigned:
                    continue
                
                cluster_id = f"auto_{cluster_num}"
                type_clusters[cluster_id].append(name1)
                assigned.add(name1)
                
                for name2 in unknown_screenshots:
                    if name2 in assigned:
                        continue
                    
                    dist = np.linalg.norm(profiles[name1] - profiles[name2])
                    if dist < 500:
                        type_clusters[cluster_id].append(name2)
                        assigned.add(name2)
                
                cluster_num += 1
        
        # Zeige Cluster
        print(f"\nGefunden: {len(type_clusters)} Screen-Gruppen")
        for cid, files in sorted(type_clusters.items()):
            print(f"  {cid}: {len(files)} Screenshots")
        
        return dict(type_clusters)
    
    def find_common_colors(self, filenames: List[str]) -> List[Dict]:
        """
        Findet gemeinsame Farben in einer Gruppe von Screenshots.
        
        Returns:
            Liste von {x, y, r, g, b, tolerance}
        """
        if not filenames:
            return []
        
        # Sammle Farben pro Position
        pos_colors = defaultdict(list)
        
        for name in filenames:
            if name not in self.screenshots:
                continue
            img, _ = self.screenshots[name]
            colors = self.sample_colors(img)
            
            for pos, rgb in colors.items():
                pos_colors[pos].append(rgb)
        
        # Finde stabile Positionen (geringe Varianz)
        stable_points = []
        
        for pos, colors in pos_colors.items():
            if len(colors) < 2:
                continue
            
            colors_arr = np.array(colors)
            mean_color = np.mean(colors_arr, axis=0)
            std_color = np.std(colors_arr, axis=0)
            
            # Nur stabile Punkte (niedrige Varianz)
            avg_std = np.mean(std_color)
            if avg_std < 30:  # Max 30 Abweichung im Schnitt
                stable_points.append({
                    'x': pos[0],
                    'y': pos[1],
                    'r': int(mean_color[0]),
                    'g': int(mean_color[1]),
                    'b': int(mean_color[2]),
                    'tolerance': int(max(20, avg_std * 2))
                })
        
        return stable_points
    
    def learn_from_icons(self) -> Dict[str, List[Dict]]:
        """
        Lernt Farbsignaturen aus vorhandenen Icon-Templates.
        
        Extrahiert dominante Farben aus jedem Icon.
        """
        if not ICONS_DIR.exists():
            print("Icons-Verzeichnis nicht gefunden")
            return {}
        
        icon_colors = {}
        
        for icon_file in ICONS_DIR.glob("*.png"):
            icon = cv2.imread(str(icon_file))
            if icon is None:
                continue
            
            # Extrahiere dominante Farbe
            h, w = icon.shape[:2]
            center_x, center_y = w // 2, h // 2
            
            # Sample aus Mitte des Icons
            roi = icon[max(0,center_y-5):center_y+5, max(0,center_x-5):center_x+5]
            if roi.size > 0:
                avg_color = np.mean(roi, axis=(0, 1))
                rgb = (int(avg_color[2]), int(avg_color[1]), int(avg_color[0]))
                
                icon_name = icon_file.stem
                icon_colors[icon_name] = {
                    'dominant_color': rgb,
                    'size': (w, h)
                }
        
        print(f"Gelernt von {len(icon_colors)} Icons")
        return icon_colors
    
    def generate_signatures(self) -> List[LearnedSignature]:
        """
        Generiert finale Signaturen aus allen Quellen.
        Nutzt die erkannten Screen-Typen aus den Cluster-IDs.
        """
        signatures = []
        
        # 1. Cluster Screenshots nach Typ
        clusters = self.cluster_screenshots()
        
        # 2. Für jeden Cluster: Finde gemeinsame Farben
        for cluster_id, files in clusters.items():
            common_colors = self.find_common_colors(files)
            
            if len(common_colors) >= 2:
                # Nutze Cluster-ID als Screen-Namen (z.B. 'home', 'pve', 'dungeon')
                # oder 'auto_X' für unbekannte
                screen_name = cluster_id
                
                sig = LearnedSignature(
                    screen_name=screen_name,
                    sample_points=common_colors,
                    min_matches=max(1, len(common_colors) // 2),
                    source_files=files[:5]  # Max 5 als Referenz
                )
                signatures.append(sig)
        
        return signatures
    
    def save_signatures(self, signatures: List[LearnedSignature]):
        """Speichert Signaturen als JSON."""
        data = {
            'version': '1.0',
            'generated_from': len(self.screenshots),
            'signatures': [asdict(s) for s in signatures]
        }
        
        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"\nSignaturen gespeichert: {OUTPUT_FILE}")
    
    def run(self):
        """Hauptablauf."""
        print("=" * 60)
        print("Rush Royale Bot - Auto-Learn")
        print("=" * 60)
        print()
        print("Lerne Farbsignaturen aus vorhandenen Screenshots...")
        print("Nach dem Lernen werden KEINE Icons mehr benoetigt!")
        print()
        
        # Screenshots laden
        count = self.find_all_screenshots()
        if count == 0:
            print("Keine Screenshots gefunden!")
            print(f"Bitte Screenshots in {DEBUG_SCREENSHOTS_DIR} ablegen.")
            return
        
        # Von Icons lernen
        icon_data = self.learn_from_icons()
        
        # Signaturen generieren
        signatures = self.generate_signatures()
        
        print(f"\nGeneriert: {len(signatures)} Screen-Signaturen")
        for sig in signatures:
            print(f"  - {sig.screen_name}: {len(sig.sample_points)} Farbpunkte")
        
        # Speichern
        self.save_signatures(signatures)
        
        # Generiere auch Python-Code
        self._generate_python_code(signatures)
        
        print()
        print("=" * 60)
        print("FERTIG! Der Bot kann jetzt OHNE Icons laufen.")
        print("=" * 60)
        print()
        print("Nächste Schritte:")
        print("1. Überprüfe die generierten Signaturen in:")
        print(f"   {OUTPUT_FILE}")
        print()
        print("2. Optional: Benenne die Screens um (cluster_0 -> home, etc.)")
        print()
        print("3. Icons-Ordner kann gelöscht werden (Backup empfohlen)")
    
    def _generate_python_code(self, signatures: List[LearnedSignature]):
        """Generiert Python-Code fuer direkte Nutzung."""
        output_py = OUTPUT_FILE.with_suffix('.py')
        
        lines = [
            '"""',
            'Auto-generierte Screen-Signaturen.',
            'Generiert aus Screenshots - KEINE Icons noetig!',
            '"""',
            'from Src.utils.template_free_detector import GameScreen, ColorCheckpoint, ScreenSignature',
            '',
            '# Mapping von gelernten Namen zu GameScreen',
            '# pve = Dungeon/PvE Screens, pvp = Battle Screens, home = Home',
            'SCREEN_MAPPING = {',
            '    "home": GameScreen.HOME,',
            '    "pve": GameScreen.DUNGEON_SELECT,',
            '    "pvp": GameScreen.BATTLE_ACTIVE,',
            '    "battle": GameScreen.BATTLE_ACTIVE,',
            '    "dungeon": GameScreen.DUNGEON_SELECT,',
            '    "victory": GameScreen.BATTLE_VICTORY,',
            '    "defeat": GameScreen.BATTLE_DEFEAT,',
            '    "store": GameScreen.STORE,',
            '    "shop": GameScreen.STORE,',
            '    "loading": GameScreen.LOADING,',
            '    "popup": GameScreen.POPUP_DIALOG,',
            '    "quest": GameScreen.HOME,',
            '    "events": GameScreen.HOME,',
            '    "expedition": GameScreen.HOME,',
            '    "heroes": GameScreen.HOME,',
            '}',
            '',
            'LEARNED_SIGNATURES = [',
        ]
        
        for sig in signatures:
            screen_enum = f'SCREEN_MAPPING.get("{sig.screen_name}", GameScreen.UNKNOWN)'
            
            lines.append(f'    # {sig.screen_name} (aus {len(sig.source_files)} Screenshots)')
            lines.append('    ScreenSignature(')
            lines.append(f'        screen_type={screen_enum},')
            lines.append('        checkpoints=[')
            
            for p in sig.sample_points:
                lines.append(
                    f'            ColorCheckpoint({p["x"]}, {p["y"]}, '
                    f'[({p["r"]}, {p["g"]}, {p["b"]})], {p["tolerance"]}, "auto"),'
                )
            
            lines.append('        ],')
            lines.append(f'        min_matches={sig.min_matches},')
            lines.append('    ),')
        
        lines.append(']')
        
        with open(output_py, 'w') as f:
            f.write('\n'.join(lines))
        
        print(f"Python-Code generiert: {output_py}")


def main():
    learner = AutoLearner()
    learner.run()


if __name__ == "__main__":
    main()
