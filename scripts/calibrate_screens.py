"""
Rush Royale Bot - Screen Calibrator
Python 3.13 Compatible

Interaktives Tool zum Kalibrieren der Farberkennung:
1. Screenshot laden
2. Screen-Typ auswählen (Home, Battle, Dungeon, etc.)
3. Automatisch Farbsignaturen extrahieren

Die kalibrierten Werte ersetzen die Standard-Signaturen.
"""
from __future__ import annotations

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass, asdict

import cv2
import numpy as np

# Projektpfade
PROJECT_ROOT = Path(__file__).parent.parent
DEBUG_SCREENSHOTS_DIR = PROJECT_ROOT / "screenshots"
CALIBRATION_FILE = PROJECT_ROOT / "Src" / "utils" / "calibrated_screens.json"

# Import GameScreen enum
try:
    from Src.utils.template_free_detector import GameScreen, ColorCheckpoint, ScreenSignature
except ImportError:
    # Fallback für direkten Aufruf
    sys.path.insert(0, str(PROJECT_ROOT))
    from Src.utils.template_free_detector import GameScreen, ColorCheckpoint, ScreenSignature


@dataclass
class CalibrationPoint:
    """Ein kalibrierter Farbpunkt."""
    x: int
    y: int
    r: int
    g: int
    b: int
    name: str


class ScreenCalibrator:
    """
    Interaktives Kalibrierungs-Tool für Farberkennung.
    
    Bedienung:
    - 1-9: Screen-Typ auswählen
    - Linke Maustaste: Farbpunkt an Position samplen
    - S: Kalibrierung speichern
    - N/P: Nächster/Vorheriger Screenshot
    - C: Alle Punkte löschen
    - ESC: Beenden
    """
    
    WINDOW_NAME = "RR Bot - Screen Calibrator"
    
    SCREEN_KEYS = {
        ord('1'): GameScreen.HOME,
        ord('2'): GameScreen.BATTLE_ACTIVE,
        ord('3'): GameScreen.BATTLE_VICTORY,
        ord('4'): GameScreen.BATTLE_DEFEAT,
        ord('5'): GameScreen.DUNGEON_SELECT,
        ord('6'): GameScreen.STORE,
        ord('7'): GameScreen.LOADING,
        ord('8'): GameScreen.POPUP_DIALOG,
        ord('9'): GameScreen.UNKNOWN,
    }
    
    def __init__(self):
        self.current_image: Optional[np.ndarray] = None
        self.screenshot_files: List[Path] = []
        self.current_index: int = 0
        
        # Aktueller Screen-Typ
        self.current_screen_type: GameScreen = GameScreen.UNKNOWN
        
        # Gesammelte Kalibrierungspunkte pro Screen
        self.calibration_data: Dict[str, List[CalibrationPoint]] = {
            screen.name: [] for screen in GameScreen
        }
        
        # Temporäre Punkte für aktuellen Screen
        self.current_points: List[CalibrationPoint] = []
        
        # Display
        self.display_width = 506
        self.display_height = 900
        self.scale_factor = 1.0
    
    def load_screenshots(self, directory: Path = None) -> int:
        """Lädt alle Screenshots."""
        if directory is None:
            directory = DEBUG_SCREENSHOTS_DIR
        
        if not directory.exists():
            print(f"Verzeichnis nicht gefunden: {directory}")
            return 0
        
        self.screenshot_files = sorted(directory.glob("*.png"))
        print(f"Gefunden: {len(self.screenshot_files)} Screenshots")
        
        if self.screenshot_files:
            self._load_current_image()
        
        return len(self.screenshot_files)
    
    def _load_current_image(self):
        """Lädt aktuelles Bild."""
        if not self.screenshot_files:
            return
        
        path = self.screenshot_files[self.current_index]
        self.current_image = cv2.imread(str(path))
        
        if self.current_image is not None:
            h, w = self.current_image.shape[:2]
            self.scale_factor = min(self.display_width / w, self.display_height / h)
            print(f"\nGeladen: {path.name} ({w}x{h})")
            self._update_display()
    
    def _update_display(self):
        """Aktualisiert Anzeige."""
        if self.current_image is None:
            return
        
        display = self.current_image.copy()
        
        # Zeichne alle Punkte
        for point in self.current_points:
            cv2.circle(display, (point.x, point.y), 10, (0, 255, 0), 2)
            cv2.putText(display, point.name, (point.x + 12, point.y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
        
        # Skalieren
        h, w = display.shape[:2]
        new_w = int(w * self.scale_factor)
        new_h = int(h * self.scale_factor)
        scaled = cv2.resize(display, (new_w, new_h))
        
        # Info-Text
        info = f"[{self.current_index + 1}/{len(self.screenshot_files)}] "
        info += f"Screen: {self.current_screen_type.name} | "
        info += f"Punkte: {len(self.current_points)} | "
        info += "1-9: Typ | LMB: Sample | S: Save | N/P: Nav | ESC: Exit"
        
        cv2.putText(scaled, info, (10, new_h - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1)
        
        # Screen-Typ Auswahl
        y_offset = 30
        for key, screen in self.SCREEN_KEYS.items():
            color = (0, 255, 0) if screen == self.current_screen_type else (150, 150, 150)
            text = f"{chr(key)}: {screen.name}"
            cv2.putText(scaled, text, (10, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.35, color, 1)
            y_offset += 18
        
        cv2.imshow(self.WINDOW_NAME, scaled)
    
    def _mouse_callback(self, event, x, y, flags, param):
        """Maus-Handler."""
        if event == cv2.EVENT_LBUTTONDOWN and self.current_image is not None:
            # Zurück auf Original-Koordinaten
            orig_x = int(x / self.scale_factor)
            orig_y = int(y / self.scale_factor)
            
            h, w = self.current_image.shape[:2]
            if orig_y < h and orig_x < w:
                # Farbe lesen (BGR)
                pixel = self.current_image[orig_y, orig_x]
                r, g, b = int(pixel[2]), int(pixel[1]), int(pixel[0])
                
                point = CalibrationPoint(
                    x=orig_x, y=orig_y,
                    r=r, g=g, b=b,
                    name=f"p{len(self.current_points) + 1}"
                )
                self.current_points.append(point)
                
                print(f"  + Punkt ({orig_x}, {orig_y}): RGB({r}, {g}, {b})")
                self._update_display()
    
    def _save_calibration(self):
        """Speichert Kalibrierung."""
        # Aktuelle Punkte zum Screen hinzufügen
        if self.current_points:
            self.calibration_data[self.current_screen_type.name].extend(self.current_points)
            print(f"\n{len(self.current_points)} Punkte zu {self.current_screen_type.name} hinzugefügt")
        
        # Als JSON speichern
        save_data = {}
        for screen_name, points in self.calibration_data.items():
            if points:
                save_data[screen_name] = [asdict(p) for p in points]
        
        CALIBRATION_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CALIBRATION_FILE, 'w') as f:
            json.dump(save_data, f, indent=2)
        
        print(f"\nKalibrierung gespeichert: {CALIBRATION_FILE}")
        print(f"Screens kalibriert: {list(save_data.keys())}")
        
        # Generiere auch Python-Code
        self._generate_python_signatures()
    
    def _generate_python_signatures(self):
        """Generiert Python-Code für Signaturen."""
        output_file = CALIBRATION_FILE.with_suffix('.py')
        
        lines = [
            '"""Auto-generierte Screen-Signaturen."""',
            'from Src.utils.template_free_detector import GameScreen, ColorCheckpoint, ScreenSignature',
            '',
            'CALIBRATED_SIGNATURES = [',
        ]
        
        for screen_name, points in self.calibration_data.items():
            if not points:
                continue
            
            lines.append(f'    # {screen_name}')
            lines.append('    ScreenSignature(')
            lines.append(f'        screen_type=GameScreen.{screen_name},')
            lines.append('        checkpoints=[')
            
            for p in points:
                lines.append(f'            ColorCheckpoint({p.x}, {p.y}, [({p.r}, {p.g}, {p.b})], 40, "{p.name}"),')
            
            lines.append('        ],')
            lines.append(f'        min_matches={max(1, len(points) // 2)},')
            lines.append('    ),')
        
        lines.append(']')
        
        with open(output_file, 'w') as f:
            f.write('\n'.join(lines))
        
        print(f"Python-Code generiert: {output_file}")
    
    def run(self, screenshot_dir: Path = None):
        """Startet Kalibrierung."""
        print("=" * 60)
        print("RR Bot - Screen Calibrator")
        print("=" * 60)
        print()
        print("Anleitung:")
        print("  1. Wähle Screen-Typ mit Taste 1-9")
        print("  2. Klicke auf charakteristische Stellen")
        print("  3. 'S' zum Speichern, dann nächster Screenshot")
        print()
        
        count = self.load_screenshots(screenshot_dir)
        if count == 0:
            print("Keine Screenshots gefunden!")
            return
        
        # Lade existierende Kalibrierung
        if CALIBRATION_FILE.exists():
            try:
                with open(CALIBRATION_FILE, 'r') as f:
                    data = json.load(f)
                for screen_name, points in data.items():
                    self.calibration_data[screen_name] = [
                        CalibrationPoint(**p) for p in points
                    ]
                print(f"Existierende Kalibrierung geladen: {list(data.keys())}")
            except Exception as e:
                print(f"Fehler beim Laden: {e}")
        
        cv2.namedWindow(self.WINDOW_NAME, cv2.WINDOW_AUTOSIZE)
        cv2.setMouseCallback(self.WINDOW_NAME, self._mouse_callback)
        
        self._update_display()
        
        while True:
            key = cv2.waitKey(50) & 0xFF
            
            if key == 27:  # ESC
                break
            
            elif key in self.SCREEN_KEYS:
                # Screen-Typ wechseln
                self.current_screen_type = self.SCREEN_KEYS[key]
                self.current_points = list(self.calibration_data.get(self.current_screen_type.name, []))
                print(f"\nScreen-Typ: {self.current_screen_type.name}")
                self._update_display()
            
            elif key == ord('s') or key == ord('S'):
                self._save_calibration()
                self.current_points = []
            
            elif key == ord('n') or key == ord('N'):
                if self.current_index < len(self.screenshot_files) - 1:
                    self.current_index += 1
                    self.current_points = []
                    self._load_current_image()
            
            elif key == ord('p') or key == ord('P'):
                if self.current_index > 0:
                    self.current_index -= 1
                    self.current_points = []
                    self._load_current_image()
            
            elif key == ord('c') or key == ord('C'):
                self.current_points = []
                print("Punkte gelöscht")
                self._update_display()
            
            elif key == ord('t') or key == ord('T'):
                # Test aktuelle Erkennung
                self._test_detection()
        
        cv2.destroyAllWindows()
        
        # Finale Speicherung
        if any(self.calibration_data.values()):
            self._save_calibration()
    
    def _test_detection(self):
        """Testet die aktuelle Erkennung."""
        if self.current_image is None:
            return
        
        try:
            from Src.utils.template_free_detector import TemplateFreeDetector
            detector = TemplateFreeDetector()
            screen, confidence = detector.detect_screen(self.current_image)
            print(f"\nTest-Erkennung: {screen.name} ({confidence:.2f})")
        except Exception as e:
            print(f"Test fehlgeschlagen: {e}")


def main():
    calibrator = ScreenCalibrator()
    
    screenshot_dir = None
    if len(sys.argv) > 1:
        screenshot_dir = Path(sys.argv[1])
    
    calibrator.run(screenshot_dir)


if __name__ == "__main__":
    main()
