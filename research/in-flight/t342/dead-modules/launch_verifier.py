"""
Launch Verifier - Checks if launched process opened successfully
=================================================================
- Checks .5 seconds after launch
- Then checks at 1 second intervals
- Uses process check (CLI) or screen OCR (GUI)

Usage:
    from launch_verifier import verify_launch, LaunchConfig
    
    config = LaunchConfig(
        name="OpenCode",
        process_name="opencode.exe",
        gui=True,  # Use screen check for GUI apps
        max_wait=30
    )
    result = verify_launch(config)
"""
import subprocess
import time
import os
import sys

# Add AI-Setup to path
sys.path.insert(0, r"E:\AI-Setup")

def check_process_running(process_name):
    """Check if process is running using tasklist"""
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {process_name}"],
            capture_output=True, text=True, timeout=5
        )
        return process_name.lower() in result.stdout.lower()
    except:
        return False

def check_window_exists(window_title_pattern):
    """Check if window with title exists using PowerShell"""
    try:
        script = f'''
$windows = Get-Process | Where-Object {{$_.MainWindowTitle -like "*{window_title_pattern}*"}}
if ($windows) {{ "FOUND" }} else {{ "NOT_FOUND" }}
'''
        result = subprocess.run(
            ["powershell", "-Command", script],
            capture_output=True, text=True, timeout=5
        )
        return "FOUND" in result.stdout
    except:
        return False

def check_screen_for_text(search_text, timeout=3):
    """Capture screen and OCR to find specific text"""
    try:
        from ai_helper import ocr
        start = time.time()
        while time.time() - start < timeout:
            text = ocr()
            if search_text.lower() in text.lower():
                return True, text
            time.sleep(0.5)
        return False, ""
    except Exception as e:
        return False, f"[Error: {e}]"

def verify_launch(config):
    """
    Verify a launched process opened successfully.
    
    config: LaunchConfig object with:
        - name: friendly name
        - process_name: exe to check (e.g., "opencode.exe")
        - window_title: window title to check (optional)
        - gui: True to also check screen OCR
        - max_wait: max seconds to wait (default 30)
    
    Returns: dict with success, message, and timing info
    """
    result = {
        "success": False,
        "method": None,
        "message": None,
        "checks": [],
        "elapsed": 0
    }
    
    start_time = time.time()
    
    # First check at 0.5 seconds
    time.sleep(0.5)
    result["elapsed"] = 0.5
    
    # Check process
    if config.process_name:
        if check_process_running(config.process_name):
            result["success"] = True
            result["method"] = "process"
            result["message"] = f"Process {config.process_name} is running"
            result["checks"].append({"time": 0.5, "type": "process", "found": True})
            return result
        else:
            result["checks"].append({"time": 0.5, "type": "process", "found": False})
    
    # Check window title
    if config.window_title:
        if check_window_exists(config.window_title):
            result["success"] = True
            result["method"] = "window"
            result["message"] = f"Window '{config.window_title}' found"
            result["checks"].append({"time": 0.5, "type": "window", "found": True})
            return result
        else:
            result["checks"].append({"time": 0.5, "type": "window", "found": False})
    
    # Check screen for GUI apps
    if config.gui and config.screen_text:
        found, text = check_screen_for_text(config.screen_text, timeout=2)
        if found:
            result["success"] = True
            result["method"] = "screen_ocr"
            result["message"] = f"Found '{config.screen_text}' on screen"
            result["checks"].append({"time": 0.5, "type": "screen", "found": True})
            return result
        else:
            result["checks"].append({"time": 0.5, "type": "screen", "found": False, "text_preview": text[:100] if text else ""})
    
    # Continue checking at 1 second intervals
    interval = 1
    while result["elapsed"] < config.max_wait:
        time.sleep(interval)
        result["elapsed"] += interval
        
        # Check process
        if config.process_name:
            if check_process_running(config.process_name):
                result["success"] = True
                result["method"] = "process"
                result["message"] = f"Process {config.process_name} started after {result['elapsed']}s"
                result["checks"].append({"time": result["elapsed"], "type": "process", "found": True})
                return result
        
        # Check window
        if config.window_title:
            if check_window_exists(config.window_title):
                result["success"] = True
                result["method"] = "window"
                result["message"] = f"Window '{config.window_title}' appeared after {result['elapsed']}s"
                result["checks"].append({"time": result["elapsed"], "type": "window", "found": True})
                return result
        
        # Check screen
        if config.gui and config.screen_text:
            found, text = check_screen_for_text(config.screen_text, timeout=1)
            if found:
                result["success"] = True
                result["method"] = "screen_ocr"
                result["message"] = f"Found '{config.screen_text}' on screen after {result['elapsed']}s"
                result["checks"].append({"time": result["elapsed"], "type": "screen", "found": True})
                return result
    
    result["message"] = f"Failed to verify launch after {result['elapsed']}s"
    return result


class LaunchConfig:
    """Configuration for launch verification"""
    def __init__(self, name="app", process_name=None, window_title=None, 
                 gui=False, screen_text=None, max_wait=30):
        self.name = name
        self.process_name = process_name
        self.window_title = window_title
        self.gui = gui
        self.screen_text = screen_text
        self.max_wait = max_wait


def quick_verify(process_name, window_title=None, max_wait=10):
    """Quick verification for a process"""
    config = LaunchConfig(
        name=process_name,
        process_name=process_name,
        window_title=window_title,
        gui=window_title is not None,
        screen_text=window_title,
        max_wait=max_wait
    )
    return verify_launch(config)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python launch_verifier.py <process_name> [window_title]")
        sys.exit(1)
    
    process = sys.argv[1]
    window = sys.argv[2] if len(sys.argv) > 2 else None
    
    print(f"Checking if {process} started...")
    result = quick_verify(process, window)
    
    print(f"\nResult: {'SUCCESS' if result['success'] else 'FAILED'}")
    print(f"Method: {result['method']}")
    print(f"Message: {result['message']}")
    print(f"Elapsed: {result['elapsed']}s")
    print(f"Checks: {len(result['checks'])}")
    
    for check in result["checks"]:
        print(f"  - {check['time']}s: {check['type']} = {check['found']}")