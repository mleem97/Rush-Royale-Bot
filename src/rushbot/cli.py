"""Device-management command line for the RushBot modernization branch."""

from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
from pathlib import Path

from rushbot import __version__
from rushbot.adb import AdbBackend, AdbError
from rushbot.capture import AdbScreenshotProvider
from rushbot.scrcpy import ScrcpyClient, ScrcpyError, ScrcpyOptions


def _add_serial_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("serial", help="Exact serial shown by 'rushbot-device devices'.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rushbot-device",
        description="Manage USB, wireless, network and emulator Android targets for RushBot.",
    )
    parser.add_argument("--adb", help="Explicit path to the official adb executable.")
    parser.add_argument("--scrcpy", help="Explicit path to the official scrcpy executable.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    devices = subparsers.add_parser("devices", help="List all ADB-visible targets.")
    devices.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    devices.add_argument("--online-only", action="store_true")

    doctor = subparsers.add_parser("doctor", help="Check ADB, scrcpy and connected devices.")
    doctor.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")

    pair = subparsers.add_parser(
        "pair", help="Pair Android 11+ Wireless Debugging using IP:pairing-port."
    )
    pair.add_argument(
        "endpoint",
        help="Pairing endpoint shown by Android, for example 10.0.0.4:37123.",
    )
    pair.add_argument(
        "--code",
        help="Pairing code. Omit this option to enter it without storing it in shell history.",
    )

    connect = subparsers.add_parser("connect", help="Connect to an ADB network endpoint.")
    connect.add_argument("endpoint", help="Connection endpoint, for example 10.0.0.4:42157.")

    disconnect = subparsers.add_parser("disconnect", help="Disconnect one or all network targets.")
    disconnect.add_argument("endpoint", nargs="?")

    tcpip = subparsers.add_parser(
        "tcpip", help="Enable legacy ADB TCP/IP on a USB-connected target."
    )
    _add_serial_argument(tcpip)
    tcpip.add_argument("--port", type=int, default=5555)

    screenshot = subparsers.add_parser("screenshot", help="Capture one deterministic PNG via ADB.")
    _add_serial_argument(screenshot)
    screenshot.add_argument("output", type=Path)

    mirror = subparsers.add_parser("mirror", help="Open official scrcpy for one target.")
    _add_serial_argument(mirror)
    mirror.add_argument("--view-only", action="store_true", help="Disable keyboard/mouse control.")
    mirror.add_argument("--audio", action="store_true", help="Enable scrcpy audio forwarding.")
    mirror.add_argument("--max-size", type=int)
    mirror.add_argument("--max-fps", type=int)
    mirror.add_argument("--turn-screen-off", action="store_true")
    mirror.add_argument("--v4l2-sink", help="Linux loopback target such as /dev/video10.")
    mirror.add_argument(
        "--no-window",
        action="store_true",
        help="Disable video playback window; normally used with --v4l2-sink.",
    )
    mirror.add_argument("--record", type=Path)
    mirror.add_argument("--log", type=Path)

    start_app = subparsers.add_parser("start-app", help="Start an Android package through ADB.")
    _add_serial_argument(start_app)
    start_app.add_argument("package")

    stop_app = subparsers.add_parser("stop-app", help="Force-stop an Android package through ADB.")
    _add_serial_argument(stop_app)
    stop_app.add_argument("package")

    return parser


def _doctor(
    adb_path: str | None, scrcpy_path: str | None
) -> tuple[dict[str, object], bool]:
    report: dict[str, object] = {"rushbot": __version__}
    healthy = True
    try:
        adb = AdbBackend(adb_path)
        report["adb"] = {"path": adb.executable, "version": adb.version()}
        devices = adb.devices()
        report["devices"] = [device.as_dict() for device in devices]
    except (AdbError, FileNotFoundError, ValueError) as exc:
        report["adb"] = {"error": str(exc)}
        report["devices"] = []
        healthy = False

    try:
        scrcpy = ScrcpyClient(scrcpy_path)
        report["scrcpy"] = {
            "path": scrcpy.executable,
            "version": str(scrcpy.ensure_supported()),
        }
    except (ScrcpyError, FileNotFoundError, ValueError) as exc:
        report["scrcpy"] = {"error": str(exc)}
        healthy = False
    return report, healthy


def _print_doctor(report: dict[str, object]) -> None:
    print(f"RushBot: {report['rushbot']}")
    for name in ("adb", "scrcpy"):
        section = report[name]
        assert isinstance(section, dict)
        if "error" in section:
            print(f"{name}: ERROR — {section['error']}")
        else:
            print(f"{name}: {section['version']} ({section['path']})")
    devices = report.get("devices", [])
    assert isinstance(devices, list)
    print(f"devices: {len(devices)}")
    for device in devices:
        assert isinstance(device, dict)
        print(
            f"  {device['serial']}  {device['state']}  {device['transport']}  "
            f"{device.get('model') or '-'}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)

    try:
        if arguments.command == "doctor":
            report, healthy = _doctor(arguments.adb, arguments.scrcpy)
            if arguments.json:
                print(json.dumps(report, indent=2))
            else:
                _print_doctor(report)
            return 0 if healthy else 1

        adb = AdbBackend(arguments.adb)
        if arguments.command == "devices":
            devices = adb.devices(online_only=arguments.online_only)
            if arguments.json:
                print(json.dumps([device.as_dict() for device in devices], indent=2))
            else:
                if not devices:
                    print("No ADB devices found.")
                for device in devices:
                    print(
                        f"{device.serial}\t{device.state}\t{device.transport.value}\t"
                        f"{device.model or '-'}"
                    )
            return 0

        if arguments.command == "pair":
            pairing_code = (
                arguments.code
                or os.getenv("RUSHBOT_PAIRING_CODE")
                or getpass.getpass("Android pairing code: ")
            )
            print(adb.pair(arguments.endpoint, pairing_code))
            return 0

        if arguments.command == "connect":
            print(adb.connect(arguments.endpoint))
            return 0

        if arguments.command == "disconnect":
            print(adb.disconnect(arguments.endpoint))
            return 0

        if arguments.command == "tcpip":
            print(adb.enable_tcpip(arguments.serial, port=arguments.port))
            return 0

        if arguments.command == "screenshot":
            path = arguments.output.expanduser().resolve()
            AdbScreenshotProvider(adb).capture(arguments.serial, path)
            print(path)
            return 0

        if arguments.command == "mirror":
            client = ScrcpyClient(arguments.scrcpy)
            options = ScrcpyOptions(
                serial=arguments.serial,
                control=not arguments.view_only,
                audio=arguments.audio,
                max_size=arguments.max_size,
                max_fps=arguments.max_fps,
                turn_screen_off=arguments.turn_screen_off,
                v4l2_sink=arguments.v4l2_sink,
                video_playback=not arguments.no_window,
                record_path=arguments.record,
            )
            session = client.session(options, log_path=arguments.log)
            session.start()
            try:
                return session.wait()
            except KeyboardInterrupt:
                session.stop()
                return 130

        if arguments.command == "start-app":
            print(adb.start_package(arguments.serial, arguments.package))
            return 0

        if arguments.command == "stop-app":
            adb.force_stop_package(arguments.serial, arguments.package)
            return 0

    except (AdbError, ScrcpyError, FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    parser.error(f"Unknown command: {arguments.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
