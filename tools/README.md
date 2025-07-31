# 🛠️ Rush Royale Bot - Tools & Utilities

Dieser Ordner enthält alle Entwicklungstools, Hilfsprogramme und Dokumentation, die nicht für den normalen Bot-Betrieb benötigt werden.

## 📂 Inhalt

### 🔧 Entwicklungstools
- **`test_dependencies.py`** - Überprüft alle Python-Abhängigkeiten
- **`health_check.py`** - Umfassende System-Gesundheitsprüfung (7 Checks)
- **`version.py`** - Versionsinformationen und -verwaltung
- **`version_info.py`** - Schöne Anzeige der Versionsinformationen

### 🔌 ADB & Device Management
- **`device_manager.py`** - Umfassendes ADB-Geräteverwaltung
- **`fix_multiple_devices.py`** - Behebt "more than one device" Fehler
- **`fix_devices.bat`** - Ein-Klick Lösung für Gerätekonflikte
- **`advanced_device_diagnostics.py`** - Erweiterte Geräte-Diagnose

### 📚 Dokumentation
- **Alle Dokumentation ist jetzt im `wiki/` Ordner organisiert**
- **Siehe `wiki/Development-Tools.md`** für detaillierte Tool-Dokumentation
- **Siehe `wiki/README.md`** für vollständige Dokumentationsübersicht

## 🚀 Verwendung

### Aus dem Hauptverzeichnis ausführen:
```batch
# Systemstatus prüfen:
python tools\version_info.py

# Abhängigkeiten testen:
python tools\test_dependencies.py

# Gerätekonflikte beheben:
python tools\fix_multiple_devices.py
# oder:
tools\fix_devices.bat

# Geräte verwalten:
python tools\device_manager.py --list
python tools\device_manager.py --restart-adb
```

### Direkt im tools Ordner:
```batch
cd tools

# Version anzeigen:
python version_info.py

# Abhängigkeiten testen:
python test_dependencies.py

# Geräte verwalten:
python device_manager.py
```

## 💡 Tipps

- **Für normale Bot-Nutzung**: Diese Tools sind optional - verwenden Sie einfach `launch_gui.bat`
- **Bei Problemen**: Schauen Sie zuerst in die entsprechenden Tools in diesem Ordner
- **Für Entwickler**: Alle Entwicklungstools und Dokumentation sind hier organisiert

## 🔄 Aktualisierung

Wenn neue Tools oder Dokumentation hinzugefügt werden, finden Sie diese in diesem Ordner. Der Hauptordner bleibt sauber und enthält nur die produktiven Bot-Dateien.

---

*Diese Tools unterstützen den Rush Royale Bot, sind aber für den normalen Betrieb nicht erforderlich.*
