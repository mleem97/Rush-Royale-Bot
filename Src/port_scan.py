from __future__ import annotations

import os
import socket
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed
from subprocess import DEVNULL
from subprocess import Popen
from subprocess import check_output

# Cross-Platform ADB path: Windows uses vendored binary, Unix uses system adb
ADB_PATH = ".scrcpy\\adb" if os.name == "nt" else "adb"
SOCKET_TIMEOUT_S = 0.05
CONNECT_WAIT_S = 1.5
MAX_WORKERS = 96


def _adb_devices() -> list[str]:
    try:
        out = check_output([ADB_PATH, "devices"], stderr=DEVNULL)
    except Exception:
        out = check_output(f"{ADB_PATH} devices", shell=True, stderr=DEVNULL)

    lines = out.decode("utf-8", errors="ignore").splitlines()
    devices = []
    for ln in lines[1:]:
        ln = ln.strip()
        if not ln:
            continue
        if "\tdevice" in ln:
            devices.append(ln.split()[0])
        elif "\t" in ln:
            serial = ln.split()[0]
            Popen([ADB_PATH, "disconnect", serial], stdout=DEVNULL, stderr=DEVNULL)
    return devices


def get_adb_device() -> str | None:
    devices = _adb_devices()
    return devices[0] if devices else None


def _port_open(ip: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(SOCKET_TIMEOUT_S)
        return sock.connect_ex((ip, port)) == 0


def _try_adb_connect(ip: str, port: int) -> None:
    p = Popen(
        [ADB_PATH, "connect", f"{ip}:{port}"],
        stdout=DEVNULL,
        stderr=DEVNULL,
    )
    time.sleep(CONNECT_WAIT_S)
    try:
        p.terminate()
    except Exception:
        pass


def scan_ports(
    target_ip: str,
    port_start: int,
    port_end: int,
    batch: int = 3,
) -> str | None:
    if batch <= 0:
        raise ValueError("batch must be > 0")

    ports = list(range(port_start, port_end, batch))
    print(f"Scanning {target_ip} Ports {port_start} - {port_end}")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(_port_open, target_ip, p): p for p in ports}
        for fut in as_completed(futures):
            port = futures[fut]
            try:
                if fut.result():
                    _try_adb_connect(target_ip, port)
            except Exception:
                continue

    return get_adb_device()


def get_device(force_scan: bool = False) -> str | None:
    """Get connected ADB device.

    Args:
        force_scan: If True, will scan ports even if already connected.
                    If False, uses existing connection first.
    """
    # First: Try to get already connected device via adbutils (fast path)
    try:
        from adbutils import adb

        devices = adb.device_list()
        if devices:
            serial = str(devices[0].serial)
            print(f"[INFO] Found connected device via adbutils: {serial}")
            return serial
    except Exception:
        pass

    # Second: Check existing ADB connections without killing server
    device = get_adb_device()
    if device and not force_scan:
        print(f"[INFO] Found existing ADB device: {device}")
        return device

    # Third: Try common local emulator ports (fast path, no server kill)
    for p in (5555, 5554, 5565, 62001, 21503, 5556, 5557):
        _try_adb_connect("127.0.0.1", p)
        device = get_adb_device()
        if device:
            print(f"[INFO] Connected to device on port {p}: {device}")
            return device

    # Fourth: Only if nothing else works, restart server and scan
    print("[INFO] No device found, restarting ADB server...")
    Popen([ADB_PATH, "kill-server"], stdout=DEVNULL, stderr=DEVNULL).wait()
    Popen([ADB_PATH, "devices"], stdout=DEVNULL, stderr=DEVNULL).wait()

    device = get_adb_device()
    if device:
        return device

    # Fallback: bounded scan (slower)
    return scan_ports("127.0.0.1", 48000, 65000, batch=10)
