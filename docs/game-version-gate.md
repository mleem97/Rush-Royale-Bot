# Game-version compatibility gate

## Purpose

RushBot must not continue issuing live input after Rush Royale changes its rendering,
layout, controls, or game mechanics. The package name alone is not a compatibility signal.
The modernization runtime therefore reads the exact installed Android build and applies a
reviewed, fail-closed support matrix before any future live controller may act.

The default game package is `com.my.defense`.

## Safety invariants

1. An unknown build is always reduced to `capture_only`.
2. A broad `version_name_prefix` rule may classify builds for capture, deprecation, or explicit
   rejection, but it can never authorize replay, shadow, or live operation.
3. Every validated status requires one exact Android `versionCode`.
4. Only `live_validated` permits live touch, swipe, key, start, or stop actions.
5. Requesting a mode above the validated stage returns a visible downgrade instead of silently
   pretending that the requested mode is safe.
6. Versioned captures store a privacy-safe serial alias, not the raw USB, emulator, or network
   serial.
7. The packaged matrix contains no live-approved build at bootstrap. Version 37.x is recognized
   for diagnostic capture only until its replay, shadow, and live suites have been completed.

These rules are enforced by `rushbot.game_version.SupportMatrix` and
`SupportDecision.require_live_actions()`.

## Compatibility stages

| Status | Capture | Offline replay | Shadow decisions | Live input |
|---|---:|---:|---:|---:|
| `unsupported` | yes, for diagnosis | no | no | no |
| `capture_only` | yes | no | no | no |
| `replay_validated` | yes | yes | no | no |
| `shadow_validated` | yes | yes | yes | no |
| `live_validated` | yes | yes | yes | yes |
| `deprecated` | yes, for migration | no | no | no |

`capture_only` is the default status for every unlisted or newly updated build.

## Inspect the installed build

```bash
rushbot-game status emulator-5554
rushbot-game status 192.168.1.20:5555 --json
```

The command executes the equivalent of:

```bash
adb -s <serial> shell dumpsys package com.my.defense
```

It parses the stable package fields including `versionName`, `versionCode`, SDK levels,
installation time, update time, and installer package. The output also shows the highest runtime
mode permitted by the matrix.

Evaluate a specific mode and fail automation when it is downgraded:

```bash
rushbot-game status emulator-5554 --request-mode live --strict
```

Exit codes:

- `0`: inspection succeeded and, with `--strict`, the requested mode was permitted;
- `2`: ADB, package parsing, matrix, capture, or filesystem error;
- `3`: `--strict` was used and the requested mode was downgraded.

## Create a versioned capture

```bash
rushbot-game capture emulator-5554 data/private/v37/frame-0001.png
```

This writes:

```text
data/private/v37/frame-0001.png
data/private/v37/frame-0001.png.json
```

The JSON sidecar contains:

```json
{
  "schema_version": 1,
  "frame_id": "sha256:<image digest>",
  "captured_at": "RFC3339 UTC timestamp",
  "serial_alias": "device-<truncated serial hash>",
  "capture_mode": "capture_only",
  "game_build": {
    "package_name": "com.my.defense",
    "version_name": "operator device value",
    "version_code": 0,
    "last_update_time": "operator device value"
  },
  "compatibility": {
    "status": "capture_only",
    "live_actions_allowed": false
  }
}
```

Use an explicit local alias when desired:

```bash
rushbot-game capture emulator-5554 frame.png --alias linux-runtime-lab-1
```

Do not use an account name, hardware serial, IP address, or other personal identifier as the
alias.

## Support matrix

The reviewed default matrix is stored at:

```text
src/rushbot/data/support-matrix.toml
```

A broad capture rule is valid:

```toml
[[builds]]
id = "rush-royale-37x-capture-baseline"
package = "com.my.defense"
version_name_prefix = "37."
status = "capture_only"
reason = "Version 37.x capture baseline; validation is pending."
```

A live rule must pin an exact `versionCode`:

```toml
[[builds]]
id = "rush-royale-37-0-1-build-3700123"
package = "com.my.defense"
version_name = "37.0.1"
version_code = 3700123
status = "live_validated"
reason = "Replay, shadow, USB, and Wireless Debugging validation passed."
```

The example number above is illustrative. Never copy a version code from documentation or a
store marketing version. Read it from the exact installed package and record evidence in the
validation report.

A custom matrix can be checked without replacing the packaged policy:

```bash
rushbot-game --matrix ./local-support-matrix.toml status emulator-5554
```

## Promotion workflow

For every new Android `versionCode`:

1. leave it at the default `capture_only` status;
2. collect private, versioned screenshots from the supported resolutions and transports;
3. update labels and pass the complete offline replay suite;
4. add an exact `replay_validated` rule;
5. run full matches in shadow mode without issuing input;
6. promote the exact build to `shadow_validated`;
7. validate emergency stop, frame freshness, foreground package checks, rate limits, USB, and
   Wireless Debugging on dedicated test accounts/devices;
8. promote only that exact build to `live_validated` through a reviewed pull request;
9. return the build to `capture_only` or `deprecated` immediately when a regression is found.

A later game update receives a different `versionCode` and therefore cannot inherit a previous
live approval.

## Integration rule for the future controller

A controller must retain the `SupportDecision` tied to the inspected build and call
`require_live_actions()` immediately before entering live mode. It must additionally re-check the
installed build when the package update time changes or the application restarts. Version approval
does not replace the remaining live gates: foreground-package verification, frame freshness,
recognized screen state, confidence threshold, action-rate limit, cancellation, and emergency
stop remain mandatory.
