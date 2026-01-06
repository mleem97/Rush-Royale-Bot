"""Rush Royale Bot Perception.

Computer vision and (limited) machine learning for unit recognition.

ML currently covers rank recognition (LogisticRegression on Canny edges).
"""
from __future__ import annotations

import os
import pickle
from pathlib import Path
from typing import Tuple

import cv2
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

# internal

####
#### Unit type recognition
###


REPO_ROOT = Path(__file__).resolve().parents[1]

OCR_INPUTS_DIR = REPO_ROOT / "OCR_inputs"
ML_DIR = REPO_ROOT / "machine_learning"
ML_INPUTS_DIR = ML_DIR / "inputs"
ML_RAW_INPUT_DIR = ML_DIR / "raw_input"

RANK_MODEL_PATH = REPO_ROOT / "rank_model.pkl"


def ensure_training_dirs() -> None:
    OCR_INPUTS_DIR.mkdir(parents=True, exist_ok=True)
    ML_INPUTS_DIR.mkdir(parents=True, exist_ok=True)
    ML_RAW_INPUT_DIR.mkdir(parents=True, exist_ok=True)


# Get most common pixel RGB value in image
def get_color(filename, crop=False):
    unit_img = cv2.imread(filename)
    if crop:
        unit_img = unit_img[15:15 + 90, 17:17 + 90]
    unit_img = cv2.cvtColor(unit_img, cv2.COLOR_BGR2RGB)
    # Flatten to pixel values
    flat_img = unit_img.reshape(-1, unit_img.shape[2])
    flat_img_round = flat_img // 20 * 20
    unique, counts = np.unique(flat_img_round, axis=0, return_counts=True)
    colors = np.zeros((5, 3), dtype=int)
    if len(unique) < 10:
        return colors
    # Sort list
    sorted_count = np.sort(counts)[::-1]
    # Get index of the most common colors
    for i in range(0, 5):
        index = np.where(counts == sorted_count[i])[0][0]
        colors[i] = unique[index]
    return colors


# Match unit based on color
def match_unit(filename, ref_colors, ref_units):
    unit_colors = get_color(filename, crop=True)
    # Find closest match (mean squared error)
    for color in unit_colors:
        mse = np.sum((ref_colors - color)**2, axis=1)
        # Dryad sometimes needs 2000 to match
        if mse[mse.argmin()] <= 2000:
            return ref_units[mse.argmin()], round(mse[mse.argmin()])
    return ['empty.png', 2001]


# Get status of current grid
# Currently 0.082 seconds call, multithreading is about 0.64 seconds
def grid_status(names, prev_grid=None):
    ref_units = os.listdir("units")
    ref_colors = [get_color('units/' + unit)[0] for unit in ref_units]
    grid_stats = []
    for filename in names:
        rank, rank_prob = match_rank(filename)
        unit_guess = match_unit(filename, ref_colors, ref_units) if rank != 0 else ['empty.png', 0]
        # Curse does not work well for different ranks
        #unit_guess = unit_guess if not is_cursed(filename) else ['cursed.png',0]
        grid_stats.append([*unit_guess, rank, rank_prob])
    grid_df = pd.DataFrame(grid_stats, columns=['unit', 'u_prob', 'rank', 'r_prob'])
    # Add grid position
    box_id = [[(i // 5) % 5, i % 5] for i in range(15)]
    grid_df.insert(0, 'grid_pos', box_id)
    if not prev_grid is None:
        # Check Consistency
        consistency = grid_df[['grid_pos', 'unit', 'rank']] == prev_grid[['grid_pos', 'unit', 'rank']]
        consistency = consistency.all(axis=1)
        # Update age from previous grid
        grid_df['Age'] = prev_grid['Age'] * consistency
        grid_df['Age'] += consistency
    else:
        grid_df['Age'] = np.zeros(len(grid_df))
    return grid_df


def match_rank(filename):
    img = cv2.imread(filename, 0)
    edges = cv2.Canny(img, 50, 100)
    with open(RANK_MODEL_PATH, 'rb') as f:
        logreg = pickle.load(f)
    prob = logreg.predict_proba(edges.reshape(1, -1))
    return prob.argmax(), round(prob.max(), 3)


# Fill find highest rank knight_statue adjacent to key_target
def position_filter(grid_df, key_target='demon_hunter.png'):
    demon_grid = grid_df[grid_df['unit'] == key_target]
    # Get max value index  in rank column
    demon_grid = demon_grid.sort_values(by='rank', ascending=False)
    unit_pos = demon_grid.iloc[0]['grid_pos']
    adjacent = unit_pos - np.array([[0, -1], [0, 1], [-1, 0], [1, 0]])
    # Keep only column values between 0 and 4 (bad rows are filtered out by isin)
    adjacent = adjacent[np.logical_and(adjacent[:, 1] >= 0, adjacent[:, 1] <= 4)]
    # Convert grid_pos to id 0-15 and extract rows
    adj_df = grid_df[grid_df.index.isin(adjacent[0:, 0] * 5 + adjacent[0:, 1])]
    adj_knights = adj_df[adj_df['unit'] == 'knight_statue.png'].sort_values(by='rank', ascending=True)
    key_pos = adj_knights.index[-1]
    return key_pos


## Add to dataset
def add_grid_to_dataset():
    """Append current `OCR_inputs/` images to the ML dataset.

    Note: This uses the *current* rank model to generate labels.
    For best results, prefer manually labeled datasets.
    """

    ensure_training_dirs()
    if not OCR_INPUTS_DIR.exists():
        return

    # Count existing examples robustly.
    example_count = len(list(ML_INPUTS_DIR.glob("*_input_*.png")))

    for slot in os.listdir(OCR_INPUTS_DIR):
        if not slot.lower().endswith(".png"):
            continue
        target = OCR_INPUTS_DIR / slot
        img = cv2.imread(str(target), 0)
        if img is None:
            continue
        edges = cv2.Canny(img, 50, 100)

        rank_guess, _ = match_rank(str(target))

        cv2.imwrite(str(ML_INPUTS_DIR / f"{rank_guess}_input_{example_count}.png"), edges)
        cv2.imwrite(str(ML_RAW_INPUT_DIR / f"{rank_guess}_raw_{example_count}.png"), img)
        example_count += 1


def _iter_labeled_images(folder: Path):
    # Layout A: files like "<rank>_input_123.png" in a flat folder
    for p in folder.glob("*_input_*.png"):
        label = p.name.split("_input", 1)[0]
        if label.isdigit():
            yield p, int(label)

    # Layout B: subfolders "0/", "1/", ... containing pngs
    for sub in folder.iterdir():
        if not sub.is_dir() or not sub.name.isdigit():
            continue
        label_int = int(sub.name)
        for p in sub.glob("*.png"):
            yield p, label_int


def load_dataset(folder: str | Path) -> Tuple[np.ndarray, np.ndarray]:
    folder_path = Path(folder)
    X_train: list[np.ndarray] = []
    y_train: list[int] = []

    for path, label in _iter_labeled_images(folder_path):
        img = cv2.imread(str(path), 0)
        if img is None:
            continue
        X_train.append(img)
        y_train.append(label)

    if not X_train:
        raise RuntimeError(f"No training images found in: {folder_path}")

    X = np.array(X_train)
    data_shape = X.shape
    X = X.reshape(data_shape[0], data_shape[1] * data_shape[2])
    y = np.array(y_train, dtype=int)
    return X, y


def train_rank_model(dataset_dir: str | Path = ML_INPUTS_DIR) -> LogisticRegression:
    X_train, y_train = load_dataset(dataset_dir)
    logreg = LogisticRegression(max_iter=200)
    logreg.fit(X_train, y_train)
    return logreg


def save_rank_model(model: LogisticRegression, path: str | Path = RANK_MODEL_PATH) -> Path:
    out = Path(path)
    with out.open("wb") as f:
        pickle.dump(model, f)
    return out


def quick_train_model():
    """Backward-compatible helper (trains from `machine_learning/inputs`)."""

    ensure_training_dirs()
    return train_rank_model(ML_INPUTS_DIR)
