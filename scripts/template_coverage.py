#!/usr/bin/env python
"""
Template Coverage Analyzer - Detects missing or outdated templates.

This module:
1. Analyzes screenshots to find unrecognized UI elements
2. Compares against existing templates
3. Suggests new templates to capture
4. Tracks template quality over time

Usage:
    python scripts/template_coverage.py
    
Or import in code:
    from scripts.template_coverage import TemplateCoverageAnalyzer
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import numpy as np
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
import json
import hashlib


@dataclass
class UIElement:
    """Detected UI element."""
    x: int
    y: int
    width: int
    height: int
    confidence: float = 0.0
    matched_template: Optional[str] = None
    element_type: str = "unknown"  # button, icon, text, panel
    
    @property
    def center(self) -> Tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)
    
    @property
    def area(self) -> int:
        return self.width * self.height
    
    def to_dict(self) -> dict:
        return {
            'x': self.x, 'y': self.y,
            'width': self.width, 'height': self.height,
            'confidence': self.confidence,
            'matched_template': self.matched_template,
            'element_type': self.element_type
        }


@dataclass 
class CoverageReport:
    """Template coverage analysis report."""
    timestamp: str
    screen_hash: str
    total_elements: int = 0
    matched_elements: int = 0
    unmatched_elements: int = 0
    weak_matches: int = 0  # Matches below threshold but close
    coverage_percent: float = 0.0
    matched: List[UIElement] = field(default_factory=list)
    unmatched: List[UIElement] = field(default_factory=list)
    weak: List[UIElement] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            'timestamp': self.timestamp,
            'screen_hash': self.screen_hash,
            'total_elements': self.total_elements,
            'matched_elements': self.matched_elements,
            'unmatched_elements': self.unmatched_elements,
            'weak_matches': self.weak_matches,
            'coverage_percent': self.coverage_percent,
            'matched': [e.to_dict() for e in self.matched],
            'unmatched': [e.to_dict() for e in self.unmatched],
            'weak': [e.to_dict() for e in self.weak],
            'suggestions': self.suggestions
        }


class TemplateCoverageAnalyzer:
    """Analyzes template coverage and detects missing UI elements."""
    
    # Known UI regions by screen type
    EXPECTED_REGIONS = {
        'home': {
            'bottom_nav': (0, 750, 900, 150),      # Bottom navigation bar
            'top_bar': (0, 0, 900, 100),           # Top status bar
            'center_buttons': (200, 200, 500, 400), # Main action area
        },
        'dungeon': {
            'header': (300, 0, 300, 100),          # Screen title
            'chapter_list': (50, 150, 800, 600),   # Chapter scroll area
            'back_button': (0, 0, 100, 100),       # Back navigation
        },
        'battle': {
            'grid': (50, 400, 800, 500),           # Unit placement grid
            'cards': (50, 920, 800, 180),          # Card selection
            'mana': (750, 350, 150, 50),           # Mana display
        }
    }
    
    # Minimum sizes for valid UI elements
    MIN_BUTTON_SIZE = (30, 30)
    MAX_BUTTON_SIZE = (400, 200)
    
    def __init__(self, icons_dir: str = "icons"):
        self.icons_dir = Path(icons_dir)
        self.templates = {}
        self.coverage_history = []
        self.history_file = Path("screenshots/coverage_history.json")
        
        self._load_templates()
        self._load_history()
    
    def _load_templates(self):
        """Load all existing templates."""
        self.templates = {}
        if not self.icons_dir.exists():
            return
        
        for template_path in self.icons_dir.glob("*.png"):
            template = cv2.imread(str(template_path), 0)
            if template is not None:
                self.templates[template_path.name] = {
                    'image': template,
                    'size': (template.shape[1], template.shape[0]),
                    'blurred': cv2.GaussianBlur(template, (3, 3), 0)
                }
    
    def _load_history(self):
        """Load coverage history."""
        if self.history_file.exists():
            try:
                with open(self.history_file) as f:
                    self.coverage_history = json.load(f)
            except:
                self.coverage_history = []
    
    def _save_history(self):
        """Save coverage history."""
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        # Keep last 100 entries
        history = self.coverage_history[-100:]
        with open(self.history_file, 'w') as f:
            json.dump(history, f, indent=2)
    
    def _compute_screen_hash(self, screenshot: np.ndarray) -> str:
        """Compute a hash to identify similar screens."""
        # Resize to small size for hashing
        small = cv2.resize(screenshot, (32, 32))
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY) if len(small.shape) == 3 else small
        return hashlib.md5(gray.tobytes()).hexdigest()[:12]
    
    def detect_ui_elements(self, screenshot: np.ndarray) -> List[UIElement]:
        """Detect potential UI elements using multiple methods."""
        elements = []
        
        gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY) if len(screenshot.shape) == 3 else screenshot
        
        # Method 1: Edge detection + contours
        edges = cv2.Canny(gray, 50, 150)
        kernel = np.ones((3, 3), np.uint8)
        edges = cv2.dilate(edges, kernel, iterations=1)
        
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            
            # Filter by size
            if (self.MIN_BUTTON_SIZE[0] <= w <= self.MAX_BUTTON_SIZE[0] and
                self.MIN_BUTTON_SIZE[1] <= h <= self.MAX_BUTTON_SIZE[1]):
                
                # Classify element type based on shape
                aspect = w / max(h, 1)
                if 0.8 <= aspect <= 1.2:
                    elem_type = "icon"
                elif aspect > 2:
                    elem_type = "text" if h < 50 else "button"
                else:
                    elem_type = "button"
                
                elements.append(UIElement(
                    x=x, y=y, width=w, height=h,
                    element_type=elem_type
                ))
        
        # Method 2: Color-based detection (bright buttons)
        hsv = cv2.cvtColor(screenshot, cv2.COLOR_BGR2HSV) if len(screenshot.shape) == 3 else None
        if hsv is not None:
            # Detect bright/saturated regions (buttons often are colorful)
            mask = cv2.inRange(hsv, (0, 50, 150), (180, 255, 255))
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                if (self.MIN_BUTTON_SIZE[0] <= w <= self.MAX_BUTTON_SIZE[0] and
                    self.MIN_BUTTON_SIZE[1] <= h <= self.MAX_BUTTON_SIZE[1]):
                    
                    # Check if we already have this region
                    is_duplicate = False
                    for existing in elements:
                        if (abs(existing.x - x) < 20 and abs(existing.y - y) < 20):
                            is_duplicate = True
                            break
                    
                    if not is_duplicate:
                        elements.append(UIElement(
                            x=x, y=y, width=w, height=h,
                            element_type="button"
                        ))
        
        return elements
    
    def match_templates(self, screenshot: np.ndarray, elements: List[UIElement],
                       threshold: float = 0.6, weak_threshold: float = 0.45) -> Tuple[List[UIElement], List[UIElement], List[UIElement]]:
        """Match detected elements against templates."""
        gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY) if len(screenshot.shape) == 3 else screenshot
        gray_blur = cv2.GaussianBlur(gray, (3, 3), 0)
        
        matched = []
        unmatched = []
        weak = []
        
        # Also do global template matching
        global_matches = {}
        for name, tmpl_data in self.templates.items():
            tmpl = tmpl_data['blurred']
            if gray_blur.shape[0] >= tmpl.shape[0] and gray_blur.shape[1] >= tmpl.shape[1]:
                res = cv2.matchTemplate(gray_blur, tmpl, cv2.TM_CCOEFF_NORMED)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
                global_matches[name] = {
                    'confidence': max_val,
                    'location': max_loc,
                    'size': tmpl_data['size']
                }
        
        for element in elements:
            best_match = None
            best_confidence = 0.0
            
            # Extract element region
            x1, y1 = element.x, element.y
            x2, y2 = x1 + element.width, y1 + element.height
            
            # Check if any global match overlaps with this element
            for name, match_data in global_matches.items():
                mx, my = match_data['location']
                mw, mh = match_data['size']
                
                # Check overlap
                overlap_x = max(0, min(x2, mx + mw) - max(x1, mx))
                overlap_y = max(0, min(y2, my + mh) - max(y1, my))
                overlap_area = overlap_x * overlap_y
                
                if overlap_area > 0:
                    confidence = match_data['confidence']
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = name
            
            element.confidence = best_confidence
            element.matched_template = best_match if best_confidence >= weak_threshold else None
            
            if best_confidence >= threshold:
                matched.append(element)
            elif best_confidence >= weak_threshold:
                weak.append(element)
            else:
                unmatched.append(element)
        
        return matched, unmatched, weak
    
    def analyze(self, screenshot: np.ndarray) -> CoverageReport:
        """Analyze template coverage for a screenshot."""
        screen_hash = self._compute_screen_hash(screenshot)
        
        # Detect UI elements
        elements = self.detect_ui_elements(screenshot)
        
        # Match against templates
        matched, unmatched, weak = self.match_templates(screenshot, elements)
        
        # Calculate coverage
        total = len(elements)
        coverage = (len(matched) / total * 100) if total > 0 else 100.0
        
        # Generate suggestions
        suggestions = []
        
        if len(unmatched) > 3:
            suggestions.append(f"Found {len(unmatched)} unrecognized UI elements - consider capturing new templates")
        
        if len(weak) > 0:
            weak_templates = set(e.matched_template for e in weak if e.matched_template)
            for tmpl in weak_templates:
                suggestions.append(f"Template '{tmpl}' has weak matches - may need updating")
        
        # Check for missing expected templates
        matched_names = set(e.matched_template for e in matched if e.matched_template)
        critical_templates = ['home_screen.png', 'battle_icon.png', 'dungeon_page.png', 'back_button.png']
        missing_critical = [t for t in critical_templates if t not in matched_names and t in self.templates]
        
        if missing_critical:
            suggestions.append(f"Critical templates not detected: {', '.join(missing_critical)}")
        
        # Create report
        report = CoverageReport(
            timestamp=datetime.now().isoformat(),
            screen_hash=screen_hash,
            total_elements=total,
            matched_elements=len(matched),
            unmatched_elements=len(unmatched),
            weak_matches=len(weak),
            coverage_percent=coverage,
            matched=matched,
            unmatched=unmatched,
            weak=weak,
            suggestions=suggestions
        )
        
        # Save to history
        self.coverage_history.append({
            'timestamp': report.timestamp,
            'hash': screen_hash,
            'coverage': coverage,
            'matched': len(matched),
            'unmatched': len(unmatched)
        })
        self._save_history()
        
        return report
    
    def visualize_coverage(self, screenshot: np.ndarray, report: CoverageReport) -> np.ndarray:
        """Create visualization of coverage analysis."""
        vis = screenshot.copy()
        
        # Draw matched elements (green)
        for elem in report.matched:
            cv2.rectangle(vis, (elem.x, elem.y), 
                         (elem.x + elem.width, elem.y + elem.height),
                         (0, 255, 0), 2)
            if elem.matched_template:
                label = elem.matched_template.replace('.png', '')[:15]
                cv2.putText(vis, label, (elem.x, elem.y - 5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
        
        # Draw weak matches (yellow)
        for elem in report.weak:
            cv2.rectangle(vis, (elem.x, elem.y),
                         (elem.x + elem.width, elem.y + elem.height),
                         (0, 255, 255), 2)
            cv2.putText(vis, f"?{elem.confidence:.2f}", (elem.x, elem.y - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
        
        # Draw unmatched elements (red)
        for elem in report.unmatched:
            cv2.rectangle(vis, (elem.x, elem.y),
                         (elem.x + elem.width, elem.y + elem.height),
                         (0, 0, 255), 2)
            cv2.putText(vis, "NEW?", (elem.x, elem.y - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
        
        # Draw legend
        cv2.rectangle(vis, (10, 10), (250, 90), (0, 0, 0), -1)
        cv2.putText(vis, f"Coverage: {report.coverage_percent:.1f}%", (15, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        cv2.putText(vis, f"Matched: {report.matched_elements} (green)", (15, 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        cv2.putText(vis, f"Weak: {report.weak_matches} (yellow)", (15, 65),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        cv2.putText(vis, f"Unknown: {report.unmatched_elements} (red)", (15, 80),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
        
        return vis
    
    def get_capture_suggestions(self, report: CoverageReport, screenshot: np.ndarray) -> List[Tuple[str, np.ndarray]]:
        """Get suggested templates to capture from unmatched elements."""
        suggestions = []
        
        # Group unmatched by location
        for i, elem in enumerate(report.unmatched[:10]):  # Limit to 10
            # Extract region with padding
            pad = 5
            x1 = max(0, elem.x - pad)
            y1 = max(0, elem.y - pad)
            x2 = min(screenshot.shape[1], elem.x + elem.width + pad)
            y2 = min(screenshot.shape[0], elem.y + elem.height + pad)
            
            region = screenshot[y1:y2, x1:x2]
            
            # Suggest name based on location and type
            if elem.y < 100:
                location = "top"
            elif elem.y > screenshot.shape[0] - 150:
                location = "bottom"
            else:
                location = "center"
            
            suggested_name = f"new_{elem.element_type}_{location}_{i+1}.png"
            suggestions.append((suggested_name, region))
        
        return suggestions


def main():
    """Run coverage analysis interactively."""
    print("\n" + "="*60)
    print("TEMPLATE COVERAGE ANALYZER")
    print("="*60)
    
    analyzer = TemplateCoverageAnalyzer()
    print(f"Loaded {len(analyzer.templates)} templates")
    
    # Try to get screenshot
    try:
        from Src.bot_core import Bot
        bot = Bot()
        bot.getScreen()
        if bot.screenRGB is not None:
            screenshot = cv2.cvtColor(bot.screenRGB, cv2.COLOR_RGB2BGR)
            print("✓ Got live screenshot")
        else:
            raise Exception("No screenshot")
    except Exception as e:
        print(f"Could not get live screenshot: {e}")
        # Try cached
        debug_dir = Path("screenshots")
        if debug_dir.exists():
            screenshots = list(debug_dir.glob("debug_screen_*.png"))
            if screenshots:
                latest = max(screenshots, key=lambda p: p.stat().st_mtime)
                screenshot = cv2.imread(str(latest))
                print(f"Using cached: {latest.name}")
            else:
                print("No screenshots available")
                return
        else:
            return
    
    # Analyze
    print("\nAnalyzing coverage...")
    report = analyzer.analyze(screenshot)
    
    # Print report
    print("\n" + "-"*40)
    print("COVERAGE REPORT")
    print("-"*40)
    print(f"Total UI elements detected: {report.total_elements}")
    print(f"Matched (covered):          {report.matched_elements} ({report.coverage_percent:.1f}%)")
    print(f"Weak matches:               {report.weak_matches}")
    print(f"Unmatched (NEW):            {report.unmatched_elements}")
    
    if report.suggestions:
        print("\n⚠ Suggestions:")
        for s in report.suggestions:
            print(f"  • {s}")
    
    if report.matched:
        print("\n✓ Detected templates:")
        matched_names = set(e.matched_template for e in report.matched if e.matched_template)
        for name in sorted(matched_names):
            conf = max(e.confidence for e in report.matched if e.matched_template == name)
            print(f"  • {name} (conf: {conf:.2f})")
    
    if report.weak:
        print("\n⚡ Weak matches (may need updating):")
        for elem in report.weak:
            if elem.matched_template:
                print(f"  • {elem.matched_template}: {elem.confidence:.2f}")
    
    # Visualization
    print("\n" + "-"*40)
    vis = analyzer.visualize_coverage(screenshot, report)
    
    # Save visualization
    vis_path = Path("screenshots") / f"coverage_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    vis_path.parent.mkdir(exist_ok=True)
    cv2.imwrite(str(vis_path), vis)
    print(f"Saved visualization: {vis_path}")
    
    # Show
    cv2.namedWindow("Coverage Analysis", cv2.WINDOW_NORMAL)
    h, w = vis.shape[:2]
    scale = min(1.0, 1400 / w, 900 / h)
    cv2.imshow("Coverage Analysis", cv2.resize(vis, (int(w*scale), int(h*scale))))
    print("\nPress any key to continue, 'c' to capture suggestions...")
    
    key = cv2.waitKey(0) & 0xFF
    cv2.destroyAllWindows()
    
    if key == ord('c') and report.unmatched:
        # Offer to capture suggestions
        suggestions = analyzer.get_capture_suggestions(report, screenshot)
        print(f"\nFound {len(suggestions)} capture suggestions")
        
        for name, region in suggestions:
            print(f"\nSuggested template: {name}")
            print(f"Size: {region.shape[1]}x{region.shape[0]}")
            
            cv2.imshow("Suggested Template", region)
            print("Press 's' to save, 'n' for next, 'q' to quit")
            
            key = cv2.waitKey(0) & 0xFF
            if key == ord('s'):
                save_name = input(f"Save as [{name}]: ").strip() or name
                if not save_name.endswith('.png'):
                    save_name += '.png'
                cv2.imwrite(f"icons/{save_name}", region)
                print(f"✓ Saved: icons/{save_name}")
            elif key == ord('q'):
                break
        
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
