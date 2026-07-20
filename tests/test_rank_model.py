from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "Src"))

from bot_perception import load_dataset, load_rank_model_artifact, quick_train_model


def test_training_uses_platform_independent_paths(tmp_path):
    for label, value in ((0, 0), (0, 10), (1, 240), (1, 255)):
        image = np.full((4, 4), value, dtype=np.uint8)
        index = len(list(tmp_path.glob("*.png")))
        cv2.imwrite(str(tmp_path / f"{label}_input_{index}.png"), image)

    x_train, y_train = load_dataset(tmp_path)
    assert x_train.shape == (4, 16)
    assert sorted(set(y_train.tolist())) == [0, 1]

    model_path = tmp_path / "rank_model.npz"
    sklearn_model = quick_train_model(tmp_path, model_path=model_path, save=True)
    frozen_model = load_rank_model_artifact(model_path)

    assert frozen_model.classes_.tolist() == [0, 1]
    np.testing.assert_allclose(
        frozen_model.predict_proba(x_train),
        sklearn_model.predict_proba(x_train),
        rtol=1e-12,
        atol=1e-12,
    )


def test_legacy_multiclass_pickle_migrates_without_changing_probabilities(tmp_path):
    import pickle

    from sklearn.linear_model import LogisticRegression

    from bot_perception import migrate_legacy_rank_model

    rng = np.random.default_rng(42)
    x_train = np.vstack(
        [rng.normal(loc=label * 3.0, scale=0.4, size=(8, 6)) for label in range(3)]
    )
    y_train = np.repeat(np.arange(3), 8)
    sklearn_model = LogisticRegression(max_iter=1000, random_state=42).fit(
        x_train, y_train
    )

    legacy_path = tmp_path / "rank_model.pkl"
    stable_path = tmp_path / "rank_model.npz"
    with legacy_path.open("wb") as model_file:
        pickle.dump(sklearn_model, model_file)

    migrated_model = migrate_legacy_rank_model(legacy_path, stable_path)

    assert stable_path.exists()
    np.testing.assert_allclose(
        migrated_model.predict_proba(x_train),
        sklearn_model.predict_proba(x_train),
        rtol=1e-12,
        atol=1e-12,
    )
