# RushBot - Projektübersicht 🎮🤖

> Automatisierter Gameplay-Assistent für Rush Royale basierend auf Computer Vision und Machine Learning

---

## 📋 Inhaltsverzeichnis

- [Vision & Ziele](#-vision--ziele)
- [Funktionsumfang](#-funktionsumfang)
- [Technologie-Stack](#-technologie-stack)
- [Systemarchitektur](#-systemarchitektur)
- [Projektstruktur](#-projektstruktur)
- [Kernkomponenten](#-kernkomponenten)
- [Machine Learning Pipeline](#-machine-learning-pipeline)
- [Konfiguration](#-konfiguration)
- [Projekthistorie](#-projekthistorie)
- [Roadmap](#-roadmap)

---

## 🎯 Vision & Ziele

### Hauptziel

RushBot ist ein fortschrittlicher Python-basierter Automatisierungsbot für das Mobile-Game **Rush Royale**. Das Projekt kombiniert:

- **Computer Vision** für Echtzeit-Spielzustandserkennung
- **Machine Learning** für strategische Entscheidungsfindung
- **Android-Gerätesteuerung** für autonomes Gameplay

### Projektziele

| Ziel | Beschreibung | Status |
|------|--------------|--------|
| **Autonomes Gameplay** | Vollautomatisches Spielen von PvE/PvP-Modi | ✅ Umgesetzt |
| **Unit-Erkennung** | CV-basierte Erkennung von 70+ Spieleinheiten | ✅ Umgesetzt |
| **Rang-Klassifikation** | ML-Modell zur Bestimmung von Einheiten-Rängen (1-5) | ✅ Umgesetzt |
| **Cross-Platform** | Unterstützung für Windows, Linux, macOS | ✅ Umgesetzt |
| **Multi-Emulator** | Kompatibilität mit BlueStacks, LDPlayer, MEmu | ✅ Umgesetzt |
| **Reinforcement Learning** | Experimentelle RL-Umgebung für optimale Strategien | 🔄 In Entwicklung |

---

## 🚀 Funktionsumfang

### Kern-Features

```
┌─────────────────────────────────────────────────────────────┐
│                    RushBot Features                         │
├─────────────────────────────────────────────────────────────┤
│  ✅ Automatisches Unit-Merging und Spawning                 │
│  ✅ Mana-Upgrade-Management                                 │
│  ✅ PvE-Dungeon-Automatisierung                             │
│  ✅ Unit-Template-Erfassungsmodus                           │
│  ✅ Echtzeit-Spielzustandsanalyse                           │
│  ✅ Moderne GUI mit Live-Logging                            │
│  ✅ Konfigurierbare Strategien                              │
└─────────────────────────────────────────────────────────────┘
```

### Spielmodi

- **PvE (Dungeon)**: Automatisiertes Durchspielen von Dungeon-Etagen
- **PvP**: Unterstützung für Spieler-vs-Spieler-Matches

### Unterstützte Einheiten

| Seltenheit | Unterstützt | Hinweise |
|------------|-------------|----------|
| Common | ✅ Vollständig | Alle Einheiten |
| Rare | ✅ Vollständig | Alle Einheiten |
| Epic | ✅ Vollständig | Alle Einheiten |
| Legendary | ⚠️ 31/40 | Twins, Treant, Mole + weitere benötigen Implementierung |

---

## 🛠 Technologie-Stack

### Programmiersprache & Framework

```yaml
Sprache: Python 3.10 - 3.14
GUI: CustomTkinter 5.2+
Build: setuptools, wheel
Testing: pytest, pytest-cov
Linting: ruff, black, isort
Type Checking: mypy, pyright
```

### Kernabhängigkeiten

| Paket | Version | Zweck |
|-------|---------|-------|
| `numpy` | ≥1.26.0 | Array-Operationen & Bildverarbeitung |
| `opencv-python` | ≥4.10.0 | Computer Vision & Template Matching |
| `pandas` | ≥2.2.0 | Datenanalyse & Grid-Management |
| `scikit-learn` | ≥1.5.0 | ML-basierte Rang-Erkennung |
| `adbutils` | ≥2.0.0 | Android Debug Bridge Kommunikation |
| `av` | ≥12.0.0 | Video-Decoding (scrcpy) |
| `Pillow` | ≥10.0.0 | Bildverarbeitung |
| `customtkinter` | ≥5.2.0 | Moderne GUI |

### Optionale ML-Abhängigkeiten

| Paket | Version | Zweck |
|-------|---------|-------|
| `gymnasium` | ≥1.0.0 | RL-Umgebungs-Framework |
| `stable-baselines3` | ≥2.4.0 | RL-Algorithmen |

---

## 📐 Systemarchitektur

### Schichtenmodell

```
┌─────────────────────────────────────────────────────────────────┐
│                         GUI Layer                                │
│                        (gui.py)                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Options   │  │ Combat Info │  │      Log Display        │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Bot Handler Layer                            │
│                    (bot_handler.py)                              │
│         Lifecycle Management, Game Loop, Unit Selection          │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Bot Core Layer                             │
│                      (bot_core.py)                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │    Click    │  │   Screen    │  │    Template Matching    │  │
│  │   Control   │  │   Capture   │  │    (Icon Detection)     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└───────────────────────────┬─────────────────────────────────────┘
                            │
          ┌─────────────────┼─────────────────┐
          ▼                 ▼                 ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  Bot Perception │ │    Port Scan    │ │  Scrcpy Client  │
│ (bot_perception)│ │  (port_scan.py) │ │   (scrcpy/)     │
│  CV & ML Engine │ │  ADB Discovery  │ │  Screen Mirror  │
└─────────────────┘ └─────────────────┘ └─────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Android Device                              │
│              (Emulator oder Physisches Gerät via ADB)            │
└─────────────────────────────────────────────────────────────────┘
```

### Datenfluss

1. **Screen Capture**: Bot erfasst Gerätebildschirm via ADB-Screenshot oder scrcpy-Stream
2. **Icon Detection**: OpenCV Template-Matching identifiziert UI-Zustand
3. **Grid Analysis**: Bildschirm wird auf 15-Zellen-Grid zugeschnitten
4. **Unit Recognition**: Jede Zelle wird per Farbanalyse mit bekannten Templates abgeglichen
5. **Rank Detection**: ML-Modell klassifiziert Einheiten-Rang (1-5) aus Kantenmerkmalen
6. **Decision Making**: Bot entscheidet Aktionen basierend auf Grid-Zustand und Konfiguration
7. **Input Injection**: Touch-Befehle werden via ADB oder scrcpy-Control gesendet

---

## 📁 Projektstruktur

```
Rush-Royale-Bot/
├── src/                      # Hauptquellcode
│   ├── rush_bot/            # Neues modulares Package
│   │   ├── core/            # Kern-Bot-Logik
│   │   ├── gui/             # GUI-Komponenten
│   │   └── perception/      # CV & ML Module
│   ├── gui.py               # CustomTkinter GUI
│   ├── bot_core.py          # Kern-Bot-Logik (Bot-Klasse)
│   ├── bot_handler.py       # Bot-Lifecycle-Management
│   ├── bot_perception.py    # Computer Vision & ML
│   ├── bot_env.py           # Gymnasium RL-Umgebung
│   ├── bot_logger.py        # Logging mit Farbunterstützung
│   └── port_scan.py         # ADB-Geräte-Erkennung
│
├── cv-images/               # Computer Vision Assets
│   ├── all_units/           # Unit-Icon-Templates
│   ├── icons/               # UI-Element-Templates
│   ├── unit_rank/           # Rang-Referenzbilder
│   └── units/               # Aktives Deck (Runtime)
│
├── machine_learning/        # ML-Trainingsdaten
│   ├── inputs/              # Gelabelte Rang-Bilder
│   ├── raw_input/           # Rohe erfasste Bilder
│   └── unit_inputs/         # Unit-spezifische Trainingsbilder
│
├── models/                  # Trainierte ML-Modelle
│   └── unit_labels.json     # Unit-Label-Mapping
│
├── scripts/                 # Utility-Skripte
│   ├── train_rank_model.py  # Rang-Modell-Training
│   └── train_unit_classifier.py  # Unit-Klassifizierer-Training
│
├── tests/                   # Unit-Tests
│   ├── test_core.py
│   ├── test_gui.py
│   └── test_perception.py
│
├── vendored/                # Externe Bibliotheken
│   └── scrcpy-client/       # Python scrcpy-Client
│
├── config.ini               # Bot-Konfiguration
├── pyproject.toml           # Projekt-Metadaten
├── requirements.txt         # Produktions-Abhängigkeiten
└── requirements-dev.txt     # Entwicklungs-Abhängigkeiten
```

---

## 🔧 Kernkomponenten

### 1. Bot Core (`bot_core.py`)

**Verantwortlichkeiten:**
- ADB-Geräteverbindung via `adbutils`
- Screen Capture (PIL Screenshot oder scrcpy)
- Touch/Click-Input-Simulation
- Icon-Erkennung via OpenCV Template Matching
- Grid-Zellen-Extraktion für Unit-Erkennung

**Schlüsselklasse: `Bot`**
```python
class Bot:
    """Kern-Bot-Klasse für Rush Royale Automatisierung."""
    
    def __init__(self, gui=None):
        self.gui = gui
        self.running = False
        self.grid_df = None
        self.device = DeviceManager()
    
    def start(self): ...    # Starte Automatisierungsschleife
    def stop(self): ...     # Stoppe den Bot
    def tap(x, y): ...      # Tippe auf Koordinaten
    def screenshot(): ...   # Erfasse Bildschirm
```

### 2. Bot Handler (`bot_handler.py`)

**Verantwortlichkeiten:**
- Bot-Lifecycle-Management (Start/Stop)
- Haupt-Game-Loop-Orchestrierung
- Unit-Template-Auswahl und -Kopierung
- Combat-Loop-Ausführung

### 3. Bot Perception (`bot_perception.py`)

**Verantwortlichkeiten:**
- Unit-Typ-Erkennung via Farbanalyse
- Rang-Erkennung via ML (LogisticRegression auf Canny-Kanten)
- Grid-Zustandsanalyse (15-Zellen-Spielgrid)
- Trainingsdaten-Management

**ML-Pipeline:**
```
Screenshot → Grid-Extraktion → Canny Edge Detection → 
Feature-Vektor → LogisticRegression → Rang (1-5)
```

### 4. Port Scan (`port_scan.py`)

**Verantwortlichkeiten:**
- Multi-threaded ADB-Port-Scanning
- Emulator-Auto-Erkennung
- Geräteverbindungs-Management

### 5. GUI (`gui.py`)

**Verantwortlichkeiten:**
- CustomTkinter-basierte Benutzeroberfläche
- Konfigurations-Management
- Echtzeit-Status-Anzeige
- Thread-Management für Bot-Ausführung

---

## 🤖 Machine Learning Pipeline

### Rang-Erkennung (Produktiv)

```
Input: Unit-Zellen-Bild (90x90 px)
    │
    ▼
┌─────────────────────────────┐
│   Canny Edge Detection      │
│   cv2.Canny(img, 50, 150)   │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│   Feature Extraction        │
│   Flatten → 1D Vector       │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│   LogisticRegression        │
│   sklearn (rank_model.pkl)  │
└──────────────┬──────────────┘
               │
               ▼
Output: Rang 1-5
```

### Reinforcement Learning (Experimentell)

**Umgebung: `bot_env.py`**

| Aspekt | Details |
|--------|---------|
| **Observation Space** | 15 Grid-Zellen × (Unit-Typ, Rang) = (15, 2) |
| **Action Space** | 67 Aktionen (Merge: 0-59, Summon: 60, Upgrade: 61-65, Wait: 66) |
| **Rewards** | +1/Step, +10 High Rank, +5 Merge, +100 Floor Complete, -100 Game Over |

---

## ⚙️ Konfiguration

### config.ini

```ini
[bot]
floor = 10                    # Dungeon-Etage (PvE)
mana_level = 1,3,5            # Mana-Upgrade-Prioritäten
units = chemist, harlequin, bombardier, dryad, demon_hunter
dps_unit = demon_hunter       # Haupt-Schadenseinheit
pve = True                    # PvE-Modus (False = PvP)
require_shaman = False        # Verlassen wenn kein Shaman-Partner
```

### Umgebungsvariablen (.env)

```bash
# ADB-Konfiguration
ADB_HOST=127.0.0.1
ADB_PORT=5037

# Bot-Konfiguration
BOT_DEBUG=false
BOT_LOG_LEVEL=INFO

# ML-Konfiguration
ML_MODEL_PATH=models/rank_classifier.pkl
ML_CONFIDENCE_THRESHOLD=0.8
```

---

## 📜 Projekthistorie

Das Projekt baut auf mehreren Rush Royale Bot-Implementierungen auf:

```
2021 ─────────────────────────────────────────────────────────────►

    ┌─────────────────────┐
    │   AxelBjork         │  Original Rush Royale Bot
    │   Rush-Royale-Bot   │  Grundlegende Automatisierung
    └──────────┬──────────┘
               │
               ▼
    ┌─────────────────────┐
    │   mleem97           │  Verbesserte Stabilität
    │   Rush-Royale-Bot   │  Bug-Fixes & Optimierungen
    └──────────┬──────────┘
               │
               ▼
    ┌─────────────────────┐
    │   Frikadellental    │  Komplette Neugestaltung
    │   Rush-Royale-AI    │  Moderne AI-Ansätze
    └──────────┬──────────┘
               │
               ▼
    ┌─────────────────────┐
    │   RushBot 2026.1    │  Aktuelle Version
    │   Unified Codebase  │  CV + ML + RL
    └─────────────────────┘
```

### Danksagungen

- **AxelBjork** - Ursprüngliche Rush Royale Bot-Implementierung
- **mleem97** - Verbesserungen und Bug-Fixes
- **Frikadellental** - AI-fokussierte Neugestaltung
- **leng-yue** - [py-scrcpy-client](https://github.com/leng-yue/py-scrcpy-client) Bibliothek

---

## 🗺️ Roadmap

### Version 2026.1 (Aktuell)

#### ✅ Abgeschlossen
- [x] Modulare Package-Struktur (`rush_bot/`)
- [x] CustomTkinter GUI mit modernem Design
- [x] Rang-ML-Modell (LogisticRegression)
- [x] Multi-Python-Support (3.10-3.14)
- [x] Cross-Platform-Installer (Windows, Linux, macOS)
- [x] ADB-Geräte-Erkennung und -Verbindung
- [x] Scrcpy-Integration für Screen-Capture
- [x] Basis-Template-Matching für Icons

#### 🔴 Kritische Bugs (Priorität 1)
- [ ] **Unit-Erkennung funktioniert nicht** - Farbbasierte Erkennung unzuverlässig
- [ ] **Grid-Parsing fehlerhaft** - Zellen werden nicht korrekt extrahiert
- [ ] **Merge-Logik instabil** - Falsches Matching von Einheiten

#### 🎮 Gameplay-Automatisierung

**PvE (Dungeon/Koop):**
- [ ] Vollständiger PvE-Dungeon-Modus
- [ ] Koop-Modus Support (2-Spieler-Dungeons)
- [ ] Automatische Dungeon-Etagen-Auswahl
- [ ] Boss-Erkennung und -Strategien
- [ ] Dungeon-Belohnungs-Optimierung
- [ ] Automatisches Wiederbetreten nach Game-Over

**PvP (Arena/Liga):**
- [ ] Vollständiger PvP-Modus
- [ ] Liga-Kampf-Automatisierung
- [ ] Gegner-Analyse (erkenne feindliches Deck)
- [ ] Adaptive Strategie basierend auf Gegner
- [ ] Automatische Match-Suche
- [ ] Trophäen-Management

**Events & Spezial-Modi:**
- [ ] Event-Erkennung (Clan Wars, Turniere)
- [ ] Tägliche Quests automatisieren
- [ ] Clan-Boss-Support
- [ ] Season-Pass-Optimierung

#### 🎯 Unit-Management

**Erkennung:**
- [ ] Zuverlässige Unit-Typ-Erkennung (alle 70+ Units)
- [ ] Rang-Erkennung (1-7, inkl. legendäre Ränge)
- [ ] Leere Zellen vs. Unit-Unterscheidung
- [ ] Spezial-Unit-Status (z.B. aktive Fähigkeiten)

**Spezial-Unit-Mechaniken:**
- [ ] **Harlequin** - Kopier-Logik implementieren
- [ ] **Dryad** - Rang-Up-Mechanik
- [ ] **Scrapper** - Gold-Optimierung
- [ ] **Shaman** - Debuff-Erkennung beim Gegner
- [ ] **Portal Keeper** - Teleport-Logik
- [ ] **Mime** - Kopier-Verhalten
- [ ] **Summoner** - Beschwörungs-Management
- [ ] **Twins** - Doppel-Unit-Handling
- [ ] **Treant** - Spezial-Merge
- [ ] **Mole** - Tunnel-Mechanik

**Merge-Strategien:**
- [ ] Intelligentes Merge-Prioritätssystem
- [ ] DPS-Unit-Schutz (nicht mergen)
- [ ] Support-Unit-Positionierung
- [ ] Rang-Balance auf dem Board

#### 💎 Mana & Ressourcen-Management

- [ ] Optimales Mana-Upgrade-Timing
- [ ] Gold-Tracking und -Optimierung
- [ ] Spawn-Timing basierend auf Mana-Regeneration
- [ ] Boss-Mana-Reserve (vor Boss sparen)
- [ ] Mana-Effizienz-Analyse

#### 🧠 Intelligenz & Strategie

**Entscheidungsfindung:**
- [ ] Board-State-Bewertung
- [ ] Nächste-Aktion-Priorisierung
- [ ] Zeitkritische Entscheidungen (Boss-Wellen)
- [ ] Anpassung an Spielsituation

**Deck-Synergien:**
- [ ] Deck-Synergie-Erkennung
- [ ] Automatische Strategie-Auswahl pro Deck
- [ ] Support-DPS-Balance
- [ ] Counter-Strategien gegen bekannte Meta-Decks

#### 🔍 Bildschirm-Erkennung

- [ ] Home-Screen-Erkennung
- [ ] Kampf-Screen-Erkennung
- [ ] Popup-/Dialog-Handling
- [ ] Ad-Erkennung und -Skip
- [ ] Verbindungsfehler-Handling
- [ ] Lade-Bildschirm-Warten
- [ ] Ergebnis-Screen-Parsing (Sieg/Niederlage)

#### 📊 Statistiken & Logging

- [ ] Match-Historie speichern
- [ ] Win/Loss-Tracking
- [ ] Unit-Performance-Statistiken
- [ ] Durchschnittliche Match-Dauer
- [ ] Mana-Effizienz-Metriken
- [ ] Export als CSV/JSON

#### ⚡ Performance & Stabilität

- [ ] Reduzierte Reaktionszeiten (<100ms)
- [ ] Fehlertoleranz bei Verbindungsabbrüchen
- [ ] Auto-Reconnect bei Device-Disconnect
- [ ] Memory-Leak-Prävention
- [ ] Langzeit-Stabilität (>8h Betrieb)

---

### Geplante Features (Langfristig)

#### 🤖 Machine Learning Verbesserungen
- [ ] CNN-basierte Unit-Klassifizierung
- [ ] RL-Agent für optimale Spielstrategie
- [ ] Transfer Learning für neue Units
- [ ] Online-Learning während des Spielens
- [ ] Model-Auto-Updater bei Game-Updates

#### 🛠 Benutzerfreundlichkeit
- [ ] Auto-Deck-Builder basierend auf verfügbaren Units
- [ ] Strategie-Vorlagen (Aggro, Control, etc.)
- [ ] Profil-System (mehrere Konfigurationen)
- [ ] Scheduler für automatische Spielzeiten
- [ ] Discord-/Telegram-Benachrichtigungen

#### 📖 Dokumentation
- [ ] Vollständiges Wiki mit Tutorials
- [ ] Video-Guides für Setup
- [ ] API-Dokumentation für Entwickler
- [ ] Troubleshooting-Guide

#### 🌐 Erweiterte Features
- [ ] Web-Dashboard für Remote-Monitoring
- [ ] Multi-Device-Support (mehrere Emulatoren)
- [ ] Docker-Container-Deployment
- [ ] Cloud-basiertes Training
- [ ] Community-Strategien-Sharing My.Games App Support
- [ ] Browser Version Support
- [ ] iOS Support

---

## 📝 Lizenz

Dieses Projekt ist unter der **MIT License** lizenziert.

## ⚠️ Disclaimer

Dieser Bot wurde für Bildungs- und Forschungszwecke erstellt. Die Nutzung erfolgt auf eigene Gefahr. Die Entwickler übernehmen keine Verantwortung für Konsequenzen durch die Nutzung dieser Software.

---

*Dokumentation generiert: Januar 2026*  
*Version: 2026.1*
