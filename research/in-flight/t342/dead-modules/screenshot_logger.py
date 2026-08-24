"""
Screenshot Logger - Session-aware screenshot capture
====================================================
Saves screenshots with timestamp + session ID + tag for easy identification.

Features:
- Connection pooling for Redis
- Parallel capture + Redis logging

Usage:
    from screenshot_logger import ScreenshotLogger
    
    logger = ScreenshotLogger(tag="ocr_test")
    logger.capture()  # Saves to E:\AI-Setup\session_screenshots\{session_id}_ocr_test_{timestamp}.png
    
    # Or use directly
    from screenshot_logger import capture_tagged
    capture_tagged("reason_for_screenshot", tag="debug")
"""
import os
import time
import mss
import sys
import redis
import json

SESSION_ID = os.environ.get("OPENCODE_SESSION", f"session_{time.strftime('%Y%m%d_%H%M%S')}")
SCREENSHOT_DIR = r"E:\AI-Setup\session_screenshots"

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# Connection pool - reuse connections
_redis_pool = None

def _get_redis_pool():
    """Get or create Redis connection pool"""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = redis.ConnectionPool(host='localhost', port=6379, db=0, decode_responses=True, max_connections=10)
    return _redis_pool


def capture_screen():
    """Capture primary monitor"""
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        return sct.grab(monitor)

def capture_tagged(reason, tag=None, session_id=None):
    """
    Capture screenshot with session ID, timestamp, and tag.
    
    Args:
        reason: Why we're taking this screenshot (e.g., "debug", "ocr_result")
        tag: Optional short tag for identification
        session_id: Optional session ID (defaults to env or generated)
    
    Returns:
        Path to saved screenshot
    """
    sid = session_id or SESSION_ID
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    
    # Clean tag for filename
    tag_str = f"_{tag}" if tag else ""
    
    # Create filename: {session_id}_{reason}_{tag}_{timestamp}.png
    filename = f"{sid}_{reason}{tag_str}_{timestamp}.png"
    filepath = os.path.join(SCREENSHOT_DIR, filename)
    
    # Capture and save (blocking, but fast)
    screenshot = capture_screen()
    mss.tools.to_png(screenshot.rgb, screenshot.size, output=filepath)
    
    print(f"[Screenshot] Saved: {filename}")
    
    # Also log to Redis for other LLMs (use pooled connection)
    try:
        r = redis.Redis(connection_pool=_get_redis_pool())
        r.rpush("screenshots:log", json.dumps({
            "session": sid,
            "reason": reason,
            "tag": tag,
            "timestamp": timestamp,
            "filepath": filepath
        }))
    except:
        pass
    
    return filepath

def get_session_screenshots(session_id=None):
    """Get all screenshots for a session"""
    sid = session_id or SESSION_ID
    files = []
    
    if os.path.exists(SCREENSHOT_DIR):
        for f in os.listdir(SCREENSHOT_DIR):
            if f.startswith(sid):
                files.append(f)
    
    return sorted(files)

def get_recent_screenshots(count=10):
    """Get most recent screenshots across all sessions"""
    files = []
    
    if os.path.exists(SCREENSHOT_DIR):
        for f in os.listdir(SCREENSHOT_DIR):
            if f.endswith(".png"):
                files.append(f)
    
    return sorted(files, reverse=True)[:count]


class ScreenshotLogger:
    """Session-aware screenshot logger"""
    
    def __init__(self, session_id=None, tag=None):
        self.session_id = session_id or SESSION_ID
        self.tag = tag
    
    def capture(self, reason="general"):
        """Capture with current session and tag"""
        return capture_tagged(reason, self.tag, self.session_id)
    
    def capture_ocr(self, result_preview=""):
        """Capture for OCR result"""
        return capture_tagged("ocr", self.tag, self.session_id)
    
    def capture_debug(self, context=""):
        """Capture for debugging"""
        return capture_tagged("debug", self.tag, self.session_id)


if __name__ == "__main__":
    # Test capture
    print(f"Session ID: {SESSION_ID}")
    print(f"Screenshot dir: {SCREENSHOT_DIR}")
    print()
    print("Testing screenshot capture...")
    
    path = capture_tagged("test", "demo", SESSION_ID)
    print(f"Saved to: {path}")
    print(f"Exists: {os.path.exists(path)}")
    
    print("\nRecent screenshots:")
    for f in get_recent_screenshots(5):
        print(f"  {f}")