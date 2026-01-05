"""
Rush Royale Bot - Hybrid Navigator
Python 3.13 Compatible

Kombiniert drei Erkennungsmethoden in Prioritätsreihenfolge:
1. Feste Positionen (am schnellsten, zuverlässigsten für bekannte Screens)
2. Farb-basierte Screen-Erkennung (robust gegen UI-Änderungen)
3. Template-Matching (Fallback für spezifische Icons)

Dies macht den Bot unabhängiger von veralteten Templates.
"""
from __future__ import annotations

import os
import time
import logging
from typing import Optional, Tuple, List, Dict, Any, Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path

import cv2
import numpy as np

# Import screen positions
try:
    from .screen_positions import (
        HomeScreen, DungeonScreen, BattleScreen, GenericButtons,
        ColorSignatures, detect_screen_by_color, color_distance,
        get_grid_positions, ScreenPosition
    )
except ImportError:
    from screen_positions import (
        HomeScreen, DungeonScreen, BattleScreen, GenericButtons,
        ColorSignatures, detect_screen_by_color, color_distance,
        get_grid_positions, ScreenPosition
    )

logger = logging.getLogger(__name__)


class ScreenType(Enum):
    """Bekannte Screen-Typen."""
    HOME = auto()
    DUNGEON_MENU = auto()
    CHAPTER_SELECT = auto()
    FLOOR_SELECT = auto()
    BATTLE_ACTIVE = auto()
    BATTLE_END = auto()
    STORE = auto()
    SETTINGS = auto()
    FRIEND_MENU = auto()
    AD_PLAYING = auto()
    UNKNOWN = auto()


@dataclass
class NavigationResult:
    """Ergebnis einer Navigation."""
    success: bool
    screen_type: ScreenType
    method_used: str  # 'position', 'color', 'template', 'ocr'
    confidence: float = 1.0
    message: str = ""


@dataclass
class DetectionMethod:
    """Eine Erkennungsmethode mit Priorität."""
    name: str
    priority: int  # Niedrigere Zahl = höhere Priorität
    detect_func: Callable
    confidence_threshold: float = 0.7


class HybridNavigator:
    """
    Hybrid-Navigator der mehrere Erkennungsmethoden kombiniert.
    
    Strategie:
    1. Versuche Screen via Farberkennung zu identifizieren (schnell, robust)
    2. Nutze feste Positionen für bekannte Screens (kein Template nötig)
    3. Fallback auf Template-Matching nur wenn nötig
    
    Example:
        nav = HybridNavigator(bot)
        result = nav.navigate_to_dungeon()
        if result.success:
            print(f"Erfolgreich via {result.method_used}")
    """
    
    def __init__(self, bot, use_templates: bool = True):
        """
        Initialisiert den Navigator.
        
        Args:
            bot: Bot-Instanz mit getScreen(), click(), etc.
            use_templates: Ob Template-Matching als Fallback genutzt werden soll
        """
        self.bot = bot
        self.use_templates = use_templates
        self.logger = logging.getLogger(f"{__name__}.HybridNavigator")
        
        # Tracking für Debug
        self.last_detected_screen: Optional[ScreenType] = None
        self.detection_history: List[Tuple[ScreenType, str]] = []
    
    # =========================================================================
    # SCREEN DETECTION
    # =========================================================================
    
    def detect_current_screen(self, screenshot: np.ndarray = None) -> Tuple[ScreenType, str, float]:
        """
        Erkennt den aktuellen Screen mit mehreren Methoden.
        
        Returns:
            Tuple von (ScreenType, method_used, confidence)
        """
        if screenshot is None:
            self.bot.getScreen()
            screenshot = self.bot.screenRGB
        
        if screenshot is None:
            return ScreenType.UNKNOWN, 'none', 0.0
        
        # Methode 1: Farb-basierte Erkennung (schnell)
        screen_by_color = self._detect_by_color(screenshot)
        if screen_by_color != ScreenType.UNKNOWN:
            self.logger.debug(f"Screen via Farbe erkannt: {screen_by_color}")
            return screen_by_color, 'color', 0.9
        
        # Methode 2: Spezifische Pixel-Prüfungen
        screen_by_pixels = self._detect_by_pixel_checks(screenshot)
        if screen_by_pixels != ScreenType.UNKNOWN:
            self.logger.debug(f"Screen via Pixel erkannt: {screen_by_pixels}")
            return screen_by_pixels, 'pixel', 0.85
        
        # Methode 3: Template-Matching (Fallback)
        if self.use_templates:
            screen_by_template, confidence = self._detect_by_templates(screenshot)
            if screen_by_template != ScreenType.UNKNOWN:
                self.logger.debug(f"Screen via Template erkannt: {screen_by_template} ({confidence:.2f})")
                return screen_by_template, 'template', confidence
        
        return ScreenType.UNKNOWN, 'none', 0.0
    
    def _detect_by_color(self, screenshot: np.ndarray) -> ScreenType:
        """Erkennt Screen via Farbanalyse."""
        screen_name = detect_screen_by_color(screenshot)
        
        mapping = {
            'home_screen': ScreenType.HOME,
            'dungeon_page': ScreenType.DUNGEON_MENU,
            'battle_active': ScreenType.BATTLE_ACTIVE,
        }
        
        return mapping.get(screen_name, ScreenType.UNKNOWN)
    
    def _detect_by_pixel_checks(self, screenshot: np.ndarray) -> ScreenType:
        """
        Erkennt Screen via spezifische Pixel-Positionen.
        
        Prüft charakteristische UI-Elemente an festen Positionen.
        """
        h, w = screenshot.shape[:2]
        
        # Home Screen: Prüfe Bottom Navigation Bar
        if self._check_pixel_region(
            screenshot, 
            region=(100, 1230, 200, 60),  # (x, y, w, h)
            expected_colors=[
                np.array([200, 180, 100]),  # Gold-Töne für Buttons
                np.array([180, 160, 80]),
            ],
            tolerance=50
        ):
            return ScreenType.HOME
        
        # Battle Screen: Prüfe Grid-Bereich
        if self._check_pixel_region(
            screenshot,
            region=(165, 900, 100, 100),
            expected_colors=[
                np.array([40, 40, 40]),  # Dunkler Grid-Hintergrund
                np.array([30, 30, 30]),
            ],
            tolerance=30
        ):
            # Zusätzlich prüfen ob Mana-Anzeige sichtbar
            if self._has_mana_display(screenshot):
                return ScreenType.BATTLE_ACTIVE
        
        # Dungeon Menu: Prüfe Chapter-Icons Bereich
        if self._check_pixel_region(
            screenshot,
            region=(100, 350, 200, 100),
            expected_colors=[
                np.array([80, 60, 40]),  # Dungeon-Hintergrund
                np.array([70, 50, 35]),
            ],
            tolerance=40
        ):
            return ScreenType.DUNGEON_MENU
        
        return ScreenType.UNKNOWN
    
    def _check_pixel_region(
        self,
        screenshot: np.ndarray,
        region: Tuple[int, int, int, int],
        expected_colors: List[np.ndarray],
        tolerance: float = 30
    ) -> bool:
        """
        Prüft ob eine Region eine der erwarteten Farben enthält.
        
        Args:
            screenshot: BGR-Bild
            region: (x, y, width, height)
            expected_colors: Liste von RGB-Farben
            tolerance: Maximale Farbdistanz
            
        Returns:
            True wenn Farbe gefunden
        """
        x, y, w, h = region
        if y + h > screenshot.shape[0] or x + w > screenshot.shape[1]:
            return False
        
        # Durchschnittsfarbe der Region (BGR -> RGB)
        roi = screenshot[y:y+h, x:x+w]
        avg_color_bgr = np.mean(roi, axis=(0, 1))
        avg_color_rgb = np.array([avg_color_bgr[2], avg_color_bgr[1], avg_color_bgr[0]])
        
        for expected in expected_colors:
            if color_distance(avg_color_rgb, expected) < tolerance:
                return True
        
        return False
    
    def _has_mana_display(self, screenshot: np.ndarray) -> bool:
        """Prüft ob die Mana-Anzeige sichtbar ist."""
        # Mana-Display Position
        x, y, w, h = 220, 1360, 90, 50
        if y + h > screenshot.shape[0]:
            return False
        
        roi = screenshot[y:y+h, x:x+w]
        
        # Mana-Display hat typischerweise blaue/lila Farben
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        
        # Prüfe auf blaue Farbtöne (Hue 100-130)
        blue_mask = cv2.inRange(hsv, (100, 50, 50), (130, 255, 255))
        blue_ratio = np.sum(blue_mask > 0) / blue_mask.size
        
        return blue_ratio > 0.1  # Mind. 10% blaue Pixel
    
    def _detect_by_templates(self, screenshot: np.ndarray) -> Tuple[ScreenType, float]:
        """Fallback: Template-basierte Erkennung."""
        # Nutze bestehende get_current_icons Funktion
        if not hasattr(self.bot, 'get_current_icons'):
            return ScreenType.UNKNOWN, 0.0
        
        df = self.bot.get_current_icons(new=False)  # Screenshot bereits vorhanden
        if df.empty:
            return ScreenType.UNKNOWN, 0.0
        
        available = df[df['available'] == True]['icon'].tolist()
        
        # Mapping von Icons zu Screens
        if 'home_screen.png' in available or 'battle_icon.png' in available:
            return ScreenType.HOME, 0.8
        if 'dungeon_page.png' in available or any('chapter_' in i for i in available):
            return ScreenType.DUNGEON_MENU, 0.8
        if 'fighting.png' in available:
            return ScreenType.BATTLE_ACTIVE, 0.8
        if '0cont_button.png' in available or '1quit.png' in available:
            return ScreenType.BATTLE_END, 0.8
        
        return ScreenType.UNKNOWN, 0.0
    
    # =========================================================================
    # NAVIGATION
    # =========================================================================
    
    def navigate_to_dungeon(self, max_attempts: int = 5) -> NavigationResult:
        """
        Navigiert zum Dungeon-Menü mit Hybrid-Ansatz.
        
        Nutzt primär feste Positionen, Farberkennung als Validierung.
        """
        for attempt in range(max_attempts):
            self.logger.info(f"Dungeon-Navigation Versuch {attempt + 1}/{max_attempts}")
            
            # Aktuellen Screen erkennen
            screen_type, method, confidence = self.detect_current_screen()
            self.logger.info(f"Erkannter Screen: {screen_type} via {method} ({confidence:.2f})")
            
            # Schon am Ziel?
            if screen_type == ScreenType.DUNGEON_MENU:
                return NavigationResult(
                    success=True,
                    screen_type=screen_type,
                    method_used=method,
                    confidence=confidence,
                    message="Bereits im Dungeon-Menü"
                )
            
            # Auf Home Screen? -> PvE Button klicken
            if screen_type == ScreenType.HOME:
                self.logger.info("Auf Home Screen, klicke PvE Button...")
                self._click_pve_button()
                time.sleep(2)
                continue
            
            # Im Kampf? -> Nicht unterbrechen
            if screen_type == ScreenType.BATTLE_ACTIVE:
                return NavigationResult(
                    success=False,
                    screen_type=screen_type,
                    method_used=method,
                    message="Kampf aktiv - Navigation nicht möglich"
                )
            
            # Kampf beendet? -> Continue klicken
            if screen_type == ScreenType.BATTLE_END:
                self.logger.info("Kampf beendet, klicke Continue...")
                self.bot.click_button(BattleScreen.CONTINUE_BUTTON.to_array())
                time.sleep(1)
                continue
            
            # Unbekannter Screen -> Probiere verschiedene Methoden
            if screen_type == ScreenType.UNKNOWN:
                self.logger.warning("Unbekannter Screen, versuche Recovery...")
                if self._try_recovery_navigation():
                    continue
            
            # Zurück-Button probieren
            self.logger.info("Sende Zurück-Taste...")
            self.bot.key_input(4)  # KEYCODE_BACK
            time.sleep(1)
        
        return NavigationResult(
            success=False,
            screen_type=ScreenType.UNKNOWN,
            method_used='none',
            message=f"Navigation nach {max_attempts} Versuchen fehlgeschlagen"
        )
    
    def _click_pve_button(self):
        """Klickt den PvE Button mit mehreren Fallback-Positionen."""
        positions = [
            HomeScreen.PVE_BUTTON,
            *HomeScreen.PVE_ALT_POSITIONS
        ]
        
        for pos in positions:
            self.logger.debug(f"Versuche PvE-Position: {pos.name} ({pos.x}, {pos.y})")
            self.bot.click_button(pos.to_array())
            time.sleep(1)
            
            # Prüfe ob Navigation erfolgreich
            screen_type, _, _ = self.detect_current_screen()
            if screen_type == ScreenType.DUNGEON_MENU:
                self.logger.info(f"PvE Button erfolgreich bei {pos.name}")
                return True
        
        return False
    
    def _try_recovery_navigation(self) -> bool:
        """
        Versucht von einem unbekannten Screen zu navigieren.
        
        Probiert typische Escape-Aktionen.
        """
        recovery_actions = [
            # Klick auf typische "Schließen" Positionen
            lambda: self.bot.click(750, 200),  # X-Button oben rechts
            lambda: self.bot.click(400, 1200),  # Cancel-Button unten
            lambda: self.bot.key_input(4),      # Back-Taste
            # Warte und prüfe ob sich was geändert hat
            lambda: time.sleep(2),
        ]
        
        for action in recovery_actions:
            action()
            time.sleep(0.5)
            
            screen_type, _, _ = self.detect_current_screen()
            if screen_type != ScreenType.UNKNOWN:
                return True
        
        return False
    
    def select_dungeon_floor(self, chapter: int = 2, floor: int = 5) -> NavigationResult:
        """
        Wählt einen spezifischen Dungeon-Floor aus.
        
        Args:
            chapter: Kapitel-Nummer (1-6)
            floor: Floor-Nummer (1-10)
        """
        # Erst zum Dungeon navigieren
        nav_result = self.navigate_to_dungeon()
        if not nav_result.success:
            return nav_result
        
        # Chapter auswählen (feste Position)
        chapter_positions = {
            1: DungeonScreen.CHAPTER_1,
            2: DungeonScreen.CHAPTER_2,
            3: DungeonScreen.CHAPTER_3,
            4: DungeonScreen.CHAPTER_4,
            5: DungeonScreen.CHAPTER_5,
            6: DungeonScreen.CHAPTER_6,
        }
        
        if chapter not in chapter_positions:
            return NavigationResult(
                success=False,
                screen_type=ScreenType.DUNGEON_MENU,
                method_used='position',
                message=f"Ungültiges Kapitel: {chapter}"
            )
        
        # Klicke Chapter
        chapter_pos = chapter_positions[chapter]
        self.logger.info(f"Wähle Kapitel {chapter} bei {chapter_pos.to_tuple()}")
        self.bot.click_button(chapter_pos.to_array())
        time.sleep(1)
        
        # Floor auswählen
        if floor in DungeonScreen.FLOOR_POSITIONS:
            floor_pos = DungeonScreen.FLOOR_POSITIONS[floor]
            self.logger.info(f"Wähle Floor {floor} bei {floor_pos.to_tuple()}")
            self.bot.click_button(floor_pos.to_array())
            time.sleep(1)
        
        # Start-Button
        self.logger.info("Klicke Start-Button")
        self.bot.click_button(DungeonScreen.START_BUTTON.to_array())
        time.sleep(2)
        
        return NavigationResult(
            success=True,
            screen_type=ScreenType.CHAPTER_SELECT,
            method_used='position',
            confidence=1.0,
            message=f"Dungeon C{chapter}F{floor} gestartet"
        )
    
    # =========================================================================
    # DIAGNOSTICS
    # =========================================================================
    
    def calibrate_positions(self, screenshot: np.ndarray = None) -> Dict[str, Any]:
        """
        Analysiert Screenshot und schlägt Position-Korrekturen vor.
        
        Nützlich wenn die festen Positionen nicht mehr stimmen.
        """
        if screenshot is None:
            self.bot.getScreen()
            screenshot = self.bot.screenRGB
        
        results = {
            'screen_size': screenshot.shape[:2] if screenshot is not None else None,
            'detected_elements': [],
            'suggestions': []
        }
        
        if screenshot is None:
            results['suggestions'].append("Kein Screenshot verfügbar")
            return results
        
        h, w = screenshot.shape[:2]
        results['screen_size'] = (w, h)
        
        # Prüfe ob Auflösung von Standard abweicht
        expected_w, expected_h = 900, 1600
        if w != expected_w or h != expected_h:
            scale_w = w / expected_w
            scale_h = h / expected_h
            results['suggestions'].append(
                f"Auflösung {w}x{h} weicht von Standard ab. "
                f"Skalierungsfaktor: {scale_w:.2f}x{scale_h:.2f}"
            )
        
        return results


# =============================================================================
# INTEGRATION MIT BESTEHENDEM BOT
# =============================================================================

def integrate_hybrid_navigator(bot) -> HybridNavigator:
    """
    Integriert den HybridNavigator in einen bestehenden Bot.
    
    Args:
        bot: Bestehende Bot-Instanz
        
    Returns:
        Konfigurierter HybridNavigator
    """
    navigator = HybridNavigator(bot)
    
    # Füge Convenience-Methoden zum Bot hinzu
    bot.hybrid_nav = navigator
    bot.navigate_to_dungeon_hybrid = navigator.navigate_to_dungeon
    bot.select_dungeon_floor_hybrid = navigator.select_dungeon_floor
    bot.detect_screen_hybrid = navigator.detect_current_screen
    
    return navigator
