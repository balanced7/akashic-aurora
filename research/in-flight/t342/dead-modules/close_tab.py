"""Close the OC tab in the main window"""
import sys
sys.path.insert(0, r"E:\AI-Setup")

from ui_scout import see, click

# Get the UI tree
print("=== FINDING OC TAB TO CLOSE ===")
data = see("OC", depth=6)

# Look for the OC tab item and its close button
# The tab has name "OC | Redis-based knowledge..."
# Each tab item should have a close button

# Let's try clicking on the close button for the OC tab
# From the JSON, the OC tab is at x=2321, y=382
# The close button should be on the right side of the tab

# Try clicking at the close button position for OC tab
result = click(x=2370, y=405, window_pattern="OC")
print(f"Click result: {result}")

# If that doesn't work, let's try a different position
# Close button is usually at the far right of the tab
result2 = click(x=2660, y=405, window_pattern="OC")
print(f"Second click result: {result2}")

print("\n[Done] Attempted to close OC tab")