"""
Launch Brave with Remote Debugging
=================================
Simple script to launch Brave with remote debugging port enabled.

Run this BEFORE using gemini_bridge.py:
    python launch_brave_remote.py

Or double-click this file to launch Brave with debugging.
"""

import os
import sys
import subprocess

BRAVE_PATH = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
DEBUG_PORT = "9222"

def launch_brave_with_debugging():
    """Launch Brave with remote debugging enabled"""
    
    # Check if Brave exists
    if not os.path.exists(BRAVE_PATH):
        print(f"[ERROR] Brave not found at: {BRAVE_PATH}")
        print("\nPlease install Brave or update BRAVE_PATH in this script.")
        return False
    
    # Check if already running on the port
    try:
        import urllib.request
        with urllib.request.urlopen(f"http://127.0.0.1:{DEBUG_PORT}/json", timeout=1):
            print(f"[INFO] Brave already running with debugging on port {DEBUG_PORT}")
            return True
    except:
        pass  # Not running, proceed
    
    # Launch Brave with debugging
    cmd = [BRAVE_PATH, f"--remote-debugging-port={DEBUG_PORT}"]
    
    try:
        subprocess.Popen(cmd, shell=True)
        print(f"[OK] Launched Brave with remote debugging on port {DEBUG_PORT}")
        print(f"[OK] Command: {' '.join(cmd)}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to launch: {e}")
        return False


def test_connection():
    """Test if remote debugging is available"""
    try:
        import urllib.request
        with urllib.request.urlopen(f"http://127.0.0.1:{DEBUG_PORT}/json", timeout=2) as response:
            data = json.loads(response.read()) if hasattr(response, 'read') else {}
            print(f"[OK] Remote debugging active")
            print(f"     URL: http://127.0.0.1:{DEBUG_PORT}")
            return True
    except Exception as e:
        print(f"[WARN] Cannot connect to remote debugging")
        print(f"       Make sure Brave is running with --remote-debugging-port={DEBUG_PORT}")
        return False


if __name__ == "__main__":
    import json
    
    print("=" * 60)
    print("Brave Remote Debugging Launcher")
    print("=" * 60)
    
    print("\nThis script launches Brave with remote debugging enabled.")
    print("This allows gemini_bridge.py to attach to your existing session.")
    print()
    
    # First check if already running
    try:
        import urllib.request
        with urllib.request.urlopen(f"http://127.0.0.1:{DEBUG_PORT}/json", timeout=1) as response:
            print(f"[INFO] Brave already running on port {DEBUG_PORT}")
            print("\nYou can now use gemini_bridge.py!")
            sys.exit(0)
    except:
        pass
    
    # Launch Brave
    print("\n[1] Launching Brave with remote debugging...")
    if launch_brave_with_debugging():
        print("\n[2] Waiting for Brave to start...")
        import time
        time.sleep(3)
        
        print("\n[3] Testing connection...")
        if test_connection():
            print("\n[OK] Ready to use gemini_bridge.py!")
        else:
            print("\n[WARN] Could not verify connection")
            print("       Try running this script again or check Brave manually")
    else:
        print("\n[ERROR] Failed to launch Brave")
        print("\nManual launch command:")
        print(f"    {BRAVE_PATH} --remote-debugging-port={DEBUG_PORT}")
    
    print("=" * 60)
