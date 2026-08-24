"""
AI Model Initialization & Context Loader
==========================================
Run this FIRST before any troubleshooting or work.

Usage:
    python init_ai.py
    
    OR in code:
    from init_ai import initialize
    context = initialize()
"""

import os
import json
from knowledge_base import KB

def get_redis_status():
    """Quick Redis status check"""
    kb = KB()
    return kb.get_status()

def load_recent_learnings(limit=5):
    """Load recent learnings from all models"""
    kb = KB()
    models = kb.get_all_models()
    learnings = []
    for model in models:
        ctx = kb.get_model_context(model)
        if ctx.get("learnings"):
            for key, data in ctx["learnings"].items():
                learnings.append({
                    "model": model,
                    "key": key,
                    "category": data.get("category", "unknown"),
                    "created": data.get("created_at", "")
                })
    # Sort by created date
    learnings.sort(key=lambda x: x["created"], reverse=True)
    return learnings[:limit]

def load_documentation():
    """Load all documentation"""
    kb = KB()
    docs = {}
    for doc_name in kb.get_all_docs():
        content = kb.read_doc(doc_name)
        if content:
            docs[doc_name] = content
    return docs

def get_current_system_state():
    """Get current state of all services"""
    import socket
    import subprocess
    
    state = {
        "services": {},
        "docker_containers": [],
        "windows_count": 0
    }
    
    # Check ports
    ports = {
        8501: "dashboard",
        11434: "ollama", 
        6379: "redis",
        3000: "webui"
    }
    
    for port, name in ports.items():
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(("127.0.0.1", port))
            sock.close()
            state["services"][name] = "RUNNING" if result == 0 else "STOPPED"
        except:
            state["services"][name] = "UNKNOWN"
    
    # Check Docker containers
    try:
        result = subprocess.run(["docker", "ps", "--format", "{{.Names}}"],
                              capture_output=True, text=True, timeout=5)
        state["docker_containers"] = result.stdout.strip().split("\n") if result.stdout else []
    except:
        pass
    
    return state

def initialize():
    """
    Main initialization - loads all context for AI models.
    Returns a dict with everything an AI needs to get started.
    """
    # AUTO-START LOGGING FIRST
    import sys
    sys.path.insert(0, r'E:\AI-Setup')
    try:
        from session_logger import log, log_chat, log_error, verify_logs
        log("session_start", "New session - initialization started")
        log("init_ai", "Auto-initialization activated")
    except Exception as e:
        print(f"[WARNING] Could not start logging: {e}")
    
    print("=" * 70)
    print("  AI MODEL INITIALIZATION")
    print("=" * 70)
    print()
    
    # 1. Logging Status
    print("[1/7] Logging System:")
    try:
        from session_logger import verify_logs
        result = verify_logs(100)
        print(f"     Status: ACTIVE")
        print(f"     Valid entries: {result['valid']}, Corrupted: {result['corrupted']}")
    except Exception as e:
        print(f"     Status: FALLBACK (file-only)")
        print(f"     Error: {e}")
    print()
    
    # 2. Knowledge Base Status
    print("[2/7] Loading Knowledge Base...")
    kb_status = get_redis_status()
    print(f"     Status: {kb_status.get('status', 'unknown')}")
    print(f"     Models: {kb_status.get('models', 0)}")
    print(f"     Learnings: {kb_status.get('learnings', 0)}")
    print(f"     Docs: {kb_status.get('docs', 0)}")
    print()
    
    # 3. Registered Models
    print("[3/7] Registered Models:")
    kb = KB()
    for model in kb.get_all_models():
        info = kb.get_model_info(model)
        if info:
            print(f"     - {model}: {info.get('description', 'N/A')}")
    print()
    
    # 4. System State
    print("[4/7] Current System State:")
    sys_state = get_current_system_state()
    for service, status in sys_state["services"].items():
        icon = "[OK]" if status == "RUNNING" else "[X]"
        print(f"     {icon} {service}: {status}")
    if sys_state["docker_containers"]:
        print(f"     Containers: {', '.join(sys_state['docker_containers'])}")
    print()
    
    # 5. Recent Learnings
    print("[5/7] Recent Learnings:")
    recent = load_recent_learnings()
    for lr in recent:
        print(f"     - [{lr['model']}] {lr['key']} ({lr['category']})")
    print()
    
    # 6. Documentation
    print("[6/7] Available Documentation:")
    docs = load_documentation()
    for doc_name in docs.keys():
        # Get first line as preview
        first_line = docs[doc_name].strip().split('\n')[0][:50]
        print(f"     - {doc_name}: {first_line}...")
    print()
    
    # 7. Important Files
    print("[7/7] Important Files (READ STARTUP.md FIRST!):")
    important_files = [
        ("Startup", "E:\\AI-Setup\\STARTUP.md"),
        ("Architecture", "E:\\AI-Setup\\ARCHITECTURE.md"),
        ("Knowledge Base", "E:\\AI-Setup\\knowledge_base.py"),
        ("Init Script", "E:\\AI-Setup\\init_ai.py"),
        ("GPU Passthrough", "E:\\AI-Setup\\docker-gpu-passthrough.md"),
        ("Dashboard", "E:\\AI-Setup\\dockerized-ai\\services\\dashboard-react\\app.py"),
        ("Launcher", "E:\\AI-Setup\\launch_dashboard.py"),
    ]
    for name, path in important_files:
        exists = "[OK]" if os.path.exists(path) else "[X]"
        print(f"     {exists} {name}")
    print()
    
    # Return context for use in code
    return {
        "kb_status": kb_status,
        "models": kb.get_all_models(),
        "system_state": sys_state,
        "recent_learnings": recent,
        "docs": docs,
        "important_files": important_files
    }

def quick_start():
    """Quick reference for common tasks"""
    print("""
QUICK START GUIDE
================

Need to check knowledge base?
    from init_ai import initialize
    context = initialize()

Need to write a learning?
    from knowledge_base import KB
    kb = KB()
    kb.register_model("my_model", "description", ["capabilities"])
    kb.write("my_model", "my_key", {"data": "value"})

Need to check GPU status?
    - Read doc: kb.read_doc("gpu_status")
    - Check port 11434
    - Run: wsl -d Ubuntu-24.04 -e rocminfo

Need to restart Ollama?
    - Run: wsl -d Ubuntu-24.04 -e docker start ollama-rocm
    - Check: curl http://localhost:11434/api/tags

Key Documentation:
    - README: kb.read_doc("README")
    - GPU Status: kb.read_doc("gpu_status") 
    - Setup: kb.read_doc("setup_status")

File Locations:
    - Documentation: E:\\AI-Setup\\SETUP_STATUS.md
    - Knowledge Base: E:\\AI-Setup\\knowledge_base.py
    - Init Script: E:\\AI-Setup\\init_ai.py
""")

if __name__ == "__main__":
    context = initialize()
    quick_start()
    print("Initialization complete!")
    print("=" * 70)