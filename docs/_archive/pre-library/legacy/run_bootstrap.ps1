# ==========================================
# Akashic Aurora Bootstrap (WSL2 + Redis Stack)
# ==========================================

Write-Host "=== Akashic Aurora Bootstrap (WSL2 + Redis Stack) ===" -ForegroundColor Cyan

# Step 1: Check WSL2
Write-Host "[1/7] Checking WSL2..." -ForegroundColor Yellow
wsl -l -v | Select-String "Ubuntu-Migrate"
if ($LASTEXITCODE -ne 0) { Write-Host "  [FAIL] Ubuntu-Migrate not found" -ForegroundColor Red; exit 1 }
Write-Host "  [OK] Ubuntu-Migrate found" -ForegroundColor Green

# Step 2: Stop old containers
Write-Host "[2/7] Stopping old containers..." -ForegroundColor Yellow
cd E:\AI-Setup\dockerized-ai\redis
docker compose -f docker-compose-ha.yml down 2>$null
Write-Host "  [OK] Old containers stopped" -ForegroundColor Green

# Step 3: Start Redis Stack HA in WSL2
Write-Host "[3/7] Starting Redis Stack HA in WSL2..." -ForegroundColor Yellow
wsl -d Ubuntu-Migrate -e bash -c "
  pkill -9 -f 'redis-server' 2>/dev/null
  pkill -9 -f 'redis-sentinel' 2>/dev/null
  sleep 2
  redis-server /opt/redis/master/redis-master.conf --daemonize yes --logfile /var/log/redis/master.log
  sleep 2
  redis-server /opt/redis/replica1/redis-replica1.conf --daemonize yes --logfile /var/log/redis/replica1.log
  redis-server /opt/redis/replica2/redis-replica2.conf --daemonize yes --logfile /var/log/redis/replica2.log
  sleep 2
  redis-cli -p 6380 REPLICAOF 127.0.0.1 6379 2>/dev/null || true
  redis-cli -p 6381 REPLICAOF 127.0.0.1 6379 2>/dev/null || true
  sleep 2
  redis-server /opt/redis/sentinel1/sentinel1.conf --sentinel --daemonize yes --logfile /var/log/redis/sentinel1.log
  redis-server /opt/redis/sentinel2/sentinel2.conf --sentinel --daemonize yes --logfile /var/log/redis/sentinel2.log
  redis-server /opt/redis/sentinel3/sentinel3.conf --sentinel --daemonize yes --logfile /var/log/redis/sentinel3.log
  sleep 3
"
Write-Host "  [OK] Redis Stack HA started in WSL2" -ForegroundColor Green

# Step 4: Wait and verify all 6 services
Write-Host "[4/7] Verifying all 6 Redis services..." -ForegroundColor Yellow
Start-Sleep 3

$masterPing = wsl -d Ubuntu-Migrate -e bash -c "redis-cli -p 6379 PING 2>/dev/null"
$replica1Ping = wsl -d Ubuntu-Migrate -e bash -c "redis-cli -p 6380 PING 2>/dev/null"
$replica2Ping = wsl -d Ubuntu-Migrate -e bash -c "redis-cli -p 6381 PING 2>/dev/null"
$sentinel1Ping = wsl -d Ubuntu-Migrate -e bash -c "redis-cli -p 26379 PING 2>/dev/null"
$sentinel2Ping = wsl -d Ubuntu-Migrate -e bash -c "redis-cli -p 26380 PING 2>/dev/null"
$sentinel3Ping = wsl -d Ubuntu-Migrate -e bash -c "redis-cli -p 26381 PING 2>/dev/null"

if ($masterPing -eq "PONG") { Write-Host "  [OK] Master (6379) responding" -ForegroundColor Green } else { Write-Host "  [FAIL] Master not responding!" -ForegroundColor Red }
if ($replica1Ping -eq "PONG") { Write-Host "  [OK] Replica1 (6380) responding" -ForegroundColor Green } else { Write-Host "  [FAIL] Replica1 not responding!" -ForegroundColor Red }
if ($replica2Ping -eq "PONG") { Write-Host "  [OK] Replica2 (6381) responding" -ForegroundColor Green } else { Write-Host "  [FAIL] Replica2 not responding!" -ForegroundColor Red }
if ($sentinel1Ping -eq "PONG") { Write-Host "  [OK] Sentinel1 (26379) responding" -ForegroundColor Green } else { Write-Host "  [FAIL] Sentinel1 not responding!" -ForegroundColor Red }
if ($sentinel2Ping -eq "PONG") { Write-Host "  [OK] Sentinel2 (26380) responding" -ForegroundColor Green } else { Write-Host "  [FAIL] Sentinel2 not responding!" -ForegroundColor Red }
if ($sentinel3Ping -eq "PONG") { Write-Host "  [OK] Sentinel3 (26381) responding" -ForegroundColor Green } else { Write-Host "  [FAIL] Sentinel3 not responding!" -ForegroundColor Red }

# Step 5: Test Redis Stack modules
Write-Host "[5/7] Testing Redis Stack modules..." -ForegroundColor Yellow
$modules = wsl -d Ubuntu-Migrate -e bash -c "redis-cli -p 6379 MODULE LIST 2>/dev/null"
Write-Host "  Loaded modules:" -ForegroundColor Cyan
Write-Host $modules

# Step 6: Start Session Compressor
Write-Host "[6/7] Starting Session Compressor..." -ForegroundColor Yellow
$compressorRunning = Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like '*session_compressor*' }
if ($compressorRunning) {
  Write-Host "  [OK] Session Compressor already running" -ForegroundColor Green
} else {
  pip install sentence-transformers requests redis 2>$null | Out-Null
  Start-Process -FilePath "python" -ArgumentList "E:\AI-Setup\session_compressor.py", "--daemon" -WindowStyle Hidden
  Start-Sleep 3
  $compressorCheck = Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like '*session_compressor*' }
  if ($compressorCheck) {
    Write-Host "  [OK] Session Compressor started" -ForegroundColor Green
  } else {
    Write-Host "  [WARN] Session Compressor may not have started" -ForegroundColor Yellow
  }
}

# Step 7: Verify Compressor Working
Write-Host "[7/7] Verifying Session Compressor..." -ForegroundColor Yellow
wsl -d Ubuntu-Migrate -e bash -c "redis-cli -p 6379 SET 'session:test:log' 'Test session for compression system.' 2>/dev/null"
Start-Sleep 5
$searchResult = wsl -d Ubuntu-Migrate -e bash -c "redis-cli -p 6379 FT.SEARCH session_text_idx '@summary:Test' LIMIT 0 3 2>/dev/null"
if ($searchResult -like '*Test*') {
  Write-Host "  [OK] Session compression working!" -ForegroundColor Green
} else {
  Write-Host "  [WARN] Compression not yet active (may need Gemma 2B)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== Bootstrap Complete! ===" -ForegroundColor Cyan
Write-Host "Services running:" -ForegroundColor White
Write-Host "  - Redis Master (6379) + 2 Replicas (6380, 6381)" -ForegroundColor White
Write-Host "  - 3 Sentinels (26379-26381)" -ForegroundColor White
Write-Host "  - Session Compressor (Python daemon)" -ForegroundColor White
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  - Start Gemma 2B: see bootstrap.md" -ForegroundColor White
Write-Host "  - Check status: redis-cli -p 6379 INFO replication" -ForegroundColor White
