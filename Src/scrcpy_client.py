"""
Rush Royale Bot - Scrcpy Client Module
Python 3.11+ Compatible

Stellt die Verbindung zum Android-Gerät über scrcpy her.
Ermöglicht Screenshot-Capture und Touch-Input.
"""
from __future__ import annotations

import sys
import os
import logging
import threading
import time
from pathlib import Path
from typing import Optional, Callable, Any
import numpy as np

# Füge den scrcpy-Ordner zum Pfad hinzu
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import des lokalen scrcpy Clients
try:
    from scrcpy import Client
    from scrcpy import const as scrcpy_const
    SCRCPY_AVAILABLE = True
except ImportError as e:
    SCRCPY_AVAILABLE = False
    Client = None
    scrcpy_const = None
    print(f"Warning: scrcpy nicht verfügbar: {e}")

logger = logging.getLogger(__name__)


class ScrcpyClientWrapper:
    """
    Wrapper-Klasse für den scrcpy Client.
    
    Stellt eine einfache Schnittstelle für:
    - Screenshot-Capture
    - Touch-Events
    - Key-Events
    """
    
    # Events
    EVENT_FRAME = "frame"
    EVENT_INIT = "init"
    EVENT_DISCONNECT = "disconnect"
    
    def __init__(
        self,
        device: Optional[str] = None,
        max_width: int = 800,
        bitrate: int = 2_000_000,
        max_fps: int = 30,
        flip: bool = False,
        block_frame: bool = False,
        stay_awake: bool = True,
    ):
        """
        Initialisiert den scrcpy Client.
        
        Args:
            device: ADB Device Serial (z.B. 'emulator-5554')
            max_width: Maximale Breite des Video-Streams
            bitrate: Video-Bitrate in bps
            max_fps: Maximale Framerate
            flip: Bild horizontal spiegeln
            block_frame: Blockiert bis Frame verfügbar
            stay_awake: Hält das Gerät wach
        """
        if not SCRCPY_AVAILABLE:
            raise RuntimeError("scrcpy Client nicht verfügbar. Bitte Abhängigkeiten installieren.")
        
        self.device = device
        self.max_width = max_width
        self.bitrate = bitrate
        self.max_fps = max_fps
        self.flip = flip
        self.block_frame = block_frame
        self.stay_awake = stay_awake
        
        self._client: Optional[Client] = None
        self._last_frame: Optional[np.ndarray] = None
        self._frame_lock = threading.Lock()
        self._connected = False
        self._frame_listeners: list[Callable] = []
        
        logger.info(f"ScrcpyClientWrapper initialisiert für Gerät: {device or 'auto'}")
    
    def _on_frame(self, frame: np.ndarray) -> None:
        """Callback wenn ein neuer Frame empfangen wird."""
        with self._frame_lock:
            self._last_frame = frame
        
        # Benachrichtige alle Listener
        for listener in self._frame_listeners:
            try:
                listener(frame)
            except Exception as e:
                logger.error(f"Frame-Listener Fehler: {e}")
    
    def _on_init(self) -> None:
        """Callback wenn die Verbindung hergestellt wurde."""
        self._connected = True
        logger.info("scrcpy Verbindung hergestellt")
    
    def _on_disconnect(self) -> None:
        """Callback wenn die Verbindung getrennt wurde."""
        self._connected = False
        logger.warning("scrcpy Verbindung getrennt")
    
    def add_frame_listener(self, callback: Callable[[np.ndarray], None]) -> None:
        """Fügt einen Frame-Listener hinzu."""
        self._frame_listeners.append(callback)
    
    def remove_frame_listener(self, callback: Callable) -> None:
        """Entfernt einen Frame-Listener."""
        if callback in self._frame_listeners:
            self._frame_listeners.remove(callback)
    
    def start(self, threaded: bool = True) -> bool:
        """
        Startet den scrcpy Client.
        
        Args:
            threaded: Ob der Client in einem eigenen Thread laufen soll
            
        Returns:
            True wenn erfolgreich gestartet
        """
        try:
            self._client = Client(
                device=self.device,
                max_width=self.max_width,
                bitrate=self.bitrate,
                max_fps=self.max_fps,
                flip=self.flip,
                block_frame=self.block_frame,
                stay_awake=self.stay_awake,
            )
            
            # Event-Handler registrieren
            self._client.add_listener(Client.EVENT_FRAME, self._on_frame)
            self._client.add_listener(Client.EVENT_INIT, self._on_init)
            self._client.add_listener(Client.EVENT_DISCONNECT, self._on_disconnect)
            
            logger.info("Starte scrcpy Client...")
            self._client.start(threaded=threaded)
            
            # Warte kurz auf Verbindung
            timeout = 5.0
            start_time = time.time()
            while not self._connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)
            
            if self._connected:
                logger.info("scrcpy Client erfolgreich gestartet")
                return True
            else:
                logger.warning("scrcpy Client Timeout - keine Verbindung")
                return False
                
        except Exception as e:
            logger.error(f"Fehler beim Starten des scrcpy Clients: {e}")
            return False
    
    def stop(self) -> None:
        """Stoppt den scrcpy Client."""
        if self._client:
            try:
                self._client.stop()
                logger.info("scrcpy Client gestoppt")
            except Exception as e:
                logger.error(f"Fehler beim Stoppen: {e}")
            finally:
                self._client = None
                self._connected = False
    
    def get_frame(self) -> Optional[np.ndarray]:
        """
        Gibt den letzten empfangenen Frame zurück.
        
        Returns:
            numpy array mit dem Bild (RGB) oder None
        """
        with self._frame_lock:
            if self._last_frame is not None:
                return self._last_frame.copy()
        return None
    
    def get_screenshot(self) -> Optional[np.ndarray]:
        """Alias für get_frame() - für Kompatibilität."""
        return self.get_frame()
    
    @property
    def is_connected(self) -> bool:
        """Gibt zurück ob der Client verbunden ist."""
        return self._connected
    
    @property
    def resolution(self) -> Optional[tuple[int, int]]:
        """Gibt die aktuelle Auflösung zurück (width, height)."""
        frame = self.get_frame()
        if frame is not None:
            return (frame.shape[1], frame.shape[0])
        return None
    
    # Touch/Input Methoden
    def touch(self, x: int, y: int, action: int = 0) -> None:
        """
        Sendet ein Touch-Event.
        
        Args:
            x: X-Koordinate
            y: Y-Koordinate
            action: 0=DOWN, 1=UP, 2=MOVE (siehe scrcpy.const)
        """
        if self._client and self._connected:
            self._client.control.touch(x, y, action)
    
    def click(self, x: int, y: int, duration: float = 0.05) -> None:
        """
        Führt einen Klick aus (touch down + up).
        
        Args:
            x: X-Koordinate
            y: Y-Koordinate
            duration: Verzögerung zwischen down und up in Sekunden
        """
        if self._client and self._connected:
            # ACTION_DOWN = 0, ACTION_UP = 1
            self._client.control.touch(x, y, 0)
            time.sleep(duration)
            self._client.control.touch(x, y, 1)
    
    def swipe(
        self, 
        start_x: int, 
        start_y: int, 
        end_x: int, 
        end_y: int, 
        duration: float = 0.3,
        steps: int = 10
    ) -> None:
        """
        Führt eine Swipe-Geste aus.
        
        Args:
            start_x, start_y: Startposition
            end_x, end_y: Endposition
            duration: Dauer der Geste
            steps: Anzahl der Zwischenschritte
        """
        if not self._client or not self._connected:
            return
        
        # Touch down
        self._client.control.touch(start_x, start_y, 0)
        
        # Bewegung in Schritten
        step_delay = duration / steps
        for i in range(1, steps + 1):
            progress = i / steps
            x = int(start_x + (end_x - start_x) * progress)
            y = int(start_y + (end_y - start_y) * progress)
            self._client.control.touch(x, y, 2)  # ACTION_MOVE
            time.sleep(step_delay)
        
        # Touch up
        self._client.control.touch(end_x, end_y, 1)
    
    def key(self, keycode: int, action: int = 0) -> None:
        """
        Sendet ein Key-Event.
        
        Args:
            keycode: Android Keycode
            action: 0=DOWN, 1=UP
        """
        if self._client and self._connected:
            self._client.control.keycode(keycode, action)
    
    def back(self) -> None:
        """Sendet die Zurück-Taste."""
        self.key(4)  # KEYCODE_BACK
        time.sleep(0.05)
        self.key(4, 1)
    
    def home(self) -> None:
        """Sendet die Home-Taste."""
        self.key(3)  # KEYCODE_HOME
        time.sleep(0.05)
        self.key(3, 1)


# Singleton-Instanz für einfachen Zugriff
_client_instance: Optional[ScrcpyClientWrapper] = None


def get_scrcpy_client(
    device: Optional[str] = None,
    auto_start: bool = True,
    **kwargs
) -> ScrcpyClientWrapper:
    """
    Gibt eine Singleton-Instanz des scrcpy Clients zurück.
    
    Args:
        device: ADB Device Serial
        auto_start: Automatisch starten wenn nicht verbunden
        **kwargs: Weitere Parameter für ScrcpyClientWrapper
        
    Returns:
        ScrcpyClientWrapper Instanz
    """
    global _client_instance
    
    if _client_instance is None:
        _client_instance = ScrcpyClientWrapper(device=device, **kwargs)
    
    if auto_start and not _client_instance.is_connected:
        _client_instance.start(threaded=True)
    
    return _client_instance


def close_scrcpy_client() -> None:
    """Schließt die Singleton-Instanz."""
    global _client_instance
    if _client_instance:
        _client_instance.stop()
        _client_instance = None


# Test/Debug
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    def on_frame(frame):
        print(f"Frame empfangen: {frame.shape}")
    
    client = get_scrcpy_client(device="emulator-5554")
    client.add_frame_listener(on_frame)
    
    print("Client gestartet. Drücke Ctrl+C zum Beenden...")
    try:
        while True:
            time.sleep(1)
            frame = client.get_frame()
            if frame is not None:
                print(f"Aktueller Frame: {frame.shape}")
    except KeyboardInterrupt:
        print("Beende...")
    finally:
        close_scrcpy_client()
