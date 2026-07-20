# Reliable ADB setup on Linux

RushBot's recommended Linux backend is Google's official `adb` executable from Android SDK Platform Tools. The Python code uses `subprocess` with argument arrays and never invokes a shell, so command behaviour is the same on Linux and Windows.

## Option 1: Distribution package

This is the simplest setup and receives security/bug-fix updates through the system package manager.

```bash
# Debian/Ubuntu
sudo apt update
sudo apt install adb

# Fedora
sudo dnf install android-tools

# Arch Linux
sudo pacman -S android-tools
```

Verify:

```bash
adb version
adb start-server
adb devices -l
```

## Option 2: Google's current Platform Tools

Google publishes a stable Linux archive whose download target always points at the current Platform Tools release:

1. Download **SDK Platform Tools for Linux** from <https://developer.android.com/tools/releases/platform-tools>.
2. Extract it, for example to `~/Android/platform-tools`.
3. Either add it to `PATH`:

```bash
export PATH="$HOME/Android/platform-tools:$PATH"
```

or point RushBot directly at the executable:

```bash
export ADB_PATH="$HOME/Android/platform-tools/adb"
```

Persist the export in `~/.bashrc`, `~/.zshrc`, or the desktop session environment when needed.

## USB permissions

When `adb devices` shows no device or `no permissions`, install the distribution's Android udev rules package when available, add the current user to the relevant device-access group, reconnect the device, and accept the debugging authorization prompt on Android. Exact package/group names vary by distribution.

## Wireless/TCP/IP ADB

For a device already listening on TCP port 5555:

```bash
adb connect 192.168.1.20:5555
export RUSHBOT_DEVICE=192.168.1.20:5555
bash launch_gui.sh
```

On Android 11 or newer, use Android's Wireless debugging pairing flow first. RushBot intentionally delegates pairing and transport security to the installed ADB version.

## Optional scrcpy

Scrcpy uses ADB and is useful for validating video/control independently of RushBot. Use the official release rather than an outdated distribution package where applicable:

```bash
scrcpy --serial "$RUSHBOT_DEVICE" --no-audio
```

Scrcpy is not required for RushBot screenshots; the bot uses `adb exec-out screencap -p` through its compatibility backend.

## Troubleshooting

```bash
adb kill-server
adb start-server
adb devices -l
```

Then check:

- USB debugging is enabled and the host key was accepted;
- only one ADB installation is active (`command -v adb`);
- `ADB_PATH` does not point to an obsolete binary;
- the emulator exposes ADB and is fully started;
- TCP/IP devices are reachable from the same network.
