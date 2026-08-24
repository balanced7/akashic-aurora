"""Save diagnostic status to knowledge base"""
from knowledge_base import KB

kb = KB()

# Register diagnostic tool
kb.register_model("system_diagnostic", "Window and service diagnostic tool", ["windows", "services", "docker"])

# Save latest status
status = {
    "services": {
        "dashboard": "running",
        "ollama": "running", 
        "redis": "running",
        "webui": "running"
    },
    "windows": [
        "Start", "PowerShell", "AI Dashboard", "Brave", "Signal", 
        "Docker Desktop", "File Explorer", "Settings", "Discord"
    ],
    "docker_containers": [
        "ai-redis", "ai-voice", "ai-open-webui"
    ],
    "timestamp": "2026-04-13"
}

kb.write("system_diagnostic", "latest_status", status)
kb.write_doc("diagnostic_history", f"""
# Diagnostic History

## 2026-04-13
- All services running
- 15 windows detected
- 3 Docker containers running
- Ollama accessible via WSL2 portproxy

## Known Issues
- Ollama GPU discovery timeout (runs on CPU)
- WSL2 IP changes on restart
""", "system_diagnostic")

print("Status saved to knowledge base")
print("Models:", kb.get_all_models())
print("Docs:", kb.get_all_docs())