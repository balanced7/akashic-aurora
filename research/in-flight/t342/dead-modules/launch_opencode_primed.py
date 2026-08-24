"""
OpenCode Primed Launcher for Daniil - GUI Version
 Loads context, greets you personally, shows what we worked on.
 Uses tkinter so window stays open.
"""
import subprocess
import sys
import os
import requests
import time
import tkinter as tk
from tkinter import scrolledtext

USER_NAME = "Daniil"
LOG_FILE = os.path.expanduser("~\\launcher_primed.log")

def log(msg):
    """Write to log file"""
    try:
        with open(LOG_FILE, "a") as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
    except:
        pass

log("=== Launcher GUI starting ===")

def get_learnings():
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        return [r.get(k) for k in r.keys('kb:learning:*')[:5]]
    except:
        return []

def get_status():
    try:
        r = requests.get('http://127.0.0.1:8501', timeout=2)
        return {"dashboard": "running" if r.status_code == 200 else "stopped"}
    except:
        return {"dashboard": "not running"}

def launch_opencode():
    log("Trying to launch OpenCode...")
    # Try PATH first
    try:
        result = subprocess.run(["opencode", "--version"], capture_output=True, timeout=5)
        if result.returncode == 0:
            log("Found in PATH, launching...")
            subprocess.Popen(["opencode"])
            return True
    except:
        pass
    
    # Try installed location
    paths = [
        r"C:\Users\L5\AppData\Local\Programs\OpenCode\opencode.exe",
        r"C:\Program Files\OpenCode\opencode.exe",
    ]
    for path in paths:
        if os.path.exists(path):
            log(f"Found at {path}")
            subprocess.Popen([path])
            return True
    
    # Try starting a primed PowerShell instead
    log("OpenCode not found, launching primed PowerShell...")
    try:
        # Use cmd.exe to launch PowerShell - more reliable
        subprocess.Popen(["cmd.exe", "/c", "start", "powershell.exe", "-NoExit", "-Command", 
            "Write-Host '=== PRIMED POWERSHELL FOR DANIIL ===' -ForegroundColor Green; "
            "Write-Host 'Tools ready: ai_helper module available'; "
            "Write-Host 'Try: from ai_helper import *'; "
            "Write-Host ''"],
            shell=True)
        log("PowerShell launch command sent")
        return True
    except Exception as e:
        log(f"PowerShell launch failed: {e}")
        pass
    
    return False

def run():
    log("Building window...")
    
    root = tk.Tk()
    root.title(f"AI Control Center - Welcome {USER_NAME}")
    root.geometry("700x500")
    
    # Output area
    txt = scrolledtext.ScrolledText(root, width=80, height=30, font=("Consolas", 10))
    txt.pack(padx=10, pady=10)
    
    def log_msg(msg):
        txt.insert(tk.END, msg + "\n")
        txt.see(tk.END)
        log(msg)
    
    # Welcome
    log_msg(f"Hey {USER_NAME}! Welcome back to the AI Control Center")
    log_msg("=" * 50)
    
    # Prior work
    log_msg("\nWHAT WE'VE BEEN WORKING ON:")
    log_msg("-" * 40)
    for item in ["Multithreaded parallel service loading", 
               "Dashboard with gear icon settings",
               "OpenRouter cloud AI integration",
               "Smart orchestrator for model selection",
               "Knowledge base system for AI models"]:
        log_msg(f"  - {item}")
    
    # Tools
    log_msg("\nTOOLS AVAILABLE:")
    log_msg("-" * 40)
    log_msg("  - ai_helper.ocr() - Read screen text")
    log_msg("  - ai_helper.status() - Dashboard status")
    log_msg("  - ai_helper.learn(key, value) - Store fix")
    log_msg("  - ai_helper.ui_list() - List open windows")
    log_msg("  - ai_helper.ui_inspect('window') - Inspect UI tree")
    log_msg("  - ai_helper.diag() - Full diagnosis")
    
    # Current status
    status = get_status()
    log_msg("\nCURRENT STATUS:")
    log_msg("-" * 40)
    if status:
        for svc, state in status.items():
            log_msg(f"  {svc}: {state}")
    else:
        log_msg("  Dashboard not running - start with:")
        log_msg("    python E:\\AI-Setup\\launch_dashboard.py")
    
    # Learnings
    learnings = get_learnings()
    if learnings:
        log_msg(f"\n{len(learnings)} stored learnings")
    
    log_msg("\n" + "=" * 50)
    log_msg(f"\nHi {USER_NAME}, what do you want to build today?")
    
    # Launch button - big!
    btn = tk.Button(root, text=">>> LAUNCH PRIMED POWERSHELL <<<", 
                   command=lambda: do_launch(),
                   font=("Consolas", 16, "bold"), 
                   bg="#2196F3", fg="white", 
                   padx=30, pady=15,
                   width=30, height=2)
    btn.pack(pady=20)
    
    def do_launch():
        log_msg("\nLaunching OpenCode...")
        if launch_opencode():
            log_msg("OpenCode launched!")
        else:
            log_msg("ERROR: OpenCode not found.")
            log_msg("Install from: https://opencode.ai")
    
    log_msg("\n[Click 'Launch OpenCode' to start]")
    
    log("Window ready")
    root.mainloop()

if __name__ == "__main__":
    run()