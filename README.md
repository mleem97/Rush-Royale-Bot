# RushBot 2 — modernization branch

RushBot 2 is a clean modernization of Axel Björk's original
[`Rush-Royale-Bot`](https://github.com/AxelBjork/Rush-Royale-Bot). This branch starts from
upstream commit `f61f658459090c18b0d1f371bddc156dc0e823d7` and ports the project in
reviewable layers instead of rewriting the existing fork history.

> **Current status:** the Android device, ADB, screenshot and scrcpy foundation is usable.
> The legacy game-decision engine is retained as migration source and is not yet declared
> production-ready on current game versions.

## Project boundary

RushBot observes pixels visible on the Android screen and sends ordinary Android user-input
events through ADB. It does not require a modified game client. Optional image imports are an
offline, local-only ML preparation step; source packages and proprietary assets are excluded
from Git history and must not be redistributed from this repository.

## Supported Android targets

The same device abstraction covers:

- Android emulators exposed by ADB;
- physical devices over USB debugging;
- Android 11+ Wireless Debugging using `adb pair`;
- classic `adb tcpip` connections after an initial USB authorization;
- explicit network endpoints, including a device supplied by the planned Linux Android
  runtime application.

RushBot uses Google's official `adb` executable. Screen mirroring uses the official external
`scrcpy` client; its private client/server protocol is not reimplemented in Python.

## Runtime baseline

- Python 3.14 stable
- current Android SDK Platform Tools
- scrcpy 4.x or newer
- Linux or Windows

Python 3.15 previews are intentionally not a production target.

## Installation

```bash
python3.14 -m venv .venv
source .venv/bin/activate                 # Linux
# .venv\\Scripts\\Activate.ps1            # Windows PowerShell
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Install Android SDK Platform Tools and scrcpy through your operating system or their official
release channels. RushBot does not silently download or replace these executables.

## Device workflow

```bash
# Verify tools and list targets
rushbot-device doctor
rushbot-device devices

# Android 11+ Wireless Debugging. Enter the pairing code interactively.
rushbot-device pair 192.168.1.50:37123
rushbot-device connect 192.168.1.50:42157

# Deterministic single-frame capture
rushbot-device screenshot 192.168.1.50:42157 data/screenshots/current.png

# Interactive mirror, or view-only mirror
rushbot-device mirror 192.168.1.50:42157
rushbot-device mirror 192.168.1.50:42157 --view-only

# Linux low-latency frame source for OpenCV/ML
rushbot-device mirror 192.168.1.50:42157 \\
  --view-only --v4l2-sink /dev/video10 --no-window
```

Never expose the ADB server directly to an untrusted network. Use local ADB or an authenticated
SSH tunnel for remote-host scenarios.

## Repository branches

| Branch | Purpose |
|---|---|
| `archive/pre-modernization-2026-08-18` | Snapshot of the previous fork state |
| `upstream/axelbjork-main` | Exact mirror of the last upstream `main` commit |
| `modernization/rushbot-2.0` | Clean Python 3.14 modernization from upstream |
| `main` | Existing fork history until migration acceptance |

See [the branch strategy](docs/branch-strategy.md) and
[the modernization roadmap](docs/modernization-roadmap.md) before merging histories.

## Documentation

- [Device, ADB and scrcpy architecture](docs/device-support.md)
- [Modernization roadmap](docs/modernization-roadmap.md)
- [ML data and Unity asset policy](docs/ml-data-pipeline.md)
- [Branch strategy and recovery](docs/branch-strategy.md)

## Attribution and license

The original project was created by Axel Björk and is licensed under the MIT License. New
work in this fork remains under the repository's MIT License unless a file explicitly states
otherwise. Rush Royale and its assets belong to their respective rightsholders; they are not
included under the MIT License.
