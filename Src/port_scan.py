"""ADB device discovery for Windows and Linux."""
from __future__ import annotations

import os
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Iterable

from adb_backend import AdbError, connect, find_adb, list_devices, run_adb

COMMON_EMULATOR_PORTS = (5555, 5556, 5557, 5585, 62001, 7555, 16384)


def _is_open(ip: str, port: int, timeout: float = 0.05) -> bool:
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except OSError:
        return False


def connect_port(ip: str, port: int, batch: int, open_ports: dict[int, str]) -> bool:
    """Compatibility helper: probe a small port batch and connect open ADB ports."""
    connected = False
    for target_port in range(port, port + batch):
        if not _is_open(ip, target_port):
            continue
        open_ports[target_port] = "open"
        connected = connect(f"{ip}:{target_port}") or connected
    return connected


def _probe_ports(ip: str, ports: Iterable[int], workers: int = 128) -> list[int]:
    open_ports: list[int] = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(_is_open, ip, port): port for port in ports}
        for future in as_completed(futures):
            port = futures[future]
            try:
                if future.result():
                    open_ports.append(port)
            except OSError:
                continue
    return sorted(open_ports)


def scan_ports(
    target_ip: str,
    port_start: int,
    port_end: int,
    batch: int = 3,
) -> str | None:
    """Scan an emulator port range using a bounded worker pool.

    The old implementation created thousands of threads. A bounded executor is
    substantially more predictable on both Windows and Linux.
    """
    del batch
    print(f"Scanning {target_ip} ports {port_start}-{port_end}")
    open_ports = _probe_ports(target_ip, range(port_start, port_end))
    print(f"Open ports: {open_ports}")
    for port in open_ports:
        connect(f"{target_ip}:{port}")
    return get_adb_device()


def get_adb_device() -> str | None:
    devices = sorted(list_devices())
    if not devices:
        return None
    device = devices[0]
    print(f"Found ADB device: {device}")
    if len(devices) > 1:
        print(
            "Multiple devices are online; using the first one. "
            "Set RUSHBOT_DEVICE or ANDROID_SERIAL to select a specific device."
        )
    return device


def _connect_requested_device(serial: str) -> str:
    if serial in list_devices() or connect(serial):
        if serial in list_devices():
            return serial
    raise RuntimeError(
        f"Requested ADB device '{serial}' is not online. Check 'adb devices' and USB debugging."
    )


def get_device() -> str | None:
    """Return an online ADB serial, connecting local emulators when necessary."""
    find_adb()
    run_adb(["start-server"], timeout=15)

    requested = os.getenv("RUSHBOT_DEVICE") or os.getenv("ANDROID_SERIAL")
    if requested:
        return _connect_requested_device(requested)

    device = get_adb_device()
    if device:
        return device

    target_ip = os.getenv("RUSHBOT_ADB_HOST", "127.0.0.1")
    for port in COMMON_EMULATOR_PORTS:
        if _is_open(target_ip, port):
            connect(f"{target_ip}:{port}")

    device = get_adb_device()
    if device:
        return device

    port_range = os.getenv("RUSHBOT_SCAN_PORT_RANGE", "48000-65000")
    try:
        start_text, end_text = port_range.split("-", maxsplit=1)
        start, end = int(start_text), int(end_text)
    except (TypeError, ValueError):
        raise ValueError(
            "RUSHBOT_SCAN_PORT_RANGE must use START-END syntax, for example 48000-65000."
        ) from None

    try:
        return scan_ports(target_ip, start, end)
    except AdbError as exc:
        raise RuntimeError(f"ADB device discovery failed: {exc}") from exc
