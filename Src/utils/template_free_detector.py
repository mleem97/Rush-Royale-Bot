"""
Rush Royale Bot - Template-Free Screen Detection
Python 3.13 Compatible

Komplette Screen- und UI-Erkennung OHNE Templates.
Nutzt ausschließlich:
1. Feste Pixel-Positionen
2. Farberkennung an charakteristischen Stellen
3. OCR für Text (optional)

Kein Template-Matching erforderlich!
"""
from __future__ import annotations

import logging
from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional, Tuple, List, Dict, Any

import cv2
import numpy as np

logger = logging.getLogger(__name__)


# =============================================================================
# SCREEN TYPES
# =============================================================================

class GameScreen(Enum):
    """Alle erkennbaren Spielbildschirme."""
    HOME = auto()              # Hauptmenü
    DUNGEON_SELECT = auto()    # Dungeon/Kapitel Auswahl
    FLOOR_SELECT = auto()      # Floor Auswahl nach Kapitel-Klick
    BATTLE_ACTIVE = auto()     # Aktiver Kampf
    BATTLE_VICTORY = auto()    # Sieg-Screen
    BATTLE_DEFEAT = auto()     # Niederlage-Screen
    STORE = auto()             # Shop
    FRIEND_MENU = auto()       # Freunde-Menü
    QUEST_MENU = auto()        # Quest/Aufgaben
    AD_PLAYING = auto()        # Werbung läuft
    LOADING = auto()           # Ladebildschirm
    POPUP_DIALOG = auto()      # Beliebiger Popup-Dialog
    UNKNOWN = auto()           # Unbekannt


class BattleState(Enum):
    """Kampfzustände."""
    PREPARING = auto()         # Vor Kampfstart
    FIGHTING = auto()          # Kampf läuft (Gegner sichtbar)
    WAITING = auto()           # Zwischen Wellen
    VICTORY = auto()           # Gewonnen
    DEFEAT = auto()            # Verloren


# =============================================================================
# PIXEL-BASIERTE ERKENNUNGSPUNKTE
# =============================================================================

@dataclass
class ColorCheckpoint:
    """Ein Punkt zum Prüfen einer bestimmten Farbe."""
    x: int
    y: int
    expected_colors: List[Tuple[int, int, int]]  # RGB
    tolerance: int = 35
    name: str = ""
    
    def check(self, screenshot: np.ndarray) -> bool:
        """Prüft ob die Farbe an dieser Position stimmt."""
        if screenshot is None:
            return False
        h, w = screenshot.shape[:2]
        if self.y >= h or self.x >= w:
            return False
        
        # BGR -> RGB
        pixel_bgr = screenshot[self.y, self.x]
        pixel_rgb = (int(pixel_bgr[2]), int(pixel_bgr[1]), int(pixel_bgr[0]))
        
        for expected in self.expected_colors:
            distance = sum((a - b) ** 2 for a, b in zip(pixel_rgb, expected)) ** 0.5
            if distance < self.tolerance:
                return True
        return False


@dataclass  
class ScreenSignature:
    """Signatur eines Screens - mehrere Checkpoints die alle passen müssen."""
    screen_type: GameScreen
    checkpoints: List[ColorCheckpoint]
    min_matches: int = None  # Wie viele müssen matchen (default: alle)
    
    def __post_init__(self):
        if self.min_matches is None:
            self.min_matches = len(self.checkpoints)
    
    def check(self, screenshot: np.ndarray) -> Tuple[bool, float]:
        """
        Prüft ob dieser Screen vorliegt.
        
        Returns:
            (matched: bool, confidence: float 0-1)
        """
        if not self.checkpoints:
            return False, 0.0
        
        matches = sum(1 for cp in self.checkpoints if cp.check(screenshot))
        confidence = matches / len(self.checkpoints)
        matched = matches >= self.min_matches
        
        return matched, confidence


# =============================================================================
# SCREEN SIGNATUREN - Basierend auf Rush Royale UI
# =============================================================================

# Auflösung: 900x1600 (Portrait) oder 1600x900 (Landscape)
# Anpassen falls nötig!

SCREEN_SIGNATURES = [
    # -------------------------------------------------------------------------
    # HOME SCREEN
    # Erkennbar an: Bottom Navigation Bar mit bunten Buttons
    # -------------------------------------------------------------------------
    ScreenSignature(
        screen_type=GameScreen.HOME,
        checkpoints=[
            # Bottom Bar Hintergrund (dunkler Bereich)
            ColorCheckpoint(450, 1550, [(30, 25, 20), (40, 35, 30), (50, 45, 40)], 40, "bottom_bar"),
            # PvP Button Bereich (links) - typisch gold/orange
            ColorCheckpoint(140, 1259, [(200, 160, 80), (220, 180, 100), (180, 140, 60)], 50, "pvp_area"),
            # PvE Button Bereich (mitte-rechts)
            ColorCheckpoint(640, 1259, [(200, 160, 80), (180, 140, 60), (160, 120, 50)], 50, "pve_area"),
            # Oberer Bereich (typisch blau/dunkel)
            ColorCheckpoint(450, 100, [(30, 50, 80), (40, 60, 90), (50, 70, 100)], 50, "top_area"),
        ],
        min_matches=2  # Mindestens 2 von 4 müssen passen
    ),
    
    # -------------------------------------------------------------------------
    # BATTLE ACTIVE
    # Erkennbar an: Grid unten, Mana-Anzeige, dunkler Hintergrund oben
    # -------------------------------------------------------------------------
    ScreenSignature(
        screen_type=GameScreen.BATTLE_ACTIVE,
        checkpoints=[
            # Grid-Bereich (braun/grau)
            ColorCheckpoint(400, 1000, [(80, 70, 60), (90, 80, 70), (70, 60, 50)], 40, "grid_area"),
            # Mana-Bereich unten links (blau/lila)
            ColorCheckpoint(250, 1380, [(100, 80, 180), (80, 60, 160), (120, 100, 200)], 50, "mana_area"),
            # Oberer Spielbereich (dunkel, wo Gegner sind)
            ColorCheckpoint(450, 300, [(20, 20, 20), (30, 30, 30), (40, 40, 40)], 30, "enemy_area"),
            # Summon Button (grün wenn aktiv)
            ColorCheckpoint(620, 1400, [(80, 180, 80), (100, 200, 100), (60, 160, 60)], 50, "summon_btn"),
        ],
        min_matches=2
    ),
    
    # -------------------------------------------------------------------------
    # BATTLE VICTORY
    # Erkennbar an: Heller Bildschirm mit "Victory" Text, Belohnungen
    # -------------------------------------------------------------------------
    ScreenSignature(
        screen_type=GameScreen.BATTLE_VICTORY,
        checkpoints=[
            # Heller Hintergrund
            ColorCheckpoint(450, 400, [(200, 180, 140), (220, 200, 160), (180, 160, 120)], 60, "victory_bg"),
            # Continue Button Bereich (grün)
            ColorCheckpoint(450, 1100, [(80, 180, 80), (100, 200, 100), (60, 160, 60)], 50, "continue_btn"),
            # Gold/Belohnungen Bereich
            ColorCheckpoint(450, 700, [(220, 200, 100), (240, 220, 120), (200, 180, 80)], 60, "rewards"),
        ],
        min_matches=2
    ),
    
    # -------------------------------------------------------------------------
    # BATTLE DEFEAT
    # Erkennbar an: Dunklerer/roter Bildschirm
    # -------------------------------------------------------------------------
    ScreenSignature(
        screen_type=GameScreen.BATTLE_DEFEAT,
        checkpoints=[
            # Roter Schimmer
            ColorCheckpoint(450, 400, [(150, 50, 50), (180, 60, 60), (120, 40, 40)], 50, "defeat_red"),
            # Retry/Quit Buttons
            ColorCheckpoint(450, 1100, [(80, 80, 80), (100, 100, 100), (60, 60, 60)], 40, "defeat_btn"),
        ],
        min_matches=1
    ),
    
    # -------------------------------------------------------------------------
    # DUNGEON SELECT
    # Erkennbar an: Chapter Icons horizontal angeordnet
    # -------------------------------------------------------------------------
    ScreenSignature(
        screen_type=GameScreen.DUNGEON_SELECT,
        checkpoints=[
            # Dungeon Hintergrund (braun/dunkel)
            ColorCheckpoint(450, 300, [(60, 45, 35), (80, 60, 45), (50, 35, 25)], 40, "dungeon_bg"),
            # Chapter Bereich (wo die Icons sind)
            ColorCheckpoint(400, 500, [(100, 80, 60), (120, 100, 80), (80, 60, 40)], 50, "chapter_area"),
            # Back Button oben links (weiß/hell)
            ColorCheckpoint(60, 80, [(200, 200, 200), (220, 220, 220), (180, 180, 180)], 50, "back_btn"),
        ],
        min_matches=2
    ),
    
    # -------------------------------------------------------------------------
    # STORE
    # Erkennbar an: Store-spezifische UI Elemente
    # -------------------------------------------------------------------------
    ScreenSignature(
        screen_type=GameScreen.STORE,
        checkpoints=[
            # Store Hintergrund
            ColorCheckpoint(450, 300, [(40, 30, 25), (50, 40, 35), (60, 50, 45)], 40, "store_bg"),
            # Coins/Gems Anzeige oben
            ColorCheckpoint(700, 50, [(255, 220, 100), (255, 200, 80), (240, 200, 60)], 50, "gold_display"),
        ],
        min_matches=1
    ),
    
    # -------------------------------------------------------------------------
    # LOADING SCREEN
    # Erkennbar an: Meist schwarzer Bildschirm mit Loading-Elementen
    # -------------------------------------------------------------------------
    ScreenSignature(
        screen_type=GameScreen.LOADING,
        checkpoints=[
            # Schwarzer Hintergrund
            ColorCheckpoint(450, 800, [(10, 10, 10), (20, 20, 20), (5, 5, 5)], 20, "black_bg"),
            ColorCheckpoint(200, 400, [(10, 10, 10), (20, 20, 20), (5, 5, 5)], 20, "black_bg2"),
            ColorCheckpoint(700, 1200, [(10, 10, 10), (20, 20, 20), (5, 5, 5)], 20, "black_bg3"),
        ],
        min_matches=3
    ),
    
    # -------------------------------------------------------------------------
    # POPUP DIALOG
    # Erkennbar an: Helles Popup in der Mitte, dunkler Rand
    # -------------------------------------------------------------------------
    ScreenSignature(
        screen_type=GameScreen.POPUP_DIALOG,
        checkpoints=[
            # Dunkler Overlay-Rand
            ColorCheckpoint(50, 800, [(20, 20, 20), (30, 30, 30), (10, 10, 10)], 25, "dark_overlay"),
            # Helles Popup Zentrum
            ColorCheckpoint(450, 800, [(200, 190, 170), (220, 210, 190), (180, 170, 150)], 50, "popup_center"),
        ],
        min_matches=2
    ),
]


# =============================================================================
# TEMPLATE-FREE DETECTOR
# =============================================================================

# Versuche gelernte Signaturen zu laden (haben Priorität!)
LEARNED_SIGNATURES_AVAILABLE = False
try:
    from .learned_signatures import LEARNED_SIGNATURES
    LEARNED_SIGNATURES_AVAILABLE = True
except ImportError:
    try:
        from Src.utils.learned_signatures import LEARNED_SIGNATURES
        LEARNED_SIGNATURES_AVAILABLE = True
    except ImportError:
        LEARNED_SIGNATURES = []


class TemplateFreeDetector:
    """
    Erkennt Screens und UI-Elemente komplett ohne Templates.
    
    Nutzt nur:
    - Feste Pixel-Positionen
    - Farberkennung
    - Geometrie-Analyse
    
    Priorität:
    1. Gelernte Signaturen (aus auto_learn.py)
    2. Standard-Signaturen (Fallback)
    
    Example:
        detector = TemplateFreeDetector()
        screen, confidence = detector.detect_screen(screenshot)
        if screen == GameScreen.HOME:
            print("Auf Home Screen!")
    """
    
    def __init__(self, signatures: List[ScreenSignature] = None, use_learned: bool = True):
        # Priorität: Gelernte Signaturen > Übergebene > Standard
        if signatures:
            self.signatures = signatures
        elif use_learned and LEARNED_SIGNATURES_AVAILABLE and LEARNED_SIGNATURES:
            self.signatures = LEARNED_SIGNATURES
            logger.info(f"Nutze {len(LEARNED_SIGNATURES)} gelernte Signaturen (keine Icons nötig!)")
        else:
            self.signatures = SCREEN_SIGNATURES
        
        self.logger = logging.getLogger(f"{__name__}.TemplateFreeDetector")
        
        # Cache für letzte Erkennung
        self._last_screen: Optional[GameScreen] = None
        self._last_confidence: float = 0.0
    
    def detect_screen(self, screenshot: np.ndarray) -> Tuple[GameScreen, float]:
        """
        Erkennt den aktuellen Bildschirm.
        
        Args:
            screenshot: BGR-Bild (OpenCV Format)
            
        Returns:
            Tuple von (GameScreen, confidence 0-1)
        """
        if screenshot is None:
            return GameScreen.UNKNOWN, 0.0
        
        best_match = GameScreen.UNKNOWN
        best_confidence = 0.0
        
        for sig in self.signatures:
            matched, confidence = sig.check(screenshot)
            if matched and confidence > best_confidence:
                best_match = sig.screen_type
                best_confidence = confidence
        
        self._last_screen = best_match
        self._last_confidence = best_confidence
        
        self.logger.debug(f"Screen erkannt: {best_match.name} ({best_confidence:.2f})")
        return best_match, best_confidence
    
    def detect_battle_state(self, screenshot: np.ndarray) -> Tuple[BattleState, float]:
        """
        Erkennt den Kampfzustand (nur wenn im Kampf).
        
        Returns:
            Tuple von (BattleState, confidence)
        """
        if screenshot is None:
            return BattleState.PREPARING, 0.0
        
        # Prüfe ob überhaupt im Kampf
        screen, _ = self.detect_screen(screenshot)
        if screen == GameScreen.BATTLE_VICTORY:
            return BattleState.VICTORY, 1.0
        if screen == GameScreen.BATTLE_DEFEAT:
            return BattleState.DEFEAT, 1.0
        if screen != GameScreen.BATTLE_ACTIVE:
            return BattleState.PREPARING, 0.5
        
        # Im aktiven Kampf - prüfe ob Gegner sichtbar
        # Gegner sind im oberen Drittel, bewegen sich (Farbvariation)
        enemy_area = screenshot[100:400, 200:700]
        
        # Berechne Farbvariation im Gegner-Bereich
        # Mehr Variation = Gegner/Animationen aktiv
        std_dev = np.std(enemy_area)
        
        if std_dev > 50:
            return BattleState.FIGHTING, 0.8
        else:
            return BattleState.WAITING, 0.7
    
    def is_button_active(
        self, 
        screenshot: np.ndarray, 
        x: int, 
        y: int, 
        check_radius: int = 20
    ) -> bool:
        """
        Prüft ob ein Button an Position (x,y) aktiv/klickbar ist.
        
        Aktive Buttons haben typischerweise:
        - Hellere Farben
        - Grüner/goldener Schimmer
        - Mehr Sättigung
        """
        if screenshot is None:
            return False
        
        h, w = screenshot.shape[:2]
        x1 = max(0, x - check_radius)
        x2 = min(w, x + check_radius)
        y1 = max(0, y - check_radius)
        y2 = min(h, y + check_radius)
        
        roi = screenshot[y1:y2, x1:x2]
        
        # Konvertiere zu HSV für bessere Farberkennung
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        
        # Prüfe Helligkeit und Sättigung
        avg_saturation = np.mean(hsv[:, :, 1])
        avg_value = np.mean(hsv[:, :, 2])
        
        # Aktive Buttons: höhere Sättigung und Helligkeit
        return avg_saturation > 80 and avg_value > 120
    
    def get_mana_value(self, screenshot: np.ndarray) -> Optional[int]:
        """
        Liest den Mana-Wert aus dem Screenshot (OCR-frei via Balken).
        
        Alternativ: Pixel-Zählung im Mana-Balken.
        """
        if screenshot is None:
            return None
        
        # Mana-Balken Position (anpassen!)
        mana_bar_y = 1380
        mana_bar_x_start = 180
        mana_bar_x_end = 320
        
        h, w = screenshot.shape[:2]
        if mana_bar_y >= h:
            return None
        
        # Mana-Balken extrahieren
        bar = screenshot[mana_bar_y:mana_bar_y+20, mana_bar_x_start:mana_bar_x_end]
        
        # Konvertiere zu HSV
        hsv = cv2.cvtColor(bar, cv2.COLOR_BGR2HSV)
        
        # Blau-Maske für gefüllten Mana-Bereich
        blue_mask = cv2.inRange(hsv, (100, 50, 50), (130, 255, 255))
        
        # Prozent des gefüllten Balkens
        fill_percent = np.sum(blue_mask > 0) / blue_mask.size
        
        # Grobe Mana-Schätzung (max ~500 im späten Spiel)
        estimated_mana = int(fill_percent * 500)
        
        return estimated_mana
    
    def has_popup(self, screenshot: np.ndarray) -> bool:
        """Prüft ob ein Popup-Dialog geöffnet ist."""
        screen, conf = self.detect_screen(screenshot)
        return screen == GameScreen.POPUP_DIALOG and conf > 0.6


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_detector() -> TemplateFreeDetector:
    """Erstellt einen konfigurierten Detector."""
    return TemplateFreeDetector()


def quick_detect(screenshot: np.ndarray) -> str:
    """
    Schnelle Screen-Erkennung.
    
    Returns:
        Screen-Name als String
    """
    detector = TemplateFreeDetector()
    screen, _ = detector.detect_screen(screenshot)
    return screen.name.lower()


# =============================================================================
# KALIBRIERUNG - Erstelle Signaturen aus echten Screenshots
# =============================================================================

def calibrate_from_screenshot(
    screenshot: np.ndarray,
    screen_type: GameScreen,
    sample_points: List[Tuple[int, int]] = None
) -> ScreenSignature:
    """
    Erstellt eine neue Screen-Signatur aus einem Screenshot.
    
    Args:
        screenshot: Bekannter Screenshot dieses Screen-Typs
        screen_type: Der Screen-Typ
        sample_points: Liste von (x, y) Positionen zum Samplen
                       Default: Automatisch verteilt
    
    Returns:
        Neue ScreenSignature
    """
    if sample_points is None:
        h, w = screenshot.shape[:2]
        # Automatisch Punkte verteilen
        sample_points = [
            (w // 4, h // 4),
            (w // 2, h // 4),
            (3 * w // 4, h // 4),
            (w // 4, h // 2),
            (w // 2, h // 2),
            (3 * w // 4, h // 2),
            (w // 4, 3 * h // 4),
            (w // 2, 3 * h // 4),
            (3 * w // 4, 3 * h // 4),
        ]
    
    checkpoints = []
    for i, (x, y) in enumerate(sample_points):
        if y < screenshot.shape[0] and x < screenshot.shape[1]:
            # BGR -> RGB
            pixel = screenshot[y, x]
            rgb = (int(pixel[2]), int(pixel[1]), int(pixel[0]))
            
            checkpoints.append(ColorCheckpoint(
                x=x, y=y,
                expected_colors=[rgb],
                tolerance=40,
                name=f"point_{i}"
            ))
    
    return ScreenSignature(
        screen_type=screen_type,
        checkpoints=checkpoints,
        min_matches=len(checkpoints) // 2  # 50% müssen matchen
    )


def save_calibration(signatures: List[ScreenSignature], filepath: str):
    """Speichert Kalibrierung als Python-Code."""
    import json
    
    data = []
    for sig in signatures:
        sig_data = {
            'screen_type': sig.screen_type.name,
            'min_matches': sig.min_matches,
            'checkpoints': [
                {
                    'x': cp.x,
                    'y': cp.y,
                    'expected_colors': cp.expected_colors,
                    'tolerance': cp.tolerance,
                    'name': cp.name
                }
                for cp in sig.checkpoints
            ]
        }
        data.append(sig_data)
    
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"Kalibrierung gespeichert: {filepath}")
