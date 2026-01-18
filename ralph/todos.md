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
- **Status:** ⏳ Offen
- **Beschreibung:** Robuste ADB-Verbindungs-Verwaltung
- **Dateien:** `src/rush_bot/core/device.py`
- **Akzeptanzkriterien:**
  - [ ] Auto-Reconnect bei Verbindungsabbruch
  - [ ] Multi-Device-Support
  - [ ] Emulator-Auto-Erkennung

### T006: Screenshot-Pipeline optimieren
- **Status:** ⏳ Offen
- **Beschreibung:** Schnellere und zuverlässigere Screen-Capture
- **Dateien:** `src/rush_bot/core/`, `scrcpy/`
- **Akzeptanzkriterien:**
  - [ ] <100ms Screenshot-Latenz
  - [ ] Fallback von scrcpy zu ADB-Screenshot
  - [ ] Frame-Buffer für konsistente Analyse

---

## 🟡 Priorität 3: Gameplay-Features

### T007: PvE-Dungeon-Loop implementieren
- **Status:** ⏳ Offen
- **Beschreibung:** Vollständige PvE-Automatisierung
- **Akzeptanzkriterien:**
  - [ ] Dungeon-Eintritt automatisiert
  - [ ] Kampf-Loop funktioniert
  - [ ] Ergebnis-Screen erkannt

### T008: Mana-Management verbessern
- **Status:** ⏳ Offen
- **Beschreibung:** Optimales Mana-Upgrade-Timing
- **Akzeptanzkriterien:**
  - [ ] Mana-Level-Erkennung
  - [ ] Upgrade-Priorisierung nach Konfiguration
  - [ ] Boss-Mana-Reserve

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
- **Status:** ⏳ Offen
- **Beschreibung:** Mehr Unit-Tests für Kernfunktionen
- **Akzeptanzkriterien:**
  - [ ] >70% Coverage für `rush_bot/core/`
  - [ ] >70% Coverage für `rush_bot/perception/`
  - [ ] Mocking für ADB-Calls

### T011: Type Hints vervollständigen
- **Status:** ⏳ Offen
- **Beschreibung:** Strenge Typisierung im gesamten Package
- **Akzeptanzkriterien:**
  - [ ] `mypy src` ohne Fehler
  - [ ] Kein `Any` außer bei externen APIs
  - [ ] Docstrings für öffentliche Funktionen

### T012: CI/CD Pipeline einrichten
- **Status:** ⏳ Offen
- **Beschreibung:** GitHub Actions für automatisierte Tests
- **Akzeptanzkriterien:**
  - [ ] Tests bei jedem Push
  - [ ] Linting-Check
  - [ ] Type-Check

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
