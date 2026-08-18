"""Command-line entry point for RushBot game-build safety and versioned capture."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from rushbot.adb import AdbBackend, AdbError
from rushbot.capture import AdbScreenshotProvider, CaptureError
from rushbot.game_capture import capture_game_frame
from rushbot.game_version import (
    DEFAULT_GAME_PACKAGE,
    GameVersionError,
    RuntimeMode,
    SupportMatrix,
    inspect_game_build,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rushbot-game",
        description=(
            "Inspect the installed Rush Royale build, apply the fail-closed support matrix, "
            "and create versioned diagnostic captures."
        ),
    )
    parser.add_argument("--adb", help="Explicit path to the official adb executable.")
    parser.add_argument(
        "--matrix",
        type=Path,
        help="Optional support-matrix TOML; defaults to the reviewed packaged matrix.",
    )
    parser.add_argument(
        "--package",
        default=DEFAULT_GAME_PACKAGE,
        help=f"Android package to inspect (default: {DEFAULT_GAME_PACKAGE}).",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    status = subparsers.add_parser(
        "status",
        help="Show exact package version and the maximum permitted runtime mode.",
    )
    status.add_argument("serial", help="Exact serial shown by 'rushbot-device devices'.")
    status.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    status.add_argument(
        "--request-mode",
        choices=[mode.value for mode in RuntimeMode],
        default=RuntimeMode.LIVE.value,
        help="Mode to evaluate against the compatibility gate (default: live).",
    )
    status.add_argument(
        "--strict",
        action="store_true",
        help="Exit with code 3 when the requested mode is downgraded.",
    )

    capture = subparsers.add_parser(
        "capture",
        help="Capture a PNG plus a JSON sidecar containing the exact game build.",
    )
    capture.add_argument("serial", help="Exact serial shown by 'rushbot-device devices'.")
    capture.add_argument("output", type=Path, help="Destination .png path.")
    capture.add_argument("--metadata", type=Path, help="Optional JSON sidecar path.")
    capture.add_argument(
        "--alias",
        help="Privacy-safe local device alias; a stable hash alias is used by default.",
    )
    capture.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")

    return parser


def _status_payload(
    *,
    adb: AdbBackend,
    matrix: SupportMatrix,
    serial: str,
    package_name: str,
    requested_mode: RuntimeMode,
) -> dict[str, object]:
    build = inspect_game_build(adb, serial, package_name)
    decision = matrix.evaluate(build)
    authorization = decision.authorize(requested_mode)
    payload = decision.as_dict()
    payload["authorization"] = authorization.as_dict()
    return payload


def _print_status(payload: dict[str, object]) -> None:
    build = payload["build"]
    authorization = payload["authorization"]
    assert isinstance(build, dict)
    assert isinstance(authorization, dict)
    print(f"Package: {build['package_name']}")
    print(f"Version: {build['version_name'] or 'unknown'} (code {build['version_code']})")
    print(f"Compatibility: {payload['status']}")
    print(f"Maximum mode: {payload['maximum_runtime_mode']}")
    print(f"Requested mode: {authorization['requested_mode']} -> {authorization['effective_mode']}")
    print(f"Live actions: {'ALLOWED' if payload['live_actions_allowed'] else 'BLOCKED'}")
    print(f"Reason: {payload['reason']}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)

    try:
        matrix = SupportMatrix.load(arguments.matrix)
        adb = AdbBackend(arguments.adb)

        if arguments.command == "status":
            payload = _status_payload(
                adb=adb,
                matrix=matrix,
                serial=arguments.serial,
                package_name=arguments.package,
                requested_mode=RuntimeMode(arguments.request_mode),
            )
            if arguments.json:
                print(json.dumps(payload, indent=2, sort_keys=True))
            else:
                _print_status(payload)
            authorization = payload["authorization"]
            assert isinstance(authorization, dict)
            if arguments.strict and authorization["downgraded"]:
                return 3
            return 0

        if arguments.command == "capture":
            result = capture_game_frame(
                screenshot_provider=AdbScreenshotProvider(adb),
                package_backend=adb,
                support_matrix=matrix,
                serial=arguments.serial,
                output_path=arguments.output,
                metadata_path=arguments.metadata,
                serial_alias=arguments.alias,
                package_name=arguments.package,
            )
            output = {
                "image_path": str(result.image_path),
                "metadata_path": str(result.metadata_path),
                "manifest": result.manifest.as_dict(),
            }
            if arguments.json:
                print(json.dumps(output, indent=2, sort_keys=True))
            else:
                print(f"Image: {result.image_path}")
                print(f"Metadata: {result.metadata_path}")
                print(f"Build: {result.manifest.build.build_id}")
                print(f"Compatibility: {result.manifest.compatibility.status.value}")
                print("Live actions: BLOCKED (capture command is diagnostic only)")
            return 0

    except (
        AdbError,
        CaptureError,
        GameVersionError,
        FileNotFoundError,
        OSError,
        ValueError,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    parser.error(f"Unknown command: {arguments.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
