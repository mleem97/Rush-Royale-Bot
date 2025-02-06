import subprocess
import time
import logging

class ADBHandler:
    def __init__(self):
        self.logger = logging.getLogger("ADBHandler")
        self.device = None

    def start_adb(self):
        self.logger.info("Starte ADB-Server...")
        subprocess.run(["adb", "start-server"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(2)

    def stop_adb(self):
        self.logger.info("Stoppe ADB-Server...")
        subprocess.run(["adb", "kill-server"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(2)

    def restart_adb(self):
        self.stop_adb()
        self.start_adb()

    def get_device(self):
        self.logger.info("Suche nach verbundenen ADB-Geräten...")
        result = subprocess.run(["adb", "devices"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        lines = result.stdout.split("\n")
        devices = [line.split("\t")[0] for line in lines[1:] if "device" in line]
        if devices:
            self.device = devices[0]
            self.logger.info(f"Gefundenes ADB-Gerät: {self.device}")
        else:
            self.logger.error("Kein ADB-Gerät gefunden!")
        return self.device

    def ensure_connection(self, max_retries=5):
        for attempt in range(max_retries):
            device = self.get_device()
            if device:
                return device
            self.logger.warning(f"ADB-Gerät nicht gefunden. Wiederhole... ({attempt + 1}/{max_retries})")
            self.restart_adb()
            time.sleep(3)
        self.logger.error("Maximale ADB-Wiederholungen erreicht. Verbindung fehlgeschlagen.")
        return None

    def connect_to_emulator(self, port=5555):
        self.logger.info(f"Versuche Verbindung zu Emulator auf Port {port}...")
        result = subprocess.run(["adb", "connect", f"localhost:{port}"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if "connected" in result.stdout:
            self.logger.info(f"Erfolgreich mit Emulator {port} verbunden!")
            return True
        self.logger.error(f"Fehler beim Verbinden mit Emulator {port}: {result.stderr}")
        return False

    def restart_scrcpy(self):
        self.logger.info("Starte Scrcpy neu...")
        result = subprocess.run(["scrcpy"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode == 0:
            self.logger.info("Scrcpy erfolgreich gestartet!")
        else:
            self.logger.error(f"Fehler beim Starten von Scrcpy: {result.stderr}")

if __name__ == "__main__":
    adb_handler = ADBHandler()
    adb_handler.start_adb()
    device = adb_handler.ensure_connection()
    if device:
        adb_handler.restart_scrcpy()
