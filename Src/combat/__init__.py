"""
Rush Royale Bot - Combat Package
Python 3.13 Compatible

Combat system components:
- Unit merging logic
- Mana management
"""
from __future__ import annotations

from .merge_logic import MergeController
from .mana_management import ManaManager

__all__ = [
    'MergeController',
    'ManaManager',
]
