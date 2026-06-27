#!/usr/bin/env python3
"""
Document the Gemma Realtime implementation in Redis
"""
import sys
import json
from datetime import datetime

sys.path.insert(0, r"E:\AI-Setup")
from core.foundation.redis_connection import connect_to_redis_with_fail_fast

r = connect_to_redis_with_fail_fast(host='localhost', port=6379, timeout_seconds=5, decode_responses=True)
if r is None:
    print("[document_implementation] Redis not available - documentation not saved")
    sys.exit(1)

# Document the implementation
implementation_doc = {
    "system": "Gemma Realtime Voice AI",
    "implemented": datetime.now().isoformat(),
    "description": "Real-time voice chat with Gemma using streaming pipeline",
    "components": {
        "server": {
            "location": "E:/AI-Setup/gemma_realtime/server.py",
            "port": 5000,
            "websocket": "ws://localhost:5000/ws",
            "framework": "FastAPI + uvicorn"
        },
        "stt": {
            "location": "E:/AI-Setup/gemma_realtime/stt_processor.py",
            "model": "faster-whisper base (int8)",
            "status": "loaded"
        },
        "tts": {
            "location": "E:/AI-Setup/gemma_realtime/tts_processor.py",
            "engines": ["kokoro-tts", "espeak-ng"],
            "voices": ["af_heart", "af_sarah", "af_bella", "am_adam", "am_eric"],
            "status": "loaded"
        },
        "llm": {
            "location": "E:/AI-Setup/gemma_realtime/llm_wrapper.py",
            "model": "gemma2:2b",
            "provider": "Ollama at localhost:11434",
            "features": ["streaming", "interrupt_detection"]
        },
        "file_analyzer": {
            "location": "E:/AI-Setup/gemma_realtime/file_analyzer.py",
            "supported": ["code", "images", "pdf", "docs", "xlsx", "db", "audio", "video"]
        },
        "audio_handler": {
            "location": "E:/AI-Setup/gemma_realtime/audio_handler.py",
            "vad": "silero-vad",
            "status": "basic (needs tuning)"
        }
    },
    "gui": {
        "url": "http://localhost:5000",
        "features": ["text_chat", "voice_input", "file_drag_drop", "voice_selection", "speed_control"]
    },
    "dependencies": {
        "python": "E:/AI-Setup/gemma_realtime/requirements.txt",
        "installed": ["fastapi", "uvicorn", "websockets", "silero-vad", "faster-whisper", "kokoro-tts", "pdfplumber", "pytesseract", "python-docx", "openpyxl"]
    },
    "issues": [
        "VAD needs tuning - occasional crashes",
        "Video analysis prompts user for choice instead of auto",
        "Voice import/download UI buttons not implemented"
    ],
    "startup_command": "source /root/rocm-venv/bin/activate && python /mnt/e/AI-Setup/gemma_realtime/server.py"
}

r.set("context:gemma_realtime_implementation", json.dumps(implementation_doc))
print("Saved implementation documentation to Redis")

# Add context:wsl_infrastructure update
current_infra = r.get("context:wsl_infrastructure") or ""
new_infra = current_infra + " | Gemma Realtime: localhost:5000"

r.set("context:wsl_infrastructure", new_infra)

# Update ports
ports = {
    "port:gemma-realtime": {
        "port": "5000",
        "protocol": "http",
        "description": "Gemma Realtime Voice AI WebUI + API",
        "components": "FastAPI + WebSocket",
        "allocated_at": datetime.now().isoformat()
    },
    "port:gemma-websocket": {
        "port": "5000",
        "protocol": "ws",
        "description": "Gemma Realtime WebSocket for voice",
        "allocated_at": datetime.now().isoformat()
    }
}

for key, data in ports.items():
    r.delete(key)
    r.hset(key, mapping=data)

print("Updated port registry")
print("\nImplementation documented!")

# List what we saved
print("\nRedis keys created/updated:")
print("  - context:gemma_realtime_implementation")
print("  - context:wsl_infrastructure (appended)")
print("  - port:gemma-realtime")
print("  - port:gemma-websocket")