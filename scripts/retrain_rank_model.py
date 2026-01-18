#!/usr/bin/env python3
"""Rush Bot - Retrain Rank Model (T018).

This script retrains the rank recognition model with sklearn 1.8.0
to eliminate version warnings and optionally export to ONNX format.

Usage:
    python scripts/retrain_rank_model.py
    python scripts/retrain_rank_model.py --export-onnx
    python scripts/retrain_rank_model.py --dataset machine_learning/inputs
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from rush_bot.ml.training import RankModelTrainer
from rush_bot.ml.training import TrainingConfig


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Retrain rank model with current sklearn version.")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=PROJECT_ROOT / "machine_learning" / "inputs",
        help="Dataset directory with labeled images",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "rank_model.pkl",
        help="Output path for model",
    )
    parser.add_argument(
        "--export-onnx",
        action="store_true",
        help="Also export model to ONNX format",
    )
    parser.add_argument(
        "--icon-size",
        type=int,
        default=120,
        help="Icon size for training (default: 120)",
    )
    parser.add_argument(
        "--max-iter",
        type=int,
        default=500,
        help="Max iterations for LogisticRegression",
    )

    args = parser.parse_args()

    # Check dataset exists
    if not args.dataset.exists():
        print(f"ERROR: Dataset directory not found: {args.dataset}")
        print("\nTo create training data:")
        print("1. Run bot with Unit Capture Mode enabled")
        print("2. Or manually add labeled images to machine_learning/inputs/")
        print("   Format: <rank>_input_<n>.png or subdirectories 0/, 1/, etc.")
        return 1

    # Check if dataset has images
    flat_count = len(list(args.dataset.glob("*_input_*.png")))
    sub_count = sum(len(list(sub.glob("*.png"))) for sub in args.dataset.iterdir() if sub.is_dir())
    total = flat_count + sub_count

    if total == 0:
        print(f"ERROR: No training images found in: {args.dataset}")
        return 1

    print(f"Found {total} training samples")
    print("sklearn version: ", end="")
    import sklearn

    print(sklearn.__version__)

    # Configure training
    config = TrainingConfig(
        icon_size=(args.icon_size, args.icon_size),
        max_iter=args.max_iter,
        test_split=0.2,
    )

    # Train model
    print("\n=== Training Rank Model ===")
    trainer = RankModelTrainer(config)

    try:
        result = trainer.train(args.dataset)
    except RuntimeError as e:
        print(f"ERROR: {e}")
        return 1

    # Save model
    print("\n=== Saving Model ===")
    saved_path = trainer.save(args.output)
    print(f"Model saved to: {saved_path}")
    print(f"Classes: {result.classes}")

    # Export to ONNX if requested
    if args.export_onnx:
        try:
            from rush_bot.ml.onnx_export import export_sklearn_to_onnx

            print("\n=== Exporting to ONNX ===")
            onnx_path = args.output.with_suffix(".onnx")
            input_shape = (args.icon_size * args.icon_size,)

            export_sklearn_to_onnx(
                trainer.model,
                onnx_path,
                input_shape=input_shape,
                model_name="rank_model",
            )
            print(f"ONNX model saved to: {onnx_path}")

        except ImportError as e:
            print(f"WARNING: Cannot export to ONNX: {e}")
            print("Install ONNX dependencies: pip install onnx skl2onnx onnxruntime")

    # Summary
    print("\n=== Training Complete ===")
    print(f"Training accuracy: {result.accuracy:.4f}")
    print(f"Validation accuracy: {result.val_accuracy:.4f}")
    print(f"Cross-validation: {sum(result.cv_scores) / len(result.cv_scores):.4f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
