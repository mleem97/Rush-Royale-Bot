# RushBot - Aufgabenliste (Todos)

> Priorisierte Liste aller zu implementierenden Features und Fixes

---

## 🔴 Priorität 1: Kritische Bugs

### T001: Unit-Erkennung reparieren
- **Status:** ✅ Erledigt
- **Beschreibung:** Farbbasierte Unit-Erkennung funktioniert nicht zuverlässig
- **Dateien:** `src/bot_perception.py`, `src/rush_bot/perception/`
- **Akzeptanzkriterien:**
  - [x] Units werden korrekt aus Screenshots extrahiert
  - [x] Mindestens 90% Erkennungsrate für bekannte Units
  - [x] Tests für Unit-Erkennung bestehen

### T002: Grid-Parsing korrigieren
- **Status:** ✅ Erledigt
- **Beschreibung:** Die 15 Grid-Zellen werden nicht korrekt aus dem Screenshot extrahiert
- **Dateien:** `src/bot_core.py`, `src/rush_bot/perception/`
- **Akzeptanzkriterien:**
  - [x] Alle 15 Zellen werden korrekt lokalisiert
  - [x] Zellen-Koordinaten sind für verschiedene Auflösungen kalibriert
  - [x] Unit-Tests für Grid-Extraktion vorhanden (20 Tests)

### T003: Merge-Logik stabilisieren
- **Status:** ✅ Erledigt
- **Beschreibung:** Falsches Matching von Einheiten beim Mergen
- **Dateien:** `src/bot_core.py`, `src/rush_bot/core/merge.py`
- **Akzeptanzkriterien:**
  - [x] Nur gleiche Unit-Typen werden gemerged
  - [x] Merge-Richtung wird korrekt berechnet
  - [x] DPS-Units werden geschützt (konfigurierbar)
  - [x] Tests für Merge-Logik vorhanden (31 Tests)

---

## 🟠 Priorität 2: Kern-Funktionalität

### T004: Modulare Package-Struktur vervollständigen
- **Status:** ⏳ Offen
- **Beschreibung:** Migration von `src/*.py` zu `src/rush_bot/` Package
- **Dateien:** `src/rush_bot/core/`, `src/rush_bot/perception/`, `src/rush_bot/gui/`
- **Akzeptanzkriterien:**
  - [ ] Alle Module in `rush_bot/` Package
  - [ ] Alte `src/*.py` Dateien entfernt oder als Legacy markiert
  - [ ] Imports funktionieren korrekt

### T005: Device-Manager implementieren
- **Status:** ✅ Erledigt
- **Beschreibung:** Robuste ADB-Verbindungs-Verwaltung
- **Dateien:** `src/rush_bot/core/device.py`
- **Akzeptanzkriterien:**
  - [x] Auto-Reconnect bei Verbindungsabbruch
  - [x] Multi-Device-Support
  - [x] Emulator-Auto-Erkennung

### T006: Screenshot-Pipeline optimieren
- **Status:** ✅ Erledigt
- **Beschreibung:** Schnellere und zuverlässigere Screen-Capture
- **Dateien:** `src/rush_bot/core/screenshot.py`
- **Akzeptanzkriterien:**
  - [x] <100ms Screenshot-Latenz (scrcpy: ~30-50ms)
  - [x] Fallback von scrcpy zu ADB-Screenshot
  - [x] Frame-Buffer für konsistente Analyse

---

## 🟡 Priorität 3: Gameplay-Features

### T007: PvE-Dungeon-Loop implementieren
- **Status:** ✅ Erledigt
- **Beschreibung:** Vollständige PvE-Automatisierung
- **Dateien:** `src/rush_bot/core/dungeon.py`
- **Akzeptanzkriterien:**
  - [x] Dungeon-Eintritt automatisiert
  - [x] Kampf-Loop funktioniert
  - [x] Ergebnis-Screen erkannt

### T008: Mana-Management verbessern
- **Status:** ✅ Erledigt
- **Beschreibung:** Optimales Mana-Upgrade-Timing
- **Dateien:** `src/rush_bot/core/mana.py`
- **Akzeptanzkriterien:**
  - [x] Mana-Level-Erkennung
  - [x] Upgrade-Priorisierung nach Konfiguration
  - [x] Boss-Mana-Reserve

### T009: Bildschirm-Zustand-Erkennung
- **Status:** ✅ Erledigt
- **Beschreibung:** Erkennung verschiedener Game-Screens
- **Dateien:** `src/rush_bot/perception/screen_state.py`
- **Akzeptanzkriterien:**
  - [x] Home-Screen erkennen
  - [x] Kampf-Screen erkennen
  - [x] Popup-Handling
  - [x] Ad-Skip

---

## 🟢 Priorität 4: Qualität & Tooling

### T010: Test-Coverage erhöhen
- **Status:** ✅ Erledigt
- **Beschreibung:** Mehr Unit-Tests für Kernfunktionen
- **Akzeptanzkriterien:**
  - [x] >70% Coverage für `rush_bot/core/` (device 85%, bot 100%, logger 100%)
  - [x] >70% Coverage für `rush_bot/perception/` (vision 72%, screen_state 88%)
  - [x] Mocking für ADB-Calls (unittest.mock für alle Device-Tests)

### T011: Type Hints vervollständigen
- **Status:** ✅ Erledigt
- **Beschreibung:** Strenge Typisierung im gesamten Package
- **Akzeptanzkriterien:**
  - [x] `mypy src` ohne Fehler
  - [x] Kein `Any` außer bei externen APIs
  - [x] Docstrings für öffentliche Funktionen

### T012: CI/CD Pipeline einrichten
- **Status:** ✅ Erledigt
- **Beschreibung:** GitHub Actions für automatisierte Tests
- **Dateien:** `.github/workflows/tests.yml`, `.github/workflows/release.yml`
- **Akzeptanzkriterien:**
  - [x] Tests bei jedem Push
  - [x] Linting-Check
  - [x] Type-Check

---

## 📋 Legende

| Symbol | Bedeutung |
|--------|-----------|
| ⏳ | Offen / Nicht gestartet |
| 🔄 | In Bearbeitung |
| ✅ | Abgeschlossen |
| ❌ | Blockiert / Abgebrochen |

---

*Zuletzt aktualisiert: Januar 2026*
