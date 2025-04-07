import socket
import threading
import time
import os
import logging
from subprocess import check_output, Popen, DEVNULL

# Dictionary to track open ports
open_ports = {}
# Create logger
logger = logging.getLogger(__name__)

# Connects to a target IP and port, if port is open try to connect adb
def connect_port(ip, port, batch):
    for tar_port in range(port, port + batch):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = s.connect_ex((ip, tar_port))
        if result == 0:
            open_ports[tar_port] = 'open'
            try:
                # Make it Popen and kill shell after couple seconds
                p = Popen(f'.scrcpy\\adb connect {ip}:{tar_port}', shell=True, stderr=DEVNULL)
                time.sleep(1)  # Reduced wait time from 3 to 1 second
                p.terminate()
            except Exception as e:
                logger.error(f"Error connecting to {ip}:{tar_port} - {str(e)}")
    return result == 0

# Attemtps to connect to ip over every port in range
# Returns device if found
def scan_ports(target_ip, port_start, port_end, batch=5):
    threads = []
    global open_ports
    open_ports = {}
    port_range = range(port_start, port_end, batch)
    socket.setdefaulttimeout(0.01)
    logger.info(f"Scanning {target_ip} Ports {port_start} - {port_end}")
    
    # Create one thread per port range
    for port in port_range:
        thread = threading.Thread(target=connect_port, args=(target_ip, port, batch))
        threads.append(thread)
    
    # Attempt to connect to every port range
    for thread in threads:
        thread.start()
    
    # Join threads
    logger.info(f'Started {len(port_range)} threads')
    for thread in threads:
        thread.join()
    
    # Get open ports
    port_list = list(open_ports.keys())
    logger.info(f"Ports Open: {port_list}")
    device = get_adb_device()
    return device

# Check if adb device is already connected
def get_adb_device():
    try:
        devList = check_output('.scrcpy\\adb devices', shell=True)
        devListArr = str(devList).split('\\n')
        # Check for online status
        device = None
        for client in devListArr[1:]:
            if '\\t' not in client:
                continue
                
            client_parts = client.split('\\t')
            if len(client_parts) < 2:
                continue
                
            client_ip = client_parts[0]
            status = client_parts[1]
            
            if 'device' in status:
                device = client_ip
                logger.info(f"Found ADB device! {device}")
            else:
                try:
                    Popen(f'.scrcpy\\adb disconnect {client_ip}', shell=True, stderr=DEVNULL)
                except:
                    pass
        return device
    except Exception as e:
        logger.error(f"Error in get_adb_device: {str(e)}")
        return None

def get_device(port_start=48000, port_end=65000):
    # First, kill any existing ADB server
    try:
        p = Popen([".scrcpy\\adb", 'kill-server'])
        p.wait(timeout=5)
    except:
        logger.warning("Could not kill ADB server")
    
    # Start a new ADB server
    try:
        p = Popen('.scrcpy\\adb start-server', shell=True)
        p.wait(timeout=5)
    except:
        logger.warning("Could not start ADB server")
    
    # Check if an ADB device is already connected
    device = get_adb_device()
    
    # If not, try the common emulator port first
    if not device:
        try:
            p = Popen('.scrcpy\\adb connect 127.0.0.1:5555', shell=True)
            p.wait(timeout=3)
            device = get_adb_device()
        except:
            pass
    
    # If still not connected, try connecting to common Bluestacks ports
    common_ports = [5555, 5037, 58526, 59010, 62001]
    if not device:
        for port in common_ports:
            try:
                p = Popen(f'.scrcpy\\adb connect 127.0.0.1:{port}', shell=True)
                p.wait(timeout=1)
            except:
                continue
        device = get_adb_device()
    
    # If still not found, do a port scan
    if not device:
        # Find valid ADB device by scanning ports
        device = scan_ports('127.0.0.1', port_start, port_end)
    
    return device