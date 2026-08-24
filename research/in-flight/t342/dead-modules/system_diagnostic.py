import mss
import subprocess
import os
import socket
import time
from context_cache import capture_to_ram, get_latest_screenshot, get_screenshot_count

# Import our RAM-based screenshot system
# Screenshots now stored in RAM, not disk!

def check_port(port):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        return result == 0
    except:
        return False

def get_windows():
    """Get all visible windows using PowerShell"""
    script = '''
Add-Type @"
using System;
using System.Runtime.InteropServices;
using System.Text;
public class Win32 {
    [DllImport("user32.dll")]
    public static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);
    public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
    [DllImport("user32.dll")]
    public static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);
    [DllImport("user32.dll")]
    public static extern int GetWindowTextLength(IntPtr hWnd);
    [DllImport("user32.dll")]
    public static extern bool IsWindowVisible(IntPtr hWnd);
}
"@
$windows = @()
$callback = [Win32+EnumWindowsProc]{
    param($hWnd, $param)
    if ([Win32]::IsWindowVisible($hWnd)) {
        $len = [Win32]::GetWindowTextLength($hWnd)
        if ($len -gt 0) {
            $sb = New-Object System.Text.StringBuilder($len + 1)
            [void][Win32]::GetWindowText($hWnd, $sb, $sb.Capacity)
            $title = $sb.ToString()
            if ($title.Length -gt 0) { $script:windows += $title }
        }
    }
    return $true
}
[void][Win32]::EnumWindows($callback, [IntPtr]::Zero)
$windows | Select-Object -First 20
'''
    try:
        result = subprocess.run([
            'powershell', '-Command', script
        ], capture_output=True, text=True, timeout=10)
        return result.stdout.strip().split('\n') if result.stdout else []
    except Exception as e:
        return [f"Error: {e}"]

def main():
    print("=" * 60)
    print("  System Diagnostic Tool")
    print("=" * 60)
    print()
    
    # List windows
    print("[WINDOWS]")
    print("-" * 40)
    windows = get_windows()
    for i, w in enumerate(windows[:15]):
        print(f"{i+1}. {w}")
    print()
    
    # Check services
    print("[SERVICES]")
    print("-" * 40)
    services = [
        ("Dashboard", 8501),
        ("Ollama", 11434),
        ("Redis", 6379),
        ("Open WebUI", 3000),
    ]
    for name, port in services:
        status = "RUNNING" if check_port(port) else "STOPPED"
        print(f"{name} (port {port}): {status}")
    print()
    
    # Check Docker
    print("[DOCKER CONTAINERS]")
    print("-" * 40)
    try:
        result = subprocess.run(['docker', 'ps', '--format', '{{.Names}}\t{{.Status}}'], 
                              capture_output=True, text=True, timeout=5)
        print(result.stdout if result.stdout else "No containers")
    except:
        print("Docker not accessible")
    print()
    
    # Check WSL2 Ollama
    print("[OLLAMA - WSL2]")
    print("-" * 40)
    try:
        result = subprocess.run(['wsl', '-d', 'Ubuntu-24.04', '-e', 'docker', 'ps', '--filter', 'name=ollama'], 
                              capture_output=True, text=True, timeout=10)
        print(result.stdout if result.stdout else "No Ollama container")
    except:
        print("WSL2 Ollama not accessible")
    print()
    
    # Capture screenshot to RAM
    print("[SCREENSHOT - RAM]")
    print("-" * 40)
    count = capture_to_ram()
    print(f"Screenshots in RAM: {count}")
    latest = get_latest_screenshot()
    if latest:
        print(f"Latest: {latest['width']}x{latest['height']}")
        print(f"Size: {latest['size_bytes']/1024/1024:.2f}MB in RAM")
    print()
    
    print("=" * 60)
    print("  Done! Screenshots stored in RAM (no disk writes)")

if __name__ == "__main__":
    main()