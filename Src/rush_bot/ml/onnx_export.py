"""ONNX Export Module for Rush Bot ML Models (T020).

Provides functionality to export scikit-learn models to ONNX format
for portable, framework-agnostic inference.

Benefits of ONNX:
- No sklearn version dependency at runtime
- Faster inference with ONNX Runtime
- Cross-platform compatibility
- Easier deployment
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

# ONNX dependencies (optional - graceful fallback if not installed)
try:
    import onnx
    import onnxruntime as ort
    from skl2onnx import convert_sklearn
    from skl2onnx.common.data_types import FloatTensorType

    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False


# Default paths
REPO_ROOT = Path(__file__).resolve().parents[4]
MODELS_DIR = REPO_ROOT / "models"


@dataclass
class ONNXExportConfig:
    """Configuration for ONNX export.

    Attributes:
        opset_version: ONNX opset version (default: 15).
        target_opset: Target opset for compatibility.
        optimize: Whether to optimize the model graph.
        include_metadata: Whether to include model metadata.
    """

    opset_version: int = 15
    optimize: bool = True
    include_metadata: bool = True


@dataclass
class ONNXInferenceResult:
    """Result of ONNX inference.

    Attributes:
        predictions: Predicted class indices.
        probabilities: Probability distribution per class.
        classes: List of class labels (if available).
    """

    predictions: NDArray[np.int64]
    probabilities: NDArray[np.float32] | None
    classes: list[Any] | None = None


class ONNXExporter:
    """Export sklearn models to ONNX format.

    Example:
        >>> from sklearn.linear_model import LogisticRegression
        >>> model = LogisticRegression().fit(X, y)
        >>> exporter = ONNXExporter()
        >>> exporter.export(model, "model.onnx", input_shape=(120*120,))
    """

    def __init__(self, config: ONNXExportConfig | None = None) -> None:
        """Initialize the exporter.

        Args:
            config: Export configuration.

        Raises:
            ImportError: If ONNX dependencies not installed.
        """
        if not ONNX_AVAILABLE:
            raise ImportError("ONNX export requires: pip install onnx skl2onnx onnxruntime")
        self.config = config or ONNXExportConfig()

    def export(
        self,
        model: Any,
        output_path: Path | str,
        input_shape: tuple[int, ...],
        model_name: str = "sklearn_model",
    ) -> Path:
        """Export a sklearn model to ONNX format.

        Args:
            model: Trained sklearn model (e.g., LogisticRegression).
            output_path: Path for the output ONNX file.
            input_shape: Shape of input features (excluding batch dimension).
            model_name: Name to embed in the ONNX model.

        Returns:
            Path to the saved ONNX model.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Define input type
        initial_type = [("input", FloatTensorType([None, input_shape[0]]))]

        # Convert to ONNX
        onnx_model = convert_sklearn(
            model,
            initial_types=initial_type,
            target_opset=self.config.opset_version,
        )

        # Add metadata if requested
        if self.config.include_metadata:
            onnx_model.doc_string = f"Converted from sklearn: {model_name}"

            # Add class labels as metadata
            if hasattr(model, "classes_"):
                classes_str = ",".join(str(c) for c in model.classes_)
                meta = onnx_model.metadata_props.add()
                meta.key = "classes"
                meta.value = classes_str

        # Validate the model
        onnx.checker.check_model(onnx_model)

        # Save model
        onnx.save(onnx_model, str(output_path))

        print(f"Exported ONNX model to: {output_path}")
        print(f"Input shape: (batch, {input_shape[0]})")

        return output_path

    def validate(self, onnx_path: Path | str) -> bool:
        """Validate an ONNX model file.

        Args:
            onnx_path: Path to ONNX model.

        Returns:
            True if valid, False otherwise.
        """
        try:
            model = onnx.load(str(onnx_path))
            onnx.checker.check_model(model)
            return True
        except Exception as e:
            print(f"ONNX validation failed: {e}")
            return False


def export_sklearn_to_onnx(
    model: Any,
    output_path: Path | str,
    input_shape: tuple[int, ...],
    model_name: str = "model",
) -> Path:
    """Convenience function to export sklearn model to ONNX.

    Args:
        model: Trained sklearn model.
        output_path: Output ONNX file path.
        input_shape: Input feature shape.
        model_name: Model name for metadata.

    Returns:
        Path to saved ONNX model.
    """
    exporter = ONNXExporter()
    return exporter.export(model, output_path, input_shape, model_name)


class ONNXModelLoader:
    """Load and run inference with ONNX models.

    Provides a sklearn-compatible interface for ONNX models.

    Example:
        >>> loader = ONNXModelLoader("model.onnx")
        >>> predictions = loader.predict(X)
        >>> probabilities = loader.predict_proba(X)
    """

    def __init__(self, model_path: Path | str) -> None:
        """Load an ONNX model.

        Args:
            model_path: Path to ONNX model file.

        Raises:
            ImportError: If ONNX runtime not available.
            FileNotFoundError: If model file doesn't exist.
        """
        if not ONNX_AVAILABLE:
            raise ImportError("ONNX inference requires: pip install onnxruntime")

        model_path = Path(model_path)
        if not model_path.exists():
            raise FileNotFoundError(f"ONNX model not found: {model_path}")

        self._session = ort.InferenceSession(str(model_path))
        self._input_name = self._session.get_inputs()[0].name
        self._output_names = [o.name for o in self._session.get_outputs()]

        # Extract classes from metadata if available
        self.classes_: list[Any] | None = None
        model = onnx.load(str(model_path))
        for meta in model.metadata_props:
            if meta.key == "classes":
                self.classes_ = meta.value.split(",")
                # Try to convert to int if possible
                try:
                    self.classes_ = [int(c) for c in self.classes_]
                except ValueError:
                    pass

    def predict(self, X: NDArray[np.float64]) -> NDArray[np.int64]:
        """Predict class labels.

        Args:
            X: Input features of shape (n_samples, n_features).

        Returns:
            Predicted class labels.
        """
        X = np.array(X, dtype=np.float32)
        if X.ndim == 1:
            X = X.reshape(1, -1)

        outputs = self._session.run(None, {self._input_name: X})

        # First output is usually predictions
        predictions = outputs[0]
        return np.array(predictions, dtype=np.int64)

    def predict_proba(self, X: NDArray[np.float64]) -> NDArray[np.float32]:
        """Predict class probabilities.

        Args:
            X: Input features of shape (n_samples, n_features).

        Returns:
            Class probabilities of shape (n_samples, n_classes).
        """
        X = np.array(X, dtype=np.float32)
        if X.ndim == 1:
            X = X.reshape(1, -1)

        outputs = self._session.run(None, {self._input_name: X})

        # Second output is usually probabilities (for classifiers)
        if len(outputs) > 1:
            return np.array(outputs[1], dtype=np.float32)

        # Fallback: compute softmax-like scores from output
        preds = outputs[0]
        # Return one-hot encoding if no probabilities
        n_classes = len(self.classes_) if self.classes_ else int(preds.max()) + 1
        proba = np.zeros((len(preds), n_classes), dtype=np.float32)
        for i, p in enumerate(preds):
            proba[i, p] = 1.0
        return proba


def load_onnx_model(path: Path | str) -> ONNXModelLoader:
    """Load an ONNX model for inference.

    Args:
        path: Path to ONNX model file.

    Returns:
        ONNXModelLoader ready for inference.
    """
    return ONNXModelLoader(path)


def run_onnx_inference(
    model_path: Path | str,
    X: NDArray[np.float64],
) -> ONNXInferenceResult:
    """Run inference on an ONNX model.

    Convenience function for one-shot inference.

    Args:
        model_path: Path to ONNX model.
        X: Input features.

    Returns:
        ONNXInferenceResult with predictions and probabilities.
    """
    loader = ONNXModelLoader(model_path)
    predictions = loader.predict(X)
    probabilities = loader.predict_proba(X)

    return ONNXInferenceResult(
        predictions=predictions,
        probabilities=probabilities,
        classes=loader.classes_,
    )


def check_onnx_available() -> bool:
    """Check if ONNX dependencies are available.

    Returns:
        True if ONNX export/inference is available.
    """
    return ONNX_AVAILABLE
