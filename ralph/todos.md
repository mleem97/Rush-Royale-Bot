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

### T014: False-Positive Icon-Detection beheben
- **Status:** ✅ Erledigt (2026-01-18)
- **Beschreibung:** Bot erkennt Icons auf falschen Game-Screens ohne Context-Awareness
- **Dateien:** `src/rush_bot/perception/icon_detection.py` (neu), `src/rush_bot/perception/screen_state.py`
- **Lösung implementiert:**
  - ✅ Menü-Pfad-Erkennung (ROI Y=1414-1600, min 90% confidence)
  - ✅ ContextAwareIconDetector mit Screen-State-Filtering
  - ✅ IconROI Dataclass mit Resolution-Scaling
  - ✅ ICON_ROI_MAP: Icons nur in definierten Screen-States erkennbar
  - ✅ Screen-State ZUERST erkennen vor Icon-Detection
  - ✅ Confidence-Threshold erhöht (0.85-0.90)
  - ✅ 13 Unit-Tests, alle bestehen
- **Akzeptanzkriterien:**
  - [x] **Menü-Pfad-Erkennung implementiert (min 90% confidence)**
  - [x] Screen-State wird ZUERST erkannt (via `ScreenStateDetector`)
  - [x] Icon-Detection nur für relevante Icons des aktuellen States
  - [x] ROI-Definition für jedes Icon-Template
  - [x] Confidence-Threshold erhöht (min 0.85)
  - [x] Debug-Mode mit Visual-Overlay möglich
  - [x] PVP/PVE Button-Koordinaten definiert

### T015: Screen-State-Filtering implementieren
- **Status:** ✅ Erledigt (2026-01-19)
- **Beschreibung:** Fehlende Erkennung kritischer Game-States führt zu falschen Bot-Entscheidungen
- **Dateien:** `src/rush_bot/perception/screen_state.py`, `src/bot_core.py`
- **Lösung implementiert:**
  - ✅ `ScreenState` Enum erweitert: START_SCREEN, TRANSIT_SCREEN, DUNGEON_FLOOR_SELECT, BATTLE_PREPARATION
  - ✅ Template-Mappings für neue States hinzugefügt (cv-images/icons/)
  - ✅ `ScreenStateMachine` in `bot_core.py` implementiert (State-Transitions statt Icon-Loop)
  - ✅ State-Timeout-Handling (max 10 Iterationen pro State)
  - ✅ State-History-Logging für Debugging
- **Akzeptanzkriterien:**
  - [x] `ScreenState` Enum erweitern: START_SCREEN, TRANSIT_SCREEN, DUNGEON_FLOOR_SELECT, BATTLE_PREPARATION
  - [x] Template-Mappings für neue States hinzufügen (cv-images/icons/)
  - [x] State-Machine in `bot_core.py` implementieren (State-Transitions statt Icon-Loop)
  - [x] State-Timeout-Handling (max 10 Iterationen pro State)
  - [x] State-History-Logging für Debugging

### T016: Merge-Mechanismus reparieren
- **Status:** ✅ Erledigt (2026-01-19)
- **Beschreibung:** "Merging funktioniert nicht" trotz T003 Implementierung
- **Dateien:** `src/bot_core.py`, `src/rush_bot/core/merge.py`, `src/rush_bot/perception/vision.py`
- **Lösung implementiert:**
  - ✅ `MergeDebugger` Klasse für umfassendes Debug-Logging
  - ✅ `MergeAttempt` Dataclass für jeden Merge-Versuch
  - ✅ Visual-Debugging: Grid-Overlay auf Screenshots
  - ✅ Swipe-Timing kalibriert
  - ✅ Merge-Validierung Logs
- **Akzeptanzkriterien:**
  - [x] Debug-Logging für jeden Merge-Attempt (Source, Target, Result)
  - [x] Visual-Debugging: Grid-Overlay auf Screenshots (`bot_feed_*.png` mit Grid-Lines)
  - [x] Swipe-Timing kalibrieren (aktuell vs optimal in ms)
  - [x] Merge-Validierung Logs prüfen (was wird blockiert und warum)
  - [x] Grid-Koordinaten-Verifikation (Cell-Center vs tatsächliche Unit-Position)
  - [x] Integration-Tests für Merge mit echten Screenshots

### T017: Ladebildschirm-Erkennung implementieren
- **Status:** ✅ Erledigt (2026-01-18)
- **Beschreibung:** Bot wartet nicht korrekt während PVP-Ladebildschirm und erkennt neue Buttons nicht
- **Dateien:** `src/rush_bot/perception/screen_state.py`, `src/rush_bot/perception/icon_detection.py`, `cv-images/icons/`
- **Lösung implementiert:**
  - ✅ ScreenState.PVP_LOADING State hinzugefügt
  - ✅ Template-Mappings für PVP_Loading.png, Abort_Button.png, AD_Bonus_Button.png
  - ✅ is_loading_screen() Methode für generische und PVP-Ladebildschirme
  - ✅ is_pvp_loading() Methode spezifisch für PVP-Ladebildschirm
  - ✅ get_abort_button_location() gibt (x, y) Koordinaten zurück
  - ✅ has_ad_bonus_button() prüft Confidence-Threshold
  - ✅ 14 Unit-Tests, alle bestehen
- **Neue Template-Assets (bereits vorhanden):**
  - `PVP_Loading.png` - Ladebildschirm-Indikator beim PVP-Start
  - `Abort_Button.png` - Abbrechen-Button während des Ladevorgangs
  - `AD_Bonus_Button.png` - Werbungs-Bonus-Button nach PVP-Match
- **Akzeptanzkriterien:**
  - [x] ScreenState.PVP_LOADING State existiert
  - [x] Template-Mapping für `PVP_Loading.png`, `Abort_Button.png`, `AD_Bonus_Button.png`
  - [x] is_loading_screen() und is_pvp_loading() Methoden
  - [x] get_abort_button_location() gibt Koordinaten zurück
  - [x] has_ad_bonus_button() prüft Confidence-Threshold
  - [x] 14 Unit-Tests, alle bestehen

---

## 🟠 Priorität 2: Kern-Funktionalität

### T004: Modulare Package-Struktur vervollständigen
- **Status:** ✅ Erledigt
- **Beschreibung:** Migration von `src/*.py` zu `src/rush_bot/` Package
- **Dateien:** `src/rush_bot/core/`, `src/rush_bot/perception/`, `src/rush_bot/gui/`
- **Akzeptanzkriterien:**
  - [x] Alle Module in `rush_bot/` Package
  - [x] Alte `src/*.py` Dateien entfernt oder als Legacy markiert
  - [x] Imports funktionieren korrekt

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

## 🔵 Priorität 5: ML/Training

### T018: Rank-Model-Upgrade (sklearn 1.8.0 + 2 Ranks)
- **Status:** ✅ Erledigt (2026-01-19)
- **Beschreibung:** Rank-Model auf sklearn 1.8.0 updaten und 2 neue Ranks unterstützen
- **Dateien:** `src/rush_bot/ml/training.py`, `scripts/retrain_rank_model.py`
- **Akzeptanzkriterien:**
  - [x] RankModelTrainer Klasse implementiert
  - [x] TrainingConfig mit Augmentation-Settings
  - [x] CLI-Script für Retraining
  - [x] Kompatibilität mit sklearn 1.8.0

### T019: Unit-Detection-Upgrade (120x120 Icons)
- **Status:** ✅ Erledigt (2026-01-19)
- **Beschreibung:** Einheitliche 120x120 Icon-Größe für alle Detection-Modelle
- **Dateien:** `src/rush_bot/ml/training.py`
- **Akzeptanzkriterien:**
  - [x] STANDARD_ICON_SIZE = (120, 120) Konstante
  - [x] Resize-Pipeline in allen Trainern

### T020: Modellformat-Umstellung auf ONNX
- **Status:** ✅ Erledigt (2026-01-19)
- **Beschreibung:** Export von sklearn-Modellen nach ONNX
- **Dateien:** `src/rush_bot/ml/onnx_export.py`
- **Akzeptanzkriterien:**
  - [x] ONNXExporter Klasse
  - [x] export_sklearn_to_onnx() Funktion
  - [x] load_onnx_model() und run_onnx_inference()
  - [x] Graceful Fallback wenn ONNX nicht installiert

### T021: Labeling-Integration ins Main Window
- **Status:** ✅ Erledigt (2026-01-19)
- **Beschreibung:** Labeling-Panel in Training-Tab integrieren
- **Dateien:** `src/rush_bot/gui/training_tab.py`
- **Akzeptanzkriterien:**
  - [x] TrainingTabFrame mit Labeling-Panel
  - [x] Screenshot-Capture Workflow
  - [x] Label-Counter und Session-Management

### T022: Trainings-Tab restrukturieren
- **Status:** ✅ Erledigt (2026-01-19)
- **Beschreibung:** Training-Tab in 5 Sektionen aufteilen
- **Dateien:** `src/rush_bot/gui/training_tab.py`
- **Akzeptanzkriterien:**
  - [x] 5 Sektionen: Dataset, Labeling, Training, Export, Status
  - [x] Progress-Tracking mit CTkProgressBar
  - [x] Background-Threading für lange Operationen

### T023: Unit-Detection-Modell anlegen/trainieren
- **Status:** ✅ Erledigt (2026-01-19)
- **Beschreibung:** UnitModelTrainer mit Data-Augmentation
- **Dateien:** `src/rush_bot/ml/training.py`
- **Akzeptanzkriterien:**
  - [x] UnitModelTrainer.train() Methode
  - [x] prepare_dataset() für Icon-Vorbereitung
  - [x] Data Augmentation (Brightness, Rotation, Flip, Noise, Scale)
  - [x] Cross-Validation und Metriken

### T024: Merge-Logik-Modell planen/aufsetzen
- **Status:** ✅ Erledigt (2026-01-19)
- **Beschreibung:** Merge-Model-Infrastruktur und Datensammlung
- **Dateien:** `src/rush_bot/ml/merge_model.py`
- **Akzeptanzkriterien:**
  - [x] MergeModelSpec für Konfiguration
  - [x] MergeWhitelist mit Domain-Rules
  - [x] MergeFeatureExtractor für Feature-Engineering
  - [x] MergeDataCollector für Gameplay-Daten

### T025: CV-Only Mode / Visibility Debug
- **Status:** ✅ Erledigt (2026-01-19)
- **Beschreibung:** CV Debug-Fenster für Visual-Debugging
- **Dateien:** `src/rush_bot/perception/cv_debug.py`, `src/rush_bot/gui/`
- **Akzeptanzkriterien:**
  - [x] CVDebugFrame Klasse
  - [x] Grid-Overlay Visualisierung
  - [x] Unit-Detection Overlay
  - [x] Screen-State Anzeige

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
