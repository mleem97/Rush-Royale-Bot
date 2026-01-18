"""
RushBot - Unit Classifier Training
Train a CNN model to recognize units from screenshots.

Usage:
    1. Collect training data:
       python train_unit_classifier.py collect

    2. Train the model:
       python train_unit_classifier.py train

    3. Test the model:
       python train_unit_classifier.py test <screenshot.png>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "Src"))

# Training data directories
TRAINING_DATA_DIR = PROJECT_ROOT / "training_data" / "units"
SCREENSHOTS_DIR = PROJECT_ROOT / "training_data" / "screenshots"
MODEL_PATH = PROJECT_ROOT / "models" / "unit_classifier.pkl"
LABELS_PATH = PROJECT_ROOT / "models" / "unit_labels.json"


def ensure_dirs():
    """Create necessary directories."""
    TRAINING_DATA_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Create subdirectories for each unit
    units_dir = PROJECT_ROOT / "cv-images" / "all_units"
    for unit_file in units_dir.glob("*.png"):
        unit_name = unit_file.stem
        if unit_name not in ("empty", "-"):
            (TRAINING_DATA_DIR / unit_name).mkdir(exist_ok=True)

    # Also from subfolders
    for subfolder in ["common", "rare", "legendary"]:
        sub_path = units_dir / subfolder
        if sub_path.exists():
            for unit_file in sub_path.glob("*.png"):
                unit_name = unit_file.stem
                if unit_name not in ("empty", "-"):
                    (TRAINING_DATA_DIR / unit_name).mkdir(exist_ok=True)

    # Create "unknown" directory for non-unit images
    (TRAINING_DATA_DIR / "unknown").mkdir(exist_ok=True)

    print(f"Training data directory: {TRAINING_DATA_DIR}")
    print(f"Created directories for {len(list(TRAINING_DATA_DIR.iterdir()))} classes")


def import_all_units_as_samples():
    """Import unit images from cv-images/all_units as training samples.

    This uses the existing unit icon images as base training data.
    """
    ensure_dirs()

    units_dir = PROJECT_ROOT / "cv-images" / "all_units"
    imported_count = 0

    # Mapping for unit name aliases (e.g., twins1, twins2 -> twins)
    UNIT_ALIASES = {
        "twins1": "twins",
        "twins2": "twins",
    }

    def process_unit_file(unit_file: Path):
        """Process a single unit file."""
        nonlocal imported_count

        unit_name = unit_file.stem
        if unit_name in ("empty", "-"):
            return

        # Apply alias mapping
        unit_name = UNIT_ALIASES.get(unit_name, unit_name)

        # Read image
        img = cv2.imread(str(unit_file))
        if img is None:
            return

        # Resize to standard size (64x64)
        img_resized = cv2.resize(img, (64, 64))

        # Create target directory
        target_dir = TRAINING_DATA_DIR / unit_name
        target_dir.mkdir(exist_ok=True)

        # Save as base sample (use original filename to avoid overwrites for aliases)
        base_name = unit_file.stem
        target_path = target_dir / f"base_icon_{base_name}.png"
        if not target_path.exists():
            cv2.imwrite(str(target_path), img_resized)
            imported_count += 1
            print(f"  Imported: {unit_file.stem} -> {unit_name}")

        # Also create augmented versions for better training
        augmented = augment_image(img_resized)
        for i, aug_img in enumerate(augmented[1:], 1):  # Skip first (original)
            aug_path = target_dir / f"base_icon_{base_name}_aug_{i:02d}.png"
            if not aug_path.exists():
                cv2.imwrite(str(aug_path), aug_img)
                imported_count += 1

    print("Importing unit icons from cv-images/all_units...")

    # Process main directory
    for unit_file in units_dir.glob("*.png"):
        process_unit_file(unit_file)

    # Process subdirectories
    for subfolder in ["common", "rare", "legendary"]:
        sub_path = units_dir / subfolder
        if sub_path.exists():
            for unit_file in sub_path.glob("*.png"):
                process_unit_file(unit_file)

    print(f"\n✓ Imported {imported_count} samples from all_units")

    # Count total samples
    total = sum(len(list(d.glob("*.png"))) for d in TRAINING_DATA_DIR.iterdir() if d.is_dir())
    print(f"✓ Total training samples: {total}")


def auto_label_screenshot(screenshot_path: str):
    """Semi-automatic labeling using template matching.

    Shows image on left with all detections, editable list on right.
    """
    import tkinter as tk
    from tkinter import ttk

    from PIL import Image
    from PIL import ImageTk

    # Load screenshot
    img = cv2.imread(screenshot_path)
    if img is None:
        print(f"Failed to load: {screenshot_path}")
        return 0

    # Get list of valid unit names
    valid_units = sorted([d.name for d in TRAINING_DATA_DIR.iterdir() if d.is_dir()])

    # Load all template icons
    icons_dir = PROJECT_ROOT / "cv-images" / "all_units"
    templates = {}

    for icon_file in icons_dir.glob("*.png"):
        name = icon_file.stem
        if name in ("empty", "-"):
            continue
        template = cv2.imread(str(icon_file))
        if template is not None:
            templates[name] = template

    # Also from subfolders
    for subfolder in ["common", "rare", "legendary"]:
        sub_path = icons_dir / subfolder
        if sub_path.exists():
            for icon_file in sub_path.glob("*.png"):
                name = icon_file.stem
                if name not in ("empty", "-"):
                    template = cv2.imread(str(icon_file))
                    if template is not None:
                        templates[name] = template

    print(f"Loaded {len(templates)} template icons")
    print(f"Scanning {screenshot_path}...")

    # Find all potential unit locations using multi-scale template matching
    detections = []
    h, w = img.shape[:2]

    # Try different scales for template matching
    scales = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]

    for unit_name, template in templates.items():
        th, tw = template.shape[:2]

        for scale in scales:
            new_w = int(tw * scale)
            new_h = int(th * scale)

            if new_w < 20 or new_h < 20 or new_w > w or new_h > h:
                continue

            resized_template = cv2.resize(template, (new_w, new_h))
            result = cv2.matchTemplate(img, resized_template, cv2.TM_CCOEFF_NORMED)

            threshold = 0.6
            locations = np.where(result >= threshold)

            for pt in zip(*locations[::-1]):
                x, y = pt
                confidence = result[y, x]
                detections.append(
                    {
                        "x": x,
                        "y": y,
                        "w": new_w,
                        "h": new_h,
                        "unit": unit_name,
                        "conf": float(confidence),
                        "scale": scale,
                    }
                )

    if not detections:
        print("No units detected! Try manual labeling with 'collect' command.")
        return 0

    # Non-maximum suppression
    detections = nms_detections(detections, iou_threshold=0.3)

    # Sort by position (top-left to bottom-right)
    detections.sort(key=lambda d: (d["y"], d["x"]))

    print(f"Found {len(detections)} potential units")

    # Create main window
    root = tk.Tk()
    root.title(f"Auto-Label: {Path(screenshot_path).name} - {len(detections)} detections")

    # Get screen dimensions
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    max_height = int(screen_height * 0.85)

    # Main container
    main_frame = tk.Frame(root)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    # LEFT SIDE: Image with detections
    left_frame = tk.Frame(main_frame)
    left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # Create image with detection boxes
    img_display = img.copy()
    colors = [(0, 255, 0), (255, 0, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255)]

    for i, det in enumerate(detections):
        color = colors[i % len(colors)]
        x, y, dw, dh = det["x"], det["y"], det["w"], det["h"]
        cv2.rectangle(img_display, (x, y), (x + dw, y + dh), color, 2)
        # Draw number
        cv2.putText(
            img_display, str(i + 1), (x + 5, y + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2
        )

    # Scale image to fit
    img_scale = min((screen_width * 0.5) / w, (max_height - 100) / h, 1.0)
    display_w = int(w * img_scale)
    display_h = int(h * img_scale)
    img_resized = cv2.resize(img_display, (display_w, display_h))

    # Convert to Tkinter
    img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(img_rgb)
    tk_img = ImageTk.PhotoImage(pil_img)

    img_label = tk.Label(left_frame, image=tk_img)
    img_label.pack()

    # RIGHT SIDE: Detection list
    right_frame = tk.Frame(main_frame, width=400)
    right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(20, 0))
    right_frame.pack_propagate(False)

    # Header
    header = tk.Label(
        right_frame, text=f"Detected Units: {len(detections)}", font=("Arial", 14, "bold")
    )
    header.pack(pady=(0, 10))

    # Instructions
    instr = tk.Label(
        right_frame,
        text="Edit names below. Empty = skip. Then click Save All.",
        font=("Arial", 9),
        fg="gray",
    )
    instr.pack(pady=(0, 10))

    # Scrollable frame for entries
    canvas = tk.Canvas(right_frame, height=max_height - 200)
    scrollbar = ttk.Scrollbar(right_frame, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas)

    scrollable_frame.bind(
        "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    # Mouse wheel scrolling
    def on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    canvas.bind_all("<MouseWheel>", on_mousewheel)

    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    # Create entry fields for each detection
    entries = []

    for i, det in enumerate(detections):
        row_frame = tk.Frame(scrollable_frame)
        row_frame.pack(fill=tk.X, pady=2)

        color = colors[i % len(colors)]
        color_hex = f"#{color[2]:02x}{color[1]:02x}{color[0]:02x}"

        # Number label with color
        num_label = tk.Label(
            row_frame, text=f"{i + 1}.", font=("Arial", 11, "bold"), fg=color_hex, width=3
        )
        num_label.pack(side=tk.LEFT)

        # Confidence
        conf_label = tk.Label(
            row_frame, text=f"{det['conf']:.0%}", font=("Arial", 9), fg="gray", width=5
        )
        conf_label.pack(side=tk.LEFT)

        # Entry field
        entry = tk.Entry(row_frame, font=("Arial", 11), width=20)
        entry.insert(0, det["unit"])
        entry.pack(side=tk.LEFT, padx=5)
        entries.append(entry)

        # Delete button (clears entry)
        del_btn = tk.Button(
            row_frame, text="✕", fg="red", command=lambda e=entry: e.delete(0, tk.END)
        )
        del_btn.pack(side=tk.LEFT)

    # Bottom buttons
    btn_frame = tk.Frame(right_frame)
    btn_frame.pack(pady=20)

    sample_count = [0]

    def save_all():
        """Save all non-empty entries."""
        for i, entry in enumerate(entries):
            unit_name = entry.get().strip().lower()

            if not unit_name:
                continue

            det = detections[i]

            # Apply alias mapping
            UNIT_ALIASES = {"twins1": "twins", "twins2": "twins"}
            unit_name = UNIT_ALIASES.get(unit_name, unit_name)

            # Extract and save the crop
            x, y, dw, dh = det["x"], det["y"], det["w"], det["h"]

            # Add padding
            pad = int(min(dw, dh) * 0.1)
            x1 = max(0, x - pad)
            y1 = max(0, y - pad)
            x2 = min(img.shape[1], x + dw + pad)
            y2 = min(img.shape[0], y + dh + pad)

            crop = img[y1:y2, x1:x2]
            if crop.size == 0:
                continue

            # Resize to standard size
            crop_resized = cv2.resize(crop, (64, 64))

            # Save
            unit_dir = TRAINING_DATA_DIR / unit_name
            unit_dir.mkdir(exist_ok=True)

            sample_num = len(list(unit_dir.glob("*.png"))) + 1
            sample_path = unit_dir / f"auto_{sample_num:04d}.png"
            cv2.imwrite(str(sample_path), crop_resized)
            sample_count[0] += 1

            # Save augmented versions
            augmented = augment_image(crop_resized)
            for j, aug_img in enumerate(augmented[1:5], 1):
                aug_path = unit_dir / f"auto_{sample_num:04d}_aug{j}.png"
                cv2.imwrite(str(aug_path), aug_img)
                sample_count[0] += 1

            print(f"  ✓ Saved: {unit_name}")

        print(f"\n✓ Saved {sample_count[0]} samples total")
        root.destroy()

    def skip_all():
        """Skip this image."""
        print("  ⏭ Skipped")
        root.destroy()

    save_btn = tk.Button(
        btn_frame,
        text="💾 Save All",
        command=save_all,
        bg="#4CAF50",
        fg="white",
        font=("Arial", 12, "bold"),
        padx=20,
        pady=10,
    )
    save_btn.pack(side=tk.LEFT, padx=5)

    skip_btn = tk.Button(
        btn_frame,
        text="⏭ Skip Image",
        command=skip_all,
        bg="#FF9800",
        fg="white",
        font=("Arial", 12, "bold"),
        padx=20,
        pady=10,
    )
    skip_btn.pack(side=tk.LEFT, padx=5)

    # Key bindings
    def on_key(event):
        if event.keysym == "Escape":
            skip_all()
        elif event.keysym == "Return" and event.state & 0x4:  # Ctrl+Enter
            save_all()

    root.bind("<Key>", on_key)

    # Focus first entry
    if entries:
        entries[0].focus()

    root.mainloop()

    return sample_count[0]


def nms_detections(detections: list, iou_threshold: float = 0.3) -> list:
    """Non-maximum suppression for detection dictionaries."""
    if not detections:
        return []

    # Sort by confidence
    detections = sorted(detections, key=lambda d: d["conf"], reverse=True)

    keep = []

    while detections:
        best = detections.pop(0)
        keep.append(best)

        remaining = []
        for det in detections:
            iou = compute_iou_dict(best, det)
            if iou < iou_threshold:
                remaining.append(det)
        detections = remaining

    return keep


def compute_iou_dict(box1: dict, box2: dict) -> float:
    """Compute IoU for detection dictionaries."""
    x1, y1, w1, h1 = box1["x"], box1["y"], box1["w"], box1["h"]
    x2, y2, w2, h2 = box2["x"], box2["y"], box2["w"], box2["h"]

    xi1 = max(x1, x2)
    yi1 = max(y1, y2)
    xi2 = min(x1 + w1, x2 + w2)
    yi2 = min(y1 + h1, y2 + h2)

    if xi2 <= xi1 or yi2 <= yi1:
        return 0.0

    intersection = (xi2 - xi1) * (yi2 - yi1)
    area1 = w1 * h1
    area2 = w2 * h2
    union = area1 + area2 - intersection

    return intersection / union if union > 0 else 0.0


def auto_label_all():
    """Run auto-labeling on all screenshots in training_data/screenshots/."""
    ensure_dirs()
    SCREENSHOTS_DIR.mkdir(exist_ok=True)

    # Find all images
    extensions = ["*.png", "*.jpg", "*.jpeg", "*.webp", "*.bmp"]
    images = []
    for ext in extensions:
        images.extend(SCREENSHOTS_DIR.glob(ext))

    if not images:
        print(f"No images found in {SCREENSHOTS_DIR}")
        return

    images = sorted(images)
    print(f"Found {len(images)} images to auto-label\n")

    total_samples = 0

    for i, img_path in enumerate(images, 1):
        print(f"\n[{i}/{len(images)}] {img_path.name}")
        print("-" * 40)

        samples = auto_label_screenshot(str(img_path))
        total_samples += samples

    print("\n" + "=" * 50)
    print(f"✓ Done! Collected {total_samples} samples total")
    print("=" * 50)


def collect_from_screenshot(screenshot_path: str, bot=None):
    """Interactive tool to collect training samples from a screenshot.

    Click on units to extract and label them.
    Press 'N' or click 'New Screenshot' button to take a new screenshot.

    Args:
        screenshot_path: Path to screenshot image
        bot: Optional bot instance for taking new screenshots
    """
    import tkinter as tk
    from tkinter import messagebox
    from tkinter import simpledialog

    from PIL import Image
    from PIL import ImageTk

    # Load screenshot
    img_container = {"img": cv2.imread(screenshot_path), "path": screenshot_path}
    if img_container["img"] is None:
        print(f"Failed to load: {screenshot_path}")
        return

    # Get list of valid unit names
    valid_units = sorted([d.name for d in TRAINING_DATA_DIR.iterdir() if d.is_dir()])

    # Create window
    root = tk.Tk()
    root.title("Unit Collector - Click on units to label them | Press N for new screenshot")

    # Get screen dimensions for scaling
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    # Reserve space for window decorations, taskbar, and controls
    max_window_width = int(screen_width * 0.9)
    max_window_height = int(screen_height * 0.85)

    # Variables for display
    tk_img_container = [None]
    scale_container = [1.0]
    canvas = None
    sample_count = [0]

    def update_display():
        """Update the canvas with current image."""
        nonlocal canvas

        img = img_container["img"]
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(img_rgb)

        # Scale to fit within screen bounds (accounting for UI elements ~100px)
        available_height = max_window_height - 100
        scale = min(max_window_width / pil_img.width, available_height / pil_img.height, 1.0)

        if scale < 1.0:
            new_size = (int(pil_img.width * scale), int(pil_img.height * scale))
            display_img = pil_img.resize(new_size, Image.Resampling.LANCZOS)
        else:
            display_img = pil_img
            scale = 1.0

        scale_container[0] = scale
        tk_img_container[0] = ImageTk.PhotoImage(display_img)

        if canvas is None:
            canvas = tk.Canvas(root, width=display_img.width, height=display_img.height)
            canvas.pack()
            canvas.bind("<Button-1>", on_click)
        else:
            canvas.config(width=display_img.width, height=display_img.height)
            canvas.delete("all")

        canvas.create_image(0, 0, anchor=tk.NW, image=tk_img_container[0])

    def take_new_screenshot():
        """Take a new screenshot from the device."""
        if bot is None:
            messagebox.showwarning(
                "No Device", "No device connection. Start collector from device."
            )
            return

        print("Taking new screenshot...")
        bot.getScreen()

        if bot.screenRGB is None:
            messagebox.showerror("Error", "Failed to get screenshot from device")
            return

        # Save and update
        temp_path = str(PROJECT_ROOT / "temp_screenshot.png")
        cv2.imwrite(temp_path, bot.screenRGB)
        print(f"New screenshot saved: {temp_path}")

        img_container["img"] = bot.screenRGB.copy()
        img_container["path"] = temp_path
        update_display()
        print("Display updated with new screenshot")

    def skip_image():
        """Skip current image (no units found)."""
        print("  ⏭ Skipped - no units in this image")
        root.destroy()

    def on_key(event):
        """Handle keyboard events."""
        if event.char.lower() == "n":
            take_new_screenshot()
        elif event.char.lower() == "s" or event.keysym == "Escape":
            skip_image()

    def on_click(event):
        # Convert to original image coordinates
        scale = scale_container[0]
        img = img_container["img"]

        orig_x = int(event.x / scale)
        orig_y = int(event.y / scale)

        # Extract 80x80 region around click
        size = 80
        half = size // 2
        x1 = max(0, orig_x - half)
        y1 = max(0, orig_y - half)
        x2 = min(img.shape[1], orig_x + half)
        y2 = min(img.shape[0], orig_y + half)

        crop = img[y1:y2, x1:x2]

        if crop.size == 0:
            return

        # Resize to standard size
        crop_resized = cv2.resize(crop, (64, 64))

        # Show cropped region and ask for label
        crop_display = cv2.cvtColor(crop_resized, cv2.COLOR_BGR2RGB)

        # Ask for unit name
        unit_name = simpledialog.askstring(
            "Label Unit",
            f"Enter unit name (or 'unknown'):\n\nValid units: {', '.join(valid_units[:10])}...",
            initialvalue="",
        )

        if unit_name and unit_name.strip():
            unit_name = unit_name.strip().lower().replace(" ", "_")

            # Check if valid
            unit_dir = TRAINING_DATA_DIR / unit_name
            if not unit_dir.exists():
                if messagebox.askyesno("New Class", f"Create new class '{unit_name}'?"):
                    unit_dir.mkdir(exist_ok=True)
                else:
                    return

            # Save sample
            sample_count[0] += 1
            sample_path = unit_dir / f"sample_{len(list(unit_dir.glob('*.png'))) + 1:04d}.png"
            cv2.imwrite(str(sample_path), crop_resized)
            print(f"Saved: {sample_path}")

            # Draw rectangle on canvas
            canvas.create_rectangle(
                event.x - half * scale,
                event.y - half * scale,
                event.x + half * scale,
                event.y + half * scale,
                outline="green",
                width=2,
            )
            canvas.create_text(event.x, event.y - half * scale - 10, text=unit_name, fill="green")

    # Button frame
    btn_frame = tk.Frame(root)
    btn_frame.pack(pady=5)

    # Skip button (no units)
    skip_btn = tk.Button(
        btn_frame,
        text="⏭ Skip / No Units (S)",
        command=skip_image,
        bg="#FF9800",
        fg="white",
        font=("Arial", 10, "bold"),
        padx=10,
        pady=5,
    )
    skip_btn.pack(side=tk.LEFT, padx=5)

    # New Screenshot button
    if bot is not None:
        new_ss_btn = tk.Button(
            btn_frame,
            text="📷 New Screenshot (N)",
            command=take_new_screenshot,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=10,
            pady=5,
        )
        new_ss_btn.pack(side=tk.LEFT, padx=5)

    # Instructions
    info = tk.Label(
        root,
        text="Click on units to label them. Press S/ESC to skip. Press N for new screenshot.",
        font=("Arial", 9),
    )
    info.pack(pady=5)

    # Bind keyboard
    root.bind("<Key>", on_key)

    # Initial display
    update_display()

    root.mainloop()
    print(f"\nCollected {sample_count[0]} samples")


def collect_from_device():
    """Collect training samples directly from connected device."""
    try:
        import bot_core
        import port_scan
    except ImportError:
        print("Could not import bot modules. Run from project root.")
        return

    print("Connecting to device...")
    device = port_scan.get_device(force_scan=False)

    if not device:
        print("No device found!")
        return

    print(f"Connected to: {device}")

    bot = bot_core.Bot(device=device)
    bot.getScreen()

    if bot.screenRGB is None:
        print("Failed to get screenshot")
        return

    # Save screenshot temporarily
    temp_path = str(PROJECT_ROOT / "temp_screenshot.png")
    cv2.imwrite(temp_path, bot.screenRGB)
    print(f"Screenshot saved: {temp_path}")

    # Run collector with bot for new screenshots
    print("\n📷 Tip: Press 'N' or click 'New Screenshot' to take a new screenshot anytime!")
    collect_from_screenshot(temp_path, bot=bot)


def augment_image(img: np.ndarray) -> list[np.ndarray]:
    """Create augmented versions of an image."""
    augmented = [img]

    # Brightness variations
    for factor in [0.8, 0.9, 1.1, 1.2]:
        adjusted = np.clip(img * factor, 0, 255).astype(np.uint8)
        augmented.append(adjusted)

    # Slight rotations
    h, w = img.shape[:2]
    center = (w // 2, h // 2)
    for angle in [-5, 5, -10, 10]:
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(img, M, (w, h))
        augmented.append(rotated)

    # Horizontal flip (some units are symmetric)
    augmented.append(cv2.flip(img, 1))

    # Slight blur
    augmented.append(cv2.GaussianBlur(img, (3, 3), 0))

    return augmented


def prepare_training_data(
    augment: bool = True,
) -> tuple[np.ndarray, np.ndarray, dict]:
    """Load and prepare training data.

    Returns:
        X: Feature array (N, features)
        y: Label array (N,)
        label_map: Dict mapping label index to unit name
    """
    X_list = []
    y_list = []
    label_map = {}

    # Get all unit directories
    unit_dirs = [d for d in TRAINING_DATA_DIR.iterdir() if d.is_dir()]

    for label_idx, unit_dir in enumerate(sorted(unit_dirs)):
        unit_name = unit_dir.name
        label_map[label_idx] = unit_name

        samples = list(unit_dir.glob("*.png"))
        print(f"Loading {len(samples)} samples for '{unit_name}'")

        for sample_path in samples:
            img = cv2.imread(str(sample_path))
            if img is None:
                continue

            # Resize to standard size
            img = cv2.resize(img, (64, 64))

            # Get samples (with augmentation if enabled)
            if augment and unit_name != "unknown":
                images = augment_image(img)
            else:
                images = [img]

            for aug_img in images:
                # Extract features (flatten or use HOG)
                features = extract_features(aug_img)
                X_list.append(features)
                y_list.append(label_idx)

    X = np.array(X_list)
    y = np.array(y_list)

    print(f"\nTotal samples: {len(X)}")
    print(f"Classes: {len(label_map)}")

    return X, y, label_map


def extract_features(img: np.ndarray) -> np.ndarray:
    """Extract features from an image for classification."""
    # Resize to consistent size
    img = cv2.resize(img, (64, 64))

    # Convert to HSV for color features
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # Color histogram
    h_hist = cv2.calcHist([hsv], [0], None, [16], [0, 180]).flatten()
    s_hist = cv2.calcHist([hsv], [1], None, [8], [0, 256]).flatten()
    v_hist = cv2.calcHist([hsv], [2], None, [8], [0, 256]).flatten()

    # Normalize histograms
    h_hist = h_hist / (h_hist.sum() + 1e-7)
    s_hist = s_hist / (s_hist.sum() + 1e-7)
    v_hist = v_hist / (v_hist.sum() + 1e-7)

    # Edge features using HOG-like descriptor
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Compute gradients
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    mag, angle = cv2.cartToPolar(gx, gy)

    # Quantize angles into bins
    n_bins = 9
    angle_bins = (angle * n_bins / (2 * np.pi)).astype(np.int32) % n_bins

    # HOG for 4x4 cells
    cell_size = 16
    hog_features = []
    for i in range(0, 64, cell_size):
        for j in range(0, 64, cell_size):
            cell_mag = mag[i : i + cell_size, j : j + cell_size]
            cell_ang = angle_bins[i : i + cell_size, j : j + cell_size]
            hist = np.bincount(cell_ang.flatten(), weights=cell_mag.flatten(), minlength=n_bins)
            hog_features.extend(hist / (hist.sum() + 1e-7))

    # Combine all features
    features = np.concatenate([h_hist, s_hist, v_hist, hog_features])

    return features


def train_model():
    """Train the unit classifier model."""
    import joblib
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import accuracy_score
    from sklearn.metrics import classification_report
    from sklearn.model_selection import train_test_split

    print("Preparing training data...")
    X, y, label_map = prepare_training_data(augment=True)

    if len(X) == 0:
        print("No training data found! Collect samples first.")
        return

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print(f"\nTraining set: {len(X_train)} samples")
    print(f"Test set: {len(X_test)} samples")

    # Train Random Forest classifier
    print("\nTraining Random Forest classifier...")
    clf = RandomForestClassifier(
        n_estimators=200,
        max_depth=20,
        min_samples_split=5,
        n_jobs=-1,
        random_state=42,
    )
    clf.fit(X_train, y_train)

    # Evaluate
    y_pred = clf.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)

    print(f"\nAccuracy: {accuracy:.2%}")
    print("\nClassification Report:")

    # Convert labels to names for report - only include labels present in test set
    unique_labels = sorted(set(y_test) | set(y_pred))
    target_names = [label_map[i] for i in unique_labels]
    print(classification_report(y_test, y_pred, labels=unique_labels, target_names=target_names))

    # Save model and labels
    print(f"\nSaving model to {MODEL_PATH}")
    joblib.dump(clf, MODEL_PATH)

    print(f"Saving labels to {LABELS_PATH}")
    with open(LABELS_PATH, "w") as f:
        json.dump(label_map, f, indent=2)

    print("\nTraining complete!")


def predict_unit(img: np.ndarray) -> tuple[str, float]:
    """Predict unit from an image.

    Args:
        img: BGR image of a unit (any size)

    Returns:
        Tuple of (unit_name, confidence)
    """
    import joblib

    if not MODEL_PATH.exists():
        return "unknown", 0.0

    # Load model and labels
    clf = joblib.load(MODEL_PATH)
    with open(LABELS_PATH) as f:
        label_map = {int(k): v for k, v in json.load(f).items()}

    # Extract features
    features = extract_features(img).reshape(1, -1)

    # Predict with probability
    proba = clf.predict_proba(features)[0]
    pred_idx = np.argmax(proba)
    confidence = proba[pred_idx]

    unit_name = label_map.get(pred_idx, "unknown")

    return unit_name, float(confidence)


def test_on_screenshot(screenshot_path: str):
    """Test the model on a screenshot."""
    img = cv2.imread(screenshot_path)
    if img is None:
        print(f"Failed to load: {screenshot_path}")
        return

    print(f"Screenshot size: {img.shape}")

    # Import deck detection module
    sys.path.insert(0, str(PROJECT_ROOT / "Src"))
    import detect_deck

    # Get slot positions
    slots_to_try = detect_deck.get_slot_positions(img.shape)

    print("\nDetecting units with ML model:\n")

    for slot_idx in range(5):
        best_unit = "unknown"
        best_conf = 0.0

        for slots in slots_to_try:
            if slot_idx >= len(slots):
                continue
            x, y, w, h = slots[slot_idx]

            if y + h > img.shape[0] or x + w > img.shape[1]:
                continue
            if y < 0 or x < 0:
                continue

            slot_img = img[y : y + h, x : x + w]
            if slot_img.size == 0:
                continue

            unit, conf = predict_unit(slot_img)
            if conf > best_conf:
                best_unit = unit
                best_conf = conf

        print(f"  Slot {slot_idx + 1}: {best_unit:20s} ({best_conf:.1%})")


def scan_for_units(screenshot_path: str, confidence_threshold: float = 0.7):
    """Scan entire image for units using sliding window approach.

    This finds units anywhere in the image, regardless of position.

    Args:
        screenshot_path: Path to the image
        confidence_threshold: Minimum confidence to report a detection
    """
    import joblib

    img = cv2.imread(screenshot_path)
    if img is None:
        print(f"Failed to load: {screenshot_path}")
        return

    print(f"Image size: {img.shape[1]}x{img.shape[0]}")
    print(f"Confidence threshold: {confidence_threshold:.0%}")

    if not MODEL_PATH.exists():
        print("Model not found! Run 'train' first.")
        return

    # Load model and labels
    clf = joblib.load(MODEL_PATH)
    with open(LABELS_PATH) as f:
        label_map = {int(k): v for k, v in json.load(f).items()}

    h, w = img.shape[:2]

    # Sliding window parameters - try multiple scales
    window_sizes = [64, 80, 96, 112, 128]
    step_ratio = 0.25  # 25% overlap

    detections = []  # (x, y, w, h, unit_name, confidence)

    print("\nScanning image for units...")

    for win_size in window_sizes:
        step = int(win_size * step_ratio)

        for y in range(0, h - win_size, step):
            for x in range(0, w - win_size, step):
                # Extract window
                window = img[y : y + win_size, x : x + win_size]

                # Extract features
                features = extract_features(window).reshape(1, -1)

                # Predict
                proba = clf.predict_proba(features)[0]
                pred_idx = np.argmax(proba)
                confidence = proba[pred_idx]

                unit_name = label_map.get(pred_idx, "unknown")

                # Skip unknown and low confidence
                if unit_name == "unknown" or confidence < confidence_threshold:
                    continue

                detections.append((x, y, win_size, win_size, unit_name, confidence))

    if not detections:
        print(f"\nNo units found with confidence >= {confidence_threshold:.0%}")
        print("Try lowering threshold: scan <image> 0.5")
        return

    # Non-maximum suppression to remove overlapping detections
    detections = non_max_suppression(detections)

    print(f"\n✓ Found {len(detections)} units:\n")

    # Sort by position (top-left to bottom-right)
    detections.sort(key=lambda d: (d[1], d[0]))

    for i, (x, y, ww, hh, unit_name, conf) in enumerate(detections, 1):
        print(f"  {i}. {unit_name:20s} ({conf:.1%}) at ({x}, {y})")

    # Visualize detections
    visualize_detections(img, detections, screenshot_path)


def non_max_suppression(detections: list, iou_threshold: float = 0.3) -> list:
    """Remove overlapping detections, keeping highest confidence ones."""
    if not detections:
        return []

    # Sort by confidence (descending)
    detections = sorted(detections, key=lambda d: d[5], reverse=True)

    keep = []

    while detections:
        best = detections.pop(0)
        keep.append(best)

        # Remove overlapping detections
        remaining = []
        for det in detections:
            if compute_iou(best, det) < iou_threshold:
                remaining.append(det)
        detections = remaining

    return keep


def compute_iou(box1: tuple, box2: tuple) -> float:
    """Compute Intersection over Union between two boxes."""
    x1, y1, w1, h1 = box1[:4]
    x2, y2, w2, h2 = box2[:4]

    # Calculate intersection
    xi1 = max(x1, x2)
    yi1 = max(y1, y2)
    xi2 = min(x1 + w1, x2 + w2)
    yi2 = min(y1 + h1, y2 + h2)

    if xi2 <= xi1 or yi2 <= yi1:
        return 0.0

    intersection = (xi2 - xi1) * (yi2 - yi1)

    # Calculate union
    area1 = w1 * h1
    area2 = w2 * h2
    union = area1 + area2 - intersection

    return intersection / union if union > 0 else 0.0


def visualize_detections(img: np.ndarray, detections: list, save_path: str):
    """Draw detection boxes on image and save/show."""
    result = img.copy()

    # Colors for different units (cycle through)
    colors = [
        (0, 255, 0),  # Green
        (255, 0, 0),  # Blue
        (0, 0, 255),  # Red
        (255, 255, 0),  # Cyan
        (255, 0, 255),  # Magenta
        (0, 255, 255),  # Yellow
    ]

    for i, (x, y, w, h, unit_name, conf) in enumerate(detections):
        color = colors[i % len(colors)]

        # Draw rectangle
        cv2.rectangle(result, (x, y), (x + w, y + h), color, 2)

        # Draw label
        label = f"{unit_name} {conf:.0%}"
        label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
        cv2.rectangle(result, (x, y - 20), (x + label_size[0], y), color, -1)
        cv2.putText(
            result,
            label,
            (x, y - 5),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            2,
        )

    # Save result
    output_path = str(Path(save_path).stem) + "_detected.png"
    cv2.imwrite(output_path, result)
    print(f"\n✓ Saved visualization: {output_path}")

    # Try to show
    try:
        import subprocess

        subprocess.Popen(["start", "", output_path], shell=True)
    except:
        pass


def collect_all_screenshots():
    """Collect samples from all screenshots in training_data/screenshots/.

    Put your Reddit images, screenshots, etc. in training_data/screenshots/
    and run this to label them all.
    """
    ensure_dirs()
    SCREENSHOTS_DIR.mkdir(exist_ok=True)

    # Find all images
    extensions = ["*.png", "*.jpg", "*.jpeg", "*.webp", "*.bmp"]
    images = []
    for ext in extensions:
        images.extend(SCREENSHOTS_DIR.glob(ext))

    if not images:
        print(f"No images found in {SCREENSHOTS_DIR}")
        print("\nSupported formats: PNG, JPG, JPEG, WEBP, BMP")
        print("\nPut your Reddit screenshots there and run again!")
        return

    images = sorted(images)
    print(f"Found {len(images)} images to label:\n")
    for i, img in enumerate(images, 1):
        print(f"  {i}. {img.name}")

    print("\n" + "=" * 50)
    print("Starting labeling session...")
    print("Press ESC or close window to skip to next image")
    print("=" * 50 + "\n")

    total_samples = 0
    for i, img_path in enumerate(images, 1):
        print(f"\n[{i}/{len(images)}] {img_path.name}")
        print("-" * 40)

        # Check if image is valid
        img = cv2.imread(str(img_path))
        if img is None:
            print("  ⚠ Could not read image, skipping...")
            continue

        print(f"  Size: {img.shape[1]}x{img.shape[0]}")

        # Run collector
        try:
            collect_from_screenshot(str(img_path))
        except Exception as e:
            print(f"  ⚠ Error: {e}")
            continue

    # Count total samples
    total = sum(len(list(d.glob("*.png"))) for d in TRAINING_DATA_DIR.iterdir() if d.is_dir())
    print("\n" + "=" * 50)
    print(f"✓ Done! Total training samples: {total}")
    print("=" * 50)


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nCommands:")
        print("  auto-label        - Auto-label all screenshots (recommended!)")
        print("  auto-label <img>  - Auto-label single image")
        print("  collect           - Manual collect from connected device")
        print("  collect <img>     - Manual collect from a screenshot")
        print("  collect-all       - Manual label all screenshots")
        print("  import            - Import cv-images/all_units as training samples")
        print("  train             - Train the classifier model")
        print("  test <img>        - Test model on fixed slot positions")
        print("  scan <img>        - Scan entire image for units (slow)")
        print("  init              - Initialize training directories")
        return

    cmd = sys.argv[1].lower()

    if cmd == "init":
        ensure_dirs()

    elif cmd == "import":
        import_all_units_as_samples()

    elif cmd == "auto-label":
        ensure_dirs()
        if len(sys.argv) > 2:
            auto_label_screenshot(sys.argv[2])
        else:
            auto_label_all()

    elif cmd == "collect-all":
        collect_all_screenshots()

    elif cmd == "collect":
        ensure_dirs()
        if len(sys.argv) > 2:
            collect_from_screenshot(sys.argv[2])
        else:
            collect_from_device()

    elif cmd == "train":
        train_model()

    elif cmd == "test":
        if len(sys.argv) < 3:
            print("Usage: train_unit_classifier.py test <screenshot.png>")
            return
        test_on_screenshot(sys.argv[2])

    elif cmd == "scan":
        if len(sys.argv) < 3:
            print("Usage: train_unit_classifier.py scan <screenshot.png> [threshold]")
            return
        threshold = float(sys.argv[3]) if len(sys.argv) > 3 else 0.7
        scan_for_units(sys.argv[2], threshold)

    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
