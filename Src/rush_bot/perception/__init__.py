"""Computer Vision and Machine Learning module."""

from .cv_debug import CVDebugFrame
from .cv_debug import CVDebugLevel
from .cv_debug import CVDebugMode
from .cv_debug import DetectionResult
from .cv_debug import MergeCandidate
from .cv_debug import PageContext
from .cv_debug import run_cv_debug_on_screenshot
from .icon_detection import ICON_ROI_MAP
from .icon_detection import ContextAwareIconDetector
from .icon_detection import IconROI
from .screen_state import ICONS_DIR
from .screen_state import TEMPLATE_STATE_MAP
from .screen_state import VALID_TRANSITIONS
from .screen_state import ScreenState
from .screen_state import ScreenStateConfig
from .screen_state import ScreenStateDetector
from .screen_state import ScreenStateMachine
from .screen_state import ScreenStateResult
from .screen_state import StateHistoryEntry
from .screen_state import StateTransition
from .vision import GRID_COLS
from .vision import GRID_ROWS
from .vision import ML_DIR  # Constants
from .vision import ML_INPUTS_DIR
from .vision import ML_RAW_INPUT_DIR
from .vision import OCR_INPUTS_DIR
from .vision import RANK_MODEL_PATH
from .vision import REFERENCE_HEIGHT
from .vision import REFERENCE_WIDTH
from .vision import BotPerception
from .vision import GridConfig
from .vision import GridExtractor
from .vision import add_grid_to_dataset
from .vision import ensure_training_dirs
from .vision import get_grid
from .vision import load_dataset
from .vision import quick_train_model
from .vision import save_rank_model
from .vision import train_rank_model

__all__ = [
    # CV Debug Mode
    "CVDebugFrame",
    "CVDebugLevel",
    "CVDebugMode",
    "DetectionResult",
    "MergeCandidate",
    "PageContext",
    "run_cv_debug_on_screenshot",
    # Icon Detection (Context-Aware)
    "ContextAwareIconDetector",
    "ICON_ROI_MAP",
    "IconROI",
    # Screen State Detection
    "ICONS_DIR",
    "TEMPLATE_STATE_MAP",
    "ScreenState",
    "ScreenStateConfig",
    "ScreenStateDetector",
    "ScreenStateMachine",
    "ScreenStateResult",
    "StateHistoryEntry",
    "StateTransition",
    "VALID_TRANSITIONS",
    # Grid Extraction
    "GRID_COLS",
    "GRID_ROWS",
    "REFERENCE_HEIGHT",
    "REFERENCE_WIDTH",
    "GridConfig",
    "GridExtractor",
    "get_grid",
    # ML/Training
    "ML_DIR",
    "ML_INPUTS_DIR",
    "ML_RAW_INPUT_DIR",
    "OCR_INPUTS_DIR",
    "RANK_MODEL_PATH",
    "BotPerception",
    "add_grid_to_dataset",
    "ensure_training_dirs",
    "load_dataset",
    "quick_train_model",
    "save_rank_model",
    "train_rank_model",
]
