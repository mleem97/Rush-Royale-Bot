# RushBot

RushBot automates parts of Rush Royale through computer vision, a small scikit-learn rank classifier, and Android Debug Bridge (ADB) input commands.

> This project is intended for education and research. Check the game's terms before using automation.

## Supported platforms

| Platform | Python | Device backend | Status |
|---|---:|---|---|
| Windows 10/11 | 3.11-3.13 | Official Android Platform Tools (`adb.exe`) | CI tested |
| Linux | 3.11-3.13 | Official Android Platform Tools (`adb`) | CI tested |

The bot no longer depends on a third-party Python implementation of the ADB protocol. A small compatibility layer calls Google's official `adb` executable on both operating systems. This also supports USB devices, emulators, and TCP/IP serials such as `192.168.1.20:5555`.

## Installation

### Windows

1. Install Python 3.11 or newer.
2. Run:

```bat
install.bat
launch_gui.bat
```

When ADB is missing and `winget` is available, `install.bat` installs the official scrcpy package. Scrcpy includes the required ADB dependency. You can instead install [Android SDK Platform Tools](https://developer.android.com/tools/releases/platform-tools) yourself or extract the official [scrcpy Windows release](https://github.com/Genymobile/scrcpy/blob/master/doc/windows.md) into `.scrcpy`.

### Linux

Install Python, Tk, and ADB through the distribution package manager. Examples:

```bash
# Debian/Ubuntu
sudo apt install python3 python3-venv python3-tk adb

# Fedora
sudo dnf install python3 python3-tkinter android-tools

# Arch Linux
sudo pacman -S python tk android-tools
```

Then run:

```bash
bash install.sh
bash launch_gui.sh
```

For the newest Platform Tools rather than the distribution package, download Google's current Linux archive and set `ADB_PATH` to its `adb` executable. See [Linux ADB setup](docs/linux-adb.md).

## Connect a device

Enable USB debugging on the Android device, then verify the connection:

```bash
adb start-server
adb devices
```

RushBot uses the first online device by default. Select one explicitly when several devices are attached:

```bash
# Linux
export RUSHBOT_DEVICE=emulator-5554

# Windows PowerShell
$env:RUSHBOT_DEVICE = "emulator-5554"
```

The standard `ANDROID_SERIAL` environment variable is also supported. Local emulator ports are discovered automatically with a bounded scanner. Override its range with `RUSHBOT_SCAN_PORT_RANGE`, for example `5555-5600`.

## scikit-learn model compatibility

scikit-learn does not guarantee that pickled estimators can be loaded across library versions. RushBot therefore:

1. loads `rank_model.pkl` only once instead of once per grid cell;
2. treats `InconsistentVersionWarning` as an incompatibility;
3. retrains from `machine_learning/inputs` using the installed scikit-learn version;
4. replaces the old model atomically.

Manual retraining remains available:

```bash
.bot_env/bin/python Src/train_rank_model.py          # Linux
.bot_env\Scripts\python.exe Src\train_rank_model.py  # Windows
```

Do not load model files from untrusted sources: Python pickle files can execute code while loading.

## Optional scrcpy diagnostics

[scrcpy](https://github.com/Genymobile/scrcpy) is optional. It is useful for checking the device view and ADB connection, but screenshots and touch input are performed through ADB directly:

```bash
scrcpy --serial emulator-5554 --no-audio
```

## Dependency policy

`requirements.txt` pins a tested runtime set so the serialized model and numerical stack are reproducible. `requirements-dev.txt` adds Jupyter, Matplotlib, and pytest. Dependency updates should update these pins together with cross-platform CI.

## Development

```bash
python -m pip install -r requirements-dev.txt
python -m compileall -q Src tests
python -m pytest -q
```

GitHub Actions runs the checks on Windows and Linux with Python 3.11 and 3.13.

## Configuration

The existing `config.ini` controls the floor, deck, mana targets, PvE mode, and optional Shaman requirement. Launchers always change to the repository root first, so relative image paths behave the same on Windows and Linux.

## Project history

RushBot builds on work from:

- [AxelBjork/Rush-Royale-Bot](https://github.com/AxelBjork/Rush-Royale-Bot)
- [mleem97/Rush-Royale-Bot](https://github.com/mleem97/Rush-Royale-Bot)
- [Frikadellental/Rush-Royale-AI](https://github.com/Frikadellental/Rush-Royale-AI)

## License

MIT — see [LICENSE](LICENSE).
