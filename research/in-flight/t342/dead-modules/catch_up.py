"""
AI CATCH-UP SCRIPT
==================
Run this to instantly prime a new AI session with all context.

Usage:
    python E:\AI-Setup\catch_up.py
    
    Then copy-paste the output into the AI session.

OR use programmatically:
    from catch_up import get_catch_up
    context = get_catch_up()
"""

import json
from knowledge_base import KB

def get_catch_up():
    """Get all context for catch-up - returns dict"""
    kb = KB()
    
    # Get system state
    import socket
    import subprocess
    
    services = {}
    for port, name in [(8501, "dashboard"), (11434, "ollama"), (6379, "redis"), (3000, "webui")]:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            s.connect(("127.0.0.1", port))
            s.close()
            services[name] = "RUNNING"
        except:
            services[name] = "STOPPED"
    
    # Get models
    models = []
    for m in kb.get_all_models():
        info = kb.get_model_info(m)
        models.append({"name": m, "info": info})
    
    # Get docs
    docs = {}
    for d in kb.get_all_docs():
        docs[d] = kb.read_doc(d)
    
    # Get learnings (structured, no duplicates)
    learnings = {}
    for m in kb.get_all_models():
        ctx = kb.get_model_context(m)
        if ctx.get("learnings"):
            learnings[m] = ctx["learnings"]
    
    return {
        "system_status": services,
        "models": models,
        "docs": docs,
        "learnings": learnings,
        "total_learnings": sum(len(v) for v in learnings.values())
    }

def print_catch_up():
    """Print formatted catch-up for AI session"""
    ctx = get_catch_up()
    
    print("=" * 70)
    print("  CATCH-UP: FULL CONTEXT FOR AI SESSION")
    print("=" * 70)
    print()
    
    print("## SYSTEM STATUS")
    for service, status in ctx["system_status"].items():
        print(f"  {service}: {status}")
    print()
    
    print("## REGISTERED MODELS")
    for m in ctx["models"]:
        print(f"  - {m['name']}")
        if m["info"]:
            print(f"      {m['info'].get('description', '')}")
    print()
    
    print("## KEY DOCUMENTATION")
    for name, content in ctx["docs"].items():
        # Get first 200 chars
        preview = content.strip()[:200].replace('\n', ' ')
        print(f"  [{name}]: {preview}...")
    print()
    
    print("## RECENT LEARNINGS")
    total = 0
    for model, learnings in ctx["learnings"].items():
        for key, data in learnings.items():
            total += 1
            if total <= 10:  # Show first 10
                print(f"  - [{model}] {key}: {data.get('category', 'N/A')}")
    print(f"  ... and {ctx['total_learnings'] - min(10, ctx['total_learnings'])} more")
    print()
    
    print("## KEY FILES")
    print("  - E:\\AI-Setup\\init_ai.py       (run this first)")
    print("  - E:\\AI-Setup\\knowledge_base.py")
    print("  - E:\\AI-Setup\\docs\\INDEX.md   (quick reference)")
    print("  - E:\\AI-Setup\\SETUP_STATUS.md")
    print()
    
    print("## INSTRUCTIONS FOR NEW AI SESSION")
    print("""
    1. Run: python E:\\AI-Setup\\init_ai.py
    2. Read docs in: E:\\AI-Setup\\docs\\
    3. For Redis KB: from knowledge_base import KB
    4. Always register your model before writing
    5. Use prefix: model_name:key
    
    Current working services:
    - Dashboard: http://127.0.0.1:8501
    - Ollama: http://127.0.0.1:11434 (CPU mode)
    - Redis: 127.0.0.1:6379
    - WebUI: http://127.0.0.1:3000
    
    Known issue: GPU (AMD RX 9070 XT) not detected by ROCm 7.2.1
    """)
    print("=" * 70)

def export_json():
    """Export all context as JSON for programmatic use"""
    ctx = get_catch_up()
    
    # Save to file
    with open("E:\\AI-Setup\\catch_up_export.json", "w", encoding="utf-8") as f:
        json.dump(ctx, f, indent=2, ensure_ascii=False)
    
    print("Exported to: E:\\AI-Setup\\catch_up_export.json")
    return ctx

if __name__ == "__main__":
    print_catch_up()
    export_json()
    print("\n[OK] Catch-up complete! Copy above into new AI session.")