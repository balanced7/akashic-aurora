"""Quick launcher with built-in verification - launches and confirms"""
import subprocess
import sys
import time

def run_and_verify(cmd, check_for, timeout=3):
    """Run command and verify target appears in windows"""
    print(f"[LAUNCH] {cmd}")
    subprocess.run(cmd, shell=True)
    
    # Wait briefly and check
    for i in range(timeout * 2):
        time.sleep(0.5)
        result = subprocess.run(
            ["python", "-m", "naturo", "list", "windows"],
            capture_output=True, text=True
        )
        if check_for.lower() in result.stdout.lower():
            print(f"[OK] Found: {check_for}")
            return True
    
    print(f"[FAIL] Not found: {check_for}")
    return False

if __name__ == "__main__":
    # Launch Windows Terminal for Daniil
    run_and_verify(
        "start C:\\Users\\L5\\Desktop\\primed_powershell.bat",
        "AI Control Center",
        timeout=3
    )