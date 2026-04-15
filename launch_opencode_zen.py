"""
OpenCode Zen Launcher for Daniil
 Calm, focused launcher with deep context and personal greeting.
"""
import subprocess
import sys
import os
import requests
import time

USER_NAME = "Daniil"

def get_kb_context():
    """Get knowledge base context summary"""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        keys = r.keys('*')
        return len(keys)
    except:
        return 0

def get_status():
    """Get dashboard status"""
    try:
        resp = requests.get('http://127.0.0.1:8501', timeout=2)
        return "running" if resp.status_code == 200 else "stopped"
    except:
        return "stopped"

def print_calm_intro():
    """Print calm welcome"""
    print()
    print("    *******************************************")
    print("    *                                         *")
    print(f"    *     Welcome back, {USER_NAME}                  *")
    print("    *     Let's build something great today    *")
    print("    *                                         *")
    print("    *******************************************")
    print()

def print_deep_context():
    """Print deep context summary"""
    print("DEEP CONTEXT LOADED:")
    print("-"*45)
    print(f"  - Knowledge base synced ({get_kb_context()} entries)")
    print(f"  - Dashboard: {get_status()}")
    print(f"  - Previous work: Dashboard, OpenRouter, Orchestrator")
    print(f"  - Latest: OCR tools (Tesseract working!)")
    print()

def print_recent_actions():
    """Print recent actions summary"""
    print("RECENT ACTIONS:")
    print("-"*45)
    print("  - Built AI Control Center dashboard")
    print("  - Added multithreaded service loading")
    print("  - Created OpenRouter integration")
    print("  - Set up knowledge base in Redis")
    print("  - Fixed dashboard bugs (list.get error)")
    print("  - Tested PaddleOCR (PIR bug - skipped)")
    print("  - Installed Tesseract for fast OCR")
    print("  - Created OpenCode launcher EXEs")
    print()

def ask_calm():
    """Ask what to work on"""
    print(f"Ready when you are, {USER_NAME}.")
    print("What shall we focus on today?")
    print()

def main():
    print_calm_intro()
    print_deep_context()
    print_recent_actions()
    ask_calm()
    
    time.sleep(0.5)
    
    # Launch OpenCode
    opencode_paths = ["opencode", r"C:\Users\L5\AppData\Local\Programs\OpenCode\opencode.exe"]
    
    for cmd in opencode_paths:
        try:
            subprocess.run([cmd, "--version"], capture_output=True, timeout=3)
            print("Launching OpenCode...")
            subprocess.run([cmd])
            return
        except:
            continue
    
    print("ERROR: OpenCode not found at: https://opencode.ai")

print()
input("Press Enter to exit...")

if __name__ == "__main__":
    main()