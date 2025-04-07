# Rush-Royale-Bot

Ein Python-basierter Bot für Rush Royale.

**Wichtiger Hinweis:** Dieser Bot ist für die Verwendung mit Bluestacks auf einem PC optimiert.

## Unbegrenzt Gold farmen!

* Kann 24/7 laufen und ermöglicht es dir, alle verfügbaren Einheiten mühelos mit reichlich Gold aufzurüsten.
* Optimiert für das Farmen von Dungeon-Etage 5.

## Funktionalitäten

* Kann Befehle mit geringer Latenz über Scrpy ADB an das Spiel senden.
* Jupyter Notebook zur Interaktion und zum Hinzufügen neuer Einheiten.
* Automatische Ladenaktualisierung, Anzeigenwiedergabe, Questabschlüsse und das Einsammeln der Werbe-Truhe.
* Erkennung von Einheitentypen mit OpenCV: ORB-Detektor.
* Rang-Erkennung mit sklearn LogisticRegression (sehr genau).

![output](https://user-images.githubusercontent.com/71280183/171181226-d680e7ca-729f-4c3d-8fc6-573736371dfb.png)

![new_gui](https://user-images.githubusercontent.com/71280183/183141310-841b100a-2ddb-4f59-a6d9-4c7789ba72db.png)

## Geplante Funktionen

* **Verbesserte Dungeon-Auswahl:** Auswahl verschiedener Dungeon-Etagen und Anpassung der Farming-Strategie.
* **Talentauswahl:** Automatisches Auswählen und Upgraden von Einheitentalenten basierend auf Konfigurationen.
* **Clan-Funktionen:** Automatisches Annehmen von Clan-Mitgliedern (optional), Teilnahme an Clan-Geschenken.
* **Event-Unterstützung:** Automatisches Spielen von Events und Sammeln von Belohnungen.
* **Intelligente Deck-Anpassung:** Vorschläge für Deck-Verbesserungen basierend auf gesammelten Einheiten und Runen.
* **Visuelle Debugging-Tools:** Integration von Visualisierungen zur besseren Überwachung des Bot-Verhaltens.
* **Erweiterte Konfigurationsmöglichkeiten:** Detailliertere Einstellungen für Farming-Strategien, Einheitenerkennung und andere Funktionen über eine Konfigurationsdatei oder GUI.
* **Unterstützung für weitere Emulatoren:** Erweiterung der Kompatibilität auf andere Android-Emulatoren neben Bluestacks.
* **Fehlerbehandlung und Reporting:** Verbesserte Fehlererkennung und detailliertere Protokollierung des Bot-Betriebs.
* **GUI-Verbesserungen:** Benutzerfreundlichere Oberfläche für die Konfiguration und Steuerung des Bots.

## Setup-Anleitung

**Python**

Installiere die neueste Python 3.9 Version (Windows Installer 64-bit).

[https://www.python.org/downloads/](https://www.python.org/downloads/) (Windows 64-Bit Installer) [[https://www.python.org/ftp/python/3.9.13/python-3.9.13-amd64.exe](https://www.python.org/ftp/python/3.9.13/python-3.9.13-amd64.exe)]

Wähle "Add Python to PATH" aus. Überprüfe, ob `python --version` funktioniert und Python 3.9.13 ausgibt.

Lade dieses Repository herunter und entpacke es.

**Bluestacks**

Installiere die neueste Bluestacks 5 Version.

Einstellungen:

(Anzeige) Auflösung: 1600 x 900

(Grafik) Grafik-Engine-Modus: Kompatibilität (kann bei Problemen mit scrcpy helfen)

(Erweitert) Android Debug Bridge: Aktiviert - Notiere dir hier die Portnummer.

Richte ein Google-Konto ein, lade Rush Royale herunter usw.

**Bot**

Führe `install.bat` aus, um das Repository einzurichten und Abhängigkeiten zu installieren.

Führe `launch_gui.bat` aus.

(Temporär) Einheiten und andere Einstellungen müssen in `bot_handler.py` konfiguriert werden. Dies wird in die `config.ini`-Datei verschoben.
