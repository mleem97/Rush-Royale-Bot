# Machine Learning

This page documents the machine learning components of the Rush Royale Bot, including rank recognition, auto-labeling, and reinforcement learning.

## Overview

The bot uses ML for:
1. **Rank Recognition** - Classifying unit star ranks (1-7) using LogisticRegression
2. **Auto-Labeling** - Bootstrapping training data from gameplay
3. **Reinforcement Learning** - Optimizing merge/summon strategies (experimental)

## Rank Recognition Model

### How It Works

The rank model (`rank_model.pkl`) uses edge detection features to classify unit ranks:

```
Screenshot → Canny Edge Detection → Flatten → LogisticRegression → Rank (0-7)
```

### Model File

| File | Location | Format |
|------|----------|--------|
| `rank_model.pkl` | Repository root | Pickle (scikit-learn) |

### Training Pipeline

```python
# In bot_perception.py
from sklearn.linear_model import LogisticRegression

def train_rank_model(dataset_dir):
    X_train, y_train = load_dataset(dataset_dir)
    model = LogisticRegression(max_iter=200)
    model.fit(X_train, y_train)
    return model
```

## Dataset Structure

Training data is stored in `machine_learning/inputs/`:

### Layout A: Flat Files
```
machine_learning/inputs/
├── 0_input_001.png    # Rank 0 (empty)
├── 1_input_002.png    # Rank 1
├── 3_input_003.png    # Rank 3
└── ...
```

### Layout B: Subdirectories
```
machine_learning/inputs/
├── 0/
│   ├── empty_001.png
│   └── empty_002.png
├── 1/
│   ├── rank1_001.png
│   └── rank1_002.png
└── ...
```

## Training the Model

### Via GUI (Recommended)

1. Open the bot GUI
2. Go to **🧠 Training** tab
3. Click **🧠 Train Model**
4. Wait for completion

### Via Command Line

```bash
# Windows
.bot_env\Scripts\python.exe scripts\train_rank_model.py

# Linux/macOS
.bot_env/bin/python scripts/train_rank_model.py
```

### Options

```bash
python scripts/train_rank_model.py \
    --dataset machine_learning/inputs \
    --out rank_model.pkl
```

## Auto-Labeling (Bootstrapping)

If you have a working `rank_model.pkl` but need to rebuild the dataset, use auto-labeling:

### Workflow

1. Start the bot and play a game (generates `OCR_inputs/`)
2. In GUI → Training → Click **🔄 Auto-Label Grid**
3. The bot uses the current model to label and save images
4. Review generated images in `machine_learning/inputs/`
5. Delete incorrectly labeled images
6. Retrain the model

### Technical Details

```python
def add_grid_to_dataset():
    """Uses current model to auto-label OCR_inputs and save to dataset."""
    for slot in os.listdir(OCR_INPUTS_DIR):
        img = cv2.imread(slot, 0)
        edges = cv2.Canny(img, 50, 100)
        
        # Use existing model to predict rank
        rank_guess, _ = match_rank(slot)
        
        # Save with predicted label
        cv2.imwrite(f"machine_learning/inputs/{rank_guess}_input_{n}.png", edges)
```

## Reinforcement Learning (Experimental)

### Overview

The RL system allows the bot to learn optimal strategies instead of following hardcoded rules.

### Environment: `bot_env.py`

```python
from bot_env import RushRoyaleEnv

env = RushRoyaleEnv(bot_instance)
```

### Observation Space

| Index | Data | Shape |
|-------|------|-------|
| 0-14 | Grid cells | (15, 2) |
| [i, 0] | Unit type (encoded) | int 0-20 |
| [i, 1] | Rank | int 0-7 |

### Action Space

| Action | ID | Description |
|--------|-----|-------------|
| Merge | 0-59 | 15 positions × 4 directions |
| Summon | 60 | Spawn new unit |
| Upgrade 1-5 | 61-65 | Mana upgrades |
| Wait | 66 | Do nothing |

### Reward Function

| Event | Reward |
|-------|--------|
| Survival (per step) | +1 |
| High rank unit (5+) | +2 per unit |
| Wave survived | +5 |
| Game lost | -100 |
| Floor complete | +100 |

### Training Example

```python
from stable_baselines3 import PPO
from bot_env import RushRoyaleEnv

# Initialize
bot = Bot(device="127.0.0.1:5555")
env = RushRoyaleEnv(bot)

# Train
model = PPO("MlpPolicy", env, verbose=1)
model.learn(total_timesteps=10000)

# Save
model.save("ppo_rushroyale")
```

## Imitation Learning

Before pure RL, use imitation learning to clone the rule-based bot:

### Data Collection

```python
from bot_env import ImitationDataCollector

collector = ImitationDataCollector()

# During gameplay, record decisions
collector.record(grid_df, action=42, action_type="merge", details={"from": [0,0], "to": [0,1]})

# Save dataset
collector.save("imitation_data.npz")
```

### Training from Demonstrations

```python
from stable_baselines3 import PPO
from imitation.algorithms import bc

# Load demonstrations
states, actions = collector.load()

# Behavior Cloning
bc_trainer = bc.BC(
    observation_space=env.observation_space,
    action_space=env.action_space,
    demonstrations=states_actions,
)
bc_trainer.train(n_epochs=10)
```

## Troubleshooting

### Model Won't Load

**Error**: `ModuleNotFoundError` or `unsupported pickle protocol`

**Cause**: Model was trained with different Python/scikit-learn version.

**Solution**:
1. Collect new training data via auto-labeling
2. Retrain model in current environment

### Poor Rank Recognition

**Symptoms**: Units showing wrong ranks

**Solutions**:
1. Check emulator resolution (should be 1080x1920 or similar)
2. Collect more training samples
3. Manually review and clean dataset

### RL Agent Not Learning

**Check**:
- Reward signal is meaningful
- Enough exploration (PPO default is usually fine)
- Episode length is reasonable
- Game state is actually changing

## Files Reference

| File | Purpose |
|------|---------|
| `Src/bot_perception.py` | CV and ML functions |
| `Src/bot_env.py` | Gymnasium RL environment |
| `scripts/train_rank_model.py` | CLI training script |
| `rank_model.pkl` | Trained classifier |
| `machine_learning/inputs/` | Training dataset |
| `OCR_inputs/` | Raw grid screenshots |
