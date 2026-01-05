"""
Rush Royale Bot - Mana Management Module
Python 3.13 Compatible

Handles mana and card upgrades:
- Card level upgrades
- Hero power activation
- Mana efficiency tracking
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..adb_controller import ADBController


class ManaManager:
    """
    Manages mana spending and card upgrades.
    
    Controls:
    - Card upgrade timing
    - Hero power usage
    - Mana efficiency
    """
    
    # Card upgrade button positions
    UPGRADE_POSITIONS = {
        1: (100, 1500),
        2: (200, 1500),
        3: (350, 1500),
        4: (500, 1500),
        5: (650, 1500),
    }
    
    # Hero power button position
    HERO_POWER_POS = (800, 1500)
    
    def __init__(
        self,
        adb: 'ADBController',
        logger: logging.Logger | None = None
    ):
        """
        Initialize mana manager.
        
        Args:
            adb: ADB controller for touch actions
            logger: Optional logger instance
        """
        self.adb = adb
        self.logger = logger or logging.getLogger(__name__)
    
    def upgrade_cards(
        self,
        cards: list[int],
        hero_power: bool = False
    ) -> None:
        """
        Upgrade selected cards.
        
        Args:
            cards: List of card positions (1-5) to upgrade
            hero_power: Also activate hero power
        """
        for card in cards:
            if card in self.UPGRADE_POSITIONS:
                pos = self.UPGRADE_POSITIONS[card]
                self.adb.tap(pos[0], pos[1])
        
        if hero_power:
            self.adb.tap(self.HERO_POWER_POS[0], self.HERO_POWER_POS[1])
    
    # Alias for backward compatibility
    mana_level = upgrade_cards
    
    def use_hero_power(self) -> None:
        """Activate hero power ability."""
        self.adb.tap(self.HERO_POWER_POS[0], self.HERO_POWER_POS[1])
