import sys, time, base64
sys.path.insert(0, r'E:\AI-Setup')
from session_logger import log
import pyautogui
from PIL import Image

# Capture screen
img = pyautogui.screenshot(region=(100, 100, 800, 600))
img.save(r"E:\AI-Setup\session_screenshots\qwen_test.png")

# Encode image to base64
buffer = __import__('io').BytesIO()
img.save(buffer, format="PNG")
img_b64 = base64.b64encode(buffer.getvalue()).decode()

# Test via Ollama API
import urllib.request, json

start = time.time()
req = urllib.request.Request(
    "http://localhost:11434/api/generate",
    data=json.dumps({
        "model": "qwen2.5vl:7b",
        "prompt": "Extract all text from this image. Be precise and include every piece of text you see.",
        "images": [img_b64],
        "stream": False
    }).encode(),
    headers={"Content-Type": "application/json"}
)

try:
    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read())
        elapsed = time.time() - start
        text = result.get("response", "")
        print(f"Qwen2.5VL OCR ({elapsed:.2f}s):")
        print(text[:500])
        log("qwen_ocr_test", f"OCR completed in {elapsed:.2f}s", {"time": elapsed, "chars": len(text)})
except Exception as e:
    print(f"Error: {e}")
    log("qwen_ocr_error", str(e))