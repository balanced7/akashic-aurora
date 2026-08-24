"""
Window Monitor - Detect failed windows and cleanup
===================================================
Checks if launched windows opened correctly and can close failed ones.

Usage:
    from window_monitor import verify_window_opened, close_window, get_window_status
    
    # After launching something
    result = verify_window_opened("OpenCode Primed", timeout=10)
    
    if result["success"]:
        print("Window opened successfully!")
    else:
        print(f"Failed: {result['reason']}")
        close_window("OpenCode Primed")  # Clean up
"""
import subprocess
import time
import sys
sys.path.insert(0, r"E:\AI-Setup")

def list_windows():
    """Get list of all windows"""
    result = subprocess.run(
        ["powershell", "-Command", "Get-Process | Where-Object {$_.MainWindowTitle} | Select-Object Id, MainWindowTitle | ConvertTo-Json"],
        capture_output=True, text=True, timeout=10
    )
    try:
        import json
        data = json.loads(result.stdout)
        if isinstance(data, list):
            return data
        return [data]
    except:
        return []

def verify_window_opened(window_pattern, timeout=10):
    """
    Verify a window opened successfully.
    
    Returns:
        dict with success, window_title, reason
    """
    start = time.time()
    window_pattern = window_pattern.lower()
    
    while time.time() - start < timeout:
        windows = list_windows()
        
        for w in windows:
            title = w.get("MainWindowTitle", "")
            if title and window_pattern in title.lower():
                return {
                    "success": True,
                    "window_title": title,
                    "pid": w.get("Id"),
                    "reason": "Window found"
                }
        
        time.sleep(1)
    
    return {
        "success": False,
        "reason": f"Window '{window_pattern}' not found after {timeout}s"
    }

def close_window(window_pattern):
    """
    Close a window by name pattern.
    """
    script = f'''
$windows = Get-Process | Where-Object {{$_.MainWindowTitle -like "*{window_pattern}*"}}
if ($windows) {{
    $windows | ForEach-Object {{ 
        Write-Host "Closing: $($_.MainWindowTitle) (PID: $($_.Id))"
        $_.CloseMainWindow() 
    }}
    Start-Sleep 1
    $still_running = Get-Process | Where-Object {{$_.MainWindowTitle -like "*{window_pattern}*"}}
    if ($still_running) {{
        Write-Host "Force killing..."
        Stop-Process -Id $still_running.Id -Force
    }}
}} else {{
    Write-Host "No window matching '{window_pattern}' found"
}}
'''
    subprocess.run(["powershell", "-Command", script], capture_output=True)
    return True

def close_failed_launchers():
    """Close any orphaned launcher windows"""
    patterns = ["OpenCode Primed", "primed_opencode", "launcher"]
    
    for pattern in patterns:
        close_window(pattern)

def get_window_status():
    """Get status of all relevant windows"""
    windows = list_windows()
    
    status = {
        "opencode": None,
        "primed": [],
        "other": []
    }
    
    for w in windows:
        title = w.get("MainWindowTitle", "")
        pid = w.get("Id")
        
        if "OC" in title or "opencode" in title.lower():
            status["opencode"] = {"title": title, "pid": pid}
        elif "primed" in title.lower():
            status["primed"].append({"title": title, "pid": pid})
        else:
            status["other"].append({"title": title, "pid": pid})
    
    return status


if __name__ == "__main__":
    print("=== WINDOW MONITOR ===")
    
    status = get_window_status()
    print(f"\nOpenCode: {status['opencode']}")
    print(f"Primed windows: {len(status['primed'])}")
    for p in status['primed']:
        print(f"  - {p['title']} (PID: {p['pid']})")
    
    print("\n[OK] Window status checked")