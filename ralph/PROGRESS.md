# RushBot - Entwicklungsfortschritt

> Tracking der Task-Implementierung durch Subagenten

---

## 📊 Übersicht

| Kategorie | Gesamt | Offen | In Arbeit | Erledigt |
|-----------|--------|-------|-----------|----------|
| Kritische Bugs | 3 | 0 | 0 | 3 |
| Kern-Funktionalität | 3 | 3 | 0 | 0 |
| Gameplay-Features | 3 | 3 | 0 | 0 |
| Qualität & Tooling | 3 | 2 | 0 | 1 |
| **Gesamt** | **12** | **8** | **0** | **4** |

---

## 🔴 Kritische Bugs (Priorität 1)

| ID | Task | Status | Bearbeiter | Datum |
|----|------|--------|------------|-------|
| T001 | Unit-Erkennung reparieren | ✅ Erledigt | Orchestrator | 2026-01-18 |
| T002 | Grid-Parsing korrigieren | ✅ Erledigt | Subagent | 2026-01-18 |
| T003 | Merge-Logik stabilisieren | ✅ Erledigt | Subagent | 2026-01-18 |

---

## 🟠 Kern-Funktionalität (Priorität 2)

| ID | Task | Status | Bearbeiter | Datum |
|----|------|--------|------------|-------|
| T004 | Modulare Package-Struktur | ⏳ Offen | - | - |
| T005 | Device-Manager implementieren | ⏳ Offen | - | - |
| T006 | Screenshot-Pipeline optimieren | ⏳ Offen | - | - |

---

## 🟡 Gameplay-Features (Priorität 3)

| ID | Task | Status | Bearbeiter | Datum |
|----|------|--------|------------|-------|
| T007 | PvE-Dungeon-Loop | ⏳ Offen | - | - |
| T008 | Mana-Management | ⏳ Offen | - | - |
| T009 | Bildschirm-Zustand-Erkennung | ⏳ Offen | - | - |

---

## 🟢 Qualität & Tooling (Priorität 4)

| ID | Task | Status | Bearbeiter | Datum |
|----|------|--------|------------|-------|
| T010 | Test-Coverage erhöhen | ⏳ Offen | - | - |
| T011 | Type Hints vervollständigen | ⏳ Offen | - | - |
| T012 | CI/CD Pipeline | ⏳ Offen | - | - |
| T013 | Bug-Fixes in gui.py | ✅ Erledigt | Orchestrator | 2026-01-18 |

---

## 📝 Änderungsprotokoll

### [2026-01-18] T003: Merge-Logik stabilisiert
- **Problem:** Merge-Validierung fehlte, DPS-Schutz war inkonsistent, keine Typen-Prüfung
- **Lösung:** Implementierung einer robusten `MergeLogic` Klasse mit Validierung und DPS-Schutz
- **Änderungen:**
  - `src/rush_bot/core/merge.py`: Neue Klassen `MergeValidator`, `MergeLogic`, `MergeCandidate`, `MergeConfig`, `MergeResult`
  - `src/rush_bot/core/__init__.py`: Neue Exports hinzugefügt
  - `src/bot_core.py`: `merge_unit()` mit Validierung erweitert, `_get_protected_units()` und `_apply_dps_protection()` hinzugefügt
  - `tests/test_core.py`: 31 neue Unit-Tests für Merge-Logik
- **Features:**
  - **Typ-Validierung:** `MergeValidator.can_merge()` prüft gleichen Typ UND Rang
  - **Special Units:** Harlequin, Dryad, Mime, Scrapper können mit anderen Typen mergen
  - **DPS-Schutz:** Konfigurierbar via `config.ini` (`dps_unit`), schützt wenn ≤3 Einheiten
  - **Merge-Richtung:** `calculate_merge_direction()` berechnet korrekte Swipe-Richtung
  - **Candidate Selection:** `select_best_candidate()` priorisiert nach Rang
- **Akzeptanzkriterien:**
  - [x] Nur gleiche Unit-Typen werden gemerged (validiert via `merge_unit(validate=True)`)
  - [x] Merge-Richtung wird korrekt berechnet (`calculate_merge_direction()`)
  - [x] DPS-Units werden geschützt (konfigurierbar via `_apply_dps_protection()`)
  - [x] Tests für Merge-Logik vorhanden (31 neue Tests)
- **Tests:** 73 Tests bestehen (31 neue Merge-Tests)

### [2026-01-18] T002: Grid-Parsing korrigiert
- **Problem:** Grid-Koordinaten waren hardcodiert für 1080x1920 Auflösung
- **Lösung:** Implementierung einer `GridExtractor` Klasse für auflösungsunabhängige Koordinatenberechnung
- **Änderungen:**
  - `src/rush_bot/perception/vision.py`: Neue `GridExtractor` und `GridConfig` Klassen hinzugefügt
  - `src/rush_bot/perception/__init__.py`: Neue Exports hinzugefügt
  - `src/bot_core.py`: `get_grid()` und `scan_grid()` aktualisiert für Auflösungs-Unterstützung
  - `tests/test_perception.py`: 20 neue Unit-Tests für Grid-Extraktion
- **Features:**
  - Alle 15 Zellen (3x5) werden korrekt lokalisiert
  - Automatische Skalierung für verschiedene Auflösungen (720p, 1080p, 1440p, etc.)
  - Hilfsmethoden: `get_cell_center()`, `get_cell_bounds()`, `cell_index_to_pos()`
  - Custom `GridConfig` für manuelle Kalibrierung möglich
- **Tests:** 42 Tests bestehen (20 neue Grid-Tests)

### [2026-01-18] Phase 0 & Erste Iteration
- Progress-Datei erstellt
- 12 initiale Tasks definiert
- Tooling geprüft (pytest, ruff, mypy installiert)
- T001: Unit-Erkennung bereits in `vision.py` implementiert (BotPerception Klasse)
- Bug-Fix: Undefined variable `e` in Exception-Handlern in `gui.py` behoben
- Code formatiert mit `ruff format .`
- Alle 22 Tests bestehen

---

## 📋 Legende

| Symbol | Bedeutung |
|--------|-----------|
| ⏳ | Offen / Nicht gestartet |
| 🔄 | In Bearbeitung |
| ✅ | Abgeschlossen |
| ❌ | Blockiert |

---

*Automatisch aktualisiert durch Subagenten*
