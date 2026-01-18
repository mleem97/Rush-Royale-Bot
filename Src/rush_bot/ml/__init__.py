"""Rush Bot Machine Learning Module.

This module provides ML model training, export, and inference capabilities
for unit detection and rank recognition.

T018: Rank Model Upgrade (sklearn 1.8.0 + new ranks)
T019: Unit Detection Upgrade (120x120 icons)
T020: ONNX model export
T023: Unit Detection Model
T024: Merge Logic Model (planning)
"""

from __future__ import annotations

from .merge_model import MergeDataCollector
from .merge_model import MergeFeatureExtractor
from .merge_model import MergeModelSpec
from .onnx_export import ONNXExporter
from .onnx_export import export_sklearn_to_onnx
from .onnx_export import load_onnx_model
from .onnx_export import run_onnx_inference
from .training import RankModelTrainer
from .training import UnitModelTrainer
from .training import augment_image
from .training import load_training_dataset

__all__ = [
    # Training
    "RankModelTrainer",
    "UnitModelTrainer",
    "augment_image",
    "load_training_dataset",
    # ONNX
    "ONNXExporter",
    "export_sklearn_to_onnx",
    "load_onnx_model",
    "run_onnx_inference",
    # Merge Model
    "MergeModelSpec",
    "MergeFeatureExtractor",
    "MergeDataCollector",
]
