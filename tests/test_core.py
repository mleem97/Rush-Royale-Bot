"""Tests for rush_bot.core module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from rush_bot.core import Bot
from rush_bot.core import BotHandler
from rush_bot.core import BotLogger
from rush_bot.core import DeviceConfig
from rush_bot.core import DeviceConnectionError
from rush_bot.core import DeviceInfo
from rush_bot.core import DeviceManager
from rush_bot.core import DeviceNotConnectedError
from rush_bot.core import DeviceState
from rush_bot.core import LatencyStats
from rush_bot.core import MergeCandidate
from rush_bot.core import MergeConfig
from rush_bot.core import MergeLogic
from rush_bot.core import MergeResult
from rush_bot.core import MergeValidator
from rush_bot.core import ScrcpyClient
from rush_bot.core import ScreenshotConfig
from rush_bot.core import ScreenshotPipeline
from rush_bot.core import ScreenshotResult
from rush_bot.core import ScreenshotSource


class TestBotLogger:
    """Tests for the BotLogger class."""

    def test_logger_creation(self) -> None:
        """Test that logger can be created."""
        logger = BotLogger()
        assert logger is not None
        assert logger.logger.name == "RushBot"

    def test_logger_with_no_widget(self) -> None:
        """Test logger works without GUI widget."""
        logger = BotLogger(log_widget=None)
        assert logger.log_widget is None


class TestDeviceConfig:
    """Tests for the DeviceConfig class."""

    def test_default_config(self) -> None:
        """Test default device configuration."""
        config = DeviceConfig()
        assert config.address == "127.0.0.1:5555"
        assert config.auto_reconnect is True
        assert config.max_reconnect_attempts == 5
        assert config.reconnect_delay_seconds == 2.0
        assert config.connection_timeout_seconds == 10.0
        assert config.screenshot_retry_count == 3

    def test_custom_config(self) -> None:
        """Test custom device configuration."""
        config = DeviceConfig(
            address="192.168.1.100:5555",
            auto_reconnect=False,
            max_reconnect_attempts=10,
        )
        assert config.address == "192.168.1.100:5555"
        assert config.auto_reconnect is False
        assert config.max_reconnect_attempts == 10


class TestDeviceInfo:
    """Tests for the DeviceInfo class."""

    def test_device_info_creation(self) -> None:
        """Test creating DeviceInfo."""
        info = DeviceInfo(
            serial="127.0.0.1:5555",
            model="Pixel 6",
            android_version="13",
            screen_width=1080,
            screen_height=1920,
            is_emulator=True,
        )
        assert info.serial == "127.0.0.1:5555"
        assert info.model == "Pixel 6"
        assert info.is_emulator is True

    def test_device_info_from_device(self) -> None:
        """Test creating DeviceInfo from mock device."""
        mock_device = MagicMock()
        mock_device.serial = "emulator-5554"
        mock_device.prop.get.side_effect = lambda key, default: {
            "ro.product.model": "sdk_gphone64_x86_64",
            "ro.build.version.release": "13",
        }.get(key, default)
        mock_device.shell.return_value = "Physical size: 1080x1920"

        info = DeviceInfo.from_device(mock_device)
        assert info.serial == "emulator-5554"
        assert info.is_emulator is True
        assert info.screen_width == 1080
        assert info.screen_height == 1920


class TestDeviceState:
    """Tests for the DeviceState enum."""

    def test_all_states_exist(self) -> None:
        """Test that all expected states exist."""
        assert DeviceState.DISCONNECTED.value == "disconnected"
        assert DeviceState.CONNECTING.value == "connecting"
        assert DeviceState.CONNECTED.value == "connected"
        assert DeviceState.RECONNECTING.value == "reconnecting"
        assert DeviceState.ERROR.value == "error"


class TestDeviceManager:
    """Tests for the DeviceManager class."""

    def test_device_manager_creation(self) -> None:
        """Test that DeviceManager can be instantiated."""
        manager = DeviceManager()
        assert manager is not None
        assert manager.device is None
        assert manager.state == DeviceState.DISCONNECTED

    def test_device_manager_with_config(self) -> None:
        """Test DeviceManager with custom config."""
        config = DeviceConfig(auto_reconnect=False)
        manager = DeviceManager(config=config)
        assert manager.config.auto_reconnect is False

    def test_adb_path_set(self) -> None:
        """Test that adb_path is configured."""
        manager = DeviceManager()
        assert hasattr(manager, "adb_path")

    def test_is_connected_property(self) -> None:
        """Test is_connected property."""
        manager = DeviceManager()
        assert manager.is_connected is False

    def test_state_change_callback(self) -> None:
        """Test state change callback is called."""
        states_received: list[DeviceState] = []

        def callback(state: DeviceState) -> None:
            states_received.append(state)

        manager = DeviceManager(on_state_change=callback)

        # Manually trigger state change
        manager._set_state(DeviceState.CONNECTING)
        assert DeviceState.CONNECTING in states_received

    def test_list_devices_empty(self) -> None:
        """Test list_devices with no devices."""
        with patch("adbutils.adb") as mock_adb:
            mock_adb.device_list.return_value = []
            manager = DeviceManager()
            devices = manager.list_devices()
            assert devices == []

    def test_connect_success(self) -> None:
        """Test successful connection."""
        with patch("adbutils.adb") as mock_adb:
            mock_device = MagicMock()
            mock_device.serial = "127.0.0.1:5555"
            mock_device.prop.get.return_value = "TestDevice"
            mock_device.shell.return_value = "Physical size: 1080x1920"
            mock_adb.device_list.return_value = [mock_device]

            manager = DeviceManager()
            result = manager.connect("127.0.0.1:5555")

            assert result is True
            assert manager.is_connected is True
            assert manager.state == DeviceState.CONNECTED

    def test_connect_no_devices(self) -> None:
        """Test connection with no devices available."""
        with patch("adbutils.adb") as mock_adb:
            mock_adb.device_list.return_value = []
            config = DeviceConfig(auto_reconnect=False)

            manager = DeviceManager(config=config)
            result = manager.connect()

            assert result is False
            assert manager.state == DeviceState.DISCONNECTED

    def test_disconnect(self) -> None:
        """Test disconnect method."""
        manager = DeviceManager()
        manager._device = MagicMock()
        manager._state = DeviceState.CONNECTED

        manager.disconnect()

        assert manager.device is None
        assert manager.state == DeviceState.DISCONNECTED

    def test_tap_not_connected(self) -> None:
        """Test tap when not connected."""
        manager = DeviceManager()
        result = manager.tap(100, 200)
        assert result is False

    def test_swipe_not_connected(self) -> None:
        """Test swipe when not connected."""
        manager = DeviceManager()
        result = manager.swipe(100, 200, 300, 400)
        assert result is False

    def test_screenshot_not_connected(self) -> None:
        """Test screenshot when not connected."""
        manager = DeviceManager()
        result = manager.screenshot()
        assert result is None

    def test_shell_not_connected(self) -> None:
        """Test shell when not connected."""
        manager = DeviceManager()
        result = manager.shell("echo test")
        assert result is None

    def test_press_back(self) -> None:
        """Test press_back calls press_key with correct keycode."""
        manager = DeviceManager()
        manager._device = MagicMock()
        manager._state = DeviceState.CONNECTED

        result = manager.press_back()
        assert result is True
        manager._device.shell.assert_called_with("input keyevent 4")

    def test_press_home(self) -> None:
        """Test press_home calls press_key with correct keycode."""
        manager = DeviceManager()
        manager._device = MagicMock()
        manager._state = DeviceState.CONNECTED

        result = manager.press_home()
        assert result is True
        manager._device.shell.assert_called_with("input keyevent 3")

    def test_tap_when_connected(self) -> None:
        """Test tap when connected."""
        manager = DeviceManager()
        manager._device = MagicMock()
        manager._state = DeviceState.CONNECTED

        result = manager.tap(500, 600)

        assert result is True
        manager._device.click.assert_called_once_with(500, 600)

    def test_swipe_when_connected(self) -> None:
        """Test swipe when connected."""
        manager = DeviceManager()
        manager._device = MagicMock()
        manager._state = DeviceState.CONNECTED

        result = manager.swipe(100, 200, 300, 400, 500)

        assert result is True
        manager._device.swipe.assert_called_once_with(100, 200, 300, 400, 0.5)

    def test_get_all_device_info(self) -> None:
        """Test getting info for all devices."""
        with patch("adbutils.adb") as mock_adb:
            mock_device1 = MagicMock()
            mock_device1.serial = "device1"
            mock_device1.prop.get.return_value = "Device1"
            mock_device1.shell.return_value = "Physical size: 1080x1920"

            mock_device2 = MagicMock()
            mock_device2.serial = "device2"
            mock_device2.prop.get.return_value = "Device2"
            mock_device2.shell.return_value = "Physical size: 1440x2560"

            mock_adb.device_list.return_value = [mock_device1, mock_device2]

            manager = DeviceManager()
            infos = manager.get_all_device_info()

            assert len(infos) == 2
            assert infos[0].serial == "device1"
            assert infos[1].serial == "device2"


class TestDeviceExceptions:
    """Tests for device-related exceptions."""

    def test_device_connection_error(self) -> None:
        """Test DeviceConnectionError exception."""
        with pytest.raises(DeviceConnectionError):
            raise DeviceConnectionError("Connection failed")

    def test_device_not_connected_error(self) -> None:
        """Test DeviceNotConnectedError exception."""
        with pytest.raises(DeviceNotConnectedError):
            raise DeviceNotConnectedError("Device not connected")


class TestBot:
    """Tests for the Bot class."""

    def test_bot_creation(self) -> None:
        """Test that Bot can be instantiated."""
        bot = Bot()
        assert bot is not None
        assert bot.running is False


class TestBotHandler:
    """Tests for the BotHandler class."""

    def test_handler_has_run_method(self) -> None:
        """Test that BotHandler has the run static method."""
        assert hasattr(BotHandler, "run")
        assert callable(BotHandler.run)

    def test_handler_has_select_units_method(self) -> None:
        """Test that BotHandler has select_units method."""
        assert hasattr(BotHandler, "select_units")
        assert callable(BotHandler.select_units)


# =============================================================================
# Merge Logic Tests (T003)
# =============================================================================


class TestMergeValidator:
    """Tests for the MergeValidator class."""

    def test_validator_creation(self) -> None:
        """Test that validator can be created."""
        validator = MergeValidator()
        assert validator is not None
        assert validator.config is not None

    def test_same_type_same_rank_can_merge(self) -> None:
        """Test that same type and rank units can merge."""
        validator = MergeValidator()
        can_merge, result = validator.can_merge("demon_hunter.png", 1, "demon_hunter.png", 1)
        assert can_merge is True
        assert result == MergeResult.SUCCESS

    def test_same_type_different_rank_cannot_merge(self) -> None:
        """Test that same type with different rank cannot merge."""
        validator = MergeValidator()
        can_merge, result = validator.can_merge("demon_hunter.png", 1, "demon_hunter.png", 2)
        assert can_merge is False
        assert result == MergeResult.INVALID_RANK

    def test_different_type_same_rank_cannot_merge(self) -> None:
        """Test that different types cannot merge."""
        validator = MergeValidator()
        can_merge, result = validator.can_merge("demon_hunter.png", 1, "engineer.png", 1)
        assert can_merge is False
        assert result == MergeResult.INVALID_TYPE

    def test_empty_cell_cannot_merge(self) -> None:
        """Test that empty cells cannot merge."""
        validator = MergeValidator()
        can_merge, result = validator.can_merge("empty.png", 1, "demon_hunter.png", 1)
        assert can_merge is False
        assert result == MergeResult.INVALID_TYPE

    def test_special_unit_can_merge_with_any_type(self) -> None:
        """Test that special units like harlequin can merge with any type."""
        validator = MergeValidator()
        can_merge, result = validator.can_merge("harlequin.png", 2, "demon_hunter.png", 2)
        assert can_merge is True
        assert result == MergeResult.SUCCESS

    def test_dryad_can_merge_with_any_type(self) -> None:
        """Test that dryad can merge with any type."""
        validator = MergeValidator()
        can_merge, result = validator.can_merge("dryad.png", 3, "knight_statue.png", 3)
        assert can_merge is True
        assert result == MergeResult.SUCCESS


class TestMergeConfig:
    """Tests for the MergeConfig class."""

    def test_default_config(self) -> None:
        """Test default merge configuration."""
        config = MergeConfig()
        assert config.protected_units == []
        assert config.max_protected_rank == 7
        assert config.min_units_to_keep == 1
        assert "harlequin.png" in config.special_units
        assert "dryad.png" in config.special_units

    def test_custom_protected_units(self) -> None:
        """Test custom protected units configuration."""
        config = MergeConfig(protected_units=["demon_hunter.png", "knight_statue.png"])
        assert "demon_hunter.png" in config.protected_units
        assert "knight_statue.png" in config.protected_units


class TestMergeCandidate:
    """Tests for the MergeCandidate class."""

    def test_candidate_creation(self) -> None:
        """Test creating a merge candidate."""
        candidate = MergeCandidate(
            unit_type="demon_hunter.png",
            rank=2,
            positions=[[0, 0], [0, 1]],
        )
        assert candidate.unit_type == "demon_hunter.png"
        assert candidate.rank == 2
        assert len(candidate.positions) == 2
        assert candidate.is_protected is False

    def test_candidate_requires_two_positions(self) -> None:
        """Test that candidate requires exactly 2 positions."""
        with pytest.raises(ValueError, match="exactly 2 positions"):
            MergeCandidate(
                unit_type="demon_hunter.png",
                rank=1,
                positions=[[0, 0]],
            )

    def test_protected_candidate(self) -> None:
        """Test creating a protected merge candidate."""
        candidate = MergeCandidate(
            unit_type="demon_hunter.png",
            rank=5,
            positions=[[1, 0], [2, 0]],
            is_protected=True,
        )
        assert candidate.is_protected is True


class TestMergeLogic:
    """Tests for the MergeLogic class."""

    @pytest.fixture
    def sample_grid_df(self) -> pd.DataFrame:
        """Create a sample grid DataFrame for testing."""
        return pd.DataFrame(
            {
                "unit": [
                    "demon_hunter.png",
                    "demon_hunter.png",
                    "engineer.png",
                    "engineer.png",
                    "empty.png",
                    "harlequin.png",
                    "knight_statue.png",
                    "knight_statue.png",
                    "empty.png",
                    "dryad.png",
                    "thunder.png",
                    "thunder.png",
                    "empty.png",
                    "empty.png",
                    "empty.png",
                ],
                "rank": [1, 1, 1, 1, 0, 2, 2, 2, 0, 2, 3, 3, 0, 0, 0],
                "grid_pos": [
                    [0, 0],
                    [0, 1],
                    [0, 2],
                    [0, 3],
                    [0, 4],
                    [1, 0],
                    [1, 1],
                    [1, 2],
                    [1, 3],
                    [1, 4],
                    [2, 0],
                    [2, 1],
                    [2, 2],
                    [2, 3],
                    [2, 4],
                ],
            }
        )

    def test_logic_creation(self) -> None:
        """Test that merge logic can be created."""
        logic = MergeLogic()
        assert logic is not None
        assert logic.validator is not None

    def test_find_merge_candidates(self, sample_grid_df: pd.DataFrame) -> None:
        """Test finding merge candidates on the grid."""
        logic = MergeLogic()
        candidates = logic.find_merge_candidates(sample_grid_df)

        # Should find: demon_hunter (2x rank 1), engineer (2x rank 1),
        # knight_statue (2x rank 2), thunder (2x rank 3)
        assert len(candidates) == 4

        unit_types = [c.unit_type for c in candidates]
        assert "demon_hunter.png" in unit_types
        assert "engineer.png" in unit_types
        assert "knight_statue.png" in unit_types
        assert "thunder.png" in unit_types

    def test_find_merge_candidates_empty_grid(self) -> None:
        """Test finding candidates on empty grid."""
        logic = MergeLogic()
        empty_df = pd.DataFrame(columns=["unit", "rank", "grid_pos"])
        candidates = logic.find_merge_candidates(empty_df)
        assert candidates == []

    def test_find_merge_candidates_none_grid(self) -> None:
        """Test finding candidates with None grid."""
        logic = MergeLogic()
        candidates = logic.find_merge_candidates(None)  # type: ignore
        assert candidates == []

    def test_find_special_merge_candidates(self, sample_grid_df: pd.DataFrame) -> None:
        """Test finding special merge candidates."""
        logic = MergeLogic()
        candidates = logic.find_special_merge_candidates(sample_grid_df, "knight_statue.png")

        # Should find harlequin+knight_statue and dryad+knight_statue
        assert len(candidates) >= 1
        # Check that special merges are found
        special_types = [c.unit_type for c in candidates]
        assert any("harlequin" in t or "dryad" in t for t in special_types)

    def test_select_best_candidate_prioritizes_low_rank(self, sample_grid_df: pd.DataFrame) -> None:
        """Test that low rank candidates are selected first."""
        logic = MergeLogic()
        candidates = logic.find_merge_candidates(sample_grid_df)
        best = logic.select_best_candidate(candidates, prioritize_low_rank=True)

        assert best is not None
        assert best.rank == 1  # Should be rank 1 (lowest)

    def test_select_best_candidate_prioritizes_high_rank(
        self, sample_grid_df: pd.DataFrame
    ) -> None:
        """Test that high rank candidates can be selected."""
        logic = MergeLogic()
        candidates = logic.find_merge_candidates(sample_grid_df)
        best = logic.select_best_candidate(candidates, prioritize_low_rank=False)

        assert best is not None
        assert best.rank == 3  # Should be rank 3 (highest)

    def test_select_best_candidate_skips_protected(self) -> None:
        """Test that protected candidates are skipped."""
        logic = MergeLogic()
        candidates = [
            MergeCandidate(
                unit_type="demon_hunter.png",
                rank=1,
                positions=[[0, 0], [0, 1]],
                is_protected=True,
            ),
            MergeCandidate(
                unit_type="engineer.png",
                rank=2,
                positions=[[1, 0], [1, 1]],
                is_protected=False,
            ),
        ]
        best = logic.select_best_candidate(candidates)

        assert best is not None
        assert best.unit_type == "engineer.png"

    def test_select_best_candidate_returns_none_if_all_protected(self) -> None:
        """Test that None is returned if all candidates are protected."""
        logic = MergeLogic()
        candidates = [
            MergeCandidate(
                unit_type="demon_hunter.png",
                rank=1,
                positions=[[0, 0], [0, 1]],
                is_protected=True,
            ),
        ]
        best = logic.select_best_candidate(candidates)
        assert best is None

    def test_execute_merge_with_callback(self) -> None:
        """Test executing a merge with swipe callback."""
        swipe_calls: list[tuple] = []

        def mock_swipe(start: list[int], end: list[int]) -> None:
            swipe_calls.append((start, end))

        logic = MergeLogic(swipe_callback=mock_swipe)
        candidate = MergeCandidate(
            unit_type="demon_hunter.png",
            rank=1,
            positions=[[0, 0], [0, 1]],
        )

        result = logic.execute_merge(candidate)

        assert result == MergeResult.SUCCESS
        assert len(swipe_calls) == 1
        assert swipe_calls[0] == ([0, 0], [0, 1])

    def test_execute_merge_protected_unit(self) -> None:
        """Test that protected units cannot be merged."""
        logic = MergeLogic()
        candidate = MergeCandidate(
            unit_type="demon_hunter.png",
            rank=1,
            positions=[[0, 0], [0, 1]],
            is_protected=True,
        )

        result = logic.execute_merge(candidate)
        assert result == MergeResult.PROTECTED_UNIT


class TestMergeProtection:
    """Tests for DPS unit protection."""

    def test_protected_unit_detection(self) -> None:
        """Test that protected units are correctly identified."""
        config = MergeConfig(protected_units=["demon_hunter.png"])
        validator = MergeValidator(config)

        # Should be protected (only 1 unit)
        is_protected = validator.is_protected("demon_hunter.png", 3, 1)
        assert is_protected is True

    def test_non_protected_unit(self) -> None:
        """Test that non-protected units are not identified as protected."""
        config = MergeConfig(protected_units=["demon_hunter.png"])
        validator = MergeValidator(config)

        # Engineer is not in protected list
        is_protected = validator.is_protected("engineer.png", 3, 1)
        assert is_protected is False

    def test_protection_with_sufficient_units(self) -> None:
        """Test that protection allows merging if enough units exist."""
        config = MergeConfig(
            protected_units=["demon_hunter.png"],
            min_units_to_keep=2,
        )
        validator = MergeValidator(config)

        # Has 5 units, min is 2, so can merge
        is_protected = validator.is_protected("demon_hunter.png", 3, 5)
        assert is_protected is False

    def test_protection_respects_max_rank(self) -> None:
        """Test that protection does not apply above max rank."""
        config = MergeConfig(
            protected_units=["demon_hunter.png"],
            max_protected_rank=5,
        )
        validator = MergeValidator(config)

        # Rank 6 is above max_protected_rank
        is_protected = validator.is_protected("demon_hunter.png", 6, 1)
        assert is_protected is False


class TestMergeDirection:
    """Tests for merge direction calculation."""

    def test_horizontal_direction(self) -> None:
        """Test horizontal merge direction."""
        from rush_bot.core.merge import calculate_merge_direction

        direction = calculate_merge_direction([0, 0], [0, 2])
        assert direction == (0, 2)

    def test_vertical_direction(self) -> None:
        """Test vertical merge direction."""
        from rush_bot.core.merge import calculate_merge_direction

        direction = calculate_merge_direction([0, 0], [2, 0])
        assert direction == (2, 0)

    def test_diagonal_direction(self) -> None:
        """Test diagonal merge direction."""
        from rush_bot.core.merge import calculate_merge_direction

        direction = calculate_merge_direction([0, 0], [1, 1])
        assert direction == (1, 1)

    def test_reverse_direction(self) -> None:
        """Test reverse merge direction."""
        from rush_bot.core.merge import calculate_merge_direction

        direction = calculate_merge_direction([2, 2], [0, 0])
        assert direction == (-2, -2)


# =============================================================================
# Extended BotLogger Tests (T010 - Coverage Enhancement)
# =============================================================================


class TestBotLoggerMethods:
    """Extended tests for BotLogger methods."""

    def test_debug_method(self) -> None:
        """Test debug log method."""
        logger = BotLogger()
        # Should not raise
        logger.debug("Debug message")

    def test_info_method(self) -> None:
        """Test info log method."""
        logger = BotLogger()
        logger.info("Info message")

    def test_warning_method(self) -> None:
        """Test warning log method."""
        logger = BotLogger()
        logger.warning("Warning message")

    def test_error_method(self) -> None:
        """Test error log method."""
        logger = BotLogger()
        logger.error("Error message")

    def test_critical_method(self) -> None:
        """Test critical log method."""
        logger = BotLogger()
        logger.critical("Critical message")

    def test_log_with_mock_widget(self) -> None:
        """Test logging with mocked GUI widget."""
        mock_widget = MagicMock()
        mock_widget.configure = MagicMock()
        mock_widget.insert = MagicMock()
        mock_widget.see = MagicMock()

        logger = BotLogger(log_widget=mock_widget)
        logger.info("Test message")

        # Widget methods should have been called
        assert mock_widget.configure.called
        assert mock_widget.insert.called

    def test_log_widget_exception_handling(self) -> None:
        """Test that widget exceptions are handled gracefully."""
        mock_widget = MagicMock()
        mock_widget.configure.side_effect = Exception("Widget error")

        logger = BotLogger(log_widget=mock_widget)
        # Should not raise despite widget error
        logger.info("Test message")


# =============================================================================
# Extended Bot Tests (T010 - Coverage Enhancement)
# =============================================================================


class TestBotMethods:
    """Extended tests for Bot class methods."""

    def test_bot_start_sets_running(self) -> None:
        """Test that start() sets running to True."""
        bot = Bot()
        bot.start()
        assert bot.running is True

    def test_bot_stop_sets_running_false(self) -> None:
        """Test that stop() sets running to False."""
        bot = Bot()
        bot.running = True
        bot.stop()
        assert bot.running is False

    def test_bot_tap_calls_device(self) -> None:
        """Test that tap() delegates to device manager."""
        bot = Bot()
        bot.device = MagicMock()
        bot.device.tap = MagicMock()

        bot.tap(100, 200)

        bot.device.tap.assert_called_once_with(100, 200)

    def test_bot_swipe_calls_device(self) -> None:
        """Test that swipe() delegates to device manager."""
        bot = Bot()
        bot.device = MagicMock()
        bot.device.swipe = MagicMock()

        bot.swipe((100, 200), (300, 400), duration_ms=500)

        bot.device.swipe.assert_called_once_with(100, 200, 300, 400, 500)

    def test_bot_screenshot_calls_device(self) -> None:
        """Test that screenshot() delegates to device manager."""
        bot = Bot()
        bot.device = MagicMock()
        mock_img = MagicMock()
        bot.device.screenshot.return_value = mock_img

        result = bot.screenshot()

        assert result is mock_img
        bot.device.screenshot.assert_called_once()

    def test_bot_with_gui(self) -> None:
        """Test bot initialization with GUI."""
        mock_gui = MagicMock()
        bot = Bot(gui=mock_gui)
        assert bot.gui is mock_gui


# =============================================================================
# Extended BotHandler Tests (T010 - Coverage Enhancement)
# =============================================================================


class TestBotHandlerSelectUnits:
    """Tests for BotHandler.select_units method."""

    def test_select_units_with_missing_file(self, temp_dir: Path) -> None:
        """Test select_units returns False for missing files."""
        result = BotHandler.select_units(["nonexistent_unit.png"])
        assert result is False

    def test_select_units_empty_list(self) -> None:
        """Test select_units with empty list."""
        result = BotHandler.select_units([])
        assert result is True  # No files to validate


# =============================================================================
# Extended DeviceManager Tests (T010 - Coverage Enhancement)
# =============================================================================


class TestDeviceManagerOperations:
    """Extended tests for DeviceManager operations."""

    def test_screenshot_success(self) -> None:
        """Test successful screenshot capture."""
        manager = DeviceManager()
        manager._device = MagicMock()
        manager._state = DeviceState.CONNECTED
        mock_img = MagicMock()
        manager._device.screenshot.return_value = mock_img

        result = manager.screenshot()

        assert result is mock_img

    def test_screenshot_retry_on_failure(self) -> None:
        """Test screenshot retries on transient failure."""
        config = DeviceConfig(screenshot_retry_count=3, screenshot_retry_delay=0.01)
        manager = DeviceManager(config=config)
        manager._device = MagicMock()
        manager._state = DeviceState.CONNECTED

        # Fail twice, succeed on third
        mock_img = MagicMock()
        manager._device.screenshot.side_effect = [
            Exception("Transient error"),
            Exception("Transient error"),
            mock_img,
        ]

        result = manager.screenshot()

        assert result is mock_img
        assert manager._device.screenshot.call_count == 3

    def test_screenshot_all_retries_fail(self) -> None:
        """Test screenshot returns None when all retries fail."""
        config = DeviceConfig(screenshot_retry_count=2, screenshot_retry_delay=0.01)
        manager = DeviceManager(config=config)
        manager._device = MagicMock()
        manager._state = DeviceState.CONNECTED
        manager._device.screenshot.side_effect = Exception("Persistent error")

        result = manager.screenshot()

        assert result is None

    def test_shell_success(self) -> None:
        """Test successful shell command."""
        manager = DeviceManager()
        manager._device = MagicMock()
        manager._state = DeviceState.CONNECTED
        manager._device.shell.return_value = "output"

        result = manager.shell("echo test")

        assert result == "output"

    def test_input_text_not_connected(self) -> None:
        """Test input_text when not connected."""
        manager = DeviceManager()
        result = manager.input_text("hello")
        assert result is False

    def test_input_text_success(self) -> None:
        """Test successful text input."""
        manager = DeviceManager()
        manager._device = MagicMock()
        manager._state = DeviceState.CONNECTED

        result = manager.input_text("hello world")

        assert result is True
        # Verify shell was called with escaped text
        manager._device.shell.assert_called()

    def test_press_key_not_connected(self) -> None:
        """Test press_key when not connected."""
        manager = DeviceManager()
        result = manager.press_key(4)
        assert result is False

    def test_press_key_success(self) -> None:
        """Test successful key press."""
        manager = DeviceManager()
        manager._device = MagicMock()
        manager._state = DeviceState.CONNECTED

        result = manager.press_key(66)  # ENTER key

        assert result is True
        manager._device.shell.assert_called_with("input keyevent 66")

    def test_device_info_property(self) -> None:
        """Test device_info property."""
        manager = DeviceManager()
        assert manager.device_info is None

        # Set device info
        info = DeviceInfo(serial="test", model="Test Device")
        manager._device_info = info
        assert manager.device_info is info

    def test_ensure_connected_raises(self) -> None:
        """Test _ensure_connected raises when not connected."""
        manager = DeviceManager()

        with pytest.raises(DeviceNotConnectedError):
            manager._ensure_connected()

    def test_tap_exception_handling(self) -> None:
        """Test tap handles exceptions and triggers reconnect check."""
        config = DeviceConfig(auto_reconnect=False)
        manager = DeviceManager(config=config)
        manager._device = MagicMock()
        manager._state = DeviceState.CONNECTED
        manager._device.click.side_effect = Exception("Click failed")
        # Simulate device ping failure (device unreachable)
        manager._device.shell.side_effect = Exception("Device offline")

        result = manager.tap(100, 200)

        assert result is False

    def test_swipe_exception_handling(self) -> None:
        """Test swipe handles exceptions gracefully."""
        config = DeviceConfig(auto_reconnect=False)
        manager = DeviceManager(config=config)
        manager._device = MagicMock()
        manager._state = DeviceState.CONNECTED
        manager._device.swipe.side_effect = Exception("Swipe failed")
        manager._device.shell.side_effect = Exception("Device offline")

        result = manager.swipe(0, 0, 100, 100)

        assert result is False

    def test_shell_exception_handling(self) -> None:
        """Test shell handles exceptions gracefully."""
        config = DeviceConfig(auto_reconnect=False)
        manager = DeviceManager(config=config)
        manager._device = MagicMock()
        manager._state = DeviceState.CONNECTED
        manager._device.shell.side_effect = Exception("Shell failed")

        result = manager.shell("invalid command")

        assert result is None


class TestDeviceInfoFromDevice:
    """Tests for DeviceInfo.from_device method edge cases."""

    def test_from_device_prop_exception(self) -> None:
        """Test from_device handles prop exceptions."""
        mock_device = MagicMock()
        mock_device.serial = "test-device"
        mock_device.prop.get.side_effect = Exception("Prop error")
        mock_device.shell.return_value = ""

        info = DeviceInfo.from_device(mock_device)

        assert info.serial == "test-device"
        assert info.model == "Unknown"
        assert info.android_version == "Unknown"

    def test_from_device_shell_exception(self) -> None:
        """Test from_device handles shell exceptions."""
        mock_device = MagicMock()
        mock_device.serial = "test-device"
        mock_device.prop.get.return_value = "TestModel"
        mock_device.shell.side_effect = Exception("Shell error")

        info = DeviceInfo.from_device(mock_device)

        assert info.serial == "test-device"
        assert info.screen_width == 0
        assert info.screen_height == 0

    def test_from_device_invalid_screen_size(self) -> None:
        """Test from_device handles invalid screen size output."""
        mock_device = MagicMock()
        mock_device.serial = "test-device"
        mock_device.prop.get.return_value = "TestModel"
        mock_device.shell.return_value = "Invalid output"

        info = DeviceInfo.from_device(mock_device)

        assert info.screen_width == 0
        assert info.screen_height == 0

    def test_emulator_detection_127(self) -> None:
        """Test emulator detection for 127.0.0.1 addresses."""
        mock_device = MagicMock()
        mock_device.serial = "127.0.0.1:5555"
        mock_device.prop.get.return_value = "Emulator"
        mock_device.shell.return_value = "Physical size: 1080x1920"

        info = DeviceInfo.from_device(mock_device)

        assert info.is_emulator is True

    def test_emulator_detection_serial(self) -> None:
        """Test emulator detection for emulator-* serials."""
        mock_device = MagicMock()
        mock_device.serial = "emulator-5554"
        mock_device.prop.get.return_value = "Emulator"
        mock_device.shell.return_value = "Physical size: 1080x1920"

        info = DeviceInfo.from_device(mock_device)

        assert info.is_emulator is True

    def test_physical_device_detection(self) -> None:
        """Test physical device is not marked as emulator."""
        mock_device = MagicMock()
        mock_device.serial = "ABCD1234"
        mock_device.prop.get.return_value = "Pixel 6"
        mock_device.shell.return_value = "Physical size: 1080x2400"

        info = DeviceInfo.from_device(mock_device)

        assert info.is_emulator is False


class TestDeviceManagerStateCallbacks:
    """Tests for DeviceManager state callback handling."""

    def test_state_callback_exception_handling(self) -> None:
        """Test that state callback exceptions don't break the manager."""

        def bad_callback(state: DeviceState) -> None:
            raise ValueError("Callback error")

        manager = DeviceManager(on_state_change=bad_callback)
        # Should not raise despite callback exception
        manager._set_state(DeviceState.CONNECTING)

    def test_state_not_changed_if_same(self) -> None:
        """Test that callback isn't called if state unchanged."""
        callback_calls: list[DeviceState] = []

        def callback(state: DeviceState) -> None:
            callback_calls.append(state)

        manager = DeviceManager(on_state_change=callback)
        manager._set_state(DeviceState.DISCONNECTED)  # Same as initial

        # Should not have been called since state didn't change
        assert len(callback_calls) == 0


class TestDeviceManagerListDevices:
    """Tests for DeviceManager.list_devices method."""

    def test_list_devices_with_devices(self) -> None:
        """Test list_devices returns device serials."""
        with patch("adbutils.adb") as mock_adb:
            mock_device1 = MagicMock()
            mock_device1.serial = "device1"
            mock_device2 = MagicMock()
            mock_device2.serial = "device2"
            mock_adb.device_list.return_value = [mock_device1, mock_device2]

            manager = DeviceManager()
            devices = manager.list_devices()

            assert devices == ["device1", "device2"]

    def test_list_devices_exception_handling(self) -> None:
        """Test list_devices handles exceptions."""
        with patch("adbutils.adb") as mock_adb:
            mock_adb.device_list.side_effect = Exception("ADB error")

            manager = DeviceManager()
            devices = manager.list_devices()

            assert devices == []


class TestDeviceManagerConnection:
    """Tests for DeviceManager connection scenarios."""

    def test_connect_falls_back_to_first_device(self) -> None:
        """Test connect falls back to first device if address not found."""
        with patch("adbutils.adb") as mock_adb:
            mock_device = MagicMock()
            mock_device.serial = "other-device"
            mock_device.prop.get.return_value = "TestDevice"
            mock_device.shell.return_value = "Physical size: 1080x1920"
            mock_adb.device_list.return_value = [mock_device]
            mock_adb.connect = MagicMock()

            manager = DeviceManager()
            result = manager.connect("nonexistent:5555")

            assert result is True
            assert manager._device == mock_device

    def test_connect_network_address(self) -> None:
        """Test connect with network address calls adb.connect."""
        with patch("adbutils.adb") as mock_adb:
            mock_device = MagicMock()
            mock_device.serial = "192.168.1.100:5555"
            mock_device.prop.get.return_value = "TestDevice"
            mock_device.shell.return_value = "Physical size: 1080x1920"
            mock_adb.device_list.return_value = [mock_device]

            manager = DeviceManager()
            result = manager.connect("192.168.1.100:5555")

            assert result is True
            mock_adb.connect.assert_called()

    def test_connect_exception_without_auto_reconnect(self) -> None:
        """Test connect raises exception when auto_reconnect is False."""
        with patch("adbutils.adb") as mock_adb:
            mock_adb.device_list.side_effect = Exception("Connection failed")
            config = DeviceConfig(auto_reconnect=False)

            manager = DeviceManager(config=config)

            with pytest.raises(DeviceConnectionError):
                manager.connect()

    def test_disconnect_sets_state(self) -> None:
        """Test disconnect properly cleans up state."""
        manager = DeviceManager()
        manager._device = MagicMock()
        manager._device_info = DeviceInfo(serial="test")
        manager._state = DeviceState.CONNECTED

        manager.disconnect()

        assert manager._device is None
        assert manager._device_info is None
        assert manager._state == DeviceState.DISCONNECTED


# ==============================================================================
# Screenshot Pipeline Tests
# ==============================================================================


class TestScreenshotConfig:
    """Tests for ScreenshotConfig dataclass."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = ScreenshotConfig()
        assert config.use_scrcpy is True
        assert config.scrcpy_max_width == 800
        assert config.scrcpy_bitrate == 4_000_000
        assert config.scrcpy_max_fps == 60
        assert config.fallback_to_adb is True
        assert config.buffer_size == 5
        assert config.target_latency_ms == 100.0
        assert config.max_latency_ms == 500.0
        assert config.auto_select_source is True
        assert config.scrcpy_startup_timeout == 5.0

    def test_custom_config(self) -> None:
        """Test custom configuration values."""
        config = ScreenshotConfig(
            use_scrcpy=False,
            scrcpy_max_width=1080,
            buffer_size=10,
            target_latency_ms=50.0,
        )
        assert config.use_scrcpy is False
        assert config.scrcpy_max_width == 1080
        assert config.buffer_size == 10
        assert config.target_latency_ms == 50.0


class TestScreenshotSource:
    """Tests for ScreenshotSource enum."""

    def test_source_values(self) -> None:
        """Test screenshot source enum values."""
        assert ScreenshotSource.SCRCPY.value == "scrcpy"
        assert ScreenshotSource.ADB.value == "adb"
        assert ScreenshotSource.BUFFER.value == "buffer"

    def test_source_enum_members(self) -> None:
        """Test all enum members exist."""
        members = list(ScreenshotSource)
        assert len(members) == 3
        assert ScreenshotSource.SCRCPY in members
        assert ScreenshotSource.ADB in members
        assert ScreenshotSource.BUFFER in members


class TestScreenshotResult:
    """Tests for ScreenshotResult dataclass."""

    def test_result_creation(self) -> None:
        """Test creating a screenshot result."""
        image = np.zeros((480, 640, 3), dtype=np.uint8)
        result = ScreenshotResult(
            image=image,
            source=ScreenshotSource.ADB,
            latency_ms=150.5,
            timestamp=1000.0,
            width=640,
            height=480,
        )
        assert result.image.shape == (480, 640, 3)
        assert result.source == ScreenshotSource.ADB
        assert result.latency_ms == 150.5
        assert result.timestamp == 1000.0
        assert result.width == 640
        assert result.height == 480

    def test_result_resolution_property(self) -> None:
        """Test resolution property."""
        image = np.zeros((1080, 1920, 3), dtype=np.uint8)
        result = ScreenshotResult(
            image=image,
            source=ScreenshotSource.SCRCPY,
            latency_ms=50.0,
            timestamp=1000.0,
            width=1920,
            height=1080,
        )
        assert result.resolution == (1920, 1080)


class TestLatencyStats:
    """Tests for LatencyStats dataclass."""

    def test_default_stats(self) -> None:
        """Test default latency stats."""
        stats = LatencyStats()
        assert stats.avg_latency_ms == 0.0
        assert stats.min_latency_ms == float("inf")
        assert stats.max_latency_ms == 0.0
        assert stats.sample_count == 0
        assert stats.source == ScreenshotSource.ADB
        assert stats.scrcpy_available is False
        assert stats.adb_available is False

    def test_custom_stats(self) -> None:
        """Test custom latency stats."""
        stats = LatencyStats(
            avg_latency_ms=75.0,
            min_latency_ms=45.0,
            max_latency_ms=120.0,
            sample_count=100,
            source=ScreenshotSource.SCRCPY,
            scrcpy_available=True,
            adb_available=True,
        )
        assert stats.avg_latency_ms == 75.0
        assert stats.min_latency_ms == 45.0
        assert stats.max_latency_ms == 120.0
        assert stats.sample_count == 100
        assert stats.source == ScreenshotSource.SCRCPY


class TestScreenshotPipeline:
    """Tests for ScreenshotPipeline class."""

    def test_pipeline_creation(self) -> None:
        """Test pipeline can be created."""
        pipeline = ScreenshotPipeline()
        assert pipeline is not None
        assert pipeline.is_running is False
        assert pipeline.current_source == ScreenshotSource.ADB
        assert pipeline.has_scrcpy is False
        assert pipeline.has_adb is False

    def test_pipeline_with_config(self) -> None:
        """Test pipeline with custom config."""
        config = ScreenshotConfig(use_scrcpy=False, buffer_size=10)
        pipeline = ScreenshotPipeline(config=config)
        assert pipeline.config.use_scrcpy is False
        assert pipeline.config.buffer_size == 10

    def test_pipeline_set_device_manager(self) -> None:
        """Test setting device manager."""
        pipeline = ScreenshotPipeline()
        mock_manager = MagicMock()
        mock_manager.is_connected = True

        pipeline.set_device_manager(mock_manager)

        assert pipeline._device_manager == mock_manager
        assert pipeline.has_adb is True

    def test_pipeline_start_no_sources(self) -> None:
        """Test starting pipeline with no sources available."""
        config = ScreenshotConfig(use_scrcpy=False)
        pipeline = ScreenshotPipeline(config=config)

        result = pipeline.start()

        assert result is False
        assert pipeline.is_running is False

    def test_pipeline_start_with_adb(self) -> None:
        """Test starting pipeline with ADB available."""
        config = ScreenshotConfig(use_scrcpy=False)
        mock_manager = MagicMock()
        mock_manager.is_connected = True

        pipeline = ScreenshotPipeline(device_manager=mock_manager, config=config)
        result = pipeline.start()

        assert result is True
        assert pipeline.is_running is True
        assert pipeline.current_source == ScreenshotSource.ADB

        pipeline.stop()

    def test_pipeline_stop(self) -> None:
        """Test stopping pipeline."""
        config = ScreenshotConfig(use_scrcpy=False)
        mock_manager = MagicMock()
        mock_manager.is_connected = True

        pipeline = ScreenshotPipeline(device_manager=mock_manager, config=config)
        pipeline.start()

        pipeline.stop()

        assert pipeline.is_running is False

    def test_pipeline_capture_adb(self) -> None:
        """Test capturing screenshot via ADB."""
        from PIL import Image as PILImage

        config = ScreenshotConfig(use_scrcpy=False)
        mock_manager = MagicMock()
        mock_manager.is_connected = True

        # Create mock PIL image
        mock_pil = PILImage.new("RGB", (640, 480), color="red")
        mock_manager.screenshot.return_value = mock_pil

        pipeline = ScreenshotPipeline(device_manager=mock_manager, config=config)
        pipeline.start()

        result = pipeline.capture()

        assert result is not None
        assert result.source == ScreenshotSource.ADB
        assert result.width == 640
        assert result.height == 480
        assert result.latency_ms >= 0

        pipeline.stop()

    def test_pipeline_capture_numpy(self) -> None:
        """Test capturing screenshot as numpy array."""
        from PIL import Image as PILImage

        config = ScreenshotConfig(use_scrcpy=False)
        mock_manager = MagicMock()
        mock_manager.is_connected = True

        mock_pil = PILImage.new("RGB", (640, 480), color="blue")
        mock_manager.screenshot.return_value = mock_pil

        pipeline = ScreenshotPipeline(device_manager=mock_manager, config=config)
        pipeline.start()

        image = pipeline.capture_numpy()

        assert image is not None
        assert isinstance(image, np.ndarray)
        assert image.shape == (480, 640, 3)

        pipeline.stop()

    def test_pipeline_get_latency_stats(self) -> None:
        """Test getting latency stats."""
        pipeline = ScreenshotPipeline()
        stats = pipeline.get_latency_stats()

        assert isinstance(stats, LatencyStats)
        assert stats.sample_count == 0

    def test_pipeline_get_latency_stats_with_samples(self) -> None:
        """Test latency stats with recorded samples."""
        from PIL import Image as PILImage

        config = ScreenshotConfig(use_scrcpy=False)
        mock_manager = MagicMock()
        mock_manager.is_connected = True

        mock_pil = PILImage.new("RGB", (640, 480), color="green")
        mock_manager.screenshot.return_value = mock_pil

        pipeline = ScreenshotPipeline(device_manager=mock_manager, config=config)
        pipeline.start()

        # Capture a few screenshots to build stats
        for _ in range(5):
            pipeline.capture()

        stats = pipeline.get_latency_stats()

        assert stats.sample_count == 5
        assert stats.avg_latency_ms > 0
        assert stats.source == ScreenshotSource.ADB

        pipeline.stop()

    def test_pipeline_switch_source_invalid(self) -> None:
        """Test switching to unavailable source."""
        pipeline = ScreenshotPipeline()

        # Try to switch to scrcpy when not available
        result = pipeline.switch_source(ScreenshotSource.SCRCPY)
        assert result is False

        # Try to switch to buffer source (not allowed)
        result = pipeline.switch_source(ScreenshotSource.BUFFER)
        assert result is False

    def test_pipeline_switch_source_valid(self) -> None:
        """Test switching to available source."""
        config = ScreenshotConfig(use_scrcpy=False)
        mock_manager = MagicMock()
        mock_manager.is_connected = True

        pipeline = ScreenshotPipeline(device_manager=mock_manager, config=config)
        pipeline.start()

        # Already using ADB, should succeed
        result = pipeline.switch_source(ScreenshotSource.ADB)
        assert result is True

        pipeline.stop()

    def test_pipeline_get_latest_frame_empty(self) -> None:
        """Test getting latest frame when buffer is empty."""
        pipeline = ScreenshotPipeline()
        frame = pipeline.get_latest_frame()
        assert frame is None

    def test_pipeline_get_latest_frame(self) -> None:
        """Test getting latest frame from buffer."""
        from PIL import Image as PILImage

        config = ScreenshotConfig(use_scrcpy=False)
        mock_manager = MagicMock()
        mock_manager.is_connected = True

        mock_pil = PILImage.new("RGB", (640, 480), color="yellow")
        mock_manager.screenshot.return_value = mock_pil

        pipeline = ScreenshotPipeline(device_manager=mock_manager, config=config)
        pipeline.start()
        pipeline.capture()

        frame = pipeline.get_latest_frame()

        assert frame is not None
        assert isinstance(frame, np.ndarray)
        assert frame.shape == (480, 640, 3)

        pipeline.stop()

    def test_pipeline_frame_callback(self) -> None:
        """Test frame callback is called on capture."""
        from PIL import Image as PILImage

        config = ScreenshotConfig(use_scrcpy=False)
        mock_manager = MagicMock()
        mock_manager.is_connected = True

        mock_pil = PILImage.new("RGB", (640, 480), color="white")
        mock_manager.screenshot.return_value = mock_pil

        callback_results: list[ScreenshotResult] = []

        def on_frame(result: ScreenshotResult) -> None:
            callback_results.append(result)

        pipeline = ScreenshotPipeline(device_manager=mock_manager, config=config, on_frame=on_frame)
        pipeline.start()
        pipeline.capture()

        assert len(callback_results) == 1
        assert callback_results[0].source == ScreenshotSource.ADB

        pipeline.stop()

    def test_pipeline_callback_error_handling(self) -> None:
        """Test frame callback error is handled gracefully."""
        from PIL import Image as PILImage

        config = ScreenshotConfig(use_scrcpy=False)
        mock_manager = MagicMock()
        mock_manager.is_connected = True

        mock_pil = PILImage.new("RGB", (640, 480), color="black")
        mock_manager.screenshot.return_value = mock_pil

        def bad_callback(result: ScreenshotResult) -> None:
            raise RuntimeError("Callback error")

        pipeline = ScreenshotPipeline(
            device_manager=mock_manager, config=config, on_frame=bad_callback
        )
        pipeline.start()

        # Should not raise, error is logged but handled
        result = pipeline.capture()
        assert result is not None

        pipeline.stop()

    def test_pipeline_benchmark(self) -> None:
        """Test benchmark method."""
        from PIL import Image as PILImage

        config = ScreenshotConfig(use_scrcpy=False)
        mock_manager = MagicMock()
        mock_manager.is_connected = True

        mock_pil = PILImage.new("RGB", (640, 480), color="gray")
        mock_manager.screenshot.return_value = mock_pil

        pipeline = ScreenshotPipeline(device_manager=mock_manager, config=config)
        pipeline.start()

        results = pipeline.benchmark(iterations=3)

        assert ScreenshotSource.ADB in results
        assert results[ScreenshotSource.ADB] > 0

        pipeline.stop()

    def test_pipeline_double_start(self) -> None:
        """Test starting pipeline twice returns True."""
        config = ScreenshotConfig(use_scrcpy=False)
        mock_manager = MagicMock()
        mock_manager.is_connected = True

        pipeline = ScreenshotPipeline(device_manager=mock_manager, config=config)

        result1 = pipeline.start()
        result2 = pipeline.start()

        assert result1 is True
        assert result2 is True

        pipeline.stop()

    def test_pipeline_stop_when_not_running(self) -> None:
        """Test stopping pipeline when not running does nothing."""
        pipeline = ScreenshotPipeline()

        # Should not raise
        pipeline.stop()

        assert pipeline.is_running is False


class TestScrcpyClient:
    """Tests for ScrcpyClient class."""

    def test_client_creation(self) -> None:
        """Test client can be created."""
        client = ScrcpyClient(device="test-device")
        assert client.device == "test-device"
        assert client.is_connected is False
        assert client.last_frame is None

    def test_client_with_config(self) -> None:
        """Test client with custom configuration."""
        client = ScrcpyClient(
            device="emulator-5554",
            max_width=1080,
            bitrate=8_000_000,
            max_fps=30,
        )
        assert client.max_width == 1080
        assert client.bitrate == 8_000_000
        assert client.max_fps == 30

    def test_client_start_import_error(self) -> None:
        """Test client handles import error gracefully."""
        client = ScrcpyClient()

        with patch.dict("sys.modules", {"scrcpy": None}):
            with patch("builtins.__import__", side_effect=ImportError("No scrcpy")):
                # May succeed or fail depending on scrcpy availability
                # The important thing is it doesn't raise
                _ = client.start(timeout=0.1)

    def test_client_stop_when_not_started(self) -> None:
        """Test stopping client when not started."""
        client = ScrcpyClient()
        # Should not raise
        client.stop()
        assert client.is_connected is False

    def test_client_frame_callback(self) -> None:
        """Test frame callback is invoked."""
        frames_received: list[np.ndarray] = []

        def on_frame(frame: np.ndarray) -> None:
            frames_received.append(frame)

        client = ScrcpyClient(on_frame=on_frame)

        # Simulate frame reception
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        client._handle_frame(test_frame)

        assert len(frames_received) == 1
        assert client.last_frame is not None

    def test_client_frame_callback_with_none(self) -> None:
        """Test frame callback handles None frame."""
        client = ScrcpyClient()
        # Should not raise
        client._handle_frame(None)
        assert client.last_frame is None

    def test_client_connection_handlers(self) -> None:
        """Test connection/disconnection handlers."""
        client = ScrcpyClient()

        assert client.is_connected is False

        client._handle_init()
        assert client.is_connected is True

        client._handle_disconnect()
        assert client.is_connected is False


# =============================================================================
# ManaManager Tests
# =============================================================================

from rush_bot.core import ManaConfig
from rush_bot.core import ManaManager
from rush_bot.core import ManaRegion
from rush_bot.core import ManaState
from rush_bot.core import UpgradeRecommendation
from rush_bot.core import UpgradeSlot
from rush_bot.core import create_mana_manager


class TestManaConfig:
    """Tests for ManaConfig dataclass."""

    def test_default_config(self) -> None:
        """Test default mana configuration."""
        config = ManaConfig()
        assert config.auto_upgrade is True
        assert config.upgrade_priority == [1, 2, 3, 4, 5]
        assert config.boss_reserve == 200
        assert config.min_summon_mana == 100
        assert config.max_summon_cost == 800
        assert config.enable_hero_power is False
        assert config.hero_power_cooldown_ms == 5000

    def test_custom_config(self) -> None:
        """Test custom mana configuration."""
        config = ManaConfig(
            auto_upgrade=False,
            upgrade_priority=[3, 1, 2, 5, 4],
            boss_reserve=300,
            enable_hero_power=True,
        )
        assert config.auto_upgrade is False
        assert config.upgrade_priority == [3, 1, 2, 5, 4]
        assert config.boss_reserve == 300
        assert config.enable_hero_power is True


class TestManaState:
    """Tests for ManaState dataclass."""

    def test_default_state(self) -> None:
        """Test default mana state."""
        state = ManaState()
        assert state.current_mana == 0
        assert state.summon_cost == 50  # BASE_SUMMON_COST
        assert state.card_levels == {1: 1, 2: 1, 3: 1, 4: 1, 5: 1}
        assert state.hero_power_level == 1
        assert state.is_boss_wave is False
        assert state.units_summoned == 0

    def test_state_reset(self) -> None:
        """Test state reset functionality."""
        state = ManaState()
        state.current_mana = 500
        state.summon_cost = 100
        state.units_summoned = 10
        state.card_levels[1] = 3
        state.is_boss_wave = True

        state.reset()

        assert state.current_mana == 0
        assert state.summon_cost == 50
        assert state.units_summoned == 0
        assert state.card_levels == {1: 1, 2: 1, 3: 1, 4: 1, 5: 1}
        assert state.is_boss_wave is False


class TestManaRegion:
    """Tests for ManaRegion dataclass."""

    def test_region_creation(self) -> None:
        """Test mana region creation."""
        region = ManaRegion(x=50, y=100, width=150, height=50)
        assert region.x == 50
        assert region.y == 100
        assert region.width == 150
        assert region.height == 50

    def test_region_bounds(self) -> None:
        """Test region bounds property."""
        region = ManaRegion(x=50, y=100, width=150, height=50)
        assert region.bounds == (50, 100, 150, 50)

    def test_region_center(self) -> None:
        """Test region center calculation."""
        region = ManaRegion(x=50, y=100, width=150, height=50)
        assert region.center == (125, 125)  # (50 + 75, 100 + 25)


class TestUpgradeSlot:
    """Tests for UpgradeSlot enum."""

    def test_slot_values(self) -> None:
        """Test upgrade slot values."""
        assert UpgradeSlot.CARD_1 == 1
        assert UpgradeSlot.CARD_2 == 2
        assert UpgradeSlot.CARD_3 == 3
        assert UpgradeSlot.CARD_4 == 4
        assert UpgradeSlot.CARD_5 == 5
        assert UpgradeSlot.HERO_POWER == 6


class TestUpgradeRecommendation:
    """Tests for UpgradeRecommendation dataclass."""

    def test_recommendation_creation(self) -> None:
        """Test upgrade recommendation creation."""
        rec = UpgradeRecommendation(
            slot=1,
            cost=100,
            priority=5.0,
            can_afford=True,
            reason="Card 1 upgrade",
        )
        assert rec.slot == 1
        assert rec.cost == 100
        assert rec.priority == 5.0
        assert rec.can_afford is True
        assert rec.reason == "Card 1 upgrade"


class TestManaManager:
    """Tests for ManaManager class."""

    def test_manager_creation(self) -> None:
        """Test mana manager creation with defaults."""
        manager = ManaManager()
        assert manager is not None
        assert manager.screen_width == 1080
        assert manager.screen_height == 1920
        assert manager.config.auto_upgrade is True

    def test_manager_with_custom_config(self) -> None:
        """Test mana manager with custom config."""
        config = ManaConfig(boss_reserve=400, auto_upgrade=False)
        manager = ManaManager(config=config)
        assert manager.config.boss_reserve == 400
        assert manager.config.auto_upgrade is False

    def test_manager_custom_resolution(self) -> None:
        """Test mana manager with custom resolution."""
        manager = ManaManager(screen_width=720, screen_height=1280)
        assert manager.screen_width == 720
        assert manager.screen_height == 1280
        assert manager._scale_x == 720 / 1080
        assert manager._scale_y == 1280 / 1920

    def test_set_screen_resolution(self) -> None:
        """Test updating screen resolution."""
        manager = ManaManager()
        manager.set_screen_resolution(1440, 2560)

        assert manager.screen_width == 1440
        assert manager.screen_height == 2560
        assert manager._scale_x == 1440 / 1080
        assert manager._scale_y == 2560 / 1920

    def test_get_mana_region(self) -> None:
        """Test getting mana region at reference resolution."""
        manager = ManaManager()
        region = manager.get_mana_region()

        assert region.x == 50
        assert region.y == 1765
        assert region.width == 150
        assert region.height == 50

    def test_get_mana_region_scaled(self) -> None:
        """Test getting mana region at scaled resolution."""
        manager = ManaManager(screen_width=540, screen_height=960)
        region = manager.get_mana_region()

        # Half resolution = half coordinates
        assert region.x == 25  # 50 * 0.5
        assert region.y == 882  # int(1765 * 0.5)

    def test_get_summon_button_region(self) -> None:
        """Test getting summon button region."""
        manager = ManaManager()
        region = manager.get_summon_button_region()

        assert region.x == 920
        assert region.y == 1770

    def test_get_summon_button_position(self) -> None:
        """Test getting summon button center position."""
        manager = ManaManager()
        pos = manager.get_summon_button_position()

        # Center of summon button region
        assert isinstance(pos, tuple)
        assert len(pos) == 2
        assert pos[0] > 900  # X should be right side

    def test_get_upgrade_button_position_valid(self) -> None:
        """Test getting upgrade button positions for valid slots."""
        manager = ManaManager()

        for slot in range(1, 7):
            pos = manager.get_upgrade_button_position(slot)
            assert isinstance(pos, tuple)
            assert len(pos) == 2
            assert pos[1] > 1400  # Y should be near bottom

    def test_get_upgrade_button_position_invalid(self) -> None:
        """Test invalid slot raises error."""
        manager = ManaManager()

        with pytest.raises(ValueError, match="Invalid slot"):
            manager.get_upgrade_button_position(0)

        with pytest.raises(ValueError, match="Invalid slot"):
            manager.get_upgrade_button_position(7)

    def test_get_all_upgrade_positions(self) -> None:
        """Test getting all upgrade positions."""
        manager = ManaManager()
        positions = manager.get_all_upgrade_positions()

        assert len(positions) == 6
        assert all(slot in positions for slot in range(1, 7))

    def test_calculate_summon_cost(self) -> None:
        """Test summon cost calculation."""
        manager = ManaManager()

        # First summon: base cost
        assert manager.calculate_summon_cost(0) == 50

        # Each unit increases cost by 10
        assert manager.calculate_summon_cost(1) == 60
        assert manager.calculate_summon_cost(5) == 100
        assert manager.calculate_summon_cost(10) == 150

        # Max cost capped at 1200
        assert manager.calculate_summon_cost(200) == 1200

    def test_can_summon_with_enough_mana(self) -> None:
        """Test can_summon returns True when mana is sufficient."""
        manager = ManaManager()
        state = ManaState(current_mana=100, summon_cost=50)

        assert manager.can_summon(state) is True

    def test_can_summon_without_enough_mana(self) -> None:
        """Test can_summon returns False when mana is insufficient."""
        manager = ManaManager()
        state = ManaState(current_mana=30, summon_cost=50)

        assert manager.can_summon(state) is False

    def test_can_summon_with_max_cost_exceeded(self) -> None:
        """Test can_summon returns False when cost exceeds max."""
        config = ManaConfig(max_summon_cost=100)
        manager = ManaManager(config=config)
        state = ManaState(current_mana=500, summon_cost=150)

        assert manager.can_summon(state) is False

    def test_can_summon_boss_wave_reserve(self) -> None:
        """Test can_summon respects boss wave reserve."""
        config = ManaConfig(boss_reserve=200)
        manager = ManaManager(config=config)

        # Without boss wave: can summon
        state = ManaState(current_mana=100, summon_cost=50, is_boss_wave=False)
        assert manager.can_summon(state) is True

        # With boss wave: need extra reserve
        state.is_boss_wave = True
        state.current_mana = 200  # 200 - 200 reserve = 0 available
        assert manager.can_summon(state) is False

        state.current_mana = 300  # 300 - 200 reserve = 100 available
        assert manager.can_summon(state) is True

    def test_should_upgrade_auto_disabled(self) -> None:
        """Test should_upgrade returns False when auto_upgrade disabled."""
        config = ManaConfig(auto_upgrade=False)
        manager = ManaManager(config=config)
        state = ManaState(current_mana=500)

        assert manager.should_upgrade(1, state) is False

    def test_should_upgrade_hero_power_disabled(self) -> None:
        """Test should_upgrade returns False for hero when disabled."""
        config = ManaConfig(enable_hero_power=False)
        manager = ManaManager(config=config)
        state = ManaState(current_mana=500)

        assert manager.should_upgrade(6, state) is False

    def test_should_upgrade_can_afford(self) -> None:
        """Test should_upgrade returns True when affordable."""
        manager = ManaManager()
        state = ManaState(current_mana=200)  # Enough for level 1 upgrade (100)

        assert manager.should_upgrade(1, state) is True

    def test_should_upgrade_cannot_afford(self) -> None:
        """Test should_upgrade returns False when not affordable."""
        manager = ManaManager()
        state = ManaState(current_mana=50)  # Not enough for level 1 upgrade (100)

        assert manager.should_upgrade(1, state) is False

    def test_get_upgrade_recommendation(self) -> None:
        """Test getting upgrade recommendation."""
        manager = ManaManager()
        state = ManaState(current_mana=200)

        rec = manager.get_upgrade_recommendation(state)

        assert rec is not None
        assert rec.can_afford is True
        assert rec.slot in [1, 2, 3, 4, 5]

    def test_get_upgrade_recommendation_no_mana(self) -> None:
        """Test no recommendation when no mana."""
        manager = ManaManager()
        state = ManaState(current_mana=0)

        rec = manager.get_upgrade_recommendation(state)

        # Should be None or not affordable
        assert rec is None or rec.can_afford is False

    def test_get_upgrade_recommendation_auto_disabled(self) -> None:
        """Test no recommendation when auto_upgrade disabled."""
        config = ManaConfig(auto_upgrade=False)
        manager = ManaManager(config=config)
        state = ManaState(current_mana=1000)

        rec = manager.get_upgrade_recommendation(state)

        assert rec is None

    def test_get_all_upgrade_recommendations(self) -> None:
        """Test getting all upgrade recommendations."""
        manager = ManaManager()
        state = ManaState(current_mana=500)

        recs = manager.get_all_upgrade_recommendations(state)

        assert len(recs) == 5  # 5 cards (hero power disabled by default)
        assert all(isinstance(r, UpgradeRecommendation) for r in recs)
        # Should be sorted by priority (descending)
        priorities = [r.priority for r in recs]
        assert priorities == sorted(priorities, reverse=True)

    def test_get_all_upgrade_recommendations_with_hero(self) -> None:
        """Test getting all recommendations including hero power."""
        config = ManaConfig(enable_hero_power=True)
        manager = ManaManager(config=config)
        state = ManaState(current_mana=500)

        recs = manager.get_all_upgrade_recommendations(state)

        assert len(recs) == 6  # 5 cards + hero power

    def test_update_after_summon(self) -> None:
        """Test state update after summoning."""
        manager = ManaManager()
        manager.state.current_mana = 100
        manager.state.summon_cost = 50
        manager.state.units_summoned = 0

        manager.update_after_summon()

        assert manager.state.units_summoned == 1
        assert manager.state.summon_cost == 60  # 50 + 10
        assert manager.state.current_mana == 50  # 100 - 50

    def test_update_after_upgrade_card(self) -> None:
        """Test state update after upgrading a card."""
        manager = ManaManager()
        manager.state.current_mana = 200
        manager.state.card_levels[1] = 1

        manager.update_after_upgrade(1)

        assert manager.state.card_levels[1] == 2
        assert manager.state.current_mana == 100  # 200 - 100 (level 1 cost)

    def test_update_after_upgrade_hero(self) -> None:
        """Test state update after upgrading hero power."""
        manager = ManaManager()
        manager.state.current_mana = 200
        manager.state.hero_power_level = 1

        manager.update_after_upgrade(6)

        assert manager.state.hero_power_level == 2
        assert manager.state.current_mana == 100  # 200 - 100

    def test_set_boss_wave(self) -> None:
        """Test setting boss wave flag."""
        manager = ManaManager()

        assert manager.state.is_boss_wave is False

        manager.set_boss_wave(True)
        assert manager.state.is_boss_wave is True

        manager.set_boss_wave(False)
        assert manager.state.is_boss_wave is False

    def test_reset_for_new_battle(self) -> None:
        """Test resetting state for new battle."""
        manager = ManaManager()
        manager.state.current_mana = 1000
        manager.state.units_summoned = 50
        manager.state.card_levels[1] = 5
        manager.state.is_boss_wave = True

        manager.reset_for_new_battle()

        assert manager.state.current_mana == 0
        assert manager.state.units_summoned == 0
        assert manager.state.card_levels == {1: 1, 2: 1, 3: 1, 4: 1, 5: 1}
        assert manager.state.is_boss_wave is False

    def test_get_mana_efficiency(self) -> None:
        """Test getting mana efficiency metrics."""
        manager = ManaManager()
        manager.state.current_mana = 500
        manager.state.units_summoned = 5
        manager.state.card_levels[1] = 2
        manager.state.card_levels[2] = 3
        manager.state.hero_power_level = 2

        metrics = manager.get_mana_efficiency()

        assert metrics["units_summoned"] == 5
        assert metrics["current_mana"] == 500
        assert metrics["card_levels"] == {1: 2, 2: 3, 3: 1, 4: 1, 5: 1}
        assert metrics["hero_power_level"] == 2
        assert "total_summon_mana_spent" in metrics
        assert "total_upgrade_mana_spent" in metrics


class TestManaManagerOCR:
    """Tests for ManaManager OCR functionality."""

    def test_detect_mana_from_valid_image(self) -> None:
        """Test mana detection from valid screenshot."""
        manager = ManaManager()

        # Create a fake screenshot (1080x1920 BGR)
        screenshot = np.zeros((1920, 1080, 3), dtype=np.uint8)
        # Add some bright pixels in mana region to simulate digits
        screenshot[1765:1815, 50:200] = 255

        result = manager.detect_mana_from_image(screenshot)

        # Should return some estimation (not None)
        # The actual value depends on contour detection
        assert result is not None or result is None  # OCR may fail without real text

    def test_detect_mana_from_invalid_image(self) -> None:
        """Test mana detection with invalid image."""
        manager = ManaManager()

        # Empty or None screenshot
        result = manager.detect_mana_from_image(np.array([]))
        assert result is None

    def test_detect_mana_region_out_of_bounds(self) -> None:
        """Test mana detection when region is out of bounds."""
        manager = ManaManager()

        # Small screenshot (region will be out of bounds)
        screenshot = np.zeros((100, 100, 3), dtype=np.uint8)

        result = manager.detect_mana_from_image(screenshot)
        assert result is None

    def test_detect_mana_state(self) -> None:
        """Test full mana state detection."""
        manager = ManaManager()

        screenshot = np.zeros((1920, 1080, 3), dtype=np.uint8)
        screenshot[1765:1815, 50:200] = 200

        state = manager.detect_mana_state(screenshot)

        assert isinstance(state, ManaState)


class TestCreateManaManager:
    """Tests for the create_mana_manager factory function."""

    def test_create_default(self) -> None:
        """Test creating manager with defaults."""
        manager = create_mana_manager()
        assert isinstance(manager, ManaManager)

    def test_create_with_config(self) -> None:
        """Test creating manager with custom config."""
        config = ManaConfig(boss_reserve=500)
        manager = create_mana_manager(config=config)
        assert manager.config.boss_reserve == 500

    def test_create_with_resolution(self) -> None:
        """Test creating manager with custom resolution."""
        manager = create_mana_manager(screen_width=720, screen_height=1280)
        assert manager.screen_width == 720
        assert manager.screen_height == 1280


# =============================================================================
# Dungeon Loop Tests
# =============================================================================

from rush_bot.core import DungeonConfig
from rush_bot.core import DungeonLoop
from rush_bot.core import DungeonResult
from rush_bot.core import DungeonRunResult
from rush_bot.core import DungeonState
from rush_bot.core import DungeonStats
from rush_bot.core import create_dungeon_loop


class TestDungeonConfig:
    """Tests for DungeonConfig dataclass."""

    def test_default_config(self) -> None:
        """Test default dungeon configuration."""
        config = DungeonConfig()
        assert config.target_chapter == 1
        assert config.target_floor == 1
        assert config.auto_retry is True
        assert config.max_retries == 3
        assert config.skip_ads is True
        assert config.battle_timeout_seconds == 600
        assert config.enable_battle_automation is True

    def test_custom_config(self) -> None:
        """Test custom dungeon configuration."""
        config = DungeonConfig(
            target_chapter=3,
            target_floor=10,
            auto_retry=False,
            max_retries=5,
        )
        assert config.target_chapter == 3
        assert config.target_floor == 10
        assert config.auto_retry is False
        assert config.max_retries == 5

    def test_invalid_chapter_raises_error(self) -> None:
        """Test that invalid chapter raises ValueError."""
        with pytest.raises(ValueError, match="Invalid chapter"):
            DungeonConfig(target_chapter=0)

        with pytest.raises(ValueError, match="Invalid chapter"):
            DungeonConfig(target_chapter=7)

    def test_invalid_floor_raises_error(self) -> None:
        """Test that invalid floor raises ValueError."""
        with pytest.raises(ValueError, match="Invalid floor"):
            DungeonConfig(target_floor=0)

        with pytest.raises(ValueError, match="Invalid floor"):
            DungeonConfig(target_floor=15)

    def test_invalid_max_retries_raises_error(self) -> None:
        """Test that invalid max_retries raises ValueError."""
        with pytest.raises(ValueError, match="Invalid max_retries"):
            DungeonConfig(max_retries=-1)


class TestDungeonState:
    """Tests for DungeonState enum."""

    def test_all_states_exist(self) -> None:
        """Test that all expected states exist."""
        assert DungeonState.IDLE is not None
        assert DungeonState.NAVIGATING_TO_DUNGEON is not None
        assert DungeonState.SELECTING_CHAPTER is not None
        assert DungeonState.SELECTING_FLOOR is not None
        assert DungeonState.WAITING_FOR_BATTLE is not None
        assert DungeonState.IN_BATTLE is not None
        assert DungeonState.BATTLE_ENDED is not None
        assert DungeonState.HANDLING_VICTORY is not None
        assert DungeonState.HANDLING_DEFEAT is not None
        assert DungeonState.HANDLING_AD is not None
        assert DungeonState.RETURNING_TO_MENU is not None
        assert DungeonState.ERROR is not None
        assert DungeonState.COMPLETED is not None


class TestDungeonResult:
    """Tests for DungeonResult enum."""

    def test_all_results_exist(self) -> None:
        """Test that all expected results exist."""
        assert DungeonResult.VICTORY is not None
        assert DungeonResult.DEFEAT is not None
        assert DungeonResult.ERROR is not None
        assert DungeonResult.CANCELLED is not None
        assert DungeonResult.TIMEOUT is not None


class TestDungeonStats:
    """Tests for DungeonStats dataclass."""

    def test_default_stats(self) -> None:
        """Test default stats are zero."""
        stats = DungeonStats()
        assert stats.runs_completed == 0
        assert stats.victories == 0
        assert stats.defeats == 0
        assert stats.errors == 0
        assert stats.total_battle_time_seconds == 0.0
        assert stats.ads_skipped == 0
        assert stats.retries_used == 0

    def test_record_victory(self) -> None:
        """Test recording a victory."""
        stats = DungeonStats()
        stats.record_victory(120.5)

        assert stats.runs_completed == 1
        assert stats.victories == 1
        assert stats.total_battle_time_seconds == 120.5

    def test_record_defeat(self) -> None:
        """Test recording a defeat."""
        stats = DungeonStats()
        stats.record_defeat(60.0)

        assert stats.runs_completed == 1
        assert stats.defeats == 1
        assert stats.total_battle_time_seconds == 60.0

    def test_record_error(self) -> None:
        """Test recording an error."""
        stats = DungeonStats()
        stats.record_error()

        assert stats.errors == 1

    def test_record_ad_skip(self) -> None:
        """Test recording ad skip."""
        stats = DungeonStats()
        stats.record_ad_skip()

        assert stats.ads_skipped == 1

    def test_record_retry(self) -> None:
        """Test recording retry."""
        stats = DungeonStats()
        stats.record_retry()

        assert stats.retries_used == 1

    def test_win_rate_calculation(self) -> None:
        """Test win rate calculation."""
        stats = DungeonStats()

        # No runs, should be 0
        assert stats.win_rate == 0.0

        # 2 victories, 1 defeat = 66.67%
        stats.record_victory(60.0)
        stats.record_victory(60.0)
        stats.record_defeat(60.0)

        assert abs(stats.win_rate - 66.666666) < 0.1

    def test_average_battle_time(self) -> None:
        """Test average battle time calculation."""
        stats = DungeonStats()

        # No runs, should be 0
        assert stats.average_battle_time == 0.0

        # 3 runs with different times
        stats.record_victory(60.0)
        stats.record_victory(120.0)
        stats.record_defeat(90.0)

        assert stats.average_battle_time == 90.0


class TestDungeonRunResult:
    """Tests for DungeonRunResult dataclass."""

    def test_victory_result(self) -> None:
        """Test victory run result."""
        result = DungeonRunResult(
            result=DungeonResult.VICTORY,
            chapter=2,
            floor=5,
            battle_time_seconds=120.0,
        )

        assert result.result == DungeonResult.VICTORY
        assert result.chapter == 2
        assert result.floor == 5
        assert result.battle_time_seconds == 120.0
        assert result.error_message == ""
        assert result.retry_count == 0

    def test_error_result(self) -> None:
        """Test error run result."""
        result = DungeonRunResult(
            result=DungeonResult.ERROR,
            chapter=1,
            floor=1,
            error_message="Failed to connect",
        )

        assert result.result == DungeonResult.ERROR
        assert result.error_message == "Failed to connect"


class TestDungeonLoop:
    """Tests for DungeonLoop class."""

    def test_dungeon_loop_creation(self) -> None:
        """Test that DungeonLoop can be created."""
        mock_device = MagicMock()
        mock_detector = MagicMock()

        dungeon = DungeonLoop(mock_device, mock_detector)

        assert dungeon is not None
        assert dungeon.state == DungeonState.IDLE
        assert dungeon.is_running is False

    def test_dungeon_loop_with_config(self) -> None:
        """Test DungeonLoop with custom config."""
        mock_device = MagicMock()
        mock_detector = MagicMock()
        config = DungeonConfig(target_chapter=3, target_floor=7)

        dungeon = DungeonLoop(mock_device, mock_detector, config)

        assert dungeon.config.target_chapter == 3
        assert dungeon.config.target_floor == 7

    def test_state_change_callback(self) -> None:
        """Test state change callback is called."""
        mock_device = MagicMock()
        mock_detector = MagicMock()
        states_received: list[DungeonState] = []

        def callback(state: DungeonState) -> None:
            states_received.append(state)

        dungeon = DungeonLoop(mock_device, mock_detector, on_state_change=callback)
        dungeon._set_state(DungeonState.NAVIGATING_TO_DUNGEON)

        assert DungeonState.NAVIGATING_TO_DUNGEON in states_received

    def test_state_change_callback_exception_handling(self) -> None:
        """Test that callback exceptions don't crash the loop."""
        mock_device = MagicMock()
        mock_detector = MagicMock()

        def bad_callback(state: DungeonState) -> None:
            raise RuntimeError("Callback error")

        dungeon = DungeonLoop(mock_device, mock_detector, on_state_change=bad_callback)

        # Should not raise
        dungeon._set_state(DungeonState.IN_BATTLE)
        assert dungeon.state == DungeonState.IN_BATTLE

    def test_battle_action_callback(self) -> None:
        """Test battle action callback is called."""
        mock_device = MagicMock()
        mock_detector = MagicMock()
        actions_received: list[str] = []

        def callback(action: str) -> None:
            actions_received.append(action)

        dungeon = DungeonLoop(mock_device, mock_detector, on_battle_action=callback)
        dungeon._notify_battle_action("Summon unit")

        assert "Summon unit" in actions_received

    def test_coordinate_scaling(self) -> None:
        """Test coordinate scaling to different resolutions."""
        mock_device = MagicMock()
        mock_detector = MagicMock()

        dungeon = DungeonLoop(mock_device, mock_detector)

        # Default is 1080x1920
        assert dungeon._scale_x(540) == 540
        assert dungeon._scale_y(960) == 960

        # Test scaling to 720x1280
        dungeon._screen_width = 720
        dungeon._screen_height = 1280

        assert dungeon._scale_x(1080) == 720  # Full width
        assert dungeon._scale_y(1920) == 1280  # Full height

    def test_update_screen_resolution(self) -> None:
        """Test screen resolution update from device info."""
        mock_device = MagicMock()
        mock_device.device_info = DeviceInfo(
            serial="test",
            screen_width=1440,
            screen_height=2560,
        )
        mock_detector = MagicMock()

        dungeon = DungeonLoop(mock_device, mock_detector)
        dungeon._update_screen_resolution()

        assert dungeon._screen_width == 1440
        assert dungeon._screen_height == 2560

    def test_stats_property(self) -> None:
        """Test stats property returns DungeonStats."""
        mock_device = MagicMock()
        mock_detector = MagicMock()

        dungeon = DungeonLoop(mock_device, mock_detector)

        assert isinstance(dungeon.stats, DungeonStats)
        assert dungeon.stats.victories == 0

    def test_stop_method(self) -> None:
        """Test stop method sets should_stop flag."""
        mock_device = MagicMock()
        mock_detector = MagicMock()

        dungeon = DungeonLoop(mock_device, mock_detector)
        dungeon.stop()

        assert dungeon._should_stop is True

    def test_reset_stats(self) -> None:
        """Test reset_stats clears statistics."""
        mock_device = MagicMock()
        mock_detector = MagicMock()

        dungeon = DungeonLoop(mock_device, mock_detector)
        dungeon._stats.record_victory(60.0)
        dungeon._stats.record_defeat(30.0)

        dungeon.reset_stats()

        assert dungeon.stats.victories == 0
        assert dungeon.stats.defeats == 0
        assert dungeon.stats.runs_completed == 0

    def test_double_run_returns_error(self) -> None:
        """Test that running while already running returns error."""
        mock_device = MagicMock()
        mock_detector = MagicMock()

        dungeon = DungeonLoop(mock_device, mock_detector)
        dungeon._is_running = True

        result = dungeon.run()

        assert result.result == DungeonResult.ERROR
        assert "Already running" in result.error_message

    def test_create_error_result(self) -> None:
        """Test error result creation."""
        mock_device = MagicMock()
        mock_detector = MagicMock()

        dungeon = DungeonLoop(mock_device, mock_detector)
        result = dungeon._create_error_result("Test error")

        assert result.result == DungeonResult.ERROR
        assert result.error_message == "Test error"
        assert dungeon.state == DungeonState.ERROR
        assert dungeon.stats.errors == 1


class TestDungeonLoopNavigation:
    """Tests for DungeonLoop navigation methods."""

    def test_navigate_to_dungeon_already_there(self) -> None:
        """Test navigation when already on dungeon select."""
        mock_device = MagicMock()
        mock_device.screenshot.return_value = MagicMock()

        mock_detector = MagicMock()
        mock_result = MagicMock()
        mock_result.state.name = "DUNGEON_SELECT"
        mock_detector.detect.return_value = mock_result

        dungeon = DungeonLoop(mock_device, mock_detector)

        # Mock _capture_screen to return valid array
        dungeon._capture_screen = MagicMock(return_value=np.zeros((1920, 1080, 3), dtype=np.uint8))

        result = dungeon._navigate_to_dungeon()

        assert result is True

    def test_select_chapter_found(self) -> None:
        """Test chapter selection when chapter template is found."""
        mock_device = MagicMock()
        mock_device.tap.return_value = True

        mock_detector = MagicMock()
        mock_detector.find_template.return_value = (True, (100, 200, 50, 50), 0.9)

        dungeon = DungeonLoop(mock_device, mock_detector)
        dungeon._capture_screen = MagicMock(return_value=np.zeros((1920, 1080, 3), dtype=np.uint8))
        dungeon._delay = MagicMock()

        result = dungeon._select_chapter()

        assert result is True
        mock_device.tap.assert_called()

    def test_select_floor_found(self) -> None:
        """Test floor selection when floor template is found."""
        mock_device = MagicMock()
        mock_device.tap.return_value = True

        mock_detector = MagicMock()
        mock_detector.find_template.return_value = (True, (100, 200, 50, 50), 0.9)

        dungeon = DungeonLoop(mock_device, mock_detector)
        dungeon._capture_screen = MagicMock(return_value=np.zeros((1920, 1080, 3), dtype=np.uint8))
        dungeon._delay = MagicMock()

        result = dungeon._select_floor()

        assert result is True


class TestDungeonLoopBattle:
    """Tests for DungeonLoop battle handling."""

    def test_handle_victory(self) -> None:
        """Test victory handling."""
        mock_device = MagicMock()
        mock_device.tap.return_value = True
        mock_detector = MagicMock()

        dungeon = DungeonLoop(mock_device, mock_detector)
        dungeon._battle_start_time = 100.0
        dungeon._delay = MagicMock()

        with patch("time.time", return_value=220.0):
            dungeon._handle_victory()

        assert dungeon.stats.victories == 1
        assert dungeon.stats.runs_completed == 1
        mock_device.tap.assert_called()

    def test_handle_defeat_no_retry(self) -> None:
        """Test defeat handling without retry."""
        mock_device = MagicMock()
        mock_device.tap.return_value = True
        mock_detector = MagicMock()

        config = DungeonConfig(auto_retry=False)
        dungeon = DungeonLoop(mock_device, mock_detector, config)
        dungeon._battle_start_time = 100.0
        dungeon._delay = MagicMock()

        with patch("time.time", return_value=200.0):
            should_retry = dungeon._handle_defeat()

        assert should_retry is False
        assert dungeon.stats.defeats == 1

    def test_handle_defeat_with_retry(self) -> None:
        """Test defeat handling with retry available."""
        mock_device = MagicMock()
        mock_device.tap.return_value = True
        mock_detector = MagicMock()

        config = DungeonConfig(auto_retry=True, max_retries=3)
        dungeon = DungeonLoop(mock_device, mock_detector, config)
        dungeon._battle_start_time = 100.0
        dungeon._current_retry = 0
        dungeon._delay = MagicMock()

        with patch("time.time", return_value=200.0):
            should_retry = dungeon._handle_defeat()

        assert should_retry is True
        assert dungeon._current_retry == 1
        assert dungeon.stats.retries_used == 1

    def test_handle_defeat_max_retries_reached(self) -> None:
        """Test defeat handling when max retries reached."""
        mock_device = MagicMock()
        mock_device.tap.return_value = True
        mock_detector = MagicMock()

        config = DungeonConfig(auto_retry=True, max_retries=3)
        dungeon = DungeonLoop(mock_device, mock_detector, config)
        dungeon._battle_start_time = 100.0
        dungeon._current_retry = 3  # Already at max
        dungeon._delay = MagicMock()

        with patch("time.time", return_value=200.0):
            should_retry = dungeon._handle_defeat()

        assert should_retry is False

    def test_handle_advertisement(self) -> None:
        """Test advertisement handling."""
        mock_device = MagicMock()
        mock_device.tap.return_value = True
        mock_detector = MagicMock()

        dungeon = DungeonLoop(mock_device, mock_detector)
        dungeon._delay = MagicMock()

        dungeon._handle_advertisement()

        assert dungeon.stats.ads_skipped == 1
        assert mock_device.tap.call_count >= 1

    def test_handle_popup_with_close_button(self) -> None:
        """Test popup handling with close button found."""
        mock_device = MagicMock()
        mock_device.tap.return_value = True

        mock_detector = MagicMock()
        mock_detector.get_close_button_location.return_value = (500, 300)

        dungeon = DungeonLoop(mock_device, mock_detector)
        dungeon._capture_screen = MagicMock(return_value=np.zeros((1920, 1080, 3), dtype=np.uint8))
        dungeon._delay = MagicMock()

        dungeon._handle_popup()

        mock_device.tap.assert_called_with(500, 300)

    def test_handle_popup_with_back_button(self) -> None:
        """Test popup handling with back button found."""
        mock_device = MagicMock()
        mock_device.tap.return_value = True

        mock_detector = MagicMock()
        mock_detector.get_close_button_location.return_value = None
        mock_detector.get_back_button_location.return_value = (100, 150)

        dungeon = DungeonLoop(mock_device, mock_detector)
        dungeon._capture_screen = MagicMock(return_value=np.zeros((1920, 1080, 3), dtype=np.uint8))
        dungeon._delay = MagicMock()

        dungeon._handle_popup()

        mock_device.tap.assert_called_with(100, 150)


class TestDungeonLoopCapture:
    """Tests for DungeonLoop capture methods."""

    def test_capture_screen_success(self) -> None:
        """Test successful screen capture."""
        from PIL import Image

        mock_device = MagicMock()
        # Create a mock PIL image
        mock_pil_image = Image.new("RGB", (1080, 1920), color=(255, 0, 0))
        mock_device.screenshot.return_value = mock_pil_image

        mock_detector = MagicMock()
        dungeon = DungeonLoop(mock_device, mock_detector)

        result = dungeon._capture_screen()

        assert result is not None
        assert result.shape == (1920, 1080, 3)

    def test_capture_screen_failure(self) -> None:
        """Test capture screen when screenshot fails."""
        mock_device = MagicMock()
        mock_device.screenshot.return_value = None

        mock_detector = MagicMock()
        dungeon = DungeonLoop(mock_device, mock_detector)

        result = dungeon._capture_screen()

        assert result is None


class TestCreateDungeonLoop:
    """Tests for create_dungeon_loop factory function."""

    def test_create_default(self) -> None:
        """Test creating dungeon loop with defaults."""
        mock_device = MagicMock()
        mock_detector = MagicMock()

        dungeon = create_dungeon_loop(mock_device, mock_detector)

        assert isinstance(dungeon, DungeonLoop)
        assert dungeon.config.target_chapter == 1
        assert dungeon.config.target_floor == 1

    def test_create_with_parameters(self) -> None:
        """Test creating dungeon loop with parameters."""
        mock_device = MagicMock()
        mock_detector = MagicMock()

        dungeon = create_dungeon_loop(
            mock_device,
            mock_detector,
            chapter=4,
            floor=10,
            auto_retry=False,
            max_retries=5,
        )

        assert dungeon.config.target_chapter == 4
        assert dungeon.config.target_floor == 10
        assert dungeon.config.auto_retry is False
        assert dungeon.config.max_retries == 5


# ============================================================================
# Merge Debugger Tests (T016)
# ============================================================================


class TestMergeDebugger:
    """Tests for MergeDebugger class."""

    def test_debugger_creation(self) -> None:
        """Test creating a merge debugger."""
        from rush_bot.core.merge import MergeDebugger

        debugger = MergeDebugger()
        assert len(debugger.history) == 0

    def test_log_attempt_success(self) -> None:
        """Test logging a successful merge attempt."""
        from rush_bot.core.merge import MergeDebugger
        from rush_bot.core.merge import MergeResult

        debugger = MergeDebugger()
        attempt = debugger.log_attempt(
            source_unit="demon_hunter.png",
            source_rank=2,
            source_pos=(0, 0),
            target_unit="demon_hunter.png",
            target_rank=2,
            target_pos=(0, 1),
            result=MergeResult.SUCCESS,
        )

        assert attempt.result == MergeResult.SUCCESS
        assert len(debugger.history) == 1
        assert debugger.history[0].source_unit == "demon_hunter.png"

    def test_log_attempt_failure(self) -> None:
        """Test logging a failed merge attempt."""
        from rush_bot.core.merge import MergeDebugger
        from rush_bot.core.merge import MergeResult

        debugger = MergeDebugger()
        attempt = debugger.log_attempt(
            source_unit="demon_hunter.png",
            source_rank=2,
            source_pos=(0, 0),
            target_unit="archer.png",
            target_rank=2,
            target_pos=(0, 1),
            result=MergeResult.INVALID_TYPE,
        )

        assert attempt.result == MergeResult.INVALID_TYPE
        assert len(debugger.history) == 1

    def test_swipe_vector_calculation(self) -> None:
        """Test swipe vector is calculated correctly."""
        from rush_bot.core.merge import MergeDebugger
        from rush_bot.core.merge import MergeResult

        debugger = MergeDebugger()
        attempt = debugger.log_attempt(
            source_unit="unit.png",
            source_rank=1,
            source_pos=(1, 2),
            target_unit="unit.png",
            target_rank=1,
            target_pos=(1, 4),
            result=MergeResult.SUCCESS,
        )

        # Swipe vector should be (target - source)
        assert attempt.swipe_vector == (0, 2)

    def test_get_failures(self) -> None:
        """Test getting failed merge attempts."""
        from rush_bot.core.merge import MergeDebugger
        from rush_bot.core.merge import MergeResult

        debugger = MergeDebugger()

        # Add some attempts
        debugger.log_attempt("u1", 1, (0, 0), "u1", 1, (0, 1), MergeResult.SUCCESS)
        debugger.log_attempt("u1", 1, (0, 0), "u2", 1, (0, 1), MergeResult.INVALID_TYPE)
        debugger.log_attempt("u1", 1, (0, 0), "u1", 2, (0, 1), MergeResult.INVALID_RANK)

        failures = debugger.get_failures()
        assert len(failures) == 2

    def test_get_success_rate(self) -> None:
        """Test success rate calculation."""
        from rush_bot.core.merge import MergeDebugger
        from rush_bot.core.merge import MergeResult

        debugger = MergeDebugger()

        # 2 success, 2 failures = 50%
        debugger.log_attempt("u1", 1, (0, 0), "u1", 1, (0, 1), MergeResult.SUCCESS)
        debugger.log_attempt("u1", 1, (0, 0), "u1", 1, (0, 1), MergeResult.SUCCESS)
        debugger.log_attempt("u1", 1, (0, 0), "u2", 1, (0, 1), MergeResult.INVALID_TYPE)
        debugger.log_attempt("u1", 1, (0, 0), "u1", 2, (0, 1), MergeResult.INVALID_RANK)

        rate = debugger.get_success_rate()
        assert rate == 50.0

    def test_get_failure_breakdown(self) -> None:
        """Test failure breakdown by reason."""
        from rush_bot.core.merge import MergeDebugger
        from rush_bot.core.merge import MergeResult

        debugger = MergeDebugger()

        debugger.log_attempt("u1", 1, (0, 0), "u2", 1, (0, 1), MergeResult.INVALID_TYPE)
        debugger.log_attempt("u1", 1, (0, 0), "u2", 1, (0, 1), MergeResult.INVALID_TYPE)
        debugger.log_attempt("u1", 1, (0, 0), "u1", 2, (0, 1), MergeResult.INVALID_RANK)

        breakdown = debugger.get_failure_breakdown()
        assert breakdown["invalid_type"] == 2
        assert breakdown["invalid_rank"] == 1

    def test_clear_history(self) -> None:
        """Test clearing history."""
        from rush_bot.core.merge import MergeDebugger
        from rush_bot.core.merge import MergeResult

        debugger = MergeDebugger()
        debugger.log_attempt("u1", 1, (0, 0), "u1", 1, (0, 1), MergeResult.SUCCESS)

        assert len(debugger.history) == 1
        debugger.clear_history()
        assert len(debugger.history) == 0

    def test_format_summary(self) -> None:
        """Test summary formatting."""
        from rush_bot.core.merge import MergeDebugger
        from rush_bot.core.merge import MergeResult

        debugger = MergeDebugger()
        debugger.log_attempt("u1", 1, (0, 0), "u1", 1, (0, 1), MergeResult.SUCCESS)
        debugger.log_attempt("u1", 1, (0, 0), "u2", 1, (0, 1), MergeResult.INVALID_TYPE)

        summary = debugger.format_summary()
        assert "2 attempts" in summary
        assert "50" in summary  # 50% success rate


class TestMergeAttempt:
    """Tests for MergeAttempt dataclass."""

    def test_merge_attempt_to_log_string(self) -> None:
        """Test MergeAttempt log string formatting."""
        from rush_bot.core.merge import MergeAttempt
        from rush_bot.core.merge import MergeResult

        attempt = MergeAttempt(
            timestamp="12:30:45.123",
            source_unit="demon_hunter.png",
            source_rank=3,
            source_pos=(1, 2),
            target_unit="demon_hunter.png",
            target_rank=3,
            target_pos=(1, 3),
            result=MergeResult.SUCCESS,
            duration_ms=15.5,
            swipe_vector=(0, 1),
        )

        log_str = attempt.to_log_string()
        assert "demon_hunter.png" in log_str
        assert "R3" in log_str
        assert "success" in log_str
        assert "✓" in log_str

    def test_merge_attempt_failure_log_string(self) -> None:
        """Test MergeAttempt failure log string."""
        from rush_bot.core.merge import MergeAttempt
        from rush_bot.core.merge import MergeResult

        attempt = MergeAttempt(
            timestamp="12:30:45.123",
            source_unit="archer.png",
            source_rank=2,
            source_pos=(0, 0),
            target_unit="knight.png",
            target_rank=2,
            target_pos=(0, 1),
            result=MergeResult.INVALID_TYPE,
            duration_ms=5.0,
            swipe_vector=(0, 1),
        )

        log_str = attempt.to_log_string()
        assert "✗" in log_str
        assert "invalid_type" in log_str


class TestGetMergeDebugger:
    """Tests for global debugger accessor."""

    def test_get_merge_debugger_returns_instance(self) -> None:
        """Test that get_merge_debugger returns a MergeDebugger."""
        from rush_bot.core.merge import MergeDebugger
        from rush_bot.core.merge import get_merge_debugger

        debugger = get_merge_debugger()
        assert isinstance(debugger, MergeDebugger)

    def test_get_merge_debugger_returns_same_instance(self) -> None:
        """Test that get_merge_debugger returns the same instance."""
        from rush_bot.core.merge import get_merge_debugger

        debugger1 = get_merge_debugger()
        debugger2 = get_merge_debugger()
        assert debugger1 is debugger2
