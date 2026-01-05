"""
Rush Royale Bot - Interactive Template Marker
Python 3.13 Compatible

Einfaches GUI-Tool zum manuellen Markieren von UI-Elementen:
1. Screenshot laden
2. Mit Maus Rechteck um Element ziehen
3. Name eingeben -> Template wird gespeichert

Viel präziser als Auto-Detection!
"""
from __future__ import annotations

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple, List, Dict
from dataclasses import dataclass, field

import cv2
import numpy as np

# Projektpfade
PROJECT_ROOT = Path(__file__).parent.parent
ICONS_DIR = PROJECT_ROOT / "icons"
DEBUG_SCREENSHOTS_DIR = PROJECT_ROOT / "screenshots"
POSITIONS_FILE = PROJECT_ROOT / "Src" / "utils" / "calibrated_positions.json"


@dataclass
class MarkedRegion:
    """Ein markierter Bereich auf dem Screenshot."""
    name: str
    x: int
    y: int
    width: int
    height: int
    screenshot_file: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def get_center(self) -> Tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)
    
    def to_dict(self) -> Dict:
        return {
            'name': self.name,
            'x': self.x,
            'y': self.y,
            'width': self.width,
            'height': self.height,
            'center': self.get_center(),
            'screenshot': self.screenshot_file,
            'timestamp': self.timestamp
        }


class InteractiveMarker:
    """
    Interaktives Tool zum Markieren von UI-Elementen.
    
    Bedienung:
    - Linke Maustaste: Ziehen um Bereich zu markieren
    - ENTER: Bereich speichern (Name eingeben)
    - ESC: Abbrechen
    - R: Screenshot neu laden
    - N: Nächster Screenshot
    - P: Vorheriger Screenshot
    - S: Alle markierten Positionen speichern
    """
    
    WINDOW_NAME = "RR Bot - Template Marker"
    
    def __init__(self):
        self.current_image: Optional[np.ndarray] = None
        self.display_image: Optional[np.ndarray] = None
        self.screenshot_files: List[Path] = []
        self.current_index: int = 0
        
        # Zeichenzustand
        self.drawing: bool = False
        self.start_point: Optional[Tuple[int, int]] = None
        self.end_point: Optional[Tuple[int, int]] = None
        self.current_rect: Optional[Tuple[int, int, int, int]] = None
        
        # Markierte Bereiche
        self.marked_regions: List[MarkedRegion] = []
        
        # Display-Einstellungen (für 9:16 Aspect Ratio)
        self.display_width = 506
        self.display_height = 900
        self.scale_factor = 1.0
    
    def load_screenshots(self, directory: Path = None) -> int:
        """Lädt alle Screenshots aus dem Verzeichnis."""
        if directory is None:
            directory = DEBUG_SCREENSHOTS_DIR
        
        if not directory.exists():
            print(f"Verzeichnis nicht gefunden: {directory}")
            return 0
        
        # PNG-Dateien laden
        self.screenshot_files = sorted(directory.glob("*.png"))
        print(f"Gefunden: {len(self.screenshot_files)} Screenshots")
        
        if self.screenshot_files:
            self._load_current_image()
        
        return len(self.screenshot_files)
    
    def _load_current_image(self):
        """Lädt das aktuelle Bild."""
        if not self.screenshot_files:
            return
        
        path = self.screenshot_files[self.current_index]
        self.current_image = cv2.imread(str(path))
        
        if self.current_image is not None:
            h, w = self.current_image.shape[:2]
            
            # Skalierung für Display berechnen
            self.scale_factor = min(self.display_width / w, self.display_height / h)
            
            print(f"\nGeladen: {path.name}")
            print(f"Größe: {w}x{h} (Anzeige: {int(w*self.scale_factor)}x{int(h*self.scale_factor)})")
            
            self._update_display()
    
    def _update_display(self):
        """Aktualisiert das Anzeigebild mit Markierungen."""
        if self.current_image is None:
            return
        
        # Kopie für Anzeige erstellen
        self.display_image = self.current_image.copy()
        
        # Aktuelle Auswahl zeichnen
        if self.current_rect:
            x, y, w, h = self.current_rect
            cv2.rectangle(self.display_image, (x, y), (x + w, y + h), (0, 255, 0), 2)
            
            # Maße anzeigen
            text = f"{w}x{h}"
            cv2.putText(self.display_image, text, (x, y - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        # Bereits markierte Bereiche zeichnen
        for region in self.marked_regions:
            if region.screenshot_file == self.screenshot_files[self.current_index].name:
                cv2.rectangle(
                    self.display_image,
                    (region.x, region.y),
                    (region.x + region.width, region.y + region.height),
                    (255, 0, 0), 2
                )
                cv2.putText(
                    self.display_image, region.name,
                    (region.x, region.y - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1
                )
        
        # Hilfe-Text
        help_text = f"[{self.current_index + 1}/{len(self.screenshot_files)}] "
        help_text += "LMB: Markieren | ENTER: Speichern | N/P: Nächster/Vorheriger | S: Alle speichern | ESC: Beenden"
        
        # Skalieren für Anzeige
        h, w = self.display_image.shape[:2]
        new_w = int(w * self.scale_factor)
        new_h = int(h * self.scale_factor)
        scaled = cv2.resize(self.display_image, (new_w, new_h))
        
        # Help-Text hinzufügen
        cv2.putText(scaled, help_text, (10, new_h - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        
        cv2.imshow(self.WINDOW_NAME, scaled)
    
    def _mouse_callback(self, event, x, y, flags, param):
        """Maus-Event-Handler."""
        # Koordinaten zurück auf Originalauflösung skalieren
        orig_x = int(x / self.scale_factor)
        orig_y = int(y / self.scale_factor)
        
        if event == cv2.EVENT_LBUTTONDOWN:
            self.drawing = True
            self.start_point = (orig_x, orig_y)
            self.end_point = None
            self.current_rect = None
        
        elif event == cv2.EVENT_MOUSEMOVE and self.drawing:
            self.end_point = (orig_x, orig_y)
            # Rechteck berechnen
            x1, y1 = self.start_point
            x2, y2 = self.end_point
            self.current_rect = (
                min(x1, x2), min(y1, y2),
                abs(x2 - x1), abs(y2 - y1)
            )
            self._update_display()
        
        elif event == cv2.EVENT_LBUTTONUP:
            self.drawing = False
            if self.start_point and self.end_point:
                x1, y1 = self.start_point
                x2, y2 = self.end_point
                self.current_rect = (
                    min(x1, x2), min(y1, y2),
                    abs(x2 - x1), abs(y2 - y1)
                )
                self._update_display()
    
    def _save_current_region(self):
        """Speichert den aktuell markierten Bereich."""
        if not self.current_rect or self.current_image is None:
            print("Kein Bereich markiert!")
            return
        
        x, y, w, h = self.current_rect
        
        if w < 5 or h < 5:
            print("Bereich zu klein!")
            return
        
        # Name abfragen
        print(f"\nMarkierter Bereich: ({x}, {y}) - {w}x{h}")
        print("Vorschläge: pve_button, dungeon_page, chapter_1, start_button, back_button")
        name = input("Name für dieses Element (leer = überspringen): ").strip()
        
        if not name:
            print("Übersprungen.")
            return
        
        # Template extrahieren und speichern
        template = self.current_image[y:y+h, x:x+w].copy()
        
        # Als PNG speichern
        template_path = ICONS_DIR / f"{name}.png"
        cv2.imwrite(str(template_path), template)
        print(f"Template gespeichert: {template_path}")
        
        # Region merken
        region = MarkedRegion(
            name=name,
            x=x, y=y,
            width=w, height=h,
            screenshot_file=self.screenshot_files[self.current_index].name
        )
        self.marked_regions.append(region)
        
        # Position auch speichern (für feste Koordinaten)
        self._save_position(region)
        
        # Reset
        self.current_rect = None
        self._update_display()
    
    def _save_position(self, region: MarkedRegion):
        """Speichert die Position für den Hybrid-Navigator."""
        positions = {}
        
        # Bestehende laden
        if POSITIONS_FILE.exists():
            try:
                with open(POSITIONS_FILE, 'r') as f:
                    positions = json.load(f)
            except json.JSONDecodeError:
                positions = {}
        
        # Hinzufügen/Aktualisieren
        positions[region.name] = region.to_dict()
        
        # Speichern
        POSITIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(POSITIONS_FILE, 'w') as f:
            json.dump(positions, f, indent=2)
        
        print(f"Position gespeichert: {POSITIONS_FILE}")
    
    def _save_all_positions(self):
        """Speichert alle markierten Positionen."""
        if not self.marked_regions:
            print("Keine Markierungen zum Speichern.")
            return
        
        positions = {}
        for region in self.marked_regions:
            positions[region.name] = region.to_dict()
        
        POSITIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(POSITIONS_FILE, 'w') as f:
            json.dump(positions, f, indent=2)
        
        print(f"\n{len(positions)} Positionen gespeichert: {POSITIONS_FILE}")
    
    def run(self, screenshot_dir: Path = None):
        """Startet das interaktive Tool."""
        print("=" * 60)
        print("RR Bot - Interactive Template Marker")
        print("=" * 60)
        print()
        print("Bedienung:")
        print("  - Linke Maustaste ziehen: Bereich markieren")
        print("  - ENTER: Markierten Bereich speichern")
        print("  - N: Nächster Screenshot")
        print("  - P: Vorheriger Screenshot")
        print("  - R: Screenshot neu laden")
        print("  - S: Alle Positionen speichern")
        print("  - ESC: Beenden")
        print()
        
        # Screenshots laden
        count = self.load_screenshots(screenshot_dir)
        if count == 0:
            print("Keine Screenshots gefunden!")
            return
        
        # Fenster erstellen
        cv2.namedWindow(self.WINDOW_NAME, cv2.WINDOW_AUTOSIZE)
        cv2.setMouseCallback(self.WINDOW_NAME, self._mouse_callback)
        
        self._update_display()
        
        while True:
            key = cv2.waitKey(50) & 0xFF
            
            if key == 27:  # ESC
                break
            
            elif key == 13:  # ENTER
                self._save_current_region()
            
            elif key == ord('n') or key == ord('N'):
                # Nächster Screenshot
                if self.current_index < len(self.screenshot_files) - 1:
                    self.current_index += 1
                    self.current_rect = None
                    self._load_current_image()
            
            elif key == ord('p') or key == ord('P'):
                # Vorheriger Screenshot
                if self.current_index > 0:
                    self.current_index -= 1
                    self.current_rect = None
                    self._load_current_image()
            
            elif key == ord('r') or key == ord('R'):
                # Neu laden
                self.current_rect = None
                self._load_current_image()
            
            elif key == ord('s') or key == ord('S'):
                # Alle speichern
                self._save_all_positions()
        
        cv2.destroyAllWindows()
        
        # Zusammenfassung
        print()
        print("=" * 60)
        print(f"Fertig! {len(self.marked_regions)} Elemente markiert.")
        print("=" * 60)
        
        if self.marked_regions:
            print("\nMarkierte Elemente:")
            for region in self.marked_regions:
                print(f"  - {region.name}: ({region.x}, {region.y}) {region.width}x{region.height}")


def main():
    """Hauptfunktion."""
    marker = InteractiveMarker()
    
    # Optional: Verzeichnis als Argument
    screenshot_dir = None
    if len(sys.argv) > 1:
        screenshot_dir = Path(sys.argv[1])
    
    marker.run(screenshot_dir)


if __name__ == "__main__":
    main()
