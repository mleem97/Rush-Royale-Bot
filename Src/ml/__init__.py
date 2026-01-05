"""
Rush Royale Bot - ML Package
Python 3.13 Compatible

Machine learning models and utilities for:
- Unit type recognition
- Rank detection
- Game state analysis
- Future RL components
"""
from __future__ import annotations

from .model_registry import ModelRegistry, ModelMetadata
from .rank_classifier import RankClassifier
from .unit_detector import UnitDetector

__all__ = [
    'ModelRegistry',
    'ModelMetadata',
    'RankClassifier',
    'UnitDetector',
]
