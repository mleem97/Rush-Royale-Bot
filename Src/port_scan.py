"""
Rush Royale Bot Port Scanner - Python 3.13 Compatible
Enhanced networking and device detection
"""
from __future__ import annotations

import socket
import threading
import time
import os
from subprocess import check_output, Popen, DEVNULL
from pathlib import Path
import shutil
from typing import Optional, Dict, Any, List, Set
from concurrent.futures import ThreadPoolExecutor


# Connects to a target IP and port, if port is open try to connect adb
def find_adb() -> str:
    """Locate adb.exe robustly across PATH, env vars, and local folders.
    Returns absolute path to adb executable or raises FileNotFoundError.
    """
    # 1) Explicit env var
    env_adb = os.getenv("ADB_PATH")
    if env_adb:
        p = Path(env_adb)
        if p.exists():
            return str(p)

    # 2) PATH
    which = shutil.which("adb.exe") or shutil.which("adb")
    if which:
        return which

    # 3) Common local/install locations
    repo_root = Path(__file__).resolve().parents[1]
    candidates = [
        repo_root / ".scrcpy" / "adb.exe",
        repo_root / "scrcpy" / "adb.exe",
        Path(os.getenv("ANDROID_HOME", "")) / "platform-tools" / "adb.exe",
        Path(os.getenv("ANDROID_SDK_ROOT", "")) / "platform-tools" / "adb.exe",
        Path(os.getenv("LOCALAPPDATA", "")) / "Android" / "Sdk" / "platform-tools" / "adb.exe",
        Path("C:/Program Files/scrcpy/adb.exe"),
    ]
    for c in candidates:
        if c and c.exists():
            return str(c)

    raise FileNotFoundError(
        "ADB nicht gefunden. Installiere ADB (platform-tools) oder setze ADB_PATH/füge adb.exe in .scrcpy/."
    )


# Connects to a target IP and port, if port is open try to connect adb
def connect_port(ip, port, batch, open_ports):
    adb = None
    try:
        adb = find_adb()
    except FileNotFoundError:
        # If adb is not available, scanning still proceeds to discover open ports
        pass
    result = 1  # default: not connected
    for tar_port in range(port, port + batch):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = s.connect_ex((ip, tar_port))
        if result == 0:
            open_ports[tar_port] = 'open'
            # Make it Popen and kill shell after couple seconds
            if adb:
                p = Popen([adb, 'connect', f'{ip}:{tar_port}'], stdout=DEVNULL, stderr=DEVNULL)
            else:
                p = None
            time.sleep(3)  # Give real client 3 seconds to connect
            if p:
                p.terminate()
        s.close()
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
def get_adb_device():
    adb = find_adb()
    devList = check_output([adb, 'devices'])
    lines = devList.decode('utf-8', errors='ignore').splitlines()
    # Check for online status
    deivce = None
    for client in lines[1:]:
        client = client.strip()
        if not client:
            continue
        parts = client.split()
        client_ip = parts[0] if parts else ''
        if 'device' in client and 'offline' not in client:
            deivce = client_ip
            print(f"Found ADB device! {deivce}")
        elif client_ip and client_ip not in ("List", "of", "devices", "attached"):
            Popen([adb, 'disconnect', client_ip], stdout=DEVNULL, stderr=DEVNULL)
    return deivce


def get_device():
    adb = find_adb()
    p = Popen([adb, 'kill-server'], stdout=DEVNULL, stderr=DEVNULL)
    p.wait()
    p = Popen([adb, 'start-server'], stdout=DEVNULL, stderr=DEVNULL)
    p.wait()
    p = Popen([adb, 'devices'], stdout=DEVNULL, stderr=DEVNULL)
    p.wait()
    # Check if adb got connected
    device = get_adb_device()
    if not device:
        # Find valid ADB device by scanning ports
        device = scan_ports('127.0.0.1', 48000, 65000)
    if device:
        return device