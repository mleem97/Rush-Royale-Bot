"""Merge Logic Model Module (T024).

This module provides the foundation for ML-based merge decisions.
Currently a planning/specification module - actual training requires
data collection from gameplay.

Domain Rules:
- Merges only within own game field
- Standard: same unit type + same rank can merge
- Exceptions: certain units can merge with specific other types (whitelist)

Example Whitelist (JSON):
    {
        "unit": "harlequin",
        "merges_with": "any"
    }
    {
        "unit": "dryad",
        "merges_with": ["knight_statue", "demon_hunter"]
    }
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

# Project paths
REPO_ROOT = Path(__file__).resolve().parents[4]
DATA_DIR = REPO_ROOT / "training_data" / "merge_decisions"


@dataclass
class MergeRule:
    """Rule defining what units can merge.
    
    Attributes:
        unit: Unit name this rule applies to.
        merges_with: "any", "same", or list of unit names.
        priority: Priority level for merge decisions (higher = prefer).
    """
    
    unit: str
    merges_with: str | list[str] = "same"
    priority: int = 0
    
    def can_merge_with(self, other_unit: str) -> bool:
        """Check if this unit can merge with another.
        
        Args:
            other_unit: Name of the potential merge target.
            
        Returns:
            True if merge is allowed by this rule.
        """
        if self.merges_with == "any":
            return True
        if self.merges_with == "same":
            return other_unit == self.unit
        if isinstance(self.merges_with, list):
            return other_unit in self.merges_with
        return False


@dataclass
class MergeWhitelist:
    """Collection of merge rules.
    
    Defines which units can merge with what other units.
    Loaded from JSON configuration.
    """
    
    rules: dict[str, MergeRule] = field(default_factory=dict)
    
    @classmethod
    def from_json(cls, path: Path | str) -> MergeWhitelist:
        """Load whitelist from JSON file.
        
        Args:
            path: Path to JSON file with merge rules.
            
        Returns:
            MergeWhitelist instance.
        """
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        
        rules = {}
        for entry in data.get("rules", []):
            rule = MergeRule(
                unit=entry["unit"],
                merges_with=entry.get("merges_with", "same"),
                priority=entry.get("priority", 0),
            )
            rules[rule.unit] = rule
        
        return cls(rules=rules)
    
    @classmethod
    def default(cls) -> MergeWhitelist:
        """Create default whitelist with common special units.
        
        Returns:
            MergeWhitelist with default rules.
        """
        rules = {
            # Harlequin (Mime/Joker) can merge with any unit
            "harlequin": MergeRule("harlequin", "any", priority=10),
            "mime": MergeRule("mime", "any", priority=10),
            
            # Dryad upgrades any unit
            "dryad": MergeRule("dryad", "any", priority=9),
            
            # Most units merge with same type only
            "demon_hunter": MergeRule("demon_hunter", "same", priority=1),
            "knight_statue": MergeRule("knight_statue", "same", priority=2),
            "chemist": MergeRule("chemist", "same", priority=3),
            "shaman": MergeRule("shaman", "same", priority=4),
        }
        return cls(rules=rules)
    
    def can_merge(self, unit1: str, unit2: str) -> bool:
        """Check if two units can merge.
        
        Args:
            unit1: First unit name.
            unit2: Second unit name.
            
        Returns:
            True if merge is allowed.
        """
        # Check rule for unit1
        rule1 = self.rules.get(unit1)
        if rule1 and rule1.can_merge_with(unit2):
            return True
        
        # Check rule for unit2
        rule2 = self.rules.get(unit2)
        if rule2 and rule2.can_merge_with(unit1):
            return True
        
        # Default: same type only
        return unit1 == unit2
    
    def to_json(self, path: Path | str) -> None:
        """Save whitelist to JSON file.
        
        Args:
            path: Output path.
        """
        data = {
            "rules": [
                {
                    "unit": rule.unit,
                    "merges_with": rule.merges_with,
                    "priority": rule.priority,
                }
                for rule in self.rules.values()
            ]
        }
        
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)


@dataclass
class MergeModelSpec:
    """Specification for the merge decision ML model.
    
    This defines the features, labels, and architecture for
    training a merge decision model.
    
    Features (per merge candidate):
        - source_unit_type: One-hot encoded unit type
        - source_rank: Normalized rank (0-1)
        - target_unit_type: One-hot encoded unit type
        - target_rank: Normalized rank (0-1)
        - board_state: Flattened 3x5 grid state
        - mana_available: Current mana normalized
        - game_phase: Early/mid/late game indicator
        
    Labels:
        - merge_value: 0-1 score (higher = better merge)
        - should_merge: Binary yes/no
        
    Architecture Options:
        - Simple: Logistic Regression (baseline)
        - MLP: 2-3 layer neural network
        - DQN: Deep Q-Network for sequential decisions
    """
    
    # Feature dimensions
    n_unit_types: int = 80  # ~80 unique units
    n_ranks: int = 8  # Ranks 0-7
    grid_size: int = 15  # 3x5 grid
    
    # Model architecture
    architecture: str = "mlp"  # "logistic", "mlp", "dqn"
    hidden_layers: list[int] = field(default_factory=lambda: [128, 64])
    
    # Training parameters
    batch_size: int = 32
    learning_rate: float = 0.001
    epochs: int = 100
    
    @property
    def feature_dim(self) -> int:
        """Total input feature dimension."""
        return (
            self.n_unit_types * 2  # source + target unit types
            + 2  # source + target ranks
            + self.grid_size * (self.n_unit_types + 1)  # board state
            + 2  # mana + game phase
        )
    
    def to_json(self, path: Path | str) -> None:
        """Save spec to JSON file."""
        data = {
            "n_unit_types": self.n_unit_types,
            "n_ranks": self.n_ranks,
            "grid_size": self.grid_size,
            "architecture": self.architecture,
            "hidden_layers": self.hidden_layers,
            "batch_size": self.batch_size,
            "learning_rate": self.learning_rate,
            "epochs": self.epochs,
            "feature_dim": self.feature_dim,
        }
        
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)


@dataclass
class MergeDecision:
    """A single merge decision for training data.
    
    Attributes:
        timestamp: When the decision was made.
        source_cell: Grid index of source unit.
        target_cell: Grid index of target unit.
        source_unit: Unit type name.
        target_unit: Unit type name.
        source_rank: Rank of source unit.
        target_rank: Rank of target unit.
        was_executed: Whether merge was actually performed.
        outcome: Result of merge (success/fail/skipped).
        mana: Mana at time of decision.
        grid_state: Snapshot of grid at decision time.
    """
    
    timestamp: datetime
    source_cell: int
    target_cell: int
    source_unit: str
    target_unit: str
    source_rank: int
    target_rank: int
    was_executed: bool
    outcome: str  # "success", "fail", "skipped"
    mana: int = 0
    grid_state: list[dict[str, Any]] = field(default_factory=list)


class MergeFeatureExtractor:
    """Extract ML features from game state for merge decisions.
    
    Converts grid state and merge candidates into feature vectors
    suitable for training or inference.
    """
    
    def __init__(
        self,
        unit_labels: list[str] | None = None,
        n_ranks: int = 8,
    ) -> None:
        """Initialize the feature extractor.
        
        Args:
            unit_labels: List of unit type names for one-hot encoding.
            n_ranks: Number of rank levels.
        """
        self.unit_labels = unit_labels or []
        self.n_ranks = n_ranks
        self._unit_to_idx: dict[str, int] = {
            u: i for i, u in enumerate(self.unit_labels)
        }
    
    def extract_merge_features(
        self,
        source_unit: str,
        source_rank: int,
        target_unit: str,
        target_rank: int,
        grid_state: list[dict[str, Any]] | None = None,
        mana: int = 0,
        game_phase: float = 0.5,
    ) -> NDArray[np.float32]:
        """Extract feature vector for a merge candidate.
        
        Args:
            source_unit: Source unit type name.
            source_rank: Source unit rank.
            target_unit: Target unit type name.
            target_rank: Target unit rank.
            grid_state: List of dicts with unit/rank per cell.
            mana: Current mana amount.
            game_phase: Game progress (0=early, 1=late).
            
        Returns:
            Feature vector as numpy array.
        """
        features: list[NDArray[np.floating[Any]]] = []
        
        # Source unit one-hot
        source_oh = np.zeros(len(self.unit_labels), dtype=np.float32)
        if source_unit in self._unit_to_idx:
            source_oh[self._unit_to_idx[source_unit]] = 1.0
        features.append(source_oh)
        
        # Target unit one-hot
        target_oh = np.zeros(len(self.unit_labels), dtype=np.float32)
        if target_unit in self._unit_to_idx:
            target_oh[self._unit_to_idx[target_unit]] = 1.0
        features.append(target_oh)
        
        # Ranks (normalized)
        features.append(np.array([
            source_rank / self.n_ranks,
            target_rank / self.n_ranks,
        ], dtype=np.float32))
        
        # Grid state encoding
        if grid_state:
            grid_features = self._encode_grid(grid_state)
        else:
            grid_features = np.zeros(15 * (len(self.unit_labels) + 1), dtype=np.float32)
        features.append(grid_features)
        
        # Context features
        features.append(np.array([
            mana / 1000.0,  # Normalize mana
            game_phase,
        ], dtype=np.float32))
        
        return np.concatenate(features)
    
    def _encode_grid(
        self,
        grid_state: list[dict[str, Any]],
    ) -> NDArray[np.float32]:
        """Encode grid state as feature vector.
        
        Args:
            grid_state: List of 15 dicts with unit/rank info.
            
        Returns:
            Flattened grid encoding.
        """
        n_units = len(self.unit_labels)
        features = np.zeros(15 * (n_units + 1), dtype=np.float32)
        
        for i, cell in enumerate(grid_state[:15]):
            offset = i * (n_units + 1)
            
            unit_name = cell.get("unit", "empty")
            if unit_name in self._unit_to_idx:
                features[offset + self._unit_to_idx[unit_name]] = 1.0
            
            rank = cell.get("rank", 0)
            features[offset + n_units] = rank / self.n_ranks
        
        return features


class MergeDataCollector:
    """Collect merge decision data during gameplay.
    
    Records merge decisions and outcomes for later training.
    Data is saved incrementally to avoid memory issues.
    """
    
    def __init__(
        self,
        output_dir: Path | str | None = None,
    ) -> None:
        """Initialize the collector.
        
        Args:
            output_dir: Directory to save collected data.
        """
        self.output_dir = Path(output_dir) if output_dir else DATA_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self._session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._decisions: list[MergeDecision] = []
    
    def record_decision(
        self,
        source_cell: int,
        target_cell: int,
        source_unit: str,
        target_unit: str,
        source_rank: int,
        target_rank: int,
        was_executed: bool,
        outcome: str,
        mana: int = 0,
        grid_state: list[dict[str, Any]] | None = None,
    ) -> None:
        """Record a merge decision.
        
        Args:
            source_cell: Source cell index.
            target_cell: Target cell index.
            source_unit: Source unit type.
            target_unit: Target unit type.
            source_rank: Source rank.
            target_rank: Target rank.
            was_executed: Whether merge was performed.
            outcome: Result string.
            mana: Current mana.
            grid_state: Current grid state.
        """
        decision = MergeDecision(
            timestamp=datetime.now(),
            source_cell=source_cell,
            target_cell=target_cell,
            source_unit=source_unit,
            target_unit=target_unit,
            source_rank=source_rank,
            target_rank=target_rank,
            was_executed=was_executed,
            outcome=outcome,
            mana=mana,
            grid_state=grid_state or [],
        )
        self._decisions.append(decision)
    
    def save_session(self) -> Path:
        """Save collected decisions to JSON file.
        
        Returns:
            Path to saved file.
        """
        output_path = self.output_dir / f"merge_data_{self._session_id}.json"
        
        data = {
            "session_id": self._session_id,
            "n_decisions": len(self._decisions),
            "decisions": [
                {
                    "timestamp": d.timestamp.isoformat(),
                    "source_cell": d.source_cell,
                    "target_cell": d.target_cell,
                    "source_unit": d.source_unit,
                    "target_unit": d.target_unit,
                    "source_rank": d.source_rank,
                    "target_rank": d.target_rank,
                    "was_executed": d.was_executed,
                    "outcome": d.outcome,
                    "mana": d.mana,
                    "grid_state": d.grid_state,
                }
                for d in self._decisions
            ],
        }
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        
        print(f"Saved {len(self._decisions)} decisions to: {output_path}")
        return output_path
    
    def clear(self) -> None:
        """Clear collected decisions (start new session)."""
        self._decisions = []
        self._session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    @property
    def n_decisions(self) -> int:
        """Number of decisions collected in current session."""
        return len(self._decisions)
