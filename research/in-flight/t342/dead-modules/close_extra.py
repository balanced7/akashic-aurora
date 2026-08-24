"""Close extra PowerShell/cmd windows"""
import sys
sys.path.insert(0, r"E:\AI-Setup")

from window_monitor import close_window, get_window_status

print("=== FINDING EXTRA WINDOWS ===\n")

# Get status
status = get_window_status()

print("Current windows:")
print(f"  OC (main): {status['opencode']}")
print(f"  Primed: {len(status['primed'])} primed windows")
for p in status['primed']:
    print(f"    - {p['title']} (PID: {p['pid']})")

# Close extra windows
print("\n=== CLOSING EXTRA WINDOWS ===")

# Close "OpenCode Primed" launcher windows (they failed)
close_window("OpenCode Primed")
print("Closed: OpenCode Primed windows")

# Close any other extra cmd windows except the main one
# Let's list them first to see what we're dealing with
print("\nAll cmd.exe windows:")
result = __import__('subprocess').run(
    ["powershell", "-Command", "Get-Process -Name cmd | Select-Object Id, MainWindowTitle | ConvertTo-Json"],
    capture_output=True, text=True
)

import json
try:
    procs = json.loads(result.stdout)
    if isinstance(procs, list):
        for p in procs:
            title = p.get("MainWindowTitle", "")
            pid = p.get("Id")
            print(f"  PID {pid}: {title}")
except:
    print("  (couldn't parse)")

print("\n[Done] Use window_monitor.close_window() to close specific ones")