"""Tests for rush_bot.core module."""

from __future__ import annotations

from unittest.mock import MagicMock
from unittest.mock import patch

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
from rush_bot.core import MergeCandidate
from rush_bot.core import MergeConfig
from rush_bot.core import MergeLogic
from rush_bot.core import MergeResult
from rush_bot.core import MergeValidator


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
