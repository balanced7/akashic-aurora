# Fix WSL and Docker - Run as Administrator

Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "FIXING WSL AND DOCKER" -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Cyan

# Check if running as admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] 'Administrator')
if (-not $isAdmin) {
    Write-Host "`nWARNING: This script should be run as Administrator!" -ForegroundColor Red
    Write-Host "Please right-click PowerShell and choose 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

Write-Host "`n[STEP 1] Attempting to restart WSL service..." -ForegroundColor Yellow

try {
    # Try to restart the LxssManager service
    Write-Host "  Stopping LxssManager..." -ForegroundColor Cyan
    Stop-Service LxssManager -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2

    Write-Host "  Starting LxssManager..." -ForegroundColor Cyan
    Start-Service LxssManager -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 3

    # Check if it's running
    $svc = Get-Service LxssManager -ErrorAction SilentlyContinue
    if ($svc.Status -eq "Running") {
        Write-Host "  SUCCESS: LxssManager is now running" -ForegroundColor Green
    } else {
        Write-Host "  FAILED: LxssManager still not running" -ForegroundColor Red
        Write-Host "  Status: $($svc.Status)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ERROR: Could not manage LxssManager service" -ForegroundColor Red
    Write-Host "  Error: $_" -ForegroundColor Red
}

Write-Host "`n[STEP 2] Restarting Docker Desktop..." -ForegroundColor Yellow

# Kill Docker processes and restart
$dockerProcs = Get-Process "Docker Desktop" -ErrorAction SilentlyContinue
if ($dockerProcs) {
    Write-Host "  Stopping Docker Desktop processes..." -ForegroundColor Cyan
    Stop-Process -Name "Docker Desktop" -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 3
}

Write-Host "  Starting Docker Desktop..." -ForegroundColor Cyan
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe" -ErrorAction SilentlyContinue
Write-Host "  Waiting for Docker to start (30 seconds)..." -ForegroundColor Cyan

# Wait and check
for ($i = 0; $i -lt 30; $i++) {
    Write-Host -NoNewline "."
    Start-Sleep -Seconds 1

    $dockerTest = docker info 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "`n  SUCCESS: Docker is running" -ForegroundColor Green
        break
    }
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n  WARNING: Docker may still be starting" -ForegroundColor Yellow
}

Write-Host "`n[STEP 3] Testing WSL..." -ForegroundColor Yellow

$wslTest = wsl --list --verbose 2>&1
if ($wslTest -like "*The service*") {
    Write-Host "  WSL service error persists" -ForegroundColor Red
    Write-Host "  RECOMMENDATION: System restart required" -ForegroundColor Yellow
} else {
    Write-Host "  WSL is responding" -ForegroundColor Green
    Write-Host $wslTest
}

Write-Host "`n=====================================================================" -ForegroundColor Cyan
Write-Host "WHAT TO DO NEXT" -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Cyan

Write-Host @"

OPTION A: If WSL is still showing service error
  - Perform a SYSTEM RESTART
  - WSL2 changes require a restart to fully activate
  - After restart, run this script again

OPTION B: If Docker is now running
  1. Open PowerShell (regular, not admin needed)
  2. Run: cd E:\AI-Setup\dockerized-ai\redis
  3. Run: docker-compose -f docker-compose.yml up -d
  4. Wait 10 seconds
  5. Run: docker exec -it ai-redis redis-cli ping
     (Should see "PONG")
  6. Then: cd E:\AI-Setup
  7. Run: py test_bootstrap_api_no_docs.py

OPTION C: If you want to skip Redis (use file fallback)
  - Redis is optional; system works with file storage
  - Just run: cd E:\AI-Setup && py test_bootstrap_api_no_docs.py
  - Initialization will be slower but will work
"@

Write-Host "`n=====================================================================" -ForegroundColor Cyan
