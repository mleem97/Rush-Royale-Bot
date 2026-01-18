"""Example usage of ContextAwareIconDetector.

This script demonstrates how to use the new context-aware icon detection
to prevent false positives and ensure icons are only detected in appropriate
screen states.
"""

from pathlib import Path

import cv2

from rush_bot.perception import ContextAwareIconDetector
from rush_bot.perception import ScreenState


def main() -> None:
    """Demonstrate context-aware icon detection."""
    # Create detector instance
    detector = ContextAwareIconDetector()

    # Example 1: Detect icons on a screenshot
    screenshot_path = Path("bot_feed.png")

    if not screenshot_path.exists():
        print(f"Screenshot not found: {screenshot_path}")
        print("Please ensure you have a screenshot available.")
        return

    # Load screenshot
    screenshot = cv2.imread(str(screenshot_path))
    if screenshot is None:
        print("Failed to load screenshot")
        return

    print("=" * 60)
    print("CONTEXT-AWARE ICON DETECTION DEMO")
    print("=" * 60)

    # Detect all icons with context awareness
    print("\n1. Auto-detecting screen state and icons...")
    icons = detector.detect_icons(screenshot)

    print(f"\nDetected Screen State: {detector.current_state.name}")
    print(f"Detected Menu Context: {detector.menu_context.name}")
    print(f"\nFound {len(icons)} icon(s):")

    for icon_data in icons:
        print(f"  - {icon_data['icon']:20s} | Confidence: {icon_data['confidence']:.2%} | State: {icon_data['state'].name}")

    # Example 2: Force specific screen state for testing
    print("\n" + "=" * 60)
    print("\n2. Testing with forced HOME screen state...")
    home_icons = detector.detect_icons(screenshot, force_state=ScreenState.HOME)

    print(f"\nFound {len(home_icons)} icon(s) on HOME screen:")
    for icon_data in home_icons:
        print(f"  - {icon_data['icon']:20s} | Confidence: {icon_data['confidence']:.2%}")

    # Example 3: Detect specific icons only
    print("\n" + "=" * 60)
    print("\n3. Looking for specific icons (PVP/PVE buttons)...")
    specific_icons = detector.detect_icons(
        screenshot, icon_list=["pvp_button.png", "pve_button.png"], force_state=ScreenState.HOME
    )

    print(f"\nFound {len(specific_icons)} PVP/PVE button(s):")
    for icon_data in specific_icons:
        x, y = icon_data["position"]
        print(f"  - {icon_data['icon']:20s} at position ({x}, {y})")

    # Example 4: Try to detect victory button on wrong screen
    print("\n" + "=" * 60)
    print("\n4. Testing false-positive prevention...")
    print("   (Trying to detect 0cont_button.png on HOME screen)")

    continue_icons = detector.detect_icons(screenshot, icon_list=["0cont_button.png"], force_state=ScreenState.HOME)

    if len(continue_icons) == 0:
        print("   ✅ Correctly prevented false positive!")
        print("   Continue button is only detectable on VICTORY screen.")
    else:
        print("   ❌ False positive detected (this should not happen)")

    print("\n" + "=" * 60)
    print("\nKey Features Demonstrated:")
    print("  1. Automatic screen state detection")
    print("  2. Menu context detection (90% confidence)")
    print("  3. ROI-based icon filtering")
    print("  4. State-specific icon validation")
    print("  5. False-positive prevention")
    print("\nAll icons now require:")
    print("  - Correct screen state")
    print("  - Detection within defined ROI")
    print("  - Minimum 85-90% confidence")
    print("=" * 60)


if __name__ == "__main__":
    main()
