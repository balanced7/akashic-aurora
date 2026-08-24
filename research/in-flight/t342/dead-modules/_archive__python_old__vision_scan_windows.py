import sys
sys.path.insert(0, r'E:\AI-Setup')
from session_logger import log
import pygetwindow as pgw
import pyautogui
from PIL import Image
import time

# Target windows to analyze
TARGET_WINDOWS = [
    "OC | Bootstrap initialization with Redis",
    "Task Manager",
    "Settings",
    "Google Gemini",
    "Duumu - Never Had"
]

def capture_window_by_title(title_pattern):
    """Capture a specific window by title pattern"""
    try:
        windows = pgw.getWindowsWithTitle(title_pattern)
        if windows:
            w = windows[0]
            if w.left < 0 or w.top < 0:
                w.restore()
                time.sleep(0.2)
            bbox = (w.left, w.top, w.left + w.width, w.top + w.height)
            img = pyautogui.screenshot(region=bbox)
            return img, w.title
    except Exception as e:
        print(f"Error capturing {title_pattern}: {e}")
    return None, None

def analyze_window(img, title):
    """Analyze a window screenshot with Florence-2"""
    sys.path.insert(0, r'E:\AI-Setup')
    from vision_engine import VisionEngine
    
    engine = VisionEngine()
    engine.load()
    
    # Run multiple analyses
    caption = engine.analyze_screen(img, "detailed_caption")
    ocr = engine.analyze_screen(img, "ocr")
    
    return {
        "title": title,
        "size": img.size,
        "caption": caption.get("caption", ""),
        "text": ocr.get("text", "")[:500]
    }

print("=" * 60)
print("VISION ANALYSIS OF OPEN WINDOWS")
print("=" * 60)

results = []
for target in TARGET_WINDOWS:
    print(f"\n>>> Capturing: {target}")
    img, title = capture_window_by_title(target)
    if img:
        print(f"    Captured: {img.size}")
        result = analyze_window(img, title)
        results.append(result)
        print(f"    Caption: {result['caption'][:100]}...")
        print(f"    Text: {result['text'][:100]}...")
    else:
        print(f"    Not found or could not capture")

print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
for r in results:
    print(f"\n[{r['title']}] ({r['size']})")
    print(f"  What I see: {r['caption']}")
    if r['text'].strip():
        print(f"  Text found: {r['text'][:150]}...")

log("vision_windows_scan", f"Scanned {len(results)} windows", {"windows": [r['title'] for r in results]})