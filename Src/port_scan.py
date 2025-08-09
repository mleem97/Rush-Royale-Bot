"""
Rush Royale Bot Port Scanner - Python 3.13 Compatible
Enhanced networking and device detection
"""
from __future__ import annotations

import socket
import threading
import time
import os
import platform
import shutil
from pathlib import Path
from subprocess import check_output, Popen, DEVNULL
from typing import Optional, Dict, Any, List, Set
from concurrent.futures import ThreadPoolExecutor


# Connects to a target IP and port, if port is open try to connect adb
def connect_port(ip, port, batch, open_ports):
    result = 1
    for tar_port in range(port, port + batch):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            result = s.connect_ex((ip, tar_port))
            if result == 0:
                open_ports[tar_port] = 'open'
                # Make it Popen and kill shell after couple seconds
                try:
                    adb_bin = find_adb()
                except Exception:
                    adb_bin = 'adb'
                p = Popen([adb_bin, 'connect', f'{ip}:{tar_port}'])
                time.sleep(3)  # Give real client 3 seconds to connect
                p.terminate()
        finally:
            try:
                s.close()
            except Exception:
                pass
    return result == 0


# Attemtps to connect to ip over every port in range
# Returns device if found
def scan_ports(target_ip, port_start, port_end, batch=3):
    threads = []
    open_ports = {}
    port_range = range(port_start, port_end, batch)
    socket.setdefaulttimeout(0.01)
    print(f"Scanning {target_ip} Ports {port_start} - {port_end}")
    # Create one thread per port
    for port in port_range:
        thread = threading.Thread(target=connect_port, args=(target_ip, port, batch, open_ports))
        threads.append(thread)
    # Attempt to connect to every port
    for thread in threads:
        thread.start()
    # Join threads
    print(f'Started {len(port_range)} threads')
    for thread in threads:
        thread.join()
    # Get open ports
    port_list = list(open_ports.keys())
    print(f"Ports Open: {port_list}")
    device = get_adb_device()
    return device


# Check if adb device is already connected
def get_adb_device() -> Optional[str]:
    """Return the first 'device' from `adb devices` or None if not found."""
    try:
        adb_bin = find_adb()
    except FileNotFoundError:
        adb_bin = 'adb'  # best-effort fallback to PATH

    try:
        # Call adb without shell for reliability; decode output
        out = check_output([adb_bin, 'devices'])
        lines = out.decode('utf-8', errors='ignore').strip().splitlines()
    except Exception as e:
        print(f"ADB devices call failed: {e}")
        return None

    device_serial: Optional[str] = None
    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue
        # Expected format: '<serial>\t<state>'
        parts = line.split('\t')
        serial = parts[0]
        state = parts[1] if len(parts) > 1 else ''
        if state == 'device':
            device_serial = serial
            print(f"Found ADB device! {device_serial}")
            break
        elif serial and state and state != 'device':
            # ensure we disconnect transient/unauthorized entries
            try:
                Popen([adb_bin, 'disconnect', serial], stderr=DEVNULL, stdout=DEVNULL)
            except Exception:
                pass
    return device_serial


_ADB_PATH = None

def find_adb() -> str:
    """
    Find a working adb executable across common locations.
    Search order:
    - Env vars: RRBOT_ADB, ADB_PATH
    - System PATH
    - Repo-local .scrcpy/adb(.exe)
    - Common Windows install paths (scrcpy, Android SDK, BlueStacks, Nox)
    Raises FileNotFoundError with guidance if not found.
    """
    global _ADB_PATH
    if _ADB_PATH and Path(_ADB_PATH).exists():
        return _ADB_PATH

    is_windows = platform.system() == "Windows"
    adb_name = "adb.exe" if is_windows else "adb"

    candidates = []
    # Environment variables
    for env_key in ("RRBOT_ADB", "ADB_PATH"):
        p = os.environ.get(env_key)
        if p:
            candidates.append(p)

    # PATH lookup
    from shutil import which
    w = which(adb_name) or which("adb")
    if w:
        candidates.append(w)

    # Repo .scrcpy directory (relative to repo root)
    repo_root = Path(__file__).resolve().parents[1]
    candidates.append(str(repo_root / ".scrcpy" / adb_name))

    # Common Windows locations
    if is_windows:
        candidates += [
            r"C:\\Program Files\\scrcpy\\adb.exe",
            r"C:\\Program Files (x86)\\Android\\android-sdk\\platform-tools\\adb.exe",
            r"C:\\Android\\platform-tools\\adb.exe",
            r"C:\\Program Files\\BlueStacks_nxt\\HD-Adb.exe",
            r"C:\\Program Files\\BlueStacks\\HD-Adb.exe",
            r"C:\\Program Files\\Nox\\bin\\adb.exe",
        ]

    for c in candidates:
        if c and Path(c).exists():
            _ADB_PATH = c
            return _ADB_PATH

    raise FileNotFoundError(
        "ADB nicht gefunden. Bitte adb installieren/konfigurieren: setzen Sie RRBOT_ADB oder ADB_PATH auf den Pfad zu adb.exe, fügen Sie adb dem PATH hinzu, oder legen Sie es unter <repo>/.scrcpy/adb(.exe) ab."
    )


def get_device(*args, **kwargs):
    adb_bin = find_adb()
    p = Popen([adb_bin, 'kill-server'])
    p.wait()
    p = Popen([adb_bin, 'start-server'])
    p.wait()
    # Check if adb got connected
    device = get_adb_device()
    if not device:
        # Find valid ADB device by scanning ports
        device = scan_ports('127.0.0.1', 48000, 65000)
    if device:
        return device