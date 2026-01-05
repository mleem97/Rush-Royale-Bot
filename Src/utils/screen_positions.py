"""
Rush Royale Bot - Fixed Screen Positions
Python 3.13 Compatible

Die Rush Royale UI hat größtenteils feste Positionen.
Diese werden als primäre Navigation genutzt, Template-Matching nur als Fallback.

Auflösung: 1600x900 (BlueStacks Standard)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple, Dict, Optional, List
import numpy as np


@dataclass
class ScreenPosition:
    """Eine fixe Position auf dem Bildschirm."""
    x: int
    y: int
    name: str
    description: str = ""
    
    def to_tuple(self) -> Tuple[int, int]:
        return (self.x, self.y)
    
    def to_array(self) -> np.ndarray:
        return np.array([self.x, self.y])


@dataclass  
class ScreenRegion:
    """Ein Bereich auf dem Bildschirm für Farberkennung."""
    x: int
    y: int
    width: int
    height: int
    name: str
    
    def get_center(self) -> Tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)


# =============================================================================
# FESTE POSITIONEN - 1600x900 Auflösung
# =============================================================================

class HomeScreen:
    """Positionen auf dem Hauptbildschirm."""
    # Bottom Navigation Bar
    PVP_BUTTON = ScreenPosition(140, 1259, "pvp_button", "PvP/Arena Modus")
    PVE_BUTTON = ScreenPosition(640, 1259, "pve_button", "PvE/Dungeon Modus") 
    STORE_BUTTON = ScreenPosition(100, 1500, "store_button", "Shop öffnen")
    
    # Alternative PvE Positionen (für verschiedene UI-Versionen)
    PVE_ALT_POSITIONS = [
        ScreenPosition(640, 1259, "pve_main", "Standard Position"),
        ScreenPosition(1100, 1250, "pve_right", "Rechte Position"),
        ScreenPosition(800, 1250, "pve_center", "Mittlere Position"),
    ]
    
    # Top Bar
    SETTINGS_BUTTON = ScreenPosition(1540, 30, "settings", "Einstellungen")
    PROFILE_BUTTON = ScreenPosition(60, 30, "profile", "Profil")
    
    # Mana/Resource Anzeige
    MANA_REGION = ScreenRegion(220, 1360, 90, 50, "mana_display")


class DungeonScreen:
    """Positionen im Dungeon-Menü."""
    # Chapter Auswahl (horizontale Positionen)
    CHAPTER_1 = ScreenPosition(160, 400, "chapter_1", "Kapitel 1")
    CHAPTER_2 = ScreenPosition(320, 400, "chapter_2", "Kapitel 2")  
    CHAPTER_3 = ScreenPosition(480, 400, "chapter_3", "Kapitel 3")
    CHAPTER_4 = ScreenPosition(640, 400, "chapter_4", "Kapitel 4")
    CHAPTER_5 = ScreenPosition(800, 400, "chapter_5", "Kapitel 5")
    CHAPTER_6 = ScreenPosition(960, 400, "chapter_6", "Kapitel 6")
    
    # Floor Auswahl (vertikale Positionen nach Chapter-Klick)
    FLOOR_POSITIONS = {
        1: ScreenPosition(400, 300, "floor_1"),
        2: ScreenPosition(400, 400, "floor_2"),
        3: ScreenPosition(400, 500, "floor_3"),
        4: ScreenPosition(400, 600, "floor_4"),
        5: ScreenPosition(400, 700, "floor_5"),
        6: ScreenPosition(400, 800, "floor_6"),
        7: ScreenPosition(400, 900, "floor_7"),
        8: ScreenPosition(400, 1000, "floor_8"),
        9: ScreenPosition(400, 1100, "floor_9"),
        10: ScreenPosition(400, 1200, "floor_10"),
    }
    
    # Dungeon Start Button
    START_BUTTON = ScreenPosition(750, 1350, "dungeon_start", "Dungeon starten")
    
    # Back Button
    BACK_BUTTON = ScreenPosition(60, 100, "back_button", "Zurück")


class BattleScreen:
    """Positionen während des Kampfes."""
    # 3x5 Grid - wird dynamisch berechnet
    GRID_START = ScreenPosition(165, 900, "grid_start", "Grid Start (links oben)")
    BOX_SIZE = (145, 145)  # Breite, Höhe einer Grid-Zelle
    
    # Kampf-Buttons
    SUMMON_BUTTON = ScreenPosition(620, 1400, "summon", "Einheit beschwören")
    HERO_ABILITY = ScreenPosition(130, 1400, "hero_ability", "Heldenf\u00e4higkeit")
    
    # Mana Anzeige
    MANA_DISPLAY = ScreenRegion(220, 1360, 90, 50, "mana")
    
    # Continue/Quit nach Kampf
    CONTINUE_BUTTON = ScreenPosition(400, 1100, "continue", "Weiter")
    QUIT_BUTTON = ScreenPosition(400, 1200, "quit", "Beenden")


class GenericButtons:
    """Generische Button-Positionen die überall vorkommen."""
    BACK_BUTTON = ScreenPosition(60, 100, "back", "Zurück (universal)")
    CLOSE_BUTTON = ScreenPosition(750, 200, "close", "Dialog schließen")
    CONFIRM_BUTTON = ScreenPosition(400, 1100, "confirm", "Bestätigen")
    CANCEL_BUTTON = ScreenPosition(400, 1200, "cancel", "Abbrechen")


# =============================================================================
# FARB-ERKENNUNG FÜR UI-ZUSTÄNDE
# =============================================================================

class ColorSignatures:
    """
    RGB-Farbsignaturen für UI-Element-Erkennung.
    Basierend auf get_store_state() Logik.
    """
    
    # Store States (bereits im Bot implementiert)
    STORE_STATES = {
        'refresh': np.array([255, 255, 255]),
        'new_store': np.array([27, 235, 206]),
        'nothing': np.array([63, 38, 12]),
        'new_offer': np.array([48, 253, 251]),
        'spin_only': np.array([80, 153, 193]),
    }
    
    # Screen Detection via Hintergrundfarben
    SCREEN_BACKGROUNDS = {
        'home_screen': {
            'position': (400, 200),  # Sample position
            'colors': [
                np.array([50, 80, 120]),   # Typischer Blau-Ton
                np.array([40, 70, 110]),
            ],
            'tolerance': 30
        },
        'dungeon_page': {
            'position': (400, 300),
            'colors': [
                np.array([60, 40, 30]),    # Dunklerer Braun-Ton
                np.array([80, 50, 35]),
            ],
            'tolerance': 25
        },
        'battle_active': {
            'position': (400, 500),
            'colors': [
                np.array([30, 30, 30]),    # Dunkler Hintergrund
            ],
            'tolerance': 20
        }
    }
    
    # Button-Highlight Farben (wenn aktiv/klickbar)
    BUTTON_ACTIVE = {
        'yellow_glow': np.array([255, 220, 100]),  # Aktive Buttons
        'green_ready': np.array([100, 255, 100]),  # Bereit zum Klicken
        'gray_disabled': np.array([100, 100, 100]),  # Deaktiviert
    }


# =============================================================================
# HILFSFUNKTIONEN
# =============================================================================

def get_grid_positions() -> Tuple[np.ndarray, Tuple[int, int]]:
    """
    Berechnet alle 15 Grid-Positionen (3x5) basierend auf festen Koordinaten.
    
    Returns:
        Tuple von (boxes_array, box_size)
        boxes_array: np.ndarray mit Shape (3, 5, 2) für [row, col, (x, y)]
    """
    start_x = BattleScreen.GRID_START.x
    start_y = BattleScreen.GRID_START.y
    box_w, box_h = BattleScreen.BOX_SIZE
    
    boxes = np.zeros((3, 5, 2), dtype=np.int32)
    for row in range(3):
        for col in range(5):
            boxes[row, col, 0] = start_x + col * box_w
            boxes[row, col, 1] = start_y + row * box_h
    
    return boxes, BattleScreen.BOX_SIZE


def color_distance(color1: np.ndarray, color2: np.ndarray) -> float:
    """Berechnet euklidische Distanz zwischen zwei RGB-Farben."""
    return np.sqrt(np.sum((color1.astype(float) - color2.astype(float))**2))


def match_color(
    pixel: np.ndarray,
    target_colors: Dict[str, np.ndarray],
    tolerance: float = 30.0
) -> Optional[str]:
    """
    Findet die beste Farbübereinstimmung.
    
    Args:
        pixel: RGB-Wert als np.array
        target_colors: Dict von Namen -> RGB-Arrays
        tolerance: Maximale Distanz für Match
        
    Returns:
        Name der besten Übereinstimmung oder None
    """
    best_match = None
    best_distance = tolerance
    
    for name, target in target_colors.items():
        dist = color_distance(pixel, target)
        if dist < best_distance:
            best_distance = dist
            best_match = name
    
    return best_match


def detect_screen_by_color(
    screenshot: np.ndarray,
    screens: Dict = None
) -> Optional[str]:
    """
    Erkennt den aktuellen Screen anhand von Farben an bestimmten Positionen.
    
    Args:
        screenshot: BGR-Bild (OpenCV Format)
        screens: Dict mit Screen-Definitionen (default: ColorSignatures.SCREEN_BACKGROUNDS)
        
    Returns:
        Name des erkannten Screens oder None
    """
    if screens is None:
        screens = ColorSignatures.SCREEN_BACKGROUNDS
    
    for screen_name, config in screens.items():
        x, y = config['position']
        tolerance = config.get('tolerance', 30)
        
        # Hole Pixel-Farbe (BGR -> RGB)
        if y < screenshot.shape[0] and x < screenshot.shape[1]:
            pixel_bgr = screenshot[y, x]
            pixel_rgb = np.array([pixel_bgr[2], pixel_bgr[1], pixel_bgr[0]])
            
            # Prüfe gegen alle möglichen Farben für diesen Screen
            for target_color in config['colors']:
                if color_distance(pixel_rgb, target_color) < tolerance:
                    return screen_name
    
    return None


def scale_position(
    pos: ScreenPosition,
    from_resolution: Tuple[int, int] = (900, 1600),
    to_resolution: Tuple[int, int] = (900, 1600)
) -> ScreenPosition:
    """
    Skaliert eine Position für andere Auflösungen.
    
    Args:
        pos: Original Position
        from_resolution: Original (width, height)
        to_resolution: Ziel (width, height)
        
    Returns:
        Neue ScreenPosition für Ziel-Auflösung
    """
    scale_x = to_resolution[0] / from_resolution[0]
    scale_y = to_resolution[1] / from_resolution[1]
    
    return ScreenPosition(
        x=int(pos.x * scale_x),
        y=int(pos.y * scale_y),
        name=pos.name,
        description=pos.description
    )
