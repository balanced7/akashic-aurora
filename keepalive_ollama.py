"""
Ollama Keep-Alive Script
=======================
Prevents Ollama container from exiting by pinging it periodically.

Usage:
    python E:\AI-Setup\keepalive_ollama.py
    
Or runs as background service:
    python E:\AI-Setup\keepalive_ollama.py --background
"""

import subprocess
import time
import socket
import sys
import os
import threading

def check_port(port):
    """Check if port is responding"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        return result == 0
    except:
        return False

def check_ollama_wsl():
    """Check if Ollama is running in WSL2"""
    try:
        result = subprocess.run([
            "wsl", "-d", "Ubuntu-24.04", "-e", "curl", "-s", "-m", "2", "http://localhost:11434/api/tags"
        ], capture_output=True, timeout=5)
        return result.returncode == 0
    except:
        return False

def start_ollama():
    """Start Ollama in WSL2 if not running"""
    print("[START] Checking Ollama...")
    
    # Check if accessible
    if check_port(11434):
        print("[OK] Ollama already running on port 11434")
        return True
    
    if check_ollama_wsl():
        print("[OK] Ollama running in WSL2, setting up port proxy...")
        setup_portproxy()
        return True
    
    print("[START] Starting Ollama in WSL2...")
    try:
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
        
        # Wait for startup
        for i in range(15):
            time.sleep(2)
            if check_ollama_wsl():
                setup_portproxy()
                print("[OK] Ollama started")
                return True
        
        print("[WARN] Ollama started but not responding")
        return False
    except Exception as e:
        print(f"[ERROR] {e}")
        return False

def setup_portproxy():
    """Setup port proxy for WSL2"""
    try:
        result = subprocess.run(
            ["wsl", "-d", "Ubuntu-24.04", "-e", "hostname", "-I"],
            capture_output=True, text=True, timeout=5
        )
        wsl_ip = result.stdout.strip().split()[0] if result.returncode == 0 else None
        
        if wsl_ip:
            subprocess.run(["netsh", "interface", "portproxy", "delete", "v4tov4", 
                          "listenport=11434"], capture_output=True, timeout=5)
            subprocess.run(["netsh", "interface", "portproxy", "add", "v4tov4",
                          "listenport=11434", "connectport=11434", 
                          f"connectaddress={wsl_ip}"], capture_output=True, timeout=5)
            print(f"[OK] Port proxy set to {wsl_ip}")
    except Exception as e:
        print(f"[WARN] Port proxy error: {e}")

def ping_ollama():
    """Ping Ollama to keep it alive"""
    try:
        import requests
        resp = requests.get("http://127.0.0.1:11434/api/tags", timeout=3)
        return resp.status_code == 200
    except:
        # Try via WSL
        try:
            result = subprocess.run([
                "wsl", "-d", "Ubuntu-24.04", "-e", "curl", "-s", "-m", "2", "http://localhost:11434/api/tags"
            ], capture_output=True, timeout=5)
            return result.returncode == 0
        except:
            return False

def keepalive_loop(interval=30):
    """Main keep-alive loop"""
    print("=" * 50)
    print("  Ollama Keep-Alive Started")
    print("=" * 50)
    print(f"  Ping interval: {interval} seconds")
    print("  Press Ctrl+C to stop")
    print()
    
    while True:
        try:
            # Check if Ollama needs to be started
            if not check_port(11434) and not check_ollama_wsl():
                print(f"[{time.strftime('%H:%M:%S')}] Ollama not running, starting...")
                start_ollama()
            else:
                # Ping to keep alive
                if ping_ollama():
                    print(f"[{time.strftime('%H:%M:%S')}] Ollama alive - ping OK")
                else:
                    print(f"[{time.strftime('%H:%M:%S')}] Ollama not responding, restarting...")
                    start_ollama()
            
            time.sleep(interval)
            
        except KeyboardInterrupt:
            print("\nStopping keep-alive...")
            break
        except Exception as e:
            print(f"[ERROR] {e}")
            time.sleep(interval)

if __name__ == "__main__":
    # Check for background flag
    interval = 30
    if len(sys.argv) > 1:
        if sys.argv[1] == "--background":
            # Run in background using start command
            cmd = f'start "Ollama Keep-Alive" cmd /c "cd /d E:\AI-Setup && python keepalive_ollama.py --interval 30"'
            subprocess.Popen(cmd, shell=True)
            print("Started keepalive in background")
            sys.exit(0)
        elif sys.argv[1] == "--interval":
            interval = int(sys.argv[2])
    
    keepalive_loop(interval)