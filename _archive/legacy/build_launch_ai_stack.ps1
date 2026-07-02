# Build "Launch AI Stack.exe" with PyInstaller (windowed, one-file).
# Prerequisite: pip install pyinstaller
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    Write-Host "Installing PyInstaller..." -ForegroundColor Yellow
    python -m pip install pyinstaller
}

pyinstaller --noconfirm "Launch AI Stack.spec"

Write-Host ""
Write-Host "Done: dist\Launch AI Stack.exe" -ForegroundColor Green
Write-Host "Copy the exe into E:\AI-Setup (same folder as stack_gui.py) or set AI_SETUP_ROOT." -ForegroundColor Cyan
