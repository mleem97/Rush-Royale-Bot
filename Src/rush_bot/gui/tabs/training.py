"""
RushBot GUI - Training Tab
ML model training and data collection interface.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

import customtkinter as ctk

from rush_bot.gui.theme import COLORS
from rush_bot.perception import ML_INPUTS_DIR
from rush_bot.perception import RANK_MODEL_PATH
from rush_bot.perception import add_grid_to_dataset
from rush_bot.perception import ensure_training_dirs
from rush_bot.perception import save_rank_model
from rush_bot.perception import train_rank_model

if TYPE_CHECKING:
    from rush_bot.gui.content import ContentFrame


class TrainingTab(ctk.CTkFrame):
    """Machine Learning training and data collection tab."""

    def __init__(self, parent: ctk.CTkFrame, master_content: ContentFrame, **kwargs) -> None:
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.master_content = master_content

        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._create_header()
        self._create_ml_section()
        self._create_data_section()

    def _create_header(self) -> None:
        """Create section header."""
        header = ctk.CTkLabel(
            self,
            text="🧠 ML Training",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        header.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

    def _create_ml_section(self) -> None:
        """Create ML training controls."""
        ml_frame = ctk.CTkFrame(self)
        ml_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=10)
        ml_frame.grid_columnconfigure(1, weight=1)

        # Model status
        status_label = ctk.CTkLabel(
            ml_frame,
            text="Model Status:",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        status_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        self.model_status = ctk.CTkLabel(
            ml_frame,
            text="⚪ Not Loaded",
            font=ctk.CTkFont(size=13),
            text_color=COLORS["text_secondary"],
        )
        self.model_status.grid(row=0, column=1, padx=10, pady=10, sticky="w")

        # Training buttons
        btn_frame = ctk.CTkFrame(ml_frame, fg_color="transparent")
        btn_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        auto_label_btn = ctk.CTkButton(
            btn_frame,
            text="🏷️ Auto-Label Data",
            command=self._auto_label,
            width=150,
        )
        auto_label_btn.grid(row=0, column=0, padx=5, pady=5)

        train_btn = ctk.CTkButton(
            btn_frame,
            text="🚀 Train Model",
            command=self._train_model,
            fg_color=COLORS["success"],
            width=150,
        )
        train_btn.grid(row=0, column=1, padx=5, pady=5)

        load_btn = ctk.CTkButton(
            btn_frame,
            text="📂 Load Model",
            command=self._load_model,
            width=150,
        )
        load_btn.grid(row=0, column=2, padx=5, pady=5)

        # Unit Classifier Section
        unit_label = ctk.CTkLabel(
            ml_frame,
            text="Unit Classifier:",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        unit_label.grid(row=2, column=0, padx=10, pady=(20, 10), sticky="w")

        self.unit_model_status = ctk.CTkLabel(
            ml_frame,
            text="⚪ Not Trained",
            font=ctk.CTkFont(size=13),
            text_color=COLORS["text_secondary"],
        )
        self.unit_model_status.grid(row=2, column=1, padx=10, pady=(20, 10), sticky="w")

        unit_btn_frame = ctk.CTkFrame(ml_frame, fg_color="transparent")
        unit_btn_frame.grid(row=3, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        collect_btn = ctk.CTkButton(
            unit_btn_frame,
            text="📷 Collect Samples",
            command=self._collect_unit_samples,
            width=150,
        )
        collect_btn.grid(row=0, column=0, padx=5, pady=5)

        train_unit_btn = ctk.CTkButton(
            unit_btn_frame,
            text="🎯 Train Unit Model",
            command=self._train_unit_classifier,
            fg_color=COLORS["accent"],
            width=150,
        )
        train_unit_btn.grid(row=0, column=1, padx=5, pady=5)

        # Check if unit model exists
        self._check_unit_model()

    def _create_data_section(self) -> None:
        """Create data collection section."""
        data_frame = ctk.CTkFrame(self)
        data_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=10)

        header = ctk.CTkLabel(
            data_frame,
            text="📊 Training Data",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        header.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        # Data info with count
        self.data_info_label = ctk.CTkLabel(
            data_frame,
            text="Collect game data by running the bot to improve recognition accuracy.",
            text_color=COLORS["text_secondary"],
            wraplength=400,
        )
        self.data_info_label.grid(row=1, column=0, padx=10, pady=10, sticky="w")

        # Update data count
        self._update_data_info()

    def _update_data_info(self) -> None:
        """Update the training data info display."""
        ensure_training_dirs()

        # Count training images
        image_count = 0
        if ML_INPUTS_DIR.exists():
            # Layout A: flat files
            image_count += len(list(ML_INPUTS_DIR.glob("*_input_*.png")))
            # Layout B: hierarchical folders
            for sub in ML_INPUTS_DIR.iterdir():
                if sub.is_dir() and sub.name.isdigit():
                    image_count += len(list(sub.glob("*.png")))

        if image_count > 0:
            self.data_info_label.configure(
                text=f"📁 {image_count} training images available in machine_learning/inputs/",
                text_color=COLORS["success"],
            )
        else:
            self.data_info_label.configure(
                text="⚠️ No training data yet. Run the bot to collect images.",
                text_color=COLORS["warning"],
            )

    def _auto_label(self) -> None:
        """Auto-label training data from OCR_inputs."""
        logger = self.master_content.master.logger

        try:
            logger.info("Starting auto-labeling from OCR_inputs...")
            added = add_grid_to_dataset()
            logger.info(f"Auto-labeled {added} images")
            self._update_data_info()
        except Exception as e:
            logger.error(f"Auto-labeling failed: {e}")

    def _train_model(self) -> None:
        """Train the ML model in a background thread."""
        logger = self.master_content.master.logger
        self.model_status.configure(text="🟡 Training...")

        def train_thread():
            try:
                logger.info("Training rank model...")

                # Check for training data
                image_count = len(list(ML_INPUTS_DIR.glob("*_input_*.png")))
                for sub in ML_INPUTS_DIR.iterdir():
                    if sub.is_dir() and sub.name.isdigit():
                        image_count += len(list(sub.glob("*.png")))

                if image_count < 10:
                    logger.warning(f"Only {image_count} images. Need at least 10 for training.")
                    self.after(
                        0,
                        lambda: self.model_status.configure(text="⚪ Insufficient Data"),
                    )
                    return

                model = train_rank_model(ML_INPUTS_DIR)
                save_rank_model(model, RANK_MODEL_PATH)

                logger.info(f"Model saved to {RANK_MODEL_PATH}")
                logger.info(f"Classes: {list(model.classes_)}")

                self.after(0, lambda: self.model_status.configure(text="🟢 Trained & Saved"))

            except Exception as e:
                logger.error(f"Training failed: {e}")
                self.after(0, lambda: self.model_status.configure(text="🔴 Training Failed"))

        threading.Thread(target=train_thread, daemon=True).start()

    def _load_model(self) -> None:
        """Check if a trained model exists and update status."""
        logger = self.master_content.master.logger

        if RANK_MODEL_PATH.exists():
            # Check model file size
            size_kb = RANK_MODEL_PATH.stat().st_size / 1024
            logger.info(f"Model found: {RANK_MODEL_PATH} ({size_kb:.1f} KB)")
            self.model_status.configure(text="🟢 Model Loaded")
        else:
            logger.warning(f"No model found at {RANK_MODEL_PATH}")
            self.model_status.configure(text="🔴 No Model Found")

    def _check_unit_model(self) -> None:
        """Check if unit classifier model exists."""
        from rush_bot import PROJECT_ROOT

        model_path = PROJECT_ROOT / "models" / "unit_classifier.pkl"
        if model_path.exists():
            size_kb = model_path.stat().st_size / 1024
            self.unit_model_status.configure(
                text=f"🟢 Trained ({size_kb:.1f} KB)",
                text_color=COLORS["success"],
            )
        else:
            self.unit_model_status.configure(
                text="⚪ Not Trained",
                text_color=COLORS["text_secondary"],
            )

    def _collect_unit_samples(self) -> None:
        """Collect unit samples from connected device."""
        import threading

        logger = self.master_content.master.logger

        def collect_thread():
            try:
                import sys

                from rush_bot import PROJECT_ROOT

                # Add scripts to path
                scripts_path = PROJECT_ROOT / "scripts"
                if str(scripts_path) not in sys.path:
                    sys.path.insert(0, str(scripts_path))

                import train_unit_classifier

                logger.info("Initializing training directories...")
                train_unit_classifier.ensure_dirs()

                logger.info("Starting sample collection from device...")
                logger.info("A window will open - click on units to label them.")

                # This will open a GUI window for labeling
                train_unit_classifier.collect_from_device()

                logger.info("Sample collection complete!")

            except Exception as e:
                logger.error(f"Collection failed: {e}")

        threading.Thread(target=collect_thread, daemon=True).start()

    def _train_unit_classifier(self) -> None:
        """Train the unit classifier model."""
        import threading

        logger = self.master_content.master.logger
        self.unit_model_status.configure(text="🟡 Training...", text_color=COLORS["warning"])

        def train_thread():
            try:
                import sys

                from rush_bot import PROJECT_ROOT

                # Add scripts to path
                scripts_path = PROJECT_ROOT / "scripts"
                if str(scripts_path) not in sys.path:
                    sys.path.insert(0, str(scripts_path))

                import train_unit_classifier

                logger.info("Training unit classifier...")
                train_unit_classifier.train_model()

                logger.info("Unit classifier training complete!")
                self.after(0, self._check_unit_model)

            except Exception as e:
                logger.error(f"Training failed: {e}")
                self.after(
                    0,
                    lambda: self.unit_model_status.configure(
                        text="🔴 Training Failed",
                        text_color=COLORS["danger"],
                    ),
                )

        threading.Thread(target=train_thread, daemon=True).start()
