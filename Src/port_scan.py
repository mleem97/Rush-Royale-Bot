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
import subprocess as sp
from pathlib import Path
import shutil
from typing import Optional, Dict, Any, List, Set, Iterable
import configparser
import re
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
    """Legacy: return the first 'device' line from adb devices (kept for compatibility)."""
    adb = find_adb()
    devList = check_output([adb, 'devices'])
    lines = devList.decode('utf-8', errors='ignore').splitlines()
    for client in lines[1:]:
        client = client.strip()
        if not client:
            continue
        parts = client.split()
        if len(parts) >= 2 and parts[1] == 'device':
            print(f"Found ADB device! {parts[0]}")
            return parts[0]
    return None


def _run(adb: str, args: List[str], timeout: float = 6.0) -> sp.CompletedProcess:
    return sp.run([adb, *args], stdout=sp.PIPE, stderr=sp.PIPE, timeout=timeout, creationflags=0x08000000)


def _start_server(adb: str) -> None:
    try:
        _run(adb, ['start-server'], timeout=6.0)
    except Exception:
        pass


def _parse_devices(out: str) -> List[str]:
    devices: List[str] = []
    for line in out.splitlines():
        line = line.strip()
        if not line or line.startswith('List of devices'):
            continue
        parts = line.split()
        if len(parts) >= 2 and parts[1] == 'device':
            devices.append(parts[0])
    return devices


def list_connected_devices() -> List[str]:
    adb = find_adb()
    _start_server(adb)
    try:
        cp = _run(adb, ['devices'], timeout=6.0)
    except Exception:
        return []
    return _parse_devices(cp.stdout.decode(errors='ignore'))


def _ports_from_env(default_ports: Iterable[int]) -> List[int]:
    env = os.getenv('ADB_PORTS')
    if not env:
        return list(default_ports)
    try:
        ports = [int(p.strip()) for p in env.split(',') if p.strip()]
        return ports or list(default_ports)
    except ValueError:
        return list(default_ports)


def connect_known_local_ports(ports: Optional[Iterable[int]] = None) -> List[str]:
    """Try to adb connect 127.0.0.1:<port> for a list of emulator ports. Return those reporting connected/already."""
    adb = find_adb()
    _start_server(adb)
    default_ports = (5554, 5555, 5556, 5557, 5558, 5559)
    ports_list = list(ports) if ports is not None else _ports_from_env(default_ports)
    connected: List[str] = []
    for p in ports_list:
        serial = f'127.0.0.1:{p}'
        try:
            cp = _run(adb, ['connect', serial], timeout=4.0)
            msg = (cp.stdout or b'').decode(errors='ignore').lower()
            if 'connected to' in msg or 'already connected' in msg:
                connected.append(serial)
        except sp.TimeoutExpired:
            continue
        except Exception:
            continue
    return connected


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _config_path() -> Path:
    return _repo_root() / 'config.ini'


def _read_preferred_from_config() -> Optional[str]:
    """Read preferred serial from config.ini ([bot].adb_port or [bot].adb_serial)."""
    cfg_path = _config_path()
    if not cfg_path.exists():
        return None
    config = configparser.ConfigParser()
    try:
        config.read(cfg_path, encoding='utf-8')
    except Exception:
        return None
    if not config.has_section('bot'):
        return None
    # Prefer explicit adb_serial
    if config.has_option('bot', 'adb_serial'):
        serial = config.get('bot', 'adb_serial').strip()
        if serial:
            return serial
    # Else build from adb_port
    if config.has_option('bot', 'adb_port'):
        try:
            port = int(config.get('bot', 'adb_port').strip())
            if 1 <= port <= 65535:
                return f'127.0.0.1:{port}'
        except Exception:
            return None
    return None


def _write_selected_to_config(serial: str) -> None:
    """Persist selected device back to config.ini: [bot].adb_serial and .adb_port (if localhost)."""
    cfg_path = _config_path()
    config = configparser.ConfigParser()
    if cfg_path.exists():
        try:
            config.read(cfg_path, encoding='utf-8')
        except Exception:
            config = configparser.ConfigParser()
    if not config.has_section('bot'):
        config.add_section('bot')
    config.set('bot', 'adb_serial', serial)
    # If localhost:port pattern, also store adb_port
    m = re.match(r'^127\.0\.0\.1:(\d{2,5})$', serial)
    if m:
        config.set('bot', 'adb_port', m.group(1))
    try:
        with open(cfg_path, 'w', encoding='utf-8') as f:
            config.write(f)
    except Exception:
        # Non-fatal if write fails
        pass


def get_device(preferred: Optional[str] = None) -> Optional[str]:
    """
    Device discovery with minimal side effects:
    1) start-server (no kill-server)
    2) connect known localhost ports (5554–5559 or ADB_PORTS)
    3) return preferred if present
    4) else return first connected emulator 127.0.0.1:<port>
    5) else return any connected device
    6) last resort: try small port scan on 5554–5559
    """
    adb = find_adb()
    _start_server(adb)

    # Step 0: resolve preference: env > argument > config
    env_pref = os.getenv('ADB_SERIAL') or os.getenv('PREFERRED_DEVICE')
    cfg_pref = _read_preferred_from_config()
    preferred = preferred or env_pref or cfg_pref

    # Step 1: connect known ports (if preferred is a localhost port, try it first)
    known_connected: List[str] = []
    if preferred and preferred.startswith('127.0.0.1:'):
        try:
            port = int(preferred.rsplit(':', 1)[-1])
            known_connected = connect_known_local_ports([port])
        except Exception:
            known_connected = connect_known_local_ports()
    else:
        known_connected = connect_known_local_ports()
    # Step 2: list devices
    all_devices = list_connected_devices()

    # Step 3: preferred env or arg
    if preferred and preferred in all_devices:
        _write_selected_to_config(preferred)
        return preferred

    # Step 4: prefer localhost emulators
    if known_connected:
        for s in known_connected:
            if s in all_devices:
                _write_selected_to_config(s)
                return s

    # Step 5: any connected device
    if all_devices:
        sel = all_devices[0]
        _write_selected_to_config(sel)
        return sel

    # Step 6: last resort small scan of emulator ports (no massive thread fan-out)
    small_ports = _ports_from_env((5554, 5555, 5556, 5557, 5558, 5559))
    connect_known_local_ports(small_ports)
    all_devices = list_connected_devices()
    if preferred and preferred in all_devices:
        _write_selected_to_config(preferred)
        return preferred
    if all_devices:
        sel = all_devices[0]
        _write_selected_to_config(sel)
        return sel
    return None