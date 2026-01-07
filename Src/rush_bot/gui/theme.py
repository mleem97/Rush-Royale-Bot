"""
RushBot GUI Theme - Colors and styling configuration.
WCAG-compliant color palette with Dark/Light mode support.
"""
from __future__ import annotations

import customtkinter as ctk


def setup_theme() -> None:
    """Initialize CustomTkinter theme settings."""
    ctk.set_appearance_mode("System")  # "System", "Dark", "Light"
    ctk.set_default_color_theme("blue")  # "blue", "green", "dark-blue"


# Color palette for consistent theming (Light, Dark) - WCAG compliant
# Using #1e1e2e instead of pure black for OLED-friendly dark mode
COLORS: dict[str, tuple[str, str]] = {
    # Layout colors
    "sidebar_bg": ("#e8e8e8", "#1e1e2e"),
    "content_bg": ("#f5f5f5", "#16213e"),
    "card_bg": ("#ffffff", "#2d3250"),
    
    # Semantic colors
    "accent": ("#3b82f6", "#60a5fa"),
    "success": ("#16a34a", "#4ade80"),
    "warning": ("#d97706", "#fbbf24"),
    "danger": ("#dc2626", "#f87171"),
    
    # Text colors
    "text_primary": ("#1f2937", "#f1f5f9"),
    "text_secondary": ("#6b7280", "#94a3b8"),
    
    # Unit colors for grid visualization
    "unit_empty": ("#d1d5db", "#374151"),
    "unit_demon_hunter": ("#7c3aed", "#a78bfa"),
    "unit_dryad": ("#15803d", "#4ade80"),
    "unit_harlequin": ("#db2777", "#f472b6"),
    "unit_chemist": ("#0891b2", "#22d3ee"),
    "unit_knight_statue": ("#b45309", "#fbbf24"),
    "unit_shaman": ("#7c2d12", "#fb923c"),
    "unit_default": ("#6366f1", "#818cf8"),
}


# Unit-specific color mapping
UNIT_COLORS: dict[str, tuple[str, str]] = {
    "demon_hunter": COLORS["unit_demon_hunter"],
    "dryad": COLORS["unit_dryad"],
    "harlequin": COLORS["unit_harlequin"],
    "chemist": COLORS["unit_chemist"],
    "knight_statue": COLORS["unit_knight_statue"],
    "shaman": COLORS["unit_shaman"],
    "empty": COLORS["unit_empty"],
}


def get_color(name: str) -> tuple[str, str]:
    """Get a color tuple by name."""
    return COLORS.get(name, COLORS["accent"])


def get_unit_color(unit_name: str) -> tuple[str, str]:
    """Get a color tuple for a specific unit."""
    return UNIT_COLORS.get(unit_name, COLORS["unit_default"])
