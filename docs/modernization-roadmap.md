# RushBot 2 modernization roadmap

## Acceptance definition

RushBot 2 is considered restored only when a clean checkout can be installed, tested and run
against at least one emulator and one physical Android device without BlueStacks-specific
paths or legacy Python dependencies. A passing import or GUI launch alone is not sufficient.

## Phase 0 — provenance and recovery

Status: **completed**

- preserve the old fork at `archive/pre-modernization-2026-08-18`;
- preserve the original upstream at `upstream/axelbjork-main`;
- create `modernization/rushbot-2.0` from the exact upstream commit;
- document recovery and protection rules;
- avoid rebasing or force-moving the divergent `main` history.

Exit gate: all three branch heads are independently recoverable by SHA.

## Phase 1 — device and capture foundation

Status: **implemented in the initial modernization commit**

- Python 3.14 project metadata and cross-platform CI;
- official ADB executable discovery and command wrapper;
- USB, emulator, Android Wireless Debugging and legacy TCP/IP support;
- exact serial selection for systems with multiple devices;
- deterministic atomic PNG screenshots;
- official scrcpy 4.x discovery, version gate and managed process lifetime;
- optional Linux V4L2 bridge for high-rate OpenCV input;
- command-line diagnostics and unit tests without a connected device;
- removal of implicit broad LAN port scanning.

Exit gate: `rushbot-device doctor`, list, pair, connect, screenshot and mirror work on Linux
and Windows with clear errors.

## Phase 2 — migrate the legacy bot engine

Status: **next**

1. Introduce an `AndroidTarget` protocol containing capture and input operations.
2. Remove direct `adb`, `ppadb` and scrcpy imports from legacy game logic.
3. Make the Android package ID configurable instead of hard-coding `com.my.defense`.
4. Replace working-directory-relative paths with a typed application path service.
5. Separate state detection, decision policy and action execution.
6. Normalize coordinates from a reference canvas to the actual frame dimensions and account
   for orientation, navigation bars, display cutouts and letterboxing.
7. Convert configuration from mutable shared INI access to validated typed settings while
   retaining an importer for existing `config.ini` files.
8. Replace untrusted pickle loading with a versioned numerical or ONNX model artifact.
9. Port useful rank-model migration work selectively from the archived fork.
10. Add graceful cancellation, bounded retries and structured error categories.

Exit gate: the engine can process a recorded frame sequence and emit an action plan without
ADB, a GUI or a live account.

## Phase 3 — screenshot replay and regression fixtures

- create a private replay corpus covering home, PvE selection, loading, combat, result,
  interruption and recovery states;
- redact account/player information before a fixture becomes public;
- add golden detections and action plans for each fixture;
- detect UI-version drift instead of lowering template thresholds globally;
- test multiple aspect ratios, Android scaling modes and locales;
- prevent actions when the frame is stale, incomplete or outside a known state.

Exit gate: deterministic replay tests cover every state transition used by live automation.

## Phase 4 — ML data and model pipeline

- implement consent-aware screenshot import and manifests;
- add duplicate/perceptual-hash checks and source-grouped data splits;
- add an offline directory importer for authorized Unity PNG exports;
- build labeling tools for board cells, units, rank, controls and screen state;
- evaluate template matching against a trained detector/classifier baseline;
- add confidence calibration, temporal smoothing and out-of-distribution rejection;
- package models in a version-neutral format with model cards.

Exit gate: a model can be reproduced from documented inputs and evaluated on a protected
holdout set without loading arbitrary pickle files.

## Phase 5 — operator UI

The UI must consume the same public application services as the CLI. Required views:

- environment doctor and installation status;
- device list grouped by emulator, USB and network;
- Wireless Debugging pairing dialog with separate pairing and connection endpoints;
- authorization/offline/error states with concrete recovery actions;
- scrcpy preview controls, view-only mode and Linux V4L2 status;
- game package selection and launch/stop controls;
- deck/unit configuration and validation;
- live screenshot, detected state, confidence and planned action;
- start, pause, emergency stop and shadow-mode controls;
- session logs and an exportable diagnostics bundle with secrets redacted;
- dataset capture consent and privacy controls.

No GUI callback may contain game logic or raw subprocess calls.

Exit gate: closing or stopping the UI always terminates automation and child scrcpy processes
without leaving input workers active.

## Phase 6 — live-device validation

Test matrix:

| Host | Target | Transport | Required result |
|---|---|---|---|
| Ubuntu/GNOME | Linux Android runtime | local ADB | discover, capture, input, mirror |
| Ubuntu/GNOME | physical Android 11+ | Wireless Debugging | pair, reconnect, capture, mirror |
| Ubuntu/GNOME | physical Android | USB | authorize, capture, input |
| Windows 11 | Android emulator | local/network ADB | discover, capture, input, mirror |
| Windows 11 | physical Android | USB/Wi-Fi | same behavior and configuration |

Start with shadow mode. Live actions are enabled only after the same session succeeds in
observation-only mode and all target dimensions are calibrated.

Exit gate: no transport-specific game logic and no unexplained action outside the recorded
state machine.

## Phase 7 — packaging and release

- Linux package or portable bundle with desktop entry;
- Windows portable bundle or signed installer;
- explicit dependency checks for ADB and scrcpy instead of bundling unknown binaries;
- checksums, SBOM, reproducible build notes and release provenance;
- migration guide from the archived fork;
- semantic versioning and compatibility matrix for Python, ADB, scrcpy, Android and game UI;
- release notes that distinguish tested from experimental device modes.

Exit gate: a release artifact installs on a clean machine and the doctor explains every
missing external prerequisite.

## Immediate implementation order

1. Port the rank-model numerical artifact code from the archive with security review.
2. Implement `AndroidTarget` plus an ADB-backed adapter.
3. Extract legacy state detection into replayable pure functions.
4. Add the first redacted screenshot fixtures.
5. Replace hard-coded coordinate and package assumptions.
6. Run the first emulator smoke test, then a physical USB test, then Wireless Debugging.
