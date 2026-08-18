# Android target and coordinate contract

## Purpose

The original RushBot was authored around a portrait **900 × 1600** game surface. Directly
sending those coordinates to every current device is unsafe: phones, emulators and the planned
Linux Android runtime may expose different resolutions, system-bar insets, letterboxing or a
rotated display.

The modernization therefore separates three layers:

1. perception reads a frame and produces a game state;
2. decision code produces a pure `ActionPlan` in the 900 × 1600 reference space;
3. an `AndroidTarget` maps and executes that plan on one exact ADB serial.

No game-state detector or policy may invoke `adb`, `scrcpy` or subprocesses directly.

## Reference geometry

The canonical reference size is:

```text
width:   900 px
height: 1600 px
orientation: portrait
```

Reference coordinates remain stable even when the target resolution changes. Mapping is
edge-to-edge rather than based on integer scale factors, so both the first and final reference
pixels map exactly to the first and final content pixels.

Examples:

| Reference point | 900 × 1600 target | 1440 × 2560 target |
|---|---:|---:|
| top-left | `(0, 0)` | `(0, 0)` |
| approximate center | `(450, 800)` | `(720, 1280)` |
| bottom-right | `(899, 1599)` | `(1439, 2559)` |

## Viewport calibration

`ScreenGeometry` models both the complete captured frame and the game viewport inside it.
The viewport can be selected in two ways:

- `FULL_FRAME`: use the available frame after configured insets;
- `CONTAIN`: center the rotated reference aspect ratio inside the available frame.

Explicit insets remove status bars, navigation bars or emulator chrome before aspect fitting.
For a 1440 × 3088 frame, `CONTAIN` produces a centered 1440 × 2560 viewport with 264 pixels
above and below it. This is a starting calibration, not permission to guess silently: live
validation must confirm the actual rendered viewport for each game/device combination.

The calibration record should eventually persist:

```json
{
  "schema_version": 1,
  "serial_alias": "local-device-1",
  "frame": {"width": 1440, "height": 3088},
  "content": {"left": 0, "top": 264, "width": 1440, "height": 2560},
  "rotation": 0,
  "reference": {"width": 900, "height": 1600},
  "verified_game_version": "operator supplied",
  "verified_at": "RFC3339 timestamp"
}
```

Do not store a raw hardware serial in a public calibration file. Use a local alias.

## `AndroidTarget` interface

The migrated engine receives only this transport-neutral capability set:

```text
serial
geometry
capture_png(output_path=None)
tap_reference(point)
swipe_reference(start, end, duration_ms)
keyevent(code)
start_package(package)
force_stop_package(package)
```

`AdbAndroidTarget` implements the contract with the official `adb` executable. The same class
works with USB serials, Android Wireless Debugging endpoints, classic TCP/IP endpoints and
emulator serials.

## Action plans

`rushbot.actions.ActionPlan` is a deterministic decision result. It records ordered actions,
a reason, confidence and optional source-frame identifier. It contains no device handle and
no perception callback. This permits:

- replay tests without ADB;
- shadow mode that logs plans without executing them;
- comparison of old and new policies on identical frames;
- cancellation between every action;
- audit logs that explain why an action was proposed.

A live controller must apply additional gates before calling `execute_plan`: target online,
frame freshness, recognized state, minimum confidence, rate limit, emergency stop and a
matching game-package foreground check.

## Migration rule for legacy code

When a legacy function currently calls `tap`, `swipe`, `screencap`, `subprocess` or a bundled
ADB client, migrate it as follows:

1. make detection consume a frame or normalized crop only;
2. return a typed state rather than mutating the bot directly;
3. make policy return an `ActionPlan` in reference coordinates;
4. execute the plan through an injected `AndroidTarget`;
5. add a screenshot-replay test before enabling live input.

Direct transport calls remaining under legacy `Src/` are migration source, not the final
architecture.
