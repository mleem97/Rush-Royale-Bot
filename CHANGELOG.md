# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Complete commit history documentation in `Commits.md` (241 commits)
- Icon template organization by menu state (Main_Menu/, Store_Menu/, Cards_Menu/, Clan_Menu/, Event_Menu/, PVE/)
- New menu navigation icons: Cards_Menu.png, Clan_Menu.png, Event_Menu.png, Store_Menu.png
- PVP loading screen templates: PVP_Loading.png, Abort_Button.png
- Main menu button templates: PVE_Button.png, PVP_Button.png, Quest_New_Weekly.png, AD_Bonus_Button.png, Home_Menu.png

### Changed
- Reorganized cv-images/icons/ structure with state-based subdirectories
- Moved all PVE dungeon icons to cv-images/icons/PVE/ subdirectory (chapter_*.png, floor_*.png, dungeon_page.png)
- Updated PROGRESS.md to reflect new icon organization strategy

### Removed
- Deprecated flat icon structure in cv-images/icons/ root directory

## [0.4.0] - 2026-01-18

### Added
- **T017**: PVP loading screen detection with abort button handling
  - `ScreenState.PVP_LOADING` state for PVP loading screens
  - `is_loading_screen()` method for generic and PVP loading detection
  - `is_pvp_loading()` method for PVP-specific loading detection
  - `get_abort_button_location()` to find abort button coordinates
  - `has_ad_bonus_button()` to check for ad bonus button
  - 14 comprehensive unit tests for loading screen functionality
- **T014**: Context-aware icon detection to prevent false positives
  - `ContextAwareIconDetector` class with screen-state validation
  - `IconROI` dataclass with resolution scaling
  - `ICON_ROI_MAP` defining allowed states per icon
  - Menu context detection with 90% minimum confidence requirement
  - ROI-based filtering (Y=1180-1414 for gamemode, Y=1414-1600 for menu)
  - 13 unit tests for icon detection functionality

### Fixed
- Type errors in `screenshot.py` (forward reference and union attribute access)
- False-positive icon detection on wrong screens

### Changed
- Enhanced CI/CD pipeline with pip caching and coverage threshold enforcement
- Increased confidence thresholds for template matching (0.85-0.90)

## [0.3.0] - 2026-01-18

### Added
- **T007**: PvE Dungeon automation loop with full battle management
  - `DungeonLoop` class for dungeon farming automation
  - Chapter/floor selection with template matching
  - Auto-retry system for defeats
  - Advertisement and popup handling
  - Continuous mode for multiple runs
  - 43 unit tests for dungeon functionality
- **T008**: Mana management system with intelligent upgrade prioritization
  - `ManaManager` class with OCR-based mana detection
  - Upgrade recommendation system based on priority
  - Boss-wave mana reserve functionality
  - Summon cost tracking (50 + 10*n, max 1200)
  - 47 unit tests for mana management
- **T009**: Screen state detection system
  - `ScreenStateDetector` with template matching for all UI screens
  - 11 screen states (HOME, BATTLE, DUNGEON_SELECT, POPUP, etc.)
  - Convenience methods for common checks
  - Button localization (close, back buttons)
  - 32 unit tests for screen state detection

### Changed
- Enhanced screenshot pipeline with scrcpy integration (<50ms latency)
- Improved device manager with auto-reconnect and state tracking

## [0.2.0] - 2026-01-18

### Added
- **T006**: Optimized screenshot pipeline
  - `ScreenshotPipeline` class with scrcpy primary source
  - ADB fallback for reliability
  - Frame buffer for consistent analysis
  - Latency monitoring and statistics
  - 34 unit tests for screenshot functionality
- **T005**: Enhanced device manager
  - Auto-reconnect on connection loss
  - State tracking with callbacks
  - Screenshot retry mechanism
  - Thread-safe operations
  - 23 unit tests for device management
- **T010**: Increased test coverage to 55%
  - 70+ new unit tests for core modules
  - Coverage improvements: bot.py (100%), device.py (85%), logger.py (100%)

### Fixed
- **T003**: Merge logic stabilization
  - Type validation for unit merging
  - DPS unit protection system
  - Correct merge direction calculation
  - 31 unit tests for merge logic
- **T002**: Grid parsing for multiple resolutions
  - `GridExtractor` class for resolution-independent coordinates
  - Automatic scaling for 720p-1440p
  - Helper methods for cell positioning
  - 20 unit tests for grid extraction

### Changed
- Completed type hints across all modules (mypy clean)
- Formatted all code with ruff

## [0.1.0] - 2026-01-18

### Added
- Initial project structure with modular package layout
- Core bot functionality with unit recognition
- Basic GUI with CustomTkinter
- Configuration management via config.ini
- Logging system with file and console output
- ADB device connection management
- Template matching for game elements
- Grid-based unit detection (3x5 grid)
- Initial test suite (22 tests)

### Changed
- Migrated from flat structure to `src/rush_bot/` package
- Refactored perception module for better organization
- Improved error handling in GUI

### Fixed
- Undefined variable bugs in exception handlers
- Import issues in legacy modules

---

## Version History Summary

- **0.4.0** - Loading screen detection & context-aware icons (T014, T017)
- **0.3.0** - Dungeon automation, mana management, screen state detection (T007-T009)
- **0.2.0** - Screenshot pipeline, device manager, test coverage, merge logic (T002-T006, T010)
- **0.1.0** - Initial release with core functionality

[Unreleased]: https://github.com/mleem97/Rush-Royale-Bot/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/mleem97/Rush-Royale-Bot/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/mleem97/Rush-Royale-Bot/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/mleem97/Rush-Royale-Bot/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/mleem97/Rush-Royale-Bot/releases/tag/v0.1.0
