# Architecture Overview

## System Design

The Rush Royale Bot is designed as a modular automation system that interfaces with Android devices to play Rush Royale autonomously.

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
          │                 │                 │
          └─────────────────┼─────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Android Device                              │
│              (Emulator or Physical Device via ADB)               │
└─────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

### GUI Layer (`gui.py`)
- Tkinter-based user interface
- Configuration management
- Real-time status display
- Thread management for bot execution

### Bot Handler Layer (`bot_handler.py`)
- Bot lifecycle management (start/stop)
- Main game loop orchestration
- Unit template selection and copying
- Combat loop execution

### Bot Core Layer (`bot_core.py`)
- ADB device connection via `adbutils`
- Screen capture (PIL screenshot or scrcpy)
- Touch/click input simulation
- Icon detection via OpenCV template matching
- Grid cell extraction for unit recognition

### Bot Perception (`bot_perception.py`)
- Unit type recognition via color matching
- Rank recognition via ML (LogisticRegression on Canny edges)
- Grid state analysis (15-cell game grid)
- Training data management

### Port Scan (`port_scan.py`)
- Multi-threaded ADB port scanning
- Emulator auto-detection
- Device connection management

### Scrcpy Client (`scrcpy/`)
- Python wrapper for scrcpy protocol
- Fast screen capture via video stream
- Touch input injection

## Data Flow

1. **Screen Capture**: Bot captures device screen via ADB screenshot or scrcpy stream
2. **Icon Detection**: OpenCV template matching identifies UI state (home, battle, menus)
3. **Grid Analysis**: Screen is cropped to game grid; 15 cells are extracted
4. **Unit Recognition**: Each cell is matched against known unit templates by color
5. **Rank Detection**: ML model classifies unit rank (1-5) from edge features
6. **Decision Making**: Bot decides actions based on grid state and config
7. **Input Injection**: Touch commands sent via ADB or scrcpy control

## Threading Model

```
Main Thread (GUI)
    │
    ├── Bot Thread (bot_handler.bot_loop)
    │       │
    │       └── Periodic grid capture & decision loop
    │
    └── Info Update Thread (status display)
```

The GUI runs on the main thread while bot logic executes in background threads to maintain UI responsiveness.
