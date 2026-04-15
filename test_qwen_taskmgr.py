import sys, time, base64
sys.path.insert(0, r'E:\AI-Setup')
from session_logger import log
import pyautogui
import pygetwindow as pgw

# Capture actual window (Task Manager if available)
TARGET = "Task Manager"
windows = pgw.getWindowsWithTitle(TARGET)
if windows:
    w = windows[0]
    bbox = (w.left, w.top, w.left + w.width, w.top + w.height)
    img = pyautogui.screenshot(region=bbox)
    img.save(r"E:\AI-Setup\session_screenshots\qwen_taskmgr.png")
    print(f"Captured Task Manager: {w.width}x{w.height}")
else:
    img = pyautogui.screenshot()
    img.save(r"E:\AI-Setup\session_screenshots\qwen_full.png")
    print("Captured full screen")

# Encode image to base64
buffer = __import__('io').BytesIO()
img.save(buffer, format="PNG")
img_b64 = base64.b64encode(buffer.getvalue()).decode()

# Test via Ollama API
import urllib.request, json

print("Running OCR via qwen2.5vl...")
start = time.time()
req = urllib.request.Request(
    "http://localhost:11434/api/generate",
    data=json.dumps({
        "model": "qwen2.5vl:7b",
        "prompt": "Extract ALL text from this image exactly as you see it. List every piece of text, number, and label.",
        "images": [img_b64],
        "stream": False,
        "options": {"temperature": 0}
    }).encode(),
    headers={"Content-Type": "application/json"}
)

try:
    with urllib.request.urlopen(req, timeout=180) as resp:
        result = json.loads(resp.read())
        elapsed = time.time() - start
        text = result.get("response", "")
        print(f"\n=== Qwen2.5VL Result ({elapsed:.1f}s) ===")
        print(text[:1000])
        log("qwen_ocr_taskmgr", f"OCR completed in {elapsed:.1f}s", {"time": elapsed, "chars": len(text)})
except Exception as e:
    print(f"Error: {e}")
    log("qwen_ocr_error", str(e))