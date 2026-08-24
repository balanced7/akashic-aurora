import mss
import os
import subprocess
import sys

# Fix Unicode for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def capture_screen():
    """Capture primary monitor"""
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        screenshot = sct.grab(monitor)
        return screenshot

def list_windows():
    """List all open windows using PowerShell"""
    try:
        result = subprocess.run([
            'powershell', '-Command',
            'Get-Process | Where-Object {$_.MainWindowTitle} | Select-Object -First 15 Name, MainWindowTitle | Format-Table -AutoSize'
        ], capture_output=True, text=True, timeout=10)
        return result.stdout
    except Exception as e:
        return f"Error: {e}"

def check_docker_desktop():
    """Check if Docker Desktop is running"""
    try:
        result = subprocess.run([
            'powershell', '-Command',
            'Get-Process -Name "docker*" -ErrorAction SilentlyContinue | Select-Object Name, Id'
        ], capture_output=True, text=True, timeout=5)
        if result.stdout.strip():
            return f"Docker process found:\n{result.stdout}"
        return "Docker Desktop not running (no docker process found)"
    except Exception as e:
        return f"Error checking Docker: {e}"

def check_ollama():
    """Check Ollama status via WSL"""
    try:
        result = subprocess.run([
            'wsl', '-d', 'Ubuntu-24.04', '-e', 'docker', 'ps', '--filter', 'name=ollama'
        ], capture_output=True, text=True, timeout=10)
        return f"Ollama containers:\n{result.stdout}"
    except Exception as e:
        return f"Error: {e}"

def main():
    print("=" * 60)
    print("  Screen Monitor & System Diagnostics")
    print("=" * 60)
    print()
    
    # List windows
    print("[OPEN WINDOWS]")
    print("-" * 40)
    print(list_windows())
    print()
    
    # Check Docker
    print("[DOCKER STATUS]")
    print("-" * 40)
    print(check_docker_desktop())
    print()
    
    # Check Ollama in WSL
    print("[OLLAMA - WSL2]")
    print("-" * 40)
    print(check_ollama())
    print()
    
    # Capture screen
    print("[CAPTURING SCREEN...]")
    print("-" * 40)
    screenshot = capture_screen()
    
    # Save to file
    output_path = os.path.expanduser("~/Desktop/screen_capture.png")
    mss.tools.to_png(screenshot.rgb, screenshot.size, output=output_path)
    print(f"Screen captured to: {output_path}")
    print(f"Resolution: {screenshot.width}x{screenshot.height}")
    
    print()
    print("=" * 60)
    print("  Done! Check the captured image on your desktop.")

if __name__ == "__main__":
    main()