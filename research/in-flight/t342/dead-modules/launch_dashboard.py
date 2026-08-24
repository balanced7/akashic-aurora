import subprocess
import sys
import time
import os
import concurrent.futures
import socket
import shutil

def print_status(msg, ok=True):
    status = "✓" if ok else "✗"
    print(f"[{status}] {msg}")

def check_port(port):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        return result == 0
    except:
        return False

def check_docker():
    """Check if Docker is accessible"""
    try:
        result = subprocess.run(["docker", "ps"], capture_output=True, timeout=5)
        return result.returncode == 0
    except:
        return False

def check_ollama_wsl():
    """Check if Ollama is running in WSL2"""
    try:
        result = subprocess.run([
            "wsl", "-d", "Ubuntu-24.04", "-e", "curl", "-s", "-m", "3", "http://localhost:11434/api/tags"
        ], capture_output=True, timeout=8)
        return result.returncode == 0
    except:
        return False

def get_status():
    """Get status of all services - returns dict of what's running"""
    return {
        "docker": check_docker(),
        "redis": check_port(6379),
        "ollama": check_port(11434) or check_ollama_wsl(),
        "dashboard": check_port(8501),
    }

def status_bar(status_dict):
    """Display status bar showing what's running"""
    parts = []
    if status_dict.get("docker"): parts.append("Docker")
    if status_dict.get("redis"): parts.append("Redis")
    if status_dict.get("ollama"): parts.append("Ollama")
    if status_dict.get("dashboard"): parts.append("Dashboard")
    
    if not parts:
        return "Nothing running"
    return " | ".join(parts)

# ============ PARALLEL SERVICE STARTERS ============

def start_docker():
    """Start Docker Desktop if not running"""
    if check_docker():
        print_status("Docker already running", True)
        return True
    
    print_status("Starting Docker Desktop...", False)
    try:
        subprocess.Popen([
            "C:\\Program Files\\Docker\\Docker\\Docker Desktop.exe"
        ], shell=True)
        # Wait for Docker to start (max 40 seconds)
        for i in range(20):
            time.sleep(2)
            if check_docker():
                print_status("Docker Desktop started", True)
                return True
        print_status("Docker started but not ready", False)
    except Exception as e:
        print_status(f"Docker error: {e}", False)
    return False

def start_redis():
    """Start Redis container if not running"""
    if check_port(6379):
        print_status("Redis already running", True)
        return True
    
    if not check_docker():
        print_status("Docker not running - skip Redis", False)
        return False
    
    print_status("Starting Redis...", False)
    try:
        # Try to start existing container
        result = subprocess.run(["docker", "start", "ai-redis"], 
                              capture_output=True, timeout=10)
        time.sleep(2)
        if check_port(6379):
            print_status("Redis started", True)
            return True
        
        # Try to create new container
        result = subprocess.run([
            "docker", "run", "-d", "--name", "ai-redis",
            "-p", "6379:6379",
            "redis:7-alpine"
        ], capture_output=True, timeout=30)
        time.sleep(3)
        if check_port(6379):
            print_status("Redis container created", True)
            return True
    except Exception as e:
        print_status(f"Redis error: {e}", False)
    
    print_status("Redis not available", False)
    return False

def get_wsl_ip():
    """Get WSL2 IP address dynamically"""
    try:
        result = subprocess.run(
            ["wsl", "-d", "Ubuntu-24.04", "-e", "hostname", "-I"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            # Get first IP (usually the main one)
            ip = result.stdout.strip().split()[0]
            return ip
    except:
        pass
    return None

def setup_ollama_portproxy():
    """Setup portproxy for Ollama - fix dynamic WSL IP"""
    wsl_ip = get_wsl_ip()
    if not wsl_ip:
        return False
    
    # Delete existing rule
    subprocess.run(["netsh", "interface", "portproxy", "delete", "v4tov4", 
                   "listenport=11434"], capture_output=True, timeout=5)
    
    # Add new rule with current WSL IP
    subprocess.run(["netsh", "interface", "portproxy", "add", "v4tov4",
                   "listenport=11434", "connectport=11434", 
                   f"connectaddress={wsl_ip}"], capture_output=True, timeout=5)
    
    return True

def start_ollama():
    """Start Ollama if not running"""
    if check_port(11434):
        print_status("Ollama already running", True)
        return True
    
    # Check WSL Ollama directly
    if check_ollama_wsl():
        setup_ollama_portproxy()
        if check_port(11434):
            print_status("Ollama (WSL2) port forwarded", True)
            return True
    
    print_status("Starting Ollama in WSL2 (GPU mode)...", False)
    try:
        # Use the working docker-compose.wsl2.yml config
        cmd = '''docker rm -f ollama-rocm 2>/dev/null; docker run -d \
  --device=/dev/dxg \
  -e OLLAMA_HOST=0.0.0.0 \
  -e HSA_ENABLE_DXG_DETECTION=1 \
  -e LD_LIBRARY_PATH=/opt/rocm/lib:/usr/lib/wsl/lib \
  -e ROCM_PATH=/opt/rocm \
  -e HIP_VISIBLE_DEVICES=0 \
  -e HSA_OVERRIDE_GFX_VERSION=12.0.1 \
  -v /opt/rocm-7.2.1:/opt/rocm:ro \
  -v /usr/lib/wsl/lib:/usr/lib/wsl/lib:ro \
  --network host \
  --shm-size=8g \
  --cap-add=SYS_PTRACE \
  --ipc=host \
  --name ollama-rocm \
  ollama/ollama:rocm'''
        
        subprocess.run(["wsl", "-d", "Ubuntu-24.04", "-e", "bash", "-c", cmd],
                      capture_output=True, timeout=30)
        
        # Wait and setup port proxy
        for i in range(15):
            time.sleep(2)
            if check_ollama_wsl():
                setup_ollama_portproxy()
                time.sleep(1)
                if check_port(11434):
                    print_status("Ollama started (WSL2 GPU)", True)
                    return True
    except Exception as e:
        print_status(f"Ollama error: {e}", False)
    
    print_status("Ollama not available", False)
    return False

def start_dashboard():
    """Start Streamlit dashboard if not running"""
    if check_port(8501):
        print_status("Dashboard already running", True)
        return True
    
    print_status("Starting Dashboard...", False)
    
    streamlit_path = shutil.which("streamlit")
    if not streamlit_path:
        print_status("Streamlit not in PATH", False)
        return False
    
    dashboard_path = r"E:\AI-Setup\dockerized-ai\services\dashboard\app.py"
    cmd = f'start "AI Dashboard" cmd /c "cd /d "{os.path.dirname(dashboard_path)}" && streamlit run app.py --server.port 8501 --server.address 127.0.0.1"'
    
    try:
        subprocess.Popen(cmd, shell=True)
        # Wait for dashboard to start
        for i in range(15):
            time.sleep(1)
            if check_port(8501):
                print_status("Dashboard running", True)
                return True
        print_status("Dashboard started (may need refresh)", True)
        return True
    except Exception as e:
        print_status(f"Dashboard error: {e}", False)
        return False

def open_browser():
    time.sleep(2)
    try:
        subprocess.Popen(["cmd", "/c", "start", "http://127.0.0.1:8501"], shell=True)
    except:
        pass

def open_privileged_terminal():
    """Open privileged PowerShell that primes opencode with context"""
    print_status("Opening privileged terminal with context...", False)
    
    # Create a startup script that runs init and shows catch-up
    script_content = '''
# AI Control Center - Privileged Terminal
# This terminal is primed with context and documentation instructions

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  AI Control Center - Privileged Mode" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Load context
Write-Host "[1/3] Loading Knowledge Base context..." -ForegroundColor Yellow
python E:\\AI-Setup\\init_ai.py

Write-Host ""
Write-Host "[2/3] System Status:" -ForegroundColor Yellow
$services = @{
    "Dashboard" = "http://127.0.0.1:8501"
    "Ollama" = "http://127.0.0.1:11434"
    "Redis" = "127.0.0.1:6379"
    "WebUI" = "http://127.0.0.1:3000"
}
foreach ($svc in $services.Keys) {
    Write-Host "  - $svc" -ForegroundColor Green
}

Write-Host ""
Write-Host "[3/3] IMPORTANT INSTRUCTIONS:" -ForegroundColor Red
Write-Host "========================================" -ForegroundColor Red
Write-Host "For every task you perform:" -ForegroundColor White
Write-Host "  1. Document in Redis KB using knowledge_base.py" -ForegroundColor White
Write-Host "  2. Register your model before writing" -ForegroundColor White
Write-Host "  3. Use prefix: your_model_name:key" -ForegroundColor White
Write-Host "  4. NEVER overwrite another model's learning" -ForegroundColor White
Write-Host "" -ForegroundColor White
Write-Host "Quick reference files:" -ForegroundColor White
Write-Host "  - E:\\AI-Setup\\init_ai.py    (run this first)" -ForegroundColor Cyan
Write-Host "  - E:\\AI-Setup\\docs\\INDEX.md (documentation)" -ForegroundColor Cyan
Write-Host "  - E:\\AI-Setup\\catch_up.py    (full context)" -ForegroundColor Cyan
Write-Host ""
Write-Host "Known Issue: GPU runs on CPU (AMD RX 9070 XT not detected by ROCm 7.2.1)"
Write-Host ""

# Open catch-up in notepad for reference
Write-Host "Opening catch-up export for reference..." -ForegroundColor Yellow
Start-Process notepad -ArgumentList "E:\\AI-Setup\\catch_up_export.json"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Terminal ready. You are primed with context." -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Keep window open
Write-Host "Press Enter to continue..." -ForegroundColor Gray
Read-Host
'''
    
    # Save script to temp file
    script_path = os.path.expanduser("~/AI_Terminal_Startup.ps1")
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script_content)
    
    # Open elevated PowerShell with the script
    try:
        # Open PowerShell with the startup script
        cmd = f'start "AI Control Center - Privileged" powershell -ExecutionPolicy Bypass -NoExit -File "{script_path}"'
        subprocess.Popen(cmd, shell=True)
        print_status("Privileged terminal opened", True)
    except Exception as e:
        print_status(f"Terminal error: {e}", False)

def start_keepalive():
    """Start Ollama keep-alive script"""
    print_status("Starting Ollama keep-alive...", False)
    try:
        # Start the keepalive script in background
        cmd = 'start "Ollama Keep-Alive" cmd /c "cd /d E:\AI-Setup && python keepalive_ollama.py --interval 30"'
        subprocess.Popen(cmd, shell=True)
        print_status("Ollama keep-alive started", True)
    except Exception as e:
        print_status(f"Keep-alive error: {e}", False)

def main():
    print("=" * 60)
    print("  AI Dashboard Launcher - Smart Start")
    print("=" * 60)
    print()
    
    # Phase 1: Quick status check (parallel)
    print("Phase 1: Checking what's already running...")
    status = get_status()
    print(f"   Status: {status_bar(status)}")
    print()
    
    # Phase 2: Start Docker (must be first - prerequisite)
    if not status["docker"]:
        print("Phase 2: Starting Docker...")
        start_docker()
        status = get_status()  # Refresh status
    else:
        print("Phase 2: Docker already ready - skipping")
    print()
    
    # Phase 3: Start Redis and Ollama in PARALLEL (they're independent)
    print("Phase 3: Starting services (parallel)...")
    
    if status["redis"]:
        print_status("Redis already running", True)
    if status["ollama"]:
        print_status("Ollama already running", True)
    
    # Start services in parallel if needed
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = []
        if not status["redis"]:
            futures.append(executor.submit(start_redis))
        if not status["ollama"]:
            futures.append(executor.submit(start_ollama))
        
        # Wait for both to complete
        concurrent.futures.wait(futures)
    
    status = get_status()  # Refresh status
    print()
    
    # Phase 4: Start Dashboard (depends on Docker at least)
    print("Phase 4: Starting Dashboard...")
    start_dashboard()
    
    # Phase 5: Start Ollama keep-alive
    print("Phase 5: Starting Ollama keep-alive...")
    start_keepalive()
    
    # Final status
    print()
    status = get_status()
    print("=" * 60)
    print(f"  FINAL STATUS: {status_bar(status)}")
    print("=" * 60)
    
    # Open browser
    open_browser()
    
    print()
    print("  Dashboard is open in your browser")
    print("  URL: http://127.0.0.1:8501")
    print("  Keep-alive is running to prevent Ollama from exiting")
    print()
    
    # Ask to open privileged terminal
    print("  Would you like to open a privileged terminal?")
    print("  This will prime an AI session with all context.")
    print("  (Y/N): ", end="")
    
    try:
        choice = input().strip().lower()
        if choice == "y":
            open_privileged_terminal()
    except:
        pass
    
    print()
    print("Press Enter to exit...")
    try:
        input()
    except:
        pass

if __name__ == "__main__":
    main()