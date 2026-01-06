from __future__ import annotations

import socket
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from subprocess import DEVNULL, Popen, check_output
from typing import Optional


ADB_PATH = ".scrcpy\\adb"
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


def get_adb_device() -> Optional[str]:
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
) -> Optional[str]:
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


def get_device() -> Optional[str]:
    Popen([ADB_PATH, "kill-server"], stdout=DEVNULL, stderr=DEVNULL).wait()
    Popen([ADB_PATH, "devices"], stdout=DEVNULL, stderr=DEVNULL).wait()

    device = get_adb_device()
    if device:
        return device

    # Try common local emulator ports first (fast path)
    for p in (5555, 5554, 5565, 62001):
        _try_adb_connect("127.0.0.1", p)
        device = get_adb_device()
        if device:
            return device

    # Fallback: bounded scan (still slower)
    return scan_ports("127.0.0.1", 48000, 65000, batch=10)