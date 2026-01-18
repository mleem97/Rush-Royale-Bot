"""Training Tab GUI Module for Rush Bot (T021, T022).

This module provides a restructured training tab with:
- Integrated labeling workflow (T021)
- Organized sections without overflow (T022)
- Dataset management
- Model training controls
- ONNX export support
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import TYPE_CHECKING

import customtkinter as ctk
from PIL import Image

if TYPE_CHECKING:
    from gui import RushBotApp

# Color palette (imported from main gui.py)
COLORS = {
    "success": ("#16a34a", "#4ade80"),
    "warning": ("#d97706", "#fbbf24"),
    "danger": ("#dc2626", "#f87171"),
    "accent": ("#3b82f6", "#60a5fa"),
    "text_primary": ("#1f2937", "#f1f5f9"),
    "text_secondary": ("#6b7280", "#94a3b8"),
    "unit_empty": ("#d1d5db", "#374151"),
    "card_bg": ("#ffffff", "#2d3250"),
}


class TrainingTabFrame(ctk.CTkFrame):
    """Restructured Training Tab with integrated labeling (T021, T022).
    
    Sections:
    1. Dataset Overview - Status and statistics
    2. Labeling Panel - Integrated quick labeling
    3. Training Controls - Model training/export
    4. Logs - Training progress and status
    """
    
    def __init__(self, master: ctk.CTkFrame, app: RushBotApp, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app = app
        
        # State
        self._current_unlabeled_file: Path | None = None
        self._unlabeled_files: list[Path] = []
        
        # Configure grid for responsive layout
        self.grid_rowconfigure(0, weight=0)  # Header
        self.grid_rowconfigure(1, weight=1)  # Main content
        self.grid_columnconfigure(0, weight=1)
        
        self._create_header()
        self._create_main_content()
    
    def _create_header(self):
        """Create header section."""
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        title = ctk.CTkLabel(
            header_frame,
            text="🧠 ML Training & Labeling",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        title.pack(side="left", padx=10)
        
        # Quick stats
        self.stats_label = ctk.CTkLabel(
            header_frame,
            text="Dataset: 0 samples | Model: checking...",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_secondary"],
        )
        self.stats_label.pack(side="right", padx=10)
        
        self._refresh_stats()
    
    def _create_main_content(self):
        """Create main content with scrollable sections."""
        # Scrollable container
        self.scroll_frame = ctk.CTkScrollableFrame(
            self,
            label_text="",
            fg_color="transparent",
        )
        self.scroll_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.scroll_frame.grid_columnconfigure(0, weight=1)
        
        # Create sections
        self._create_dataset_section()
        self._create_labeling_section()
        self._create_training_section()
        self._create_export_section()
        self._create_status_section()
    
    def _create_dataset_section(self):
        """Section 1: Dataset Overview."""
        section = self._create_section_frame("📊 Dataset Overview", row=0)
        
        # Dataset info grid
        info_frame = ctk.CTkFrame(section, fg_color="transparent")
        info_frame.pack(fill="x", padx=10, pady=5)
        info_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
        # Rank samples
        self.rank_samples_label = ctk.CTkLabel(
            info_frame,
            text="Rank Samples: 0",
            font=ctk.CTkFont(size=12),
        )
        self.rank_samples_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        # Unit samples
        self.unit_samples_label = ctk.CTkLabel(
            info_frame,
            text="Unit Samples: 0",
            font=ctk.CTkFont(size=12),
        )
        self.unit_samples_label.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        # Pending labels
        self.pending_label = ctk.CTkLabel(
            info_frame,
            text="Pending: 0",
            font=ctk.CTkFont(size=12),
        )
        self.pending_label.grid(row=0, column=2, padx=5, pady=5, sticky="w")
        
        # Buttons
        btn_frame = ctk.CTkFrame(section, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=5)
        
        refresh_btn = ctk.CTkButton(
            btn_frame,
            text="🔄 Refresh",
            command=self._refresh_stats,
            width=100,
        )
        refresh_btn.pack(side="left", padx=5)
        
        open_rank_btn = ctk.CTkButton(
            btn_frame,
            text="📂 Rank Data",
            command=lambda: self._open_folder(Path("machine_learning/inputs")),
            width=100,
        )
        open_rank_btn.pack(side="left", padx=5)
        
        open_unit_btn = ctk.CTkButton(
            btn_frame,
            text="📂 Unit Data",
            command=lambda: self._open_folder(Path("machine_learning/unit_inputs")),
            width=100,
        )
        open_unit_btn.pack(side="left", padx=5)
    
    def _create_labeling_section(self):
        """Section 2: Integrated Labeling (T021)."""
        section = self._create_section_frame("🏷️ Quick Labeling", row=1)
        
        # Two-column layout
        content_frame = ctk.CTkFrame(section, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=10, pady=5)
        content_frame.grid_columnconfigure(0, weight=0)  # Preview
        content_frame.grid_columnconfigure(1, weight=1)  # Controls
        
        # Left: Preview
        preview_frame = ctk.CTkFrame(content_frame, fg_color=COLORS["card_bg"])
        preview_frame.grid(row=0, column=0, rowspan=3, padx=(0, 10), pady=5, sticky="ns")
        
        self.preview_label = ctk.CTkLabel(
            preview_frame,
            text="No image\nloaded",
            width=120,
            height=120,
            fg_color=COLORS["unit_empty"],
            corner_radius=8,
        )
        self.preview_label.pack(padx=10, pady=10)
        
        self.file_name_label = ctk.CTkLabel(
            preview_frame,
            text="",
            font=ctk.CTkFont(size=10),
            text_color=COLORS["text_secondary"],
        )
        self.file_name_label.pack(padx=5, pady=(0, 10))
        
        # Right: Controls
        controls_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        controls_frame.grid(row=0, column=1, sticky="nsew", pady=5)
        
        # Unit selection
        unit_label = ctk.CTkLabel(
            controls_frame,
            text="Select Unit Type:",
            font=ctk.CTkFont(size=12),
        )
        unit_label.pack(anchor="w", pady=(0, 5))
        
        self.label_unit_var = ctk.StringVar(value="Select unit...")
        self.label_dropdown = ctk.CTkOptionMenu(
            controls_frame,
            variable=self.label_unit_var,
            values=self._load_available_units(),
            width=200,
        )
        self.label_dropdown.pack(anchor="w", pady=(0, 10))
        
        # Action buttons
        btn_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=5)
        
        self.load_next_btn = ctk.CTkButton(
            btn_frame,
            text="📷 Load",
            command=self._load_next_unlabeled,
            width=80,
        )
        self.load_next_btn.pack(side="left", padx=(0, 5))
        
        self.save_label_btn = ctk.CTkButton(
            btn_frame,
            text="💾 Save",
            command=self._save_and_next,
            fg_color=COLORS["success"],
            width=80,
        )
        self.save_label_btn.pack(side="left", padx=5)
        
        self.skip_btn = ctk.CTkButton(
            btn_frame,
            text="⏭ Skip",
            command=self._skip_current,
            fg_color=COLORS["warning"],
            width=80,
        )
        self.skip_btn.pack(side="left", padx=5)
        
        self.delete_btn = ctk.CTkButton(
            btn_frame,
            text="🗑️",
            command=self._delete_current,
            fg_color=COLORS["danger"],
            width=40,
        )
        self.delete_btn.pack(side="left", padx=5)
        
        # Keyboard shortcuts hint
        hint_label = ctk.CTkLabel(
            controls_frame,
            text="Shortcuts: Enter=Save, Tab=Skip, Delete=Remove",
            font=ctk.CTkFont(size=10),
            text_color=COLORS["text_secondary"],
        )
        hint_label.pack(anchor="w", pady=(10, 0))
    
    def _create_training_section(self):
        """Section 3: Model Training Controls."""
        section = self._create_section_frame("🤖 Model Training", row=2)
        
        content_frame = ctk.CTkFrame(section, fg_color="transparent")
        content_frame.pack(fill="x", padx=10, pady=5)
        content_frame.grid_columnconfigure((0, 1), weight=1)
        
        # Rank Model column
        rank_frame = ctk.CTkFrame(content_frame)
        rank_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        
        rank_title = ctk.CTkLabel(
            rank_frame,
            text="Rank Model",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        rank_title.pack(pady=(10, 5))
        
        self.rank_model_status = ctk.CTkLabel(
            rank_frame,
            text="Status: checking...",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_secondary"],
        )
        self.rank_model_status.pack(pady=5)
        
        train_rank_btn = ctk.CTkButton(
            rank_frame,
            text="🧠 Train Rank Model",
            command=self._train_rank_model,
            fg_color=COLORS["accent"],
        )
        train_rank_btn.pack(pady=10, padx=20, fill="x")
        
        # Unit Model column
        unit_frame = ctk.CTkFrame(content_frame)
        unit_frame.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        
        unit_title = ctk.CTkLabel(
            unit_frame,
            text="Unit Model",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        unit_title.pack(pady=(10, 5))
        
        self.unit_model_status = ctk.CTkLabel(
            unit_frame,
            text="Status: checking...",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_secondary"],
        )
        self.unit_model_status.pack(pady=5)
        
        prepare_btn = ctk.CTkButton(
            unit_frame,
            text="📦 Prepare Dataset",
            command=self._prepare_unit_dataset,
        )
        prepare_btn.pack(pady=(10, 5), padx=20, fill="x")
        
        train_unit_btn = ctk.CTkButton(
            unit_frame,
            text="🧠 Train Unit Model",
            command=self._train_unit_model,
            fg_color=COLORS["accent"],
        )
        train_unit_btn.pack(pady=5, padx=20, fill="x")
        
        self._check_model_status()
    
    def _create_export_section(self):
        """Section 4: ONNX Export (T020)."""
        section = self._create_section_frame("📤 Export Models", row=3)
        
        content_frame = ctk.CTkFrame(section, fg_color="transparent")
        content_frame.pack(fill="x", padx=10, pady=5)
        
        info_label = ctk.CTkLabel(
            content_frame,
            text="Export models to ONNX format for portable inference.",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_secondary"],
        )
        info_label.pack(anchor="w", pady=(0, 10))
        
        btn_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        btn_frame.pack(fill="x")
        
        export_rank_btn = ctk.CTkButton(
            btn_frame,
            text="Export Rank → ONNX",
            command=lambda: self._export_to_onnx("rank"),
            width=150,
        )
        export_rank_btn.pack(side="left", padx=5)
        
        export_unit_btn = ctk.CTkButton(
            btn_frame,
            text="Export Unit → ONNX",
            command=lambda: self._export_to_onnx("unit"),
            width=150,
        )
        export_unit_btn.pack(side="left", padx=5)
        
        self.onnx_status = ctk.CTkLabel(
            content_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_secondary"],
        )
        self.onnx_status.pack(anchor="w", pady=(10, 0))
    
    def _create_status_section(self):
        """Section 5: Progress and Status."""
        section = self._create_section_frame("📝 Status", row=4)
        
        content_frame = ctk.CTkFrame(section, fg_color="transparent")
        content_frame.pack(fill="x", padx=10, pady=5)
        
        self.progress_bar = ctk.CTkProgressBar(content_frame)
        self.progress_bar.pack(fill="x", pady=(0, 5))
        self.progress_bar.set(0)
        
        self.status_label = ctk.CTkLabel(
            content_frame,
            text="Ready",
            font=ctk.CTkFont(size=12),
        )
        self.status_label.pack(anchor="w")
    
    def _create_section_frame(self, title: str, row: int) -> ctk.CTkFrame:
        """Create a collapsible section frame."""
        section = ctk.CTkFrame(self.scroll_frame)
        section.grid(row=row, column=0, sticky="ew", padx=5, pady=5)
        section.grid_columnconfigure(0, weight=1)
        
        # Section header
        header = ctk.CTkLabel(
            section,
            text=title,
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        )
        header.pack(fill="x", padx=10, pady=(10, 5))
        
        return section
    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    def _load_available_units(self) -> list[str]:
        """Load available unit names from cv-images/all_units."""
        units_dir = Path("cv-images/all_units")
        if not units_dir.exists():
            return ["demon_hunter", "dryad", "harlequin", "chemist", "knight_statue"]
        
        units = sorted(
            {p.stem for p in units_dir.glob("*.png") if p.is_file() and p.stem != "empty"}
        )
        return units if units else ["empty"]
    
    def _refresh_stats(self):
        """Refresh dataset statistics."""
        # Rank samples
        rank_dir = Path("machine_learning/inputs")
        rank_count = 0
        if rank_dir.exists():
            rank_count = len(list(rank_dir.glob("*_input_*.png")))
            rank_count += sum(
                len(list(sub.glob("*.png")))
                for sub in rank_dir.iterdir()
                if sub.is_dir()
            )
        self.rank_samples_label.configure(text=f"Rank Samples: {rank_count}")
        
        # Unit samples
        unit_dir = Path("machine_learning/unit_inputs")
        unit_count = 0
        if unit_dir.exists():
            unit_count = sum(
                len(list(sub.glob("*.png")))
                for sub in unit_dir.iterdir()
                if sub.is_dir()
            )
        self.unit_samples_label.configure(text=f"Unit Samples: {unit_count}")
        
        # Pending labels
        pending_dir = Path("cv-images/all_units/missing_units")
        pending = 0
        if pending_dir.exists():
            pending = len(list(pending_dir.glob("*.png")))
        self.pending_label.configure(text=f"Pending: {pending}")
        
        # Update header stats
        self.stats_label.configure(
            text=f"Dataset: {rank_count + unit_count} samples | Pending: {pending}"
        )
    
    def _check_model_status(self):
        """Check status of both models."""
        # Rank model
        rank_path = Path("rank_model.pkl")
        if rank_path.exists():
            try:
                import pickle
                with open(rank_path, "rb") as f:
                    model = pickle.load(f)
                classes = list(getattr(model, "classes_", []))
                self.rank_model_status.configure(
                    text=f"✅ Classes: {classes}",
                    text_color=COLORS["success"],
                )
            except Exception as e:
                self.rank_model_status.configure(
                    text=f"⚠️ Error: {e}",
                    text_color=COLORS["warning"],
                )
        else:
            self.rank_model_status.configure(
                text="❌ Not found",
                text_color=COLORS["danger"],
            )
        
        # Unit model
        unit_path = Path("models/unit_classifier.pkl")
        if unit_path.exists():
            try:
                import pickle
                with open(unit_path, "rb") as f:
                    model = pickle.load(f)
                n_classes = len(getattr(model, "classes_", []))
                self.unit_model_status.configure(
                    text=f"✅ {n_classes} unit types",
                    text_color=COLORS["success"],
                )
            except Exception as e:
                self.unit_model_status.configure(
                    text=f"⚠️ Error: {e}",
                    text_color=COLORS["warning"],
                )
        else:
            self.unit_model_status.configure(
                text="❌ Not found",
                text_color=COLORS["danger"],
            )
    
    def _open_folder(self, path: Path):
        """Open folder in file explorer."""
        import subprocess
        import sys
        
        path = path.resolve()
        path.mkdir(parents=True, exist_ok=True)
        
        if sys.platform == "win32":
            subprocess.Popen(["explorer", str(path)])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
    
    # =========================================================================
    # Labeling Methods (T021)
    # =========================================================================
    
    def _load_next_unlabeled(self):
        """Load next unlabeled image."""
        missing_dir = Path("cv-images/all_units/missing_units")
        if not missing_dir.exists():
            self.status_label.configure(text="No missing_units folder")
            return
        
        self._unlabeled_files = list(missing_dir.glob("*.png"))
        
        if not self._unlabeled_files:
            self.status_label.configure(text="No unlabeled images found")
            self.preview_label.configure(text="No image\nloaded", image=None)
            self.file_name_label.configure(text="")
            self._current_unlabeled_file = None
            self._refresh_stats()
            return
        
        self._current_unlabeled_file = self._unlabeled_files[0]
        self._display_preview(self._current_unlabeled_file)
        self.status_label.configure(
            text=f"Loaded ({len(self._unlabeled_files)} remaining)"
        )
    
    def _display_preview(self, image_path: Path):
        """Display image preview."""
        try:
            pil_image = Image.open(image_path)
            pil_image.thumbnail((120, 120), Image.Resampling.LANCZOS)
            ctk_image = ctk.CTkImage(
                light_image=pil_image,
                dark_image=pil_image,
                size=(120, 120),
            )
            self.preview_label.configure(image=ctk_image, text="")
            self.preview_label._image = ctk_image
            self.file_name_label.configure(text=image_path.name[:20])
        except Exception as e:
            self.preview_label.configure(text="Error", image=None)
            self.status_label.configure(text=f"Error: {e}")
    
    def _save_and_next(self):
        """Save label and load next."""
        if not self._current_unlabeled_file:
            return
        
        unit_name = self.label_unit_var.get()
        if unit_name == "Select unit..." or not unit_name:
            self.status_label.configure(text="Please select a unit first")
            return
        
        target_dir = Path("cv-images/all_units")
        target_path = target_dir / f"{unit_name}.png"
        
        # Handle duplicates
        if target_path.exists():
            counter = 1
            while target_path.exists():
                target_path = target_dir / f"{unit_name}_{counter}.png"
                counter += 1
        
        try:
            import shutil
            shutil.move(str(self._current_unlabeled_file), str(target_path))
            self.status_label.configure(text=f"Saved as {target_path.name}")
            self._refresh_stats()
            self._load_next_unlabeled()
        except Exception as e:
            self.status_label.configure(text=f"Error: {e}")
    
    def _skip_current(self):
        """Skip current image."""
        if self._unlabeled_files and len(self._unlabeled_files) > 1:
            self._unlabeled_files.append(self._unlabeled_files.pop(0))
            self._current_unlabeled_file = self._unlabeled_files[0]
            self._display_preview(self._current_unlabeled_file)
            self.status_label.configure(text="Skipped")
    
    def _delete_current(self):
        """Delete current unlabeled image."""
        if not self._current_unlabeled_file:
            return
        
        try:
            self._current_unlabeled_file.unlink()
            self.status_label.configure(text="Deleted")
            self._refresh_stats()
            self._load_next_unlabeled()
        except Exception as e:
            self.status_label.configure(text=f"Delete error: {e}")
    
    # =========================================================================
    # Training Methods
    # =========================================================================
    
    def _train_rank_model(self):
        """Train rank model in background."""
        def run_training():
            try:
                self.progress_bar.set(0.1)
                self.status_label.configure(text="Loading dataset...")
                
                from rush_bot.ml.training import RankModelTrainer
                from rush_bot.ml.training import TrainingConfig
                
                config = TrainingConfig(max_iter=500)
                trainer = RankModelTrainer(config)
                
                self.progress_bar.set(0.3)
                self.status_label.configure(text="Training...")
                
                result = trainer.train()
                
                self.progress_bar.set(0.8)
                self.status_label.configure(text="Saving...")
                
                trainer.save()
                
                self.progress_bar.set(1.0)
                self.app.after(0, lambda: self.status_label.configure(
                    text=f"✅ Trained! Accuracy: {result.val_accuracy:.2%}"
                ))
                self.app.after(0, self._check_model_status)
                
            except Exception as exc:
                self.app.after(0, lambda e=exc: self.status_label.configure(
                    text=f"❌ Error: {e}"
                ))
            finally:
                self.app.after(500, lambda: self.progress_bar.set(0))
        
        thread = threading.Thread(target=run_training, daemon=True)
        thread.start()
    
    def _prepare_unit_dataset(self):
        """Prepare unit training dataset."""
        def run_prepare():
            try:
                self.progress_bar.set(0.2)
                self.status_label.configure(text="Preparing dataset...")
                
                from rush_bot.ml.training import UnitModelTrainer
                
                trainer = UnitModelTrainer()
                count = trainer.prepare_dataset()
                
                self.progress_bar.set(1.0)
                self.app.after(0, lambda: self.status_label.configure(
                    text=f"✅ Created {count} samples"
                ))
                self.app.after(0, self._refresh_stats)
                
            except Exception as exc:
                self.app.after(0, lambda e=exc: self.status_label.configure(
                    text=f"❌ Error: {e}"
                ))
            finally:
                self.app.after(500, lambda: self.progress_bar.set(0))
        
        thread = threading.Thread(target=run_prepare, daemon=True)
        thread.start()
    
    def _train_unit_model(self):
        """Train unit model in background."""
        def run_training():
            try:
                self.progress_bar.set(0.1)
                self.status_label.configure(text="Loading dataset...")
                
                from rush_bot.ml.training import TrainingConfig
                from rush_bot.ml.training import UnitModelTrainer
                
                config = TrainingConfig(max_iter=500)
                trainer = UnitModelTrainer(config)
                
                self.progress_bar.set(0.3)
                self.status_label.configure(text="Training...")
                
                result = trainer.train()
                
                self.progress_bar.set(0.8)
                self.status_label.configure(text="Saving...")
                
                trainer.save()
                
                self.progress_bar.set(1.0)
                self.app.after(0, lambda: self.status_label.configure(
                    text=f"✅ Trained! {len(result.classes)} units, {result.val_accuracy:.2%} acc"
                ))
                self.app.after(0, self._check_model_status)
                
            except Exception as exc:
                self.app.after(0, lambda e=exc: self.status_label.configure(
                    text=f"❌ Error: {e}"
                ))
            finally:
                self.app.after(500, lambda: self.progress_bar.set(0))
        
        thread = threading.Thread(target=run_training, daemon=True)
        thread.start()
    
    def _export_to_onnx(self, model_type: str):
        """Export model to ONNX format (T020)."""
        def run_export():
            try:
                self.progress_bar.set(0.2)
                self.status_label.configure(text=f"Exporting {model_type} model...")
                
                from rush_bot.ml.onnx_export import check_onnx_available
                from rush_bot.ml.onnx_export import export_sklearn_to_onnx
                
                if not check_onnx_available():
                    self.app.after(0, lambda: self.status_label.configure(
                        text="❌ ONNX not available. Install: pip install onnx skl2onnx"
                    ))
                    return
                
                import pickle
                
                if model_type == "rank":
                    model_path = Path("rank_model.pkl")
                    onnx_path = Path("rank_model.onnx")
                    input_shape = (120 * 120,)
                else:
                    model_path = Path("models/unit_classifier.pkl")
                    onnx_path = Path("models/unit_classifier.onnx")
                    input_shape = (120 * 120 * 3,)  # Color images
                
                if not model_path.exists():
                    self.app.after(0, lambda: self.status_label.configure(
                        text=f"❌ Model not found: {model_path}"
                    ))
                    return
                
                with open(model_path, "rb") as f:
                    model = pickle.load(f)
                
                self.progress_bar.set(0.6)
                
                export_sklearn_to_onnx(model, onnx_path, input_shape, model_type)
                
                self.progress_bar.set(1.0)
                self.app.after(0, lambda: self.status_label.configure(
                    text=f"✅ Exported to {onnx_path}"
                ))
                self.app.after(0, lambda: self.onnx_status.configure(
                    text=f"Last export: {onnx_path}"
                ))
                
            except Exception as exc:
                self.app.after(0, lambda e=exc: self.status_label.configure(
                    text=f"❌ Export error: {e}"
                ))
            finally:
                self.app.after(500, lambda: self.progress_bar.set(0))
        
        thread = threading.Thread(target=run_export, daemon=True)
        thread.start()
