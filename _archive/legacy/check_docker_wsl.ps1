# Diagnostic and Fix Script for Docker + WSL2 + Redis

Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "DOCKER + WSL2 + REDIS DIAGNOSTIC & SETUP" -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Cyan

# Step 1: Check Windows Features
Write-Host "`n[STEP 1] Checking Windows Features..." -ForegroundColor Yellow

$wslFeature = Get-WindowsOptionalFeature -Online -FeatureName "Microsoft-Windows-Subsystem-Linux" -ErrorAction SilentlyContinue
$vmFeature = Get-WindowsOptionalFeature -Online -FeatureName "VirtualMachinePlatform" -ErrorAction SilentlyContinue

if ($wslFeature) {
    Write-Host "  WSL Feature: $($wslFeature.State)" -ForegroundColor $(if($wslFeature.State -eq "Enabled") {"Green"} else {"Red"})
} else {
    Write-Host "  WSL Feature: Could not check" -ForegroundColor Red
}

if ($vmFeature) {
    Write-Host "  VM Platform: $($vmFeature.State)" -ForegroundColor $(if($vmFeature.State -eq "Enabled") {"Green"} else {"Red"})
} else {
    Write-Host "  VM Platform: Could not check" -ForegroundColor Red
}

# Step 2: Check WSL
Write-Host "`n[STEP 2] Checking WSL Status..." -ForegroundColor Yellow

$wslOutput = wsl --list --verbose 2>&1
if ($wslOutput -like "*The service*") {
    Write-Host "  ERROR: WSL service is not running" -ForegroundColor Red
    Write-Host "  Solution: Restart required after WSL enable, or manually start LxssManager service" -ForegroundColor Yellow
} else {
    Write-Host "  WSL Status: Running" -ForegroundColor Green
    $wslOutput | Write-Host
}

# Step 3: Check Docker
Write-Host "`n[STEP 3] Checking Docker..." -ForegroundColor Yellow

$dockerProcess = Get-Process "Docker Desktop" -ErrorAction SilentlyContinue
if ($dockerProcess) {
    Write-Host "  Docker Desktop: Running (PID: $($dockerProcess.Id))" -ForegroundColor Green
} else {
    Write-Host "  Docker Desktop: Not running" -ForegroundColor Red
    Write-Host "  Action: Start Docker Desktop from Start menu" -ForegroundColor Yellow
}

$dockerInfo = docker info 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  Docker CLI: Connected" -ForegroundColor Green
} else {
    Write-Host "  Docker CLI: Not connected" -ForegroundColor Red
}

# Step 4: Check Redis Files
Write-Host "`n[STEP 4] Checking Redis Docker Files..." -ForegroundColor Yellow

$redisCompose = Test-Path "E:\AI-Setup\dockerized-ai\redis\docker-compose.yml"
Write-Host "  Simple docker-compose.yml: $(if($redisCompose) {'Found'} else {'NOT FOUND'})" -ForegroundColor $(if($redisCompose) {"Green"} else {"Red"})

$redisHA = Test-Path "E:\AI-Setup\dockerized-ai\redis\docker-compose-ha.yml"
Write-Host "  HA docker-compose.yml: $(if($redisHA) {'Found'} else {'NOT FOUND'})" -ForegroundColor $(if($redisHA) {"Green"} else {"Red"})

# Step 5: Quick Test
Write-Host "`n[STEP 5] Testing Docker..." -ForegroundColor Yellow

$testResult = docker run --rm hello-world 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  Docker Test: SUCCESS" -ForegroundColor Green
} else {
    Write-Host "  Docker Test: FAILED" -ForegroundColor Red
    Write-Host "  Error: $testResult" -ForegroundColor Red
}

# Summary and Next Steps
Write-Host "`n=====================================================================" -ForegroundColor Cyan
Write-Host "NEXT STEPS" -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Cyan

Write-Host @"
1. If WSL service is not running:
   - System restart required to activate WSL2 features
   - Or manually: Start-Service LxssManager

2. If Docker Desktop is not running:
   - Click Start menu, search "Docker Desktop", launch it
   - Wait 30-60 seconds for it to fully start

3. Once WSL and Docker are running, start Redis:
   cd E:\AI-Setup\dockerized-ai\redis
   docker-compose -f docker-compose.yml up -d

4. Verify Redis is running:
   docker ps | findstr redis
   docker-compose logs redis

5. Test Redis connection:
   docker exec -it ai-redis redis-cli ping

6. Then run the Bootstrap API test:
   cd E:\AI-Setup
   py test_bootstrap_api_no_docs.py
"@

Write-Host "`n=====================================================================" -ForegroundColor Cyan
