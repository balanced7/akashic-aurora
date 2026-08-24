import sys
sys.path.insert(0, r'E:\AI-Setup')
from session_logger import log
import pygetwindow as pgw

print("=== OPEN WINDOWS ===\n")
windows = pgw.getAllWindows()
for w in windows:
    if w.title and w.title.strip():
        print(f"Title: {w.title}")
        print(f"  Position: ({w.left}, {w.top}) Size: ({w.width}x{w.height})")
        print()