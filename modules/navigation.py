#!/usr/bin/env python3
"""
Rush Royale Bot - Navigation Module
Game navigation and state management
"""

import time
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class GameState:
    """Game state information"""
    current_screen: str = "unknown"
    in_battle: bool = False
    battle_type: str = ""
    chapter: int = 0
    wave: int = 0
    gold: int = 0
    energy: int = 0
    confidence: float = 0.0
    last_update: float = 0.0


class NavigationSystem:
    """Game navigation and state detection system"""
    
    def __init__(self, device_manager, perception_system):
        self.device = device_manager
        self.perception = perception_system
        self.logger = logging.getLogger(__name__)
        
        # Current game state
        self.current_state = GameState()
        
        # Navigation timeouts
        self.default_timeout = 10.0
        self.click_delay = 0.5
        self.screen_check_delay = 1.0
        
        # Icon paths for navigation
        self.icons = {
            'home_screen': 'icons/home_screen.png',
            'battle_icon': 'icons/battle_icon.png',
            'pvp_button': 'icons/pvp_button.png',
            'pve_button': 'icons/ad_pve.png',
            'dungeon_page': 'icons/dungeon_page.png',
            'back_button': 'icons/back_button.png',
            'continue_button': 'icons/0cont_button.png',
            'quit_button': 'icons/1quit.png',
            'fighting': 'icons/fighting.png',
            'refresh_button': 'icons/refresh_button.png',
            'x_mark': 'icons/x_mark.png',
            'quest_collect': 'icons/quest_collect.png',
            'quest_done': 'icons/quest_done.png'
        }
        
        # Chapter icons
        for i in range(1, 6):
            self.icons[f'chapter_{i}'] = f'icons/chapter_{i}.png'
        
        self.logger.info("Navigation system initialized")
    
    def detect_current_screen(self, img = None) -> GameState:
        """Detect current game screen and state"""
        try:
            if img is None:
                img = self.device.get_screenshot()
                if img is None:
                    self.logger.warning("Could not get screenshot for screen detection")
                    return self.current_state
            
            state = GameState()
            state.last_update = time.time()
            
            # Check for various screens in priority order
            if self._is_battle_screen(img):
                state.current_screen = "battle"
                state.in_battle = True
                state.battle_type = self._detect_battle_type(img)
                state.wave = self._detect_wave_number(img)
                
            elif self._is_home_screen(img):
                state.current_screen = "home"
                state.in_battle = False
                
            elif self._is_dungeon_screen(img):
                state.current_screen = "dungeon"
                state.in_battle = False
                state.chapter = self._detect_chapter(img)
                
            elif self._is_battle_selection(img):
                state.current_screen = "battle_selection"
                state.in_battle = False
                
            elif self._is_loading_screen(img):
                state.current_screen = "loading"
                state.in_battle = False
                
            else:
                state.current_screen = "unknown"
                state.confidence = 0.0
            
            # Update current state
            self.current_state = state
            
            self.logger.debug(f"Screen detected: {state.current_screen} "
                            f"(confidence: {state.confidence:.2f})")
            
            return state
            
        except Exception as e:
            self.logger.error(f"Screen detection error: {e}")
            return self.current_state
    
    def _is_battle_screen(self, img) -> bool:
        """Check if current screen is battle"""
        try:
            # Look for battle-specific elements
            fighting_found = self.perception.find_icon(img, self.icons['fighting'])
            if fighting_found:
                self.current_state.confidence = 0.9
                return True
            
            # Check for unit grid pattern
            grid_found = self._detect_battle_grid(img)
            if grid_found:
                self.current_state.confidence = 0.8
                return True
            
            return False
            
        except Exception as e:
            self.logger.debug(f"Battle screen check error: {e}")
            return False
    
    def _is_home_screen(self, img) -> bool:
        """Check if current screen is home"""
        try:
            home_found = self.perception.find_icon(img, self.icons['home_screen'])
            if home_found:
                self.current_state.confidence = 0.9
                return True
            
            # Look for multiple home screen elements
            battle_icon = self.perception.find_icon(img, self.icons['battle_icon'])
            if battle_icon:
                self.current_state.confidence = 0.7
                return True
            
            return False
            
        except Exception as e:
            self.logger.debug(f"Home screen check error: {e}")
            return False
    
    def _is_dungeon_screen(self, img) -> bool:
        """Check if current screen is dungeon selection"""
        try:
            dungeon_found = self.perception.find_icon(img, self.icons['dungeon_page'])
            if dungeon_found:
                self.current_state.confidence = 0.9
                return True
            
            # Check for chapter icons
            for i in range(1, 6):
                chapter_found = self.perception.find_icon(img, self.icons[f'chapter_{i}'])
                if chapter_found:
                    self.current_state.confidence = 0.8
                    return True
            
            return False
            
        except Exception as e:
            self.logger.debug(f"Dungeon screen check error: {e}")
            return False
    
    def _is_battle_selection(self, img) -> bool:
        """Check if current screen is battle type selection"""
        try:
            pvp_found = self.perception.find_icon(img, self.icons['pvp_button'])
            pve_found = self.perception.find_icon(img, self.icons['pve_button'])
            
            if pvp_found or pve_found:
                self.current_state.confidence = 0.8
                return True
            
            return False
            
        except Exception as e:
            self.logger.debug(f"Battle selection check error: {e}")
            return False
    
    def _is_loading_screen(self, img) -> bool:
        """Check if current screen is loading"""
        try:
            # Loading screens often have specific patterns or animations
            # This is a simplified check
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Check for very dark or uniform image (loading screen characteristic)
            mean_brightness = np.mean(gray)
            if mean_brightness < 30:  # Very dark screen
                self.current_state.confidence = 0.6
                return True
            
            return False
            
        except Exception as e:
            self.logger.debug(f"Loading screen check error: {e}")
            return False
    
    def _detect_battle_type(self, img) -> str:
        """Detect type of battle (PvE, PvP, etc.)"""
        try:
            # This would need specific visual indicators for each battle type
            # Placeholder implementation
            return "pve"
            
        except Exception as e:
            self.logger.debug(f"Battle type detection error: {e}")
            return "unknown"
    
    def _detect_wave_number(self, img) -> int:
        """Detect current wave number in battle"""
        try:
            # This would require OCR or specific wave indicators
            # Placeholder implementation
            return 1
            
        except Exception as e:
            self.logger.debug(f"Wave detection error: {e}")
            return 0
    
    def _detect_chapter(self, img) -> int:
        """Detect selected chapter in dungeon"""
        try:
            for i in range(1, 6):
                chapter_found = self.perception.find_icon(img, self.icons[f'chapter_{i}'])
                if chapter_found:
                    return i
            
            return 0
            
        except Exception as e:
            self.logger.debug(f"Chapter detection error: {e}")
            return 0
    
    def _detect_battle_grid(self, img) -> bool:
        """Detect battle grid pattern"""
        try:
            # Look for the characteristic grid pattern of the battle field
            # This is a simplified check
            height, width = img.shape[:2]
            
            # Battle grid is typically in the lower portion of screen
            grid_region = img[int(height * 0.4):int(height * 0.9), 
                             int(width * 0.1):int(width * 0.9)]
            
            # Look for grid-like patterns (this would need refinement)
            gray = cv2.cvtColor(grid_region, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            
            # Count horizontal and vertical lines
            lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=50)
            
            if lines is not None and len(lines) > 10:
                return True
            
            return False
            
        except Exception as e:
            self.logger.debug(f"Battle grid detection error: {e}")
            return False
    
    def navigate_to_home(self, timeout: float = None) -> bool:
        """Navigate to home screen"""
        timeout = timeout or self.default_timeout
        start_time = time.time()
        
        self.logger.info("Navigating to home screen")
        
        while time.time() - start_time < timeout:
            # Check current state
            current_state = self.detect_current_screen()
            
            if current_state.current_screen == "home":
                self.logger.info("Successfully reached home screen")
                return True
            
            # Try different navigation methods based on current screen
            if current_state.current_screen == "battle":
                self._exit_battle()
            elif current_state.current_screen in ["dungeon", "battle_selection"]:
                self._click_back_button()
            elif current_state.current_screen == "unknown":
                self._handle_unknown_screen()
            
            time.sleep(self.screen_check_delay)
        
        self.logger.warning(f"Failed to reach home screen within {timeout}s")
        return False
    
    def navigate_to_dungeon(self, chapter: int = 1, timeout: float = None) -> bool:
        """Navigate to dungeon screen and select chapter"""
        timeout = timeout or self.default_timeout
        start_time = time.time()
        
        self.logger.info(f"Navigating to dungeon chapter {chapter}")
        
        # First navigate to home
        if not self.navigate_to_home(timeout / 2):
            return False
        
        while time.time() - start_time < timeout:
            current_state = self.detect_current_screen()
            
            if current_state.current_screen == "dungeon":
                # Select chapter
                return self._select_chapter(chapter)
            
            elif current_state.current_screen == "home":
                # Click battle icon to go to battle selection
                if self._click_icon('battle_icon'):
                    time.sleep(self.click_delay)
                
            elif current_state.current_screen == "battle_selection":
                # Click PvE button
                if self._click_icon('pve_button'):
                    time.sleep(self.click_delay)
            
            time.sleep(self.screen_check_delay)
        
        self.logger.warning(f"Failed to reach dungeon within {timeout}s")
        return False
    
    def start_battle(self, battle_type: str = "pve", chapter: int = 1, timeout: float = None) -> bool:
        """Start a battle of specified type"""
        timeout = timeout or self.default_timeout
        
        self.logger.info(f"Starting {battle_type} battle")
        
        if battle_type.lower() == "pve":
            # Navigate to dungeon and start battle
            if not self.navigate_to_dungeon(chapter, timeout / 2):
                return False
            
            # Click continue/start button
            return self._click_icon('continue_button', timeout / 2)
        
        elif battle_type.lower() == "pvp":
            # Navigate to PvP (implementation would depend on UI)
            return self._start_pvp_battle(timeout)
        
        else:
            self.logger.error(f"Unknown battle type: {battle_type}")
            return False
    
    def _exit_battle(self) -> bool:
        """Exit current battle"""
        try:
            # Look for quit button
            if self._click_icon('quit_button'):
                time.sleep(self.click_delay)
                return True
            
            # Alternative: look for X mark
            if self._click_icon('x_mark'):
                time.sleep(self.click_delay)
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error exiting battle: {e}")
            return False
    
    def _click_back_button(self) -> bool:
        """Click back button"""
        return self._click_icon('back_button')
    
    def _click_icon(self, icon_key: str, timeout: float = 5.0) -> bool:
        """Click on specified icon"""
        try:
            if icon_key not in self.icons:
                self.logger.error(f"Unknown icon: {icon_key}")
                return False
            
            img = self.device.get_screenshot()
            if img is None:
                return False
            
            icon_location = self.perception.find_icon(img, self.icons[icon_key])
            
            if icon_location:
                x, y = icon_location
                self.device.click(x, y)
                self.logger.debug(f"Clicked {icon_key} at ({x}, {y})")
                return True
            else:
                self.logger.debug(f"Icon {icon_key} not found")
                return False
                
        except Exception as e:
            self.logger.error(f"Error clicking icon {icon_key}: {e}")
            return False
    
    def _select_chapter(self, chapter: int) -> bool:
        """Select specific chapter in dungeon"""
        try:
            if chapter < 1 or chapter > 5:
                self.logger.error(f"Invalid chapter: {chapter}")
                return False
            
            return self._click_icon(f'chapter_{chapter}')
            
        except Exception as e:
            self.logger.error(f"Error selecting chapter {chapter}: {e}")
            return False
    
    def _start_pvp_battle(self, timeout: float) -> bool:
        """Start PvP battle (implementation depends on UI)"""
        # Placeholder for PvP battle start
        self.logger.info("PvP battle start not implemented")
        return False
    
    def _handle_unknown_screen(self):
        """Handle unknown screen state"""
        try:
            # Try common navigation actions
            img = self.device.get_screenshot()
            if img is None:
                return
            
            # Look for any recognizable buttons
            for icon_key in ['back_button', 'x_mark', 'home_screen']:
                if self._click_icon(icon_key):
                    time.sleep(self.click_delay)
                    return
            
            # If nothing found, try clicking center of screen
            height, width = img.shape[:2]
            self.device.click(width // 2, height // 2)
            
        except Exception as e:
            self.logger.debug(f"Error handling unknown screen: {e}")
    
    def wait_for_screen(self, target_screen: str, timeout: float = 10.0) -> bool:
        """Wait for specific screen to appear"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            current_state = self.detect_current_screen()
            
            if current_state.current_screen == target_screen:
                return True
            
            time.sleep(self.screen_check_delay)
        
        return False
    
    def wait_for_battle_start(self, timeout: float = 30.0) -> bool:
        """Wait for battle to start"""
        return self.wait_for_screen("battle", timeout)
    
    def wait_for_battle_end(self, timeout: float = 300.0) -> bool:
        """Wait for battle to end"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            current_state = self.detect_current_screen()
            
            if not current_state.in_battle:
                return True
            
            time.sleep(self.screen_check_delay)
        
        return False
    
    def collect_rewards(self) -> bool:
        """Collect any available rewards"""
        try:
            img = self.device.get_screenshot()
            if img is None:
                return False
            
            # Look for collect buttons
            collect_found = self.perception.find_icon(img, self.icons['quest_collect'])
            if collect_found:
                x, y = collect_found
                self.device.click(x, y)
                self.logger.info("Collected reward")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error collecting rewards: {e}")
            return False
    
    def get_current_state(self) -> GameState:
        """Get current game state"""
        return self.current_state
    
    def refresh_state(self) -> GameState:
        """Refresh current game state"""
        return self.detect_current_screen()
    
    def is_battle_active(self) -> bool:
        """Check if battle is currently active"""
        current_state = self.detect_current_screen()
        return current_state.in_battle
