from __future__ import annotations

import argparse
import sys
from pathlib import Path


# Allow running as: `python scripts/train_rank_model.py`
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / 'Src'))

import bot_perception


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            'Train the rank recognition model (LogisticRegression) and write rank_model.pkl.\n\n'
            'Dataset layouts supported:\n'
            '  A) machine_learning/inputs/<rank>_input_<n>.png\n'
            '  B) machine_learning/inputs/<rank>/<anything>.png\n\n'
            'Tip: you can generate samples via OCR_inputs/ and '
            'bot_perception.add_grid_to_dataset(), but best results come from '
            'manually labeled data.'
        )
    )
    parser.add_argument(
        '--dataset',
        default=str(bot_perception.ML_INPUTS_DIR),
        help='Dataset directory (default: machine_learning/inputs)',
    )
    parser.add_argument(
        '--out',
        default=str(bot_perception.RANK_MODEL_PATH),
        help='Output pickle path (default: rank_model.pkl)',
    )
    args = parser.parse_args()

    dataset_dir = Path(args.dataset)
    out_path = Path(args.out)

    bot_perception.ensure_training_dirs()
    model = bot_perception.train_rank_model(dataset_dir)
    saved = bot_perception.save_rank_model(model, out_path)

    print(f'Saved: {saved}')
    print(f'Classes: {list(model.classes_)}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
