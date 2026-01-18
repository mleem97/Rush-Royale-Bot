"""Tests for rush_bot.gui module."""

from __future__ import annotations


class TestTheme:
    """Tests for the theme module."""

    def test_colors_dict_exists(self) -> None:
        """Test that COLORS dictionary is defined."""
        from rush_bot.gui.theme import COLORS

        assert isinstance(COLORS, dict)
        assert "sidebar_bg" in COLORS
        assert "accent" in COLORS

    def test_unit_colors_exist(self) -> None:
        """Test that UNIT_COLORS dictionary is defined."""
        from rush_bot.gui.theme import UNIT_COLORS

        assert isinstance(UNIT_COLORS, dict)

    def test_get_color_function(self) -> None:
        """Test get_color helper function."""
        from rush_bot.gui.theme import COLORS
        from rush_bot.gui.theme import get_color

        # Should return color from COLORS dict
        assert get_color("sidebar_bg") == COLORS["sidebar_bg"]

        # Should return default (accent) for unknown keys
        result = get_color("unknown_color")
        assert result == COLORS["accent"]


class TestTabsImport:
    """Tests for tab module imports."""

    def test_all_tabs_importable(self) -> None:
        """Test that all tab classes can be imported."""
        from rush_bot.gui.tabs import AboutTab
        from rush_bot.gui.tabs import CombatTab
        from rush_bot.gui.tabs import ConfigTab
        from rush_bot.gui.tabs import DashboardTab
        from rush_bot.gui.tabs import LogTab
        from rush_bot.gui.tabs import TrainingTab

        # Just verify they're classes
        assert DashboardTab is not None
        assert ConfigTab is not None
        assert TrainingTab is not None
        assert CombatTab is not None
        assert LogTab is not None
        assert AboutTab is not None
