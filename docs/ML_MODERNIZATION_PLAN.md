# 🧠 ML-Modelle Modernisierungsplan

## Aktueller Stand

### Bestehende Modelle

| Modell | Typ | Zweck | Datei |
|--------|-----|-------|-------|
| **Rank Model** | LogisticRegression | Erkennt Unit-Rang (0-7) aus Canny-Edges | `rank_model.pkl` |
| **Color Matching** | Nearest Neighbor | Erkennt Unit-Typ anhand dominanter Farben | Inline in `bot_perception.py` |

### Aktuelle Probleme

1. **Pickle-Format**: Nicht Python-versionsübergreifend kompatibel
2. **Veralteter Algorithmus**: LogisticRegression auf Canny-Edges ist limitiert
3. **Keine Versionierung**: Modell-Versionen nicht nachverfolgbar
4. **Hardcoded Thresholds**: MSE-Threshold von 2000 für Color-Matching
5. **Keine Validierung**: Kein Cross-Validation, keine Metriken
6. **Fehlende Daten-Pipeline**: Manuelles Training ohne automatisierte Pipeline

---

## 🎯 Modernisierungsziele

### Phase 1: Infrastruktur (Woche 1-2)

#### 1.1 Modell-Persistenz modernisieren

- [ ] **ONNX-Format** für Modelle (plattformübergreifend, schnell)
- [ ] **Joblib** als Backup für sklearn-Modelle
- [ ] **Modell-Versionierung** mit Metadaten (Datum, Accuracy, Daten-Hash)

```python
# Neue Modell-Persistenz
from pathlib import Path
import joblib
import json

class ModelRegistry:
    """Zentrale Modellverwaltung mit Versionierung."""
    
    def __init__(self, models_dir: Path = Path("models")):
        self.models_dir = models_dir
        self.registry_file = models_dir / "registry.json"
    
    def save_model(self, model, name: str, metrics: dict) -> str:
        """Speichert Modell mit Metadaten."""
        version = self._get_next_version(name)
        model_path = self.models_dir / f"{name}_v{version}.joblib"
        
        joblib.dump(model, model_path)
        
        # Metadaten speichern
        self._update_registry(name, version, metrics, model_path)
        return version
```

#### 1.2 Daten-Pipeline erstellen

- [ ] **Datensatz-Struktur** standardisieren
- [ ] **Automatisches Labeling** für neue Trainingsbilder
- [ ] **Augmentation-Pipeline** für robusteres Training

```
models/
├── registry.json           # Modell-Versionen und Metriken
├── rank/
│   ├── rank_v1.joblib
│   ├── rank_v2.onnx
│   └── metrics_v2.json
├── unit_classifier/
│   ├── unit_v1.joblib
│   └── embeddings.npy
└── training_data/
    ├── rank/
    │   ├── 0/              # Rang 0 Bilder
    │   ├── 1/
    │   └── ...
    └── units/
        ├── demon_hunter/
        ├── chemist/
        └── ...
```

### Phase 2: Modell-Upgrades (Woche 3-4)

#### 2.1 Rank Detection verbessern

**Option A: CNN mit PyTorch/TensorFlow Lite**

```python
import torch.nn as nn

class RankClassifier(nn.Module):
    """Leichtgewichtiger CNN für Rang-Erkennung."""
    
    def __init__(self, num_classes=8):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(1, 16, 3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(16, 32, 3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.AdaptiveAvgPool2d(4)
        )
        self.classifier = nn.Linear(32 * 16, num_classes)
    
    def forward(self, x):
        x = self.features(x)
        x = x.view(x.size(0), -1)
        return self.classifier(x)
```

**Option B: Verbesserte sklearn Pipeline (leichter zu warten)**

```python
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import GradientBoostingClassifier

rank_pipeline = Pipeline([
    ('scaler', StandardScaler()),
    ('classifier', GradientBoostingClassifier(
        n_estimators=100,
        max_depth=5,
        random_state=42
    ))
])
```

#### 2.2 Unit Detection verbessern

**Feature Embedding mit HOG + Color Histogram**

```python
from skimage.feature import hog
from sklearn.neighbors import KNeighborsClassifier

class UnitDetector:
    """Kombiniert HOG-Features mit Farbhistogramm."""
    
    def extract_features(self, img):
        # HOG für Formmerkmale
        hog_features = hog(
            img, 
            orientations=9, 
            pixels_per_cell=(8, 8),
            cells_per_block=(2, 2)
        )
        
        # Farbhistogramm
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        hist = cv2.calcHist([hsv], [0, 1], None, [30, 32], [0, 180, 0, 256])
        hist = cv2.normalize(hist, hist).flatten()
        
        return np.concatenate([hog_features, hist])
```

### Phase 3: RL-Vorbereitung (Woche 5-8)

#### 3.1 State Representation für RL

```python
@dataclass
class GameState:
    """Strukturierter Spielzustand für RL."""
    
    grid: np.ndarray           # 3x5 Unit-Matrix
    unit_types: np.ndarray     # Unit-Typ IDs
    unit_ranks: np.ndarray     # Unit-Ränge
    mana: int                  # Aktuelles Mana
    wave: int                  # Aktuelle Welle
    health: int                # Verbleibende Leben
    
    def to_tensor(self) -> torch.Tensor:
        """Konvertiert zu Tensor für RL-Agent."""
        # Flatten und normalisieren
        state = np.concatenate([
            self.unit_types.flatten() / 100,  # Normalisiert
            self.unit_ranks.flatten() / 7,    # Max Rang 7
            [self.mana / 1000, self.wave / 100, self.health / 10]
        ])
        return torch.tensor(state, dtype=torch.float32)
```

#### 3.2 Action Space definieren

```python
class ActionSpace:
    """Definiert mögliche Bot-Aktionen."""
    
    SPAWN_UNIT = 0          # Neue Einheit spawnen
    MERGE = list(range(1, 16))  # Merge an Position 0-14
    UPGRADE_CARD = list(range(16, 21))  # Karte 1-5 upgraden
    HERO_ABILITY = 21       # Helden-Fähigkeit aktivieren
    WAIT = 22               # Nichts tun
    
    @property
    def n_actions(self) -> int:
        return 23
```

### Phase 4: Hybrid DQN/PPO System (Woche 9-12)

#### 4.1 DQN für strategische Entscheidungen

- Menu-Navigation
- Deck-Building
- Hero-Auswahl
- Ressourcen-Optimierung

#### 4.2 PPO für Echtzeit-Combat

- Grid-Platzierung
- Unit-Merging
- Mana-Management
- Hero-Ability Timing

---

## 📋 Migrations-Checkliste

### Kurzfristig (Diese Woche)

- [ ] `models/` Verzeichnis erstellen
- [ ] ModelRegistry-Klasse implementieren
- [ ] rank_model.pkl zu .joblib konvertieren
- [ ] Modell-Metriken berechnen und speichern

### Mittelfristig (Nächster Monat)

- [ ] HOG+Color Unit-Detektor implementieren
- [ ] CNN Rank-Classifier trainieren
- [ ] Automatische Training-Pipeline
- [ ] Cross-Validation und Hyperparameter-Tuning

### Langfristig (3+ Monate)

- [ ] RL State/Action Space implementieren
- [ ] DQN für Meta-Game
- [ ] PPO für Combat
- [ ] Self-Play Training

---

## 🔧 Neue Dependencies für ML

```toml
# pyproject.toml Ergänzungen
[project.optional-dependencies]
ml-advanced = [
    "torch>=2.1.0,<3.0.0",
    "torchvision>=0.16.0,<1.0.0",
    "onnx>=1.15.0,<2.0.0",
    "onnxruntime>=1.16.0,<2.0.0",
    "scikit-image>=0.22.0,<1.0.0",
    "stable-baselines3>=2.2.0,<3.0.0",
]

ml-light = [
    "scikit-image>=0.22.0,<1.0.0",
    "joblib>=1.3.0,<2.0.0",
]
```

---

## 📊 Erwartete Verbesserungen

| Metrik | Aktuell | Ziel |
|--------|---------|------|
| Rank Accuracy | ~85% (geschätzt) | >95% |
| Unit Detection | ~90% (geschätzt) | >98% |
| Inference Zeit | ~50ms/Grid | <20ms/Grid |
| Robustheit | Niedrig | Hoch (Augmentation) |
| Wartbarkeit | Schlecht (pickle) | Gut (Registry, Versionierung) |

---

## 🚀 Nächste Schritte

1. **Sofort**: `Src/ml/` Package erstellen mit ModelRegistry
2. **Diese Woche**: Bestehende Modelle analysieren und Baseline-Metriken erfassen
3. **Nächste Woche**: HOG-basierte Unit-Detection implementieren
4. **In 2 Wochen**: CNN Rank-Classifier trainieren und vergleichen
