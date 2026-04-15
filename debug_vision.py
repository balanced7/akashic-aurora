import sys
sys.path.insert(0, r'E:\AI-Setup')
from session_logger import log
import pyautogui
import time

print("=== DEBUG VISION ===")

# Capture a region directly
print("Capturing screen region...")
img = pyautogui.screenshot(region=(100, 100, 800, 600))
print(f"Image size: {img.size}, mode: {img.mode}")

# Save to check
img.save(r"E:\AI-Setup\session_screenshots\debug_test.png")
print("Saved to debug_test.png")

# Test with VisionEngine
sys.path.insert(0, r'E:\AI-Setup')
from vision_engine import VisionEngine
import torch

print("\nLoading VisionEngine...")
engine = VisionEngine()
print(f"Device: {engine.device}, DML: {engine._dml_available}")

print("\nLoading model...")
engine.load()
print(f"Model loaded: {engine._loaded}")

print("\nRunning caption...")
result = engine.analyze_screen(img, "caption")
print(f"Caption result: {result}")

print("\nRunning OCR...")
result = engine.analyze_screen(img, "ocr")
print(f"OCR result: {result}")

log("vision_debug", "Debug completed", {"device": str(engine.device), "result": str(result)})