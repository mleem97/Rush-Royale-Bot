# Android device, ADB and scrcpy architecture

## Design goals

RushBot must treat an emulator and a physical Android device as equivalent automation
targets once ADB has authorized them. The game logic receives a serial, screenshots and
normalized input operations; it must not know whether the target is USB, wireless or an
emulator.

The transport layer has four responsibilities:

1. discover and identify ADB targets;
2. pair or connect network devices without leaking pairing secrets;
3. capture deterministic frames and send ordinary Android input events;
4. launch scrcpy as an optional user-visible or high-rate video process.

## Components

### `rushbot.adb.AdbBackend`

Uses Google's official `adb` executable through argument arrays and never invokes a shell.
It supports:

- `adb devices -l` parsing with state and model metadata;
- exact serial selection for multi-device systems;
- Android 11+ `adb pair` with the code sent over standard input;
- `adb connect` and `adb disconnect`;
- classic `adb tcpip PORT` after USB authorization;
- screenshots through `adb exec-out screencap -p`;
- tap, swipe, key-event, package start and package stop operations.

The broad 48,000–65,000 port scan used in the previous fork is intentionally removed.
Wireless Debugging exposes pairing and connection ports explicitly and modern ADB uses mDNS
for discovery. Unsolicited LAN scanning is slower, unreliable and harder to secure.

### `rushbot.capture.AdbScreenshotProvider`

This is the portable single-frame baseline. It validates the PNG signature and writes files
atomically, preventing the perception pipeline from reading a partially written screenshot.
It works identically with USB, TCP/IP and emulator serials.

### `rushbot.scrcpy.ScrcpyClient`

Locates and validates an official scrcpy 4.x executable, then starts it as an external
process. RushBot does not vendor a Python package that imitates scrcpy's private protocol.
This avoids client/server version drift and keeps the upstream security and compatibility
fixes replaceable without changing RushBot.

### `rushbot.capture.V4L2FrameSource`

On Linux, scrcpy can write video to a `v4l2loopback` device. OpenCV can then consume the
Android screen as a regular `/dev/videoN` source. This path is intended for higher-rate
observation and ML dataset collection; ADB PNG capture remains the diagnostic fallback.

## Connection workflows

### USB debugging

1. Enable Android developer options and USB debugging.
2. Connect the cable.
3. Unlock the phone and accept the RSA authorization prompt.
4. Run:

```bash
rushbot-device devices
rushbot-device screenshot SERIAL test.png
```

An `unauthorized` state means the confirmation on the Android device has not been accepted.
A `no-permissions` state on Linux normally indicates missing udev permissions.

### Android 11+ Wireless Debugging

The pairing endpoint and connection endpoint are usually different dynamic ports.

1. On Android, open **Developer options → Wireless debugging**.
2. Select **Pair device with pairing code**.
3. Pair using the endpoint shown in that dialog:

```bash
rushbot-device pair 192.168.1.50:37123
```

4. Enter the code at the hidden prompt.
5. Connect using the separate connection endpoint shown on the main Wireless Debugging
   screen:

```bash
rushbot-device connect 192.168.1.50:42157
rushbot-device devices
```

Do not put the pairing code in shell scripts or repository configuration. The CLI accepts an
interactive code by default specifically to keep it out of shell history.

### Classic ADB TCP/IP

This method is required for many Android 10 and older devices and remains useful for some
emulators.

```bash
# Device must already be authorized over USB
rushbot-device tcpip USB_SERIAL --port 5555
rushbot-device connect 192.168.1.50:5555
```

Disconnect when finished:

```bash
rushbot-device disconnect 192.168.1.50:5555
```

### Emulator or Linux Android runtime

The runtime must expose a normal ADB serial. RushBot does not require a vendor-specific SDK.
Examples include `emulator-5554`, `127.0.0.1:5555` or another explicit host/port endpoint.
The planned Linux Android application should publish the selected instance serial through
its integration API and let RushBot consume it unchanged.

## scrcpy workflows

Interactive mirror:

```bash
rushbot-device mirror SERIAL
```

Observation-only mirror:

```bash
rushbot-device mirror SERIAL --view-only --max-size 1920 --max-fps 60
```

Linux V4L2 bridge:

```bash
sudo modprobe v4l2loopback video_nr=10 card_label=RushBot exclusive_caps=1
rushbot-device mirror SERIAL \
  --view-only --v4l2-sink /dev/video10 --no-window --max-fps 60
```

The bot can then open `/dev/video10` through `V4L2FrameSource` or another OpenCV consumer.
The V4L2 path must be allocated per concurrent device when multi-device support is added.

## Security requirements

- Never expose ADB port 5037 or a device's ADB TCP port to the public internet.
- Keep Wireless Debugging limited to trusted networks.
- Revoke old host authorizations from Android when a workstation is retired.
- Do not run RushBot, ADB or scrcpy as root.
- Do not auto-accept Android authorization dialogs.
- Do not store pairing codes, RSA private keys or raw device serials in public logs.
- Remote operation must use an authenticated tunnel or run the RushBot worker beside the
  device; plain remote ADB is not an acceptable internet transport.

## Interface contract for the bot engine

The migrated game engine must depend on a small target interface rather than subprocesses:

```text
capture() -> frame
tap(x, y)
swipe(x1, y1, x2, y2, duration_ms)
keyevent(code)
start_package(package)
force_stop_package(package)
```

This contract permits live devices, emulators, replay fixtures and a future Linux runtime to
share the same decision logic and tests.
