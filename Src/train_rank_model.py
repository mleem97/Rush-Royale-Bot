"""Retrain rank_model.pkl with the currently installed scikit-learn version."""
from __future__ import annotations

from sklearn import __version__ as sklearn_version

from bot_perception import DATASET_DIR, MODEL_PATH, load_rank_model, quick_train_model


def main() -> None:
    model = quick_train_model(DATASET_DIR, model_path=MODEL_PATH, save=True)
    load_rank_model.cache_clear()
    print(
        f"Saved {MODEL_PATH} with scikit-learn {sklearn_version}; "
        f"classes={model.classes_.tolist()}"
    )


if __name__ == "__main__":
    main()
