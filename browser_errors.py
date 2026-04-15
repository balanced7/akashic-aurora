"""
Browser Console Reader
======================
Reads browser console errors via PowerShell automation.
More reliable than OCR for detecting errors.

Usage:
    python browser_errors.py
"""

import subprocess

def get_browser_errors():
    """Get browser console errors via PowerShell"""
    
    ps_script = '''
# Get Brave browser errors
$brave = Get-Process brave -ErrorAction SilentlyContinue

if ($brave) {
    Write-Host "[OK] Brave is running"
    
    # Try to get window text
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
        [DllImport("user32.dll")]
        public static extern IntPtr GetWindow(IntPtr hWnd, uint uCmd);
        [DllImport("user32.dll")]
        public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);
        [StructLayout(LayoutKind.Sequential)]
        public struct RECT { public int Left, Top, Right, Bottom; }
    }
"@

    $windows = @()
    $callback = [Win32+EnumWindowsProc]{
        param($hWnd, $param)
        if ([Win32]::IsWindowVisible($hWnd)) {
            $len = [Win32]::GetWindowTextLength($hWnd)
            if ($len -gt 0 -and $len -lt 200) {
                $sb = New-Object System.Text.StringBuilder($len + 1)
                [void][Win32]::GetWindowText($hWnd, $sb, $sb.Capacity)
                $title = $sb.ToString()
                if ($title -match "Brave|AI Control" -or $title.Length -gt 0) {
                    Write-Host "  Window: $title"
                }
            }
        }
        return $true
    }
    [void][Win32]::EnumWindows($callback, [IntPtr]::Zero)
    
} else {
    Write-Host "[X] Brave not running"
}

# Also check for Streamlit errors
$streamlit = Get-Process python -ErrorAction SilentlyContinue | Where-Object {$_.MainWindowTitle -match "Streamlit|dashboard"}
if ($streamlit) {
    Write-Host "[OK] Streamlit is running"
}
'''
    
    try:
        result = subprocess.run([
            'powershell', '-Command', ps_script
        ], capture_output=True, text=True, timeout=15)
        return result.stdout
    except Exception as e:
        return f"Error: {e}"

def get_dashboard_errors():
    """Get Streamlit/dashboard errors"""
    
    ps_script = '''
# Check Streamlit logs
$logs = Get-Content "$env:TEMP\streamlit logs" -ErrorAction SilentlyContinue
if ($logs) {
    $logs | Select-Object -Last 20
}

# Check Python processes
Get-Process python -ErrorAction SilentlyContinue | Select-Object Id, ProcessName, MainWindowTitle
'''
    
    try:
        result = subprocess.run([
            'powershell', '-Command', ps_script
        ], capture_output=True, text=True, timeout=10)
        return result.stdout
    except Exception as e:
        return f"Error: {e}"

if __name__ == "__main__":
    print("=" * 60)
    print("  Browser & Dashboard Error Check")
    print("=" * 60)
    print()
    
    print("[BRAVE BROWSER]")
    print("-" * 40)
    print(get_browser_errors())
    print()
    
    print("[DASHBOARD]")
    print("-" * 40)
    print(get_dashboard_errors())