#!/usr/bin/env python
"""
Auto-Detect Templates - Automatically detect and extract UI elements from screenshots.

Uses edge detection, contour analysis, and color segmentation to find
clickable UI elements like buttons, icons, and text.

Usage:
    python scripts/auto_detect_templates.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import numpy as np
from pathlib import Path
from datetime import datetime
import shutil
from dataclasses import dataclass
from typing import List, Tuple, Optional


@dataclass
class DetectedElement:
    """A detected UI element."""
    x: int
    y: int
    width: int
    height: int
    confidence: float
    element_type: str  # 'button', 'icon', 'text', 'banner'
    suggested_name: str = ""
    
    @property
    def center(self) -> Tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)
    
    @property 
    def area(self) -> int:
        return self.width * self.height
    
    def crop_from(self, image: np.ndarray, padding: int = 2) -> np.ndarray:
        """Extract this element from an image."""
        h, w = image.shape[:2]
        x1 = max(0, self.x - padding)
        y1 = max(0, self.y - padding)
        x2 = min(w, self.x + self.width + padding)
        y2 = min(h, self.y + self.height + padding)
        return image[y1:y2, x1:x2]


class UIElementDetector:
    """Automatic UI element detection."""
    
    # Size constraints for different element types
    ELEMENT_SIZES = {
        'icon': {'min_w': 40, 'max_w': 120, 'min_h': 40, 'max_h': 120, 'aspect': (0.7, 1.4)},
        'button': {'min_w': 80, 'max_w': 400, 'min_h': 40, 'max_h': 150, 'aspect': (1.5, 6.0)},
        'banner': {'min_w': 200, 'max_w': 500, 'min_h': 60, 'max_h': 150, 'aspect': (2.0, 8.0)},
        'text': {'min_w': 50, 'max_w': 300, 'min_h': 20, 'max_h': 60, 'aspect': (2.0, 15.0)},
    }
    
    # Screen regions for naming suggestions
    REGIONS = {
        'top': (0, 0, 1.0, 0.15),      # Top 15%
        'bottom': (0, 0.85, 1.0, 1.0),  # Bottom 15%
        'center': (0.2, 0.3, 0.8, 0.7), # Center area
        'left': (0, 0, 0.3, 1.0),       # Left 30%
        'right': (0.7, 0, 1.0, 1.0),    # Right 30%
    }
    
    def __init__(self):
        self.elements: List[DetectedElement] = []
    
    def detect(self, image: np.ndarray) -> List[DetectedElement]:
        """Detect all UI elements in image."""
        self.elements = []
        h, w = image.shape[:2]
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Method 1: Edge-based detection
        self._detect_by_edges(image, gray)
        
        # Method 2: Color-based detection (bright/saturated regions)
        self._detect_by_color(image)
        
        # Method 3: Text region detection
        self._detect_text_regions(gray)
        
        # Remove duplicates and overlapping
        self._remove_duplicates()
        
        # Assign suggested names based on position and type
        self._assign_names(w, h)
        
        # Sort by position (top to bottom, left to right)
        self.elements.sort(key=lambda e: (e.y // 100, e.x))
        
        return self.elements
    
    def _detect_by_edges(self, image: np.ndarray, gray: np.ndarray):
        """Detect elements using edge detection."""
        # Canny edge detection
        edges = cv2.Canny(gray, 50, 150)
        
        # Dilate to connect nearby edges
        kernel = np.ones((3, 3), np.uint8)
        edges = cv2.dilate(edges, kernel, iterations=2)
        
        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            
            # Skip very small or very large
            if w < 30 or h < 20 or w > 600 or h > 300:
                continue
            
            # Classify by aspect ratio and size
            aspect = w / max(h, 1)
            elem_type = self._classify_element(w, h, aspect)
            
            if elem_type:
                # Calculate confidence based on contour properties
                area = cv2.contourArea(contour)
                rect_area = w * h
                fill_ratio = area / max(rect_area, 1)
                confidence = min(fill_ratio * 1.5, 1.0)
                
                self.elements.append(DetectedElement(
                    x=x, y=y, width=w, height=h,
                    confidence=confidence,
                    element_type=elem_type
                ))
    
    def _detect_by_color(self, image: np.ndarray):
        """Detect colorful UI elements (buttons are often bright/saturated)."""
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Detect bright, saturated regions (typical for buttons)
        # High saturation and value
        mask = cv2.inRange(hsv, (0, 80, 150), (180, 255, 255))
        
        # Clean up mask
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            
            if w < 40 or h < 30 or w > 500 or h > 200:
                continue
            
            aspect = w / max(h, 1)
            elem_type = self._classify_element(w, h, aspect)
            
            if elem_type:
                self.elements.append(DetectedElement(
                    x=x, y=y, width=w, height=h,
                    confidence=0.7,
                    element_type=elem_type
                ))
    
    def _detect_text_regions(self, gray: np.ndarray):
        """Detect text-like regions using MSER or gradient."""
        # Use gradient to find text regions
        grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        gradient = cv2.magnitude(grad_x, grad_y)
        gradient = np.uint8(gradient / gradient.max() * 255)
        
        # Threshold
        _, binary = cv2.threshold(gradient, 30, 255, cv2.THRESH_BINARY)
        
        # Horizontal dilation to connect text
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 3))
        dilated = cv2.dilate(binary, kernel, iterations=2)
        
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            
            # Text is typically wide and short
            aspect = w / max(h, 1)
            if w > 60 and h > 15 and h < 80 and aspect > 2:
                self.elements.append(DetectedElement(
                    x=x, y=y, width=w, height=h,
                    confidence=0.5,
                    element_type='text'
                ))
    
    def _classify_element(self, w: int, h: int, aspect: float) -> Optional[str]:
        """Classify element type based on dimensions."""
        for elem_type, constraints in self.ELEMENT_SIZES.items():
            if (constraints['min_w'] <= w <= constraints['max_w'] and
                constraints['min_h'] <= h <= constraints['max_h'] and
                constraints['aspect'][0] <= aspect <= constraints['aspect'][1]):
                return elem_type
        return None
    
    def _remove_duplicates(self):
        """Remove overlapping elements, keeping highest confidence."""
        if not self.elements:
            return
        
        # Sort by confidence (descending)
        self.elements.sort(key=lambda e: -e.confidence)
        
        filtered = []
        for elem in self.elements:
            # Check overlap with already accepted elements
            overlaps = False
            for accepted in filtered:
                # Calculate IoU
                x1 = max(elem.x, accepted.x)
                y1 = max(elem.y, accepted.y)
                x2 = min(elem.x + elem.width, accepted.x + accepted.width)
                y2 = min(elem.y + elem.height, accepted.y + accepted.height)
                
                if x1 < x2 and y1 < y2:
                    intersection = (x2 - x1) * (y2 - y1)
                    union = elem.area + accepted.area - intersection
                    iou = intersection / max(union, 1)
                    
                    if iou > 0.3:  # 30% overlap threshold
                        overlaps = True
                        break
            
            if not overlaps:
                filtered.append(elem)
        
        self.elements = filtered
    
    def _assign_names(self, img_w: int, img_h: int):
        """Assign suggested names based on position and type."""
        type_counts = {}
        
        for elem in self.elements:
            # Determine region
            cx, cy = elem.center
            rx, ry = cx / img_w, cy / img_h
            
            region = "center"
            if ry < 0.15:
                region = "top"
            elif ry > 0.85:
                region = "bottom"
            elif rx < 0.3:
                region = "left"
            elif rx > 0.7:
                region = "right"
            
            # Generate name
            key = f"{elem.element_type}_{region}"
            type_counts[key] = type_counts.get(key, 0) + 1
            count = type_counts[key]
            
            elem.suggested_name = f"{elem.element_type}_{region}_{count}.png"


class AutoTemplateExtractor:
    """Interactive auto-detection and extraction."""
    
    def __init__(self):
        self.screenshots_dir = Path("screenshots")
        self.icons_dir = Path("icons")
        self.backup_dir = None
        self.screenshots = []
        self.current_idx = 0
        self.captured = []
        self.detector = UIElementDetector()
        
    def load_screenshots(self):
        """Load screenshots."""
        self.screenshots = sorted(
            self.screenshots_dir.glob("*.png"),
            key=lambda p: p.stat().st_mtime
        )
        return len(self.screenshots) > 0
    
    def backup_existing(self):
        """Backup existing templates."""
        if self.icons_dir.exists() and any(self.icons_dir.glob("*.png")):
            self.backup_dir = Path("icons_backup_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
            shutil.copytree(self.icons_dir, self.backup_dir)
            print(f"📦 Backup: {self.backup_dir}")
    
    def run(self):
        """Run interactive extraction."""
        print("\n" + "="*60)
        print("🔍 AUTO-ERKENNUNG VON UI-ELEMENTEN")
        print("="*60)
        
        if not self.load_screenshots():
            print("❌ Keine Screenshots in screenshots/")
            return
        
        print(f"✓ {len(self.screenshots)} Screenshots gefunden")
        self.backup_existing()
        
        print("\n" + "-"*60)
        print("STEUERUNG:")
        print("  [Linksklick]   = Element auswählen/speichern")
        print("  [Rechtsklick]  = Element ignorieren")
        print("  [A/D oder ←/→] = Screenshot wechseln")
        print("  [R]            = Neu erkennen")
        print("  [ESC]          = Beenden")
        print("-"*60)
        
        input("\nDrücke ENTER zum Starten...")
        
        window = "Auto-Erkennung"
        cv2.namedWindow(window, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window, 506, 900)
        
        current_elements = []
        selected_idx = -1
        
        def on_mouse(event, x, y, flags, param):
            nonlocal selected_idx
            if event == cv2.EVENT_LBUTTONDOWN:
                # Find clicked element
                for i, elem in enumerate(current_elements):
                    ex, ey = int(elem.x * scale), int(elem.y * scale)
                    ew, eh = int(elem.width * scale), int(elem.height * scale)
                    if ex <= x <= ex + ew and ey <= y <= ey + eh:
                        selected_idx = i
                        break
        
        cv2.setMouseCallback(window, on_mouse)
        
        while True:
            # Load current screenshot
            path = self.screenshots[self.current_idx]
            image = cv2.imread(str(path))
            if image is None:
                self.current_idx = (self.current_idx + 1) % len(self.screenshots)
                continue
            
            h, w = image.shape[:2]
            scale = min(506/w, 900/h)
            display_w, display_h = int(w * scale), int(h * scale)
            
            # Detect elements
            current_elements = self.detector.detect(image)
            
            print(f"\n📸 {path.name} - {len(current_elements)} Elemente erkannt")
            
            selected_idx = -1
            
            while True:
                # Draw
                display = cv2.resize(image.copy(), (display_w, display_h))
                
                # Draw all detected elements
                for i, elem in enumerate(current_elements):
                    ex, ey = int(elem.x * scale), int(elem.y * scale)
                    ew, eh = int(elem.width * scale), int(elem.height * scale)
                    
                    # Color by type
                    colors = {
                        'icon': (0, 255, 0),      # Green
                        'button': (255, 165, 0),  # Orange
                        'banner': (255, 0, 255),  # Magenta
                        'text': (0, 255, 255),    # Cyan
                    }
                    color = colors.get(elem.element_type, (255, 255, 255))
                    
                    # Highlight selected
                    thickness = 3 if i == selected_idx else 1
                    cv2.rectangle(display, (ex, ey), (ex + ew, ey + eh), color, thickness)
                    
                    # Label
                    label = f"{i+1}"
                    cv2.putText(display, label, (ex, ey - 3),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
                
                # Info overlay
                cv2.rectangle(display, (5, 5), (500, 50), (0, 0, 0), -1)
                cv2.putText(display, f"Screenshot {self.current_idx+1}/{len(self.screenshots)}: {len(current_elements)} Elemente",
                           (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                cv2.putText(display, "Klick=Speichern | A/D=Wechseln | R=Neu erkennen | ESC=Ende",
                           (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
                
                # Legend
                cv2.rectangle(display, (5, display_h - 60), (150, display_h - 5), (0, 0, 0), -1)
                cv2.putText(display, "Icon", (10, display_h - 45), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
                cv2.putText(display, "Button", (60, display_h - 45), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 165, 0), 1)
                cv2.putText(display, "Banner", (10, display_h - 25), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 255), 1)
                cv2.putText(display, "Text", (70, display_h - 25), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
                
                cv2.imshow(window, display)
                key = cv2.waitKey(30) & 0xFF
                
                # Handle selection
                if selected_idx >= 0:
                    elem = current_elements[selected_idx]
                    
                    # Ask for name
                    default_name = elem.suggested_name
                    print(f"\n   Element {selected_idx+1}: {elem.element_type} ({elem.width}x{elem.height})")
                    print(f"   Vorschlag: {default_name}")
                    name = input(f"   Name eingeben (ENTER für Vorschlag, 's' zum Überspringen): ").strip()
                    
                    if name.lower() == 's':
                        print("   ⏭️ Übersprungen")
                    else:
                        if not name:
                            name = default_name
                        if not name.endswith('.png'):
                            name += '.png'
                        
                        # Save
                        template = elem.crop_from(image, padding=2)
                        save_path = self.icons_dir / name
                        cv2.imwrite(str(save_path), template)
                        self.captured.append(name)
                        print(f"   ✓ Gespeichert: {name} ({template.shape[1]}x{template.shape[0]})")
                    
                    selected_idx = -1
                
                if key == 27:  # ESC
                    cv2.destroyAllWindows()
                    self._print_summary()
                    return
                
                elif key == ord('a') or key == ord('A') or key == 81:
                    self.current_idx = (self.current_idx - 1) % len(self.screenshots)
                    break
                
                elif key == ord('d') or key == ord('D') or key == 83:
                    self.current_idx = (self.current_idx + 1) % len(self.screenshots)
                    break
                
                elif key == ord('r') or key == ord('R'):
                    # Re-detect
                    break
        
        cv2.destroyAllWindows()
        self._print_summary()
    
    def _print_summary(self):
        """Print summary."""
        print("\n" + "="*60)
        print("📊 ZUSAMMENFASSUNG")
        print("="*60)
        print(f"\n✓ Gespeichert: {len(self.captured)} Templates")
        
        if self.captured:
            for name in sorted(self.captured):
                path = self.icons_dir / name
                if path.exists():
                    img = cv2.imread(str(path))
                    if img is not None:
                        print(f"   {name}: {img.shape[1]}x{img.shape[0]}")
        
        if self.backup_dir:
            print(f"\n📦 Backup: {self.backup_dir}")
        print("\n💡 Teste mit: python scripts/debug_dungeon_detection.py")


def main():
    extractor = AutoTemplateExtractor()
    extractor.run()


if __name__ == "__main__":
    main()
