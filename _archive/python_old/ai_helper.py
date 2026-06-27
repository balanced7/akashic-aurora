"""
AI Control Center Helper Module
============================
Fast tools for OpenCode to troubleshoot and learn.
Usage:
    from ai_helper import *
    ocr()           # Quick screen OCR
    status()        # Dashboard status
    learn("key", "value")  # Store learning
    ui_inspect("window title")  # Naturo UI inspection
    ui_list()       # List open windows
"""
import os
import sys
import time
import subprocess
import requests

# ============ SCREEN OCR ============
def ocr():
    """Quick screen OCR - returns extracted text"""
    import pytesseract
    from PIL import Image
    import mss
    
    print("[OCR] Capturing screen...")
    with mss.mss() as sct:
        img = sct.grab(sct.monitors[1])
        path = os.path.expanduser("~\\ai_helper_screen.png")
        mss.tools.to_png(img.rgb, img.size, output=path)
    
    print("[OCR] Reading text...")
    text = pytesseract.image_to_string(path)
    
    try:
        os.remove(path)
    except:
        pass
    
    return text

def ocr_lines():
    """Screen OCR as list of lines"""
    text = ocr()
    return [l.strip() for l in text.split('\n') if l.strip()]

# ============ DASHBOARD ============
def status():
    """Get dashboard status"""
    try:
        r = requests.get('http://127.0.0.1:8501/api/status', timeout=2)
        return r.json()
    except:
        return {"error": "Dashboard not running"}

def services():
    """Get service list"""
    try:
        r = requests.get('http://127.0.0.1:8501/api/services', timeout=2)
        return r.json()
    except:
        return []

def restart_dashboard():
    """Restart dashboard service"""
    print("[INFO] Run: python E:\\AI-Setup\\launch_dashboard.py")

# ============ KNOWLEDGE BASE ============
def learn(key, value):
    """Store a learning in Redis"""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        r.set(f"kb:learning:{key}", value)
        print(f"[LEARNED] {key}: {value}")
        return True
    except:
        print("[ERROR] Redis not available")
        return False

def get_learnings():
    """Get all learnings"""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        return {k: r.get(k) for k in r.keys('kb:learning:*')}
    except:
        return {}

def recall(key):
    """Recall a specific learning"""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        return r.get(f"kb:learning:{key}")
    except:
        return None

# ============ QUICK DIAGNOSTICS ============
def diag():
    """Run quick diagnosis"""
    print("="*50)
    print("AI Control Center - Quick Diagnosis")
    print("="*50)
    
    # Dashboard
    print("\n[Dashboard]")
    s = status()
    if "error" in s:
        print("  NOT RUNNING - start with: python E:\\AI-Setup\\launch_dashboard.py")
    else:
        print("  Running")
        for svc, state in s.get('services', {}).items():
            print(f"    {svc}: {state}")
    
    # OCR
    print("\n[OCR]")
    print("  Tesseract: Ready (ocr() function)")
    
    # Learnings
    print("\n[Learnings]")
    ls = get_learnings()
    print(f"  {len(ls)} entries stored")
    
    print("\n" + "="*50)

# ============ EXPORT CONTEXT ============
def context():
    """Export full context for OpenCode"""
    return {
        'dashboard': status(),
        'services': services(),
        'learnings': get_learnings(),
        'ocr_available': True,
        'files': {
            'dashboard': 'E:\\AI-Setup\\dockerized-ai\\services\\dashboard\\app.py',
            'launcher': 'E:\\AI-Setup\\launch_dashboard.py',
            'ocr': 'E:\\AI-Setup\\fast_ocr.py',
            'knowledge': 'E:\\AI-Setup\\knowledge_base.py',
        }
    }

# ============ UI INSPECTION (NATURO) ============
def ui_list():
    """List all open windows"""
    print("[UI] Listing windows...")
    try:
        result = subprocess.run(
            ["python", "-m", "naturo", "list", "windows"],
            capture_output=True, text=True, timeout=10,
            env={**os.environ, "PYTHONPATH": r"C:\Users\L5\AppData\Local\Programs\Python\Python311\Lib\site-packages"}
        )
        return result.stdout
    except Exception as e:
        return f"[ERROR] {e}"

def ui_inspect(window_pattern, depth=3):
    """Inspect UI elements in a window"""
    print(f"[UI] Inspecting: {window_pattern}")
    try:
        result = subprocess.run(
            ["python", "-m", "naturo", "see", "--window", window_pattern, "--depth", str(depth)],
            capture_output=True, text=True, timeout=15
        )
        return result.stdout
    except Exception as e:
        return f"[ERROR] {e}"

def ui_windows():
    """Get open windows as structured data"""
    windows = []
    try:
        result = subprocess.run(
            ["python", "-m", "naturo", "list", "windows"],
            capture_output=True, text=True, timeout=10
        )
        for line in result.stdout.split('\n')[2:]:  # Skip header
            if line.strip():
                parts = line.split()
                if len(parts) >= 4:
                    windows.append({
                        'hwnd': parts[0],
                        'pid': parts[1],
                        'size': parts[2],
                        'title': ' '.join(parts[3:])
                    })
    except:
        pass
    return windows

def ui_find(window_pattern, element_pattern):
    """Find specific element in window"""
    print(f"[UI] Finding '{element_pattern}' in {window_pattern}")
    output = ui_inspect(window_pattern, depth=5)
    matches = []
    for line in output.split('\n'):
        if element_pattern.lower() in line.lower():
            matches.append(line)
    return matches

# ============ SESSION LOGGING ============
def get_session_logger(task_name="default"):
    """Get a session logger for crash-safe logging"""
    try:
        from session_logger import SessionLogger
        return SessionLogger(task_name=task_name)
    except Exception as e:
        print(f"[WARNING] Could not load session_logger: {e}")
        return None

def auto_log(action, description, data=None):
    """Quick log action to session"""
    logger = get_session_logger()
    if logger:
        logger.log(action, description, data)
    else:
        print(f"[LOG] {action}: {description}")

def get_recovery_summary():
    """Get crash recovery info"""
    try:
        from crash_recovery import get_summary
        return get_summary()
    except:
        return {"error": "crash_recovery not available"}

# ============ SCREENSHOT LOGGING ============
def screenshot(reason="general", tag=None):
    """Take a screenshot with session ID, timestamp, and tag"""
    try:
        from screenshot_logger import capture_tagged
        return capture_tagged(reason, tag)
    except Exception as e:
        print(f"[Screenshot] Error: {e}")
        return None

def get_screenshots(session_id=None):
    """Get screenshots for a session"""
    try:
        from screenshot_logger import get_session_screenshots
        return get_session_screenshots(session_id)
    except:
        return []

# ============ UI SCOUT (NATURO) ============
def ui_scout(window_pattern=None, depth=3):
    """Deep UI inspection with Naturo"""
    try:
        from ui_scout import see
        return see(window_pattern, depth=depth)
    except Exception as e:
        return {"error": str(e)}

def ui_find(query, window_pattern=None):
    """Find UI elements matching query"""
    try:
        from ui_scout import find
        return find(query, window_pattern)
    except Exception as e:
        return [{"error": str(e)}]

def ui_highlight(window_pattern=None):
    """Highlight UI elements visually"""
    try:
        from ui_scout import highlight
        return highlight(window_pattern)
    except:
        return "Error"

def ui_screenshot(window_pattern=None):
    """Capture screenshot with UI element labels"""
    try:
        from ui_scout import capture
        return capture(window_pattern)
    except:
        return None

# ============ UI INTERACTION ============
def ui_click(element_id=None, x=None, y=None, window=None):
    """Click UI element or coordinates"""
    try:
        from ui_scout import click
        return click(element_id, x, y, window)
    except Exception as e:
        return f"Error: {e}"

def ui_type(text, window=None):
    """Type text"""
    try:
        from ui_scout import type_text
        return type_text(text, window)
    except Exception as e:
        return f"Error: {e}"

def ui_press(keys, window=None):
    """Press keyboard shortcut"""
    try:
        from ui_scout import press_keys
        return press_keys(keys, window)
    except Exception as e:
        return f"Error: {e}"

def ui_scroll(direction="down", amount=3, window=None):
    """Scroll"""
    try:
        from ui_scout import scroll
        return scroll(direction, amount, window)
    except Exception as e:
        return f"Error: {e}"

# ============ DRAG AND DROP ============
def ui_drag(start_x, start_y, end_x, end_y, window=None):
    """Drag from one position to another"""
    try:
        from ui_scout import drag
        return drag(start_x, start_y, end_x, end_y, window)
    except Exception as e:
        return f"Error: {e}"

def ui_drag_element(element_id, dest_x, dest_y, window=None):
    """Drag element to coordinates"""
    try:
        from ui_scout import drag_element
        return drag_element(element_id, dest_x, dest_y, window)
    except Exception as e:
        return f"Error: {e}"

# ============ HYBRID OCR + UI ============
def hybrid_inspect(window=None, depth=5):
    """Combine Naturo + OCR for complete coverage"""
    try:
        from ui_scout import hybrid_inspect
        return hybrid_inspect(window, depth)
    except Exception as e:
        return {"error": str(e)}

def smart_find(term, window=None):
    """Smart search - tries UI first, then OCR"""
    try:
        from ui_scout import smart_find
        return smart_find(term, window)
    except Exception as e:
        return {"error": str(e)}

def get_visual_context(window=None):
    """Get comprehensive visual context"""
    try:
        from ui_scout import get_visual_context
        return get_visual_context(window)
    except Exception as e:
        return {"error": str(e)}

# ============ WINDOW ISOLATION (for troubleshooting) ============
def bring_to_front(window_pattern):
    """
    Bring a window to foreground before inspection.
    CRITICAL: Use this before capturing/inspecting to avoid occluded windows.
    
    Usage:
        bring_to_front("AI Control Center")
    """
    try:
        from ui_scout import bring_to_front
        return bring_to_front(window_pattern)
    except Exception as e:
        return {"error": str(e)}

def screenshot_isolated(window_pattern, output_path=None):
    """
    Capture isolated screenshot of specific window (not full screen).
    Window is automatically brought to front first.
    
    Usage:
        path = screenshot_isolated("AI Control Center")
        path = screenshot_isolated("AI Control Center", "C:/temp/screenshot.png")
    """
    try:
        from ui_scout import screenshot_isolated
        return screenshot_isolated(window_pattern, output_path)
    except Exception as e:
        return {"error": str(e)}

# ============ WINDOW ORDER PRESERVATION ============
_window_order_stack = []
_our_terminal_hwnd = None
_z_order_verification_enabled = True

def _capture_window_order():
    """
    Capture current window z-order as verified ordered list.
    Returns list of (hwnd, title) tuples in z-order (bottom to top).
    """
    try:
        result = ui_list()
        if result and isinstance(result, str):
            lines = result.strip().split('\n')[2:]  # Skip header
            captured = []
            for line in lines:
                parts = line.split()
                if len(parts) >= 4:
                    hwnd = parts[0]
                    title = ' '.join(parts[3:])
                    captured.append((hwnd, title))
            return captured
    except Exception as e:
        print(f"[zorder] Capture error: {e}")
    return []

def _verify_z_order_match(before, after):
    """
    Compare two z-order lists. Returns (match, diff_description).
    """
    if before == after:
        return True, "Match"
    
    # Find first difference
    min_len = min(len(before), len(after))
    for i in range(min_len):
        if before[i] != after[i]:
            return False, f"Position {i}: {before[i]} -> {after[i]}"
    
    if len(before) != len(after):
        return False, f"Length changed: {len(before)} -> {len(after)}"
    
    return False, "Unknown difference"

def _set_window_z_order(hwnd):
    """Bring specific window to front in z-order."""
    try:
        from ui_scout import _run_naturo
        _run_naturo(['app', 'focus', '--hwnd', hwnd], timeout=2)
    except:
        pass

def _assert_state(condition, success_msg, failure_msg):
    """Assert with logging - ensures failures are never silent."""
    if not condition:
        try:
            from session_logger import log_error
            log_error("assertion_failed", failure_msg)
        except:
            pass
        raise AssertionError(failure_msg)
    print(f"[VERIFY] {success_msg}")

def _get_terminal_hwnd():
    """Get the HWND of this terminal/PowerShell window"""
    global _our_terminal_hwnd
    if _our_terminal_hwnd:
        return _our_terminal_hwnd
    try:
        result = ui_list()
        if result and isinstance(result, str):
            lines = result.strip().split('\n')[2:]
            for line in lines:
                parts = line.split()
                if len(parts) >= 4:
                    title = ' '.join(parts[3:])
                    if 'PowerShell' in title or 'cmd.exe' in title or 'terminal' in title.lower():
                        _our_terminal_hwnd = parts[0]
                        return _our_terminal_hwnd
    except:
        pass
    return None

def track_window_order():
    """
    Track current window z-order BEFORE bringing target to front.
    Stores the COMPLETE z-order for restoration.
    
    Usage:
        track_window_order()  # Call before bring_to_front()
        bring_to_front("Target")
        # ... do inspection ...
        restore_window_order()  # Call after to FULLY restore z-order
    """
    global _window_order_stack, _our_terminal_hwnd
    try:
        result = ui_list()
        if result and isinstance(result, str):
            lines = result.strip().split('\n')[2:]  # Skip header
            _window_order_stack = []
            for line in lines:
                parts = line.split()
                if len(parts) >= 4:
                    hwnd = parts[0]
                    title = ' '.join(parts[3:])
                    _window_order_stack.append((hwnd, title))
                    if 'PowerShell' in title and _our_terminal_hwnd is None:
                        _our_terminal_hwnd = hwnd
        
        captured = _capture_window_order()
        _assert_state(
            len(_window_order_stack) > 0,
            f"Tracked {len(_window_order_stack)} windows, terminal HWND={_our_terminal_hwnd}",
            f"Failed to track windows! Stack={_window_order_stack}"
        )
        return _window_order_stack
    except Exception as e:
        print(f"[window_order] Error tracking: {e}")
        return []

def restore_window_order():
    """
    FULLY RESTORED: Actually restores all windows to original z-order AND verifies.
    
    This function now:
    1. Iterates through stored z-order in REVERSE (bottom to top)
    2. Brings each window to front in sequence
    3. VERIFIES restoration matches original
    4. Returns True ONLY if verification passes
    
    Usage:
        track_window_order()
        bring_to_front("Target")
        # ... work ...
        restore_window_order()  # Restores FULL z-order
    """
    global _window_order_stack
    try:
        from ui_scout import _run_naturo
        
        if not _window_order_stack:
            print("[window_order] No order tracked, cannot restore")
            return False
        
        # Store current state for verification
        before_restore = _capture_window_order()
        
        # Actually restore each window in reverse order (bottom to top)
        for hwnd, title in reversed(_window_order_stack):
            _set_window_z_order(hwnd)
        
        # VERIFY restoration
        after_restore = _capture_window_order()
        match, diff = _verify_z_order_match(_window_order_stack, after_restore)
        
        if match:
            print(f"[window_order] Restored {len(_window_order_stack)} windows to original z-order")
            _window_order_stack = []
            return True
        else:
            print(f"[window_order] VERIFICATION FAILED: {diff}")
            print(f"[window_order] Original: {_window_order_stack[:3]}...")
            print(f"[window_order] Current:  {after_restore[:3]}...")
            # Try once more
            for hwnd, title in reversed(_window_order_stack):
                _set_window_z_order(hwnd)
            after_retry = _capture_window_order()
            match_retry, diff_retry = _verify_z_order_match(_window_order_stack, after_retry)
            if match_retry:
                print(f"[window_order] Retry succeeded")
                _window_order_stack = []
                return True
            print(f"[window_order] Retry also failed: {diff_retry}")
            _window_order_stack = []
            return False
            
    except Exception as e:
        print(f"[window_order] Error restoring: {e}")
        return False

def focus_this_terminal():
    """
    Quick helper to bring THIS terminal back to front.
    Use after any bring_to_front() call if you just need terminal focus.
    Note: Use restore_window_order() if you need FULL z-order restoration.
    
    Usage:
        focus_this_terminal()  # No tracking needed
    """
    try:
        from ui_scout import _run_naturo
        term_hwnd = _get_terminal_hwnd()
        if term_hwnd:
            _run_naturo(['app', 'focus', '--hwnd', term_hwnd], timeout=5)
            print(f"[terminal] Focused HWND {term_hwnd}")
            return True
        print("[terminal] Could not find terminal window")
        return False
    except Exception as e:
        print(f"[terminal] Error: {e}")
        return False


class WindowZOrder:
    """
    Context manager for window z-order tracking and restoration.
    
    Usage:
        with WindowZOrder() as z:
            bring_to_front("Target")
            # ... work ...
        # Automatically restores and verifies on exit
    
    Example:
        with WindowZOrder() as z:
            z.bring_to_front("AI Control Center")
            ocr()
        # Terminal automatically restored to front
    """
    
    def __init__(self):
        self.original_order = []
        self.restored = False
        self.verification_error = None
        self.terminal_hwnd = None
    
    def __enter__(self):
        self.original_order = _capture_window_order()
        self.terminal_hwnd = _get_terminal_hwnd()
        print(f"[WindowZOrder] Captured {len(self.original_order)} windows")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self.original_order:
            return False
        
        # Restore each window in reverse order
        for hwnd, title in reversed(self.original_order):
            _set_window_z_order(hwnd)
        
        # Verify restoration
        current = _capture_window_order()
        if current != self.original_order:
            self.verification_error = "Z-order mismatch"
            print(f"[WindowZOrder] WARNING: {self.verification_error}")
            print(f"[WindowZOrder] Expected: {len(self.original_order)}, Got: {len(current)}")
        else:
            print(f"[WindowZOrder] Verified restoration of {len(self.original_order)} windows")
        
        # Bring terminal back to front
        if self.terminal_hwnd:
            _set_window_z_order(self.terminal_hwnd)
        
        self.restored = True
        return False  # Don't suppress exceptions
    
    def bring_to_front(self, window_pattern):
        """Bring a window to front within the context."""
        bring_to_front(window_pattern)


def test_z_order_restoration():
    """
    TEST: Verify z-order tracking and restoration works.
    Run this to validate the system before relying on it.
    
    Returns:
        (passed, failure_details)
    """
    print("[TEST] Running z-order restoration test...")
    
    # Capture initial state
    initial = _capture_window_order()
    if len(initial) < 3:
        return False, f"Not enough windows: {len(initial)}"
    
    # Track order
    track_window_order()
    
    # Bring first window to front
    first_hwnd, first_title = _window_order_stack[0]
    _set_window_z_order(first_hwnd)
    
    # Restore
    result = restore_window_order()
    
    # Verify
    after = _capture_window_order()
    match, diff = _verify_z_order_match(initial, after)
    
    if match:
        print("[TEST] PASSED: Z-order restoration verified")
        return True, None
    else:
        print(f"[TEST] FAILED: {diff}")
        return False, diff


def minimize_non_essential():
    """
    Minimize all windows except the target (for cleaner inspection).
    Target should already be in front.
    
    Usage:
        minimize_non_essential("AI Control Center")
    """
    try:
        result = ui_list()
        if result and isinstance(result, str):
            lines = result.strip().split('\n')[2:]
            minimized = 0
            for line in lines:
                parts = line.split()
                if len(parts) >= 4:
                    title = ' '.join(parts[3:])
                    # Don't minimize our target or terminal
                    if 'AI Control Center' not in title and 'PowerShell' not in title and 'cmd.exe' not in title:
                        hwnd = parts[0]
                        try:
                            _run_naturo(['window', 'minimize', '--hwnd', hwnd], timeout=2)
                            minimized += 1
                        except:
                            pass
            print(f"[window_order] Minimized {minimized} windows")
            return minimized
    except Exception as e:
        print(f"[window_order] Error minimizing: {e}")
        return 0

# ============ SESSION RECOVERY ============
def quick_catchup():
    """Print quick catch-up summary - call this immediately on startup!"""
    try:
        from session_logger import get_chat_history, get_recent_sessions
        
        print("\n" + "="*60)
        print("  QUICK CATCH-UP")
        print("="*60)
        
        # Get recent sessions
        sessions = get_recent_sessions(3)
        if sessions:
            print("\nRecent sessions:")
            for s in sessions:
                print(f"  [{s.get('session_id', '?')}] {s.get('task', 'unknown')} - {s.get('status', '?')}")
        
        # Get recent chat
        chats = get_chat_history(10)
        if chats:
            print(f"\nRecent chat ({len(chats)} messages):")
            for c in chats[-5:]:
                role = c.get("role", "?")[:8]
                msg = c.get("message", "")[:60].replace('\n', ' ')
                print(f"  {role}: {msg}")
        
        print("\n" + "="*60)
        print("  Available: log(), log_chat(), log_error(), screenshot()")
        print("  Run log_chat('assistant', 'message') to save your responses!")
        print("="*60 + "\n")
        
        return {"sessions": sessions, "chats": len(chats)}
    except Exception as e:
        print(f"Catch-up error: {e}")
        return {"error": str(e)}

# ============ CONVERSATION BACKUP LOGGER ============
def get_conversation_backup():
    """Get conversation backup log for verification"""
    try:
        import json
        BACKUP_LOG = r"E:\AI-Setup\session_logs\backup_session_all.jsonl"
        
        entries = []
        if os.path.exists(BACKUP_LOG):
            with open(BACKUP_LOG, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entries.append(json.loads(line))
                    except:
                        pass
        
        return entries[-20:]  # Last 20 entries
    except Exception as e:
        return [{"error": str(e)}]

def verify_logging():
    """Verify session logging is working - compare with backup"""
    try:
        from conversation_logger import ConversationLogger
        logger = ConversationLogger()
        return logger.verify_other_loggers()
    except Exception as e:
        return {"error": str(e)}

def get_logging_status():
    """Get summary of all logging systems"""
    import json
    import redis
    
    status = {
        "conversation_backup": [],
        "chat_history_count": 0,
        "sessions_active": {},
        "file_logs": []
    }
    
    # Get conversation backup
    try:
        from conversation_logger import CONVO_LOG
        if os.path.exists(CONVO_LOG):
            with open(CONVO_LOG, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in lines[-10:]:
                    try:
                        status["conversation_backup"].append(json.loads(line))
                    except:
                        pass
    except:
        pass
    
    # Get Redis counts
    try:
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        status["chat_history_count"] = r.llen("chat:history")
        status["sessions_active"] = r.hgetall("sessions:active")
    except:
        pass
    
    # Get session files
    try:
        log_dir = r"E:\AI-Setup\session_logs"
        for f in os.listdir(log_dir):
            if f.endswith(".jsonl"):
                status["file_logs"].append(f)
    except:
        pass
    
    return status

# ============ ERROR DOCUMENTATION ============
def log_error_category(system, error_type, details, severity="medium"):
    """Log an error with categorization"""
    try:
        from error_documentation import ErrorDoc
        doc = ErrorDoc()
        return doc.log_error(system, error_type, details, severity)
    except Exception as e:
        return {"error": str(e)}

def get_error_summary():
    """Get error summary by system and severity"""
    try:
        from error_documentation import ErrorDoc
        doc = ErrorDoc()
        return doc.get_summary()
    except Exception as e:
        return {"error": str(e)}

def get_errors_by_system(system):
    """Get all errors for a specific system"""
    try:
        from error_documentation import ErrorDoc
        doc = ErrorDoc()
        return doc.get_errors_by_system(system)
    except Exception as e:
        return [{"error": str(e)}]

def get_recent_errors(count=10):
    """Get most recent errors"""
    try:
        from error_documentation import ErrorDoc
        doc = ErrorDoc()
        return doc.get_recent_errors(count)
    except Exception as e:
        return [{"error": str(e)}]

# Run diagnostics if called directly
if __name__ == "__main__":
    diag()