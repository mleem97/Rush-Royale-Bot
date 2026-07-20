"""Computer vision and machine-learning helpers for unit recognition."""
from __future__ import annotations

import os
import pickle
import warnings
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
from sklearn.exceptions import InconsistentVersionWarning
from sklearn.linear_model import LogisticRegression

REPO_ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = REPO_ROOT / "rank_model.npz"
LEGACY_MODEL_PATH = REPO_ROOT / "rank_model.pkl"
DATASET_DIR = REPO_ROOT / "machine_learning" / "inputs"
OCR_INPUT_DIR = REPO_ROOT / "OCR_inputs"
UNITS_DIR = REPO_ROOT / "units"


@dataclass(frozen=True)
class FrozenRankModel:
    """Version-neutral logistic-regression predictor.

    Only the numerical parameters needed for inference are retained. The
    artifact is stored as NumPy arrays, so it is independent of scikit-learn's
    private pickle layout.
    """

    classes_: np.ndarray
    coef_: np.ndarray
    intercept_: np.ndarray
    mode: str

    @property
    def n_features_in_(self) -> int:
        return int(self.coef_.shape[1])

    def predict_proba(self, features: np.ndarray) -> np.ndarray:
        x = np.asarray(features, dtype=np.float64)
        if x.ndim == 1:
            x = x.reshape(1, -1)
        if x.ndim != 2 or x.shape[1] != self.n_features_in_:
            raise ValueError(
                f"Expected {self.n_features_in_} features, received shape {x.shape}."
            )

        scores = x @ self.coef_.T + self.intercept_
        if self.coef_.shape[0] == 1:
            positive = 1.0 / (1.0 + np.exp(-np.clip(scores[:, 0], -709, 709)))
            return np.column_stack((1.0 - positive, positive))

        if self.mode == "ovr":
            probabilities = 1.0 / (1.0 + np.exp(-np.clip(scores, -709, 709)))
            totals = probabilities.sum(axis=1, keepdims=True)
            return probabilities / np.where(totals == 0, 1.0, totals)

        shifted = scores - scores.max(axis=1, keepdims=True)
        exp_scores = np.exp(shifted)
        return exp_scores / exp_scores.sum(axis=1, keepdims=True)


def get_color(filename: str | os.PathLike[str], crop: bool = False) -> np.ndarray:
    unit_img = cv2.imread(str(filename))
    if unit_img is None:
        raise FileNotFoundError(f"Could not read image: {filename}")
    if crop:
        unit_img = unit_img[15:105, 17:107]
    unit_img = cv2.cvtColor(unit_img, cv2.COLOR_BGR2RGB)
    flat_img = unit_img.reshape(-1, unit_img.shape[2])
    flat_img_round = flat_img // 20 * 20
    unique, counts = np.unique(flat_img_round, axis=0, return_counts=True)
    colors = np.zeros((5, 3), dtype=int)
    if len(unique) < 10:
        return colors
    sorted_count = np.sort(counts)[::-1]
    for index in range(5):
        color_index = np.where(counts == sorted_count[index])[0][0]
        colors[index] = unique[color_index]
    return colors


def match_unit(filename, ref_colors, ref_units):
    unit_colors = get_color(filename, crop=True)
    for color in unit_colors:
        mse = np.sum((ref_colors - color) ** 2, axis=1)
        if mse[mse.argmin()] <= 2000:
            return ref_units[mse.argmin()], round(mse[mse.argmin()])
    return ["empty.png", 2001]


def grid_status(names, prev_grid=None):
    ref_units = sorted(path.name for path in UNITS_DIR.glob("*.png"))
    ref_colors = [get_color(UNITS_DIR / unit)[0] for unit in ref_units]
    grid_stats = []
    for filename in names:
        rank, rank_prob = match_rank(filename)
        unit_guess = (
            match_unit(filename, ref_colors, ref_units)
            if rank != 0
            else ["empty.png", 0]
        )
        grid_stats.append([*unit_guess, rank, rank_prob])
    grid_df = pd.DataFrame(grid_stats, columns=["unit", "u_prob", "rank", "r_prob"])
    box_id = [[(index // 5) % 5, index % 5] for index in range(15)]
    grid_df.insert(0, "grid_pos", box_id)
    if prev_grid is not None:
        consistency = grid_df[["grid_pos", "unit", "rank"]] == prev_grid[
            ["grid_pos", "unit", "rank"]
        ]
        consistency = consistency.all(axis=1)
        grid_df["Age"] = prev_grid["Age"] * consistency
        grid_df["Age"] += consistency
    else:
        grid_df["Age"] = np.zeros(len(grid_df))
    return grid_df


def _inference_mode(model: LogisticRegression) -> str:
    configured = getattr(model, "multi_class", "auto")
    if configured == "ovr":
        return "ovr"
    if configured == "multinomial":
        return "multinomial"
    solver = getattr(model, "solver", "lbfgs")
    return "ovr" if solver == "liblinear" or len(model.classes_) <= 2 else "multinomial"


def freeze_rank_model(model: LogisticRegression) -> FrozenRankModel:
    required = ("classes_", "coef_", "intercept_")
    missing = [attribute for attribute in required if not hasattr(model, attribute)]
    if missing:
        raise TypeError(f"Rank model is missing fitted attributes: {', '.join(missing)}")
    frozen = FrozenRankModel(
        classes_=np.asarray(model.classes_).copy(),
        coef_=np.asarray(model.coef_, dtype=np.float64).copy(),
        intercept_=np.asarray(model.intercept_, dtype=np.float64).copy(),
        mode=_inference_mode(model),
    )
    if frozen.coef_.ndim != 2 or frozen.intercept_.shape != (frozen.coef_.shape[0],):
        raise ValueError("Rank model coefficients have an unsupported shape.")
    if len(frozen.classes_) not in (2, frozen.coef_.shape[0]):
        raise ValueError("Rank model classes do not match its coefficients.")
    return frozen


def save_rank_model(model: FrozenRankModel, model_path: Path = MODEL_PATH) -> None:
    model_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = model_path.with_suffix(model_path.suffix + ".tmp")
    with temporary_path.open("wb") as model_file:
        np.savez_compressed(
            model_file,
            format_version=np.asarray(1, dtype=np.int64),
            classes=model.classes_,
            coef=model.coef_,
            intercept=model.intercept_,
            mode=np.asarray(model.mode),
        )
    temporary_path.replace(model_path)


def load_rank_model_artifact(model_path: Path = MODEL_PATH) -> FrozenRankModel:
    with np.load(model_path, allow_pickle=False) as artifact:
        format_version = int(artifact["format_version"])
        if format_version != 1:
            raise ValueError(f"Unsupported rank model format version: {format_version}")
        model = FrozenRankModel(
            classes_=artifact["classes"].copy(),
            coef_=artifact["coef"].astype(np.float64, copy=True),
            intercept_=artifact["intercept"].astype(np.float64, copy=True),
            mode=str(artifact["mode"].item()),
        )
    if model.mode not in {"ovr", "multinomial"}:
        raise ValueError(f"Unsupported rank model inference mode: {model.mode}")
    return model


def migrate_legacy_rank_model(
    legacy_path: Path = LEGACY_MODEL_PATH,
    model_path: Path = MODEL_PATH,
) -> FrozenRankModel:
    """Convert the trusted bundled sklearn pickle to a stable NumPy artifact."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", InconsistentVersionWarning)
        with legacy_path.open("rb") as model_file:
            legacy_model = pickle.load(model_file)
    if not isinstance(legacy_model, LogisticRegression):
        raise TypeError(
            f"Expected LogisticRegression in {legacy_path}, got {type(legacy_model).__name__}."
        )
    frozen = freeze_rank_model(legacy_model)
    save_rank_model(frozen, model_path)
    return frozen


@lru_cache(maxsize=1)
def load_rank_model(
    model_path: Path = MODEL_PATH,
    legacy_path: Path = LEGACY_MODEL_PATH,
    dataset_dir: Path = DATASET_DIR,
) -> FrozenRankModel:
    """Load a stable model, migrating or retraining once when necessary."""
    try:
        return load_rank_model_artifact(model_path)
    except FileNotFoundError:
        pass
    except (KeyError, OSError, TypeError, ValueError) as exc:
        warnings.warn(
            f"Ignoring invalid rank model artifact '{model_path}': {exc}",
            RuntimeWarning,
            stacklevel=2,
        )

    if legacy_path.is_file():
        try:
            return migrate_legacy_rank_model(legacy_path, model_path)
        except (AttributeError, EOFError, OSError, pickle.UnpicklingError, TypeError, ValueError) as exc:
            migration_error = exc
        else:
            migration_error = None
    else:
        migration_error = FileNotFoundError(f"Legacy model not found: {legacy_path}")

    if dataset_dir.is_dir() and any(dataset_dir.glob("*.png")):
        trained = quick_train_model(dataset_dir, model_path=model_path, save=True)
        return freeze_rank_model(trained)

    raise RuntimeError(
        "No usable rank model is available. Migration of the bundled model failed "
        f"({migration_error}), and no training PNG files were found in '{dataset_dir}'."
    )


def match_rank(filename):
    image = cv2.imread(str(filename), 0)
    if image is None:
        raise FileNotFoundError(f"Could not read rank image: {filename}")
    edges = cv2.Canny(image, 50, 100)
    model = load_rank_model()
    probabilities = model.predict_proba(edges.reshape(1, -1))[0]
    best_index = int(probabilities.argmax())
    rank = int(model.classes_[best_index])
    return rank, round(float(probabilities[best_index]), 3)


def position_filter(grid_df, key_target="demon_hunter.png"):
    demon_grid = grid_df[grid_df["unit"] == key_target]
    demon_grid = demon_grid.sort_values(by="rank", ascending=False)
    unit_pos = demon_grid.iloc[0]["grid_pos"]
    adjacent = unit_pos - np.array([[0, -1], [0, 1], [-1, 0], [1, 0]])
    adjacent = adjacent[np.logical_and(adjacent[:, 1] >= 0, adjacent[:, 1] <= 4)]
    adj_df = grid_df[grid_df.index.isin(adjacent[0:, 0] * 5 + adjacent[0:, 1])]
    adj_knights = adj_df[adj_df["unit"] == "knight_statue.png"].sort_values(
        by="rank", ascending=True
    )
    return adj_knights.index[-1]


def add_grid_to_dataset():
    input_dir = DATASET_DIR
    raw_dir = REPO_ROOT / "machine_learning" / "raw_input"
    input_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    ref_units = sorted(path.name for path in UNITS_DIR.glob("*.png"))
    ref_colors = [get_color(UNITS_DIR / unit)[0] for unit in ref_units]
    for target in sorted(OCR_INPUT_DIR.glob("*.png")):
        image = cv2.imread(str(target), 0)
        if image is None:
            continue
        edges = cv2.Canny(image, 50, 100)
        rank_guess = 0
        unit_guess = match_unit(target, ref_colors, ref_units)
        if unit_guess[0] != "empty.png":
            rank_guess, _ = match_rank(target)
        example_count = len(list(input_dir.glob("*.png")))
        cv2.imwrite(str(input_dir / f"{rank_guess}_input_{example_count}.png"), edges)
        cv2.imwrite(str(raw_dir / f"{rank_guess}_raw_{example_count}.png"), image)


def load_dataset(folder: str | os.PathLike[str] = DATASET_DIR):
    folder_path = Path(folder)
    images: list[np.ndarray] = []
    labels: list[int] = []
    for file_path in sorted(folder_path.glob("*.png")):
        image = cv2.imread(str(file_path), 0)
        if image is None:
            continue
        images.append(image)
        labels.append(int(file_path.name.split("_input", maxsplit=1)[0]))

    if not images:
        raise FileNotFoundError(f"No training PNG files found in: {folder_path}")
    shapes = {image.shape for image in images}
    if len(shapes) != 1:
        raise ValueError(f"Training images have inconsistent dimensions: {sorted(shapes)}")

    x_train = np.asarray(images)
    x_train = x_train.reshape(x_train.shape[0], -1)
    return x_train, np.asarray(labels, dtype=int)


def quick_train_model(
    folder: str | os.PathLike[str] = DATASET_DIR,
    *,
    model_path: Path = MODEL_PATH,
    save: bool = False,
) -> LogisticRegression:
    x_train, y_train = load_dataset(folder)
    logreg = LogisticRegression(max_iter=2000, random_state=42)
    logreg.fit(x_train, y_train)
    if save:
        save_rank_model(freeze_rank_model(logreg), model_path)
    return logreg
