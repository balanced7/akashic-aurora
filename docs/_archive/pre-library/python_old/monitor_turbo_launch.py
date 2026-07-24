"""
Monitor Turbo Launch - Uses Fast Cache + Screenspace
==================================================
"""
import sys
sys.path.insert(0, r'E:\AI-Setup')

import json
import time
from fast_cache import redis_get, redis_set, get_cache_status
from ai_setup_mcp import (
    list_windows, capture_window, ocr, screenshot,
    get_cursor_position, activate_window
)

def get_window_list_cached():
    """Get windows using cache - fast"""
    # Check cache first (10 second TTL)
    cached = redis_get("windows:list")
    if cached:
        return cached, True  # cached
    
    # Get fresh list
    import subprocess
    import ctypes
    from ctypes import wintypes
    
    EnumWindows = ctypes.windll.user32.EnumWindows
    GetWindowText = ctypes.windll.user32.GetWindowTextW
    IsWindowVisible = ctypes.windll.user32.IsWindowVisible
    GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
    
    windows = []
    def enum_callback(hwnd, lparam):
        if IsWindowVisible(hwnd):
            length = GetWindowTextLength(hwnd)
            if length > 0:
                buffer = ctypes.create_unicode_buffer(length + 1)
                GetWindowText(hwnd, buffer, length + 1)
                title = buffer.value
                if title:
                    windows.append(title)
        return True
    
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    EnumWindows(EnumWindowsProc(enum_callback), 0)
    
    result = {"windows": windows, "count": len(windows)}
    redis_set("windows:list", result, ttl=10)  # Cache for 10 seconds
    
    return result, False  # fresh


def monitor_launch():
    print("=" * 60)
    print("  TURBO LAUNCH MONITOR")
    print("=" * 60)
    print()
    
    # Initial state
    print("[INIT] Cache status:")
    status = get_cache_status()
    print("  RAM: " + str(status['ram_cache_entries']) + " entries")
    print("  RAM Disk: " + status['ram_disk'])
    print("  Redis: " + ("OK" if status['redis_available'] else "DOWN"))
    print()
    
    # Get initial windows (cached)
    windows, cached = get_window_list_cached()
    print("[INIT] Windows: " + str(windows['count']) + " (" + ("cached" if cached else "fresh") + ")")
    
    # Take initial screenshot
    print("[INIT] Taking screenshot...")
    result = json.loads(screenshot("monitor_start"))
    if result['success']:
        print("  Screenshot: " + result['path'])
    
    # Start the launch in background
    import subprocess
    print()
    print("[LAUNCH] Starting turbo_launch.bat...")
    proc = subprocess.Popen(
        ['cmd', '/c', r'E:\AI-Setup\turbo_launch.bat'],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    
    # Monitor loop
    print()
    print("[MONITOR] Watching for changes every 1 second...")
    print("-" * 60)
    
    opencode_found = False
    for i in range(30):
        time.sleep(1)
        
        # Check cache status
        if i % 5 == 0:
            cache_status = get_cache_status()
            print("[" + str(i) + "s] Cache: RAM(" + str(cache_status['ram_cache_entries']) + ")")
        
        # Get windows (uses cache)
        windows, from_cache = get_window_list_cached()
        
        # Look for OpenCode
        opencode_windows = [w for w in windows['windows'] if 'OpenCode' in w or 'opencode' in w.lower()]
        
        # Get cursor position
        cursor = json.loads(get_cursor_position())
        
        # Every 5 seconds, take a screenshot
        if i % 5 == 0 and i > 0:
            result = json.loads(screenshot("monitor_" + str(i) + "s"))
        
        # Status line
        status = "[" + str(i) + "s] Windows: " + str(windows['count'])
        if opencode_windows:
            status += " | OpenCode: FOUND at (" + str(cursor['x']) + "," + str(cursor['y']) + ")"
        else:
            status += " | Cursor: (" + str(cursor['x']) + "," + str(cursor['y']) + ")"
        
        print(status)
        
        # If OpenCode found, capture it
        if opencode_windows and not opencode_found:
            opencode_found = True
            print()
            print(">>> OpenCode window detected!")
            print("    " + opencode_windows[0])
            
            # Try to capture the window
            result = capture_window("OpenCode")
            cap = json.loads(result)
            if cap['success']:
                print("    Captured: " + cap['path'])
                # OCR it
                text = ocr(cap['path'])
                print()
                print(">>> OCR Content:")
                print(text[:500])
            break
        
        # Check if launch script ended
        if proc.poll() is not None:
            print()
            print("[DONE] Launch script finished")
            break
    
    # Final state
    print()
    print("=" * 60)
    print("  FINAL STATE")
    print("=" * 60)
    
    final_windows, _ = get_window_list_cached()
    print("Total windows: " + str(final_windows['count']))
    
    for w in final_windows['windows']:
        if 'OpenCode' in w or 'opencode' in w.lower():
            print("OpenCode: " + w)
    
    # Final screenshot
    print()
    print("[FINAL] Taking screenshot...")
    result = json.loads(screenshot("monitor_final"))
    if result['success']:
        text = ocr(result['path'])
        print("OCR of final screen (first 1000 chars):")
        print(text[:1000])
    
    # Cache summary
    print()
    final_cache = get_cache_status()
    print("Cache hits: " + str(final_cache['ram_cache_entries']) + " RAM entries")
    print("RAM disk files: " + str(final_cache['ramdisk_files']))
    
    return opencode_found


if __name__ == "__main__":
    success = monitor_launch()
    print()
    if success:
        print("[OK] Turbo Launch succeeded - OpenCode window found!")
    else:
        print("[WARN] OpenCode window not found - checking for issues...")
