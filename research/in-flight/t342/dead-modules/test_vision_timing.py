import sys
import time
sys.path.insert(0, r'E:\AI-Setup')

print('[1] Testing vision engine with screen capture...')
from vision_engine import VisionEngine, capture_active_window

ve = VisionEngine()
print('    Device:', ve.device)

print('[2] Loading model...')
start = time.time()
ve.load()
print('    Loaded in', round(time.time() - start, 1), 's')

print('[3] Capturing screen...')
start = time.time()
screenshot = capture_active_window()
print('    Captured in', round(time.time() - start, 1), 's')

if screenshot:
    print('[4] Analyzing screen...')
    start = time.time()
    context = ve.analyze_screen(screenshot, task='caption')
    elapsed = time.time() - start
    print('    Analyzed in', round(elapsed, 1), 's')
    if 'error' not in context:
        caption = context.get('caption', 'N/A')
        print('    Caption:', caption[:100])
    else:
        print('    Error:', context.get('error'))
else:
    print('    Failed to capture')

print('[5] Done')
