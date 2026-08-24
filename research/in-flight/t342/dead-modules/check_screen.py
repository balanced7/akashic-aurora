"""Check current screen for opencode window"""
import sys
sys.path.insert(0, r"E:\AI-Setup")

from ai_helper import ocr, ui_list

print("=== SCREEN CHECK ===")
text = ocr()
print(f"Screen OCR:\n{text[:500]}")

print("\n=== WINDOW LIST ===")
windows = ui_list()
print(windows)