#!/usr/bin/env python3
"""
Document the current state in Redis for future sessions
"""
import sys
import json
from datetime import datetime

sys.path.insert(0, r"E:\AI-Setup")
from core.foundation.redis_connection import connect_to_redis_with_fail_fast

r = connect_to_redis_with_fail_fast(host='localhost', port=6379, timeout_seconds=5, decode_responses=True)
if r is None:
    print("[document_state] Redis not available - documentation not saved")
    sys.exit(1)

# Document ROCm setup status
rocm_doc = {
    "status": "not_working",
    "date": datetime.now().isoformat(),
    "issue": "RX 9070 XT (RDNA4/gfx1201) not detected by ROCm in WSL2",
    "attempts": [
        {
            "date": "2026-04-23",
            "action": "Created /etc/profile.d/rocm.sh with HSA_ENABLE_DXG_DETECTION=1, HSA_OVERRIDE_GFX_VERSION=12.0.0",
            "result": "ROCk module NOT loaded - no GPU detected"
        },
        {
            "date": "2026-04-23", 
            "action": "Added gpuSupport=true to .wslconfig",
            "result": "Still not working - ROCm cannot detect GPU"
        }
    ],
    "root_cause": "RX 9070 XT (RDNA4) is not yet fully supported by ROCm on WSL2. Known limitation - requires newer ROCm nightly builds.",
    "research_sources": [
        "https://github.com/ROCm/ROCm/issues/4471",
        "https://github.com/microsoft/WSL/issues/14144"
    ],
    "requirements_for_fix": [
        "AMD Adrenalin driver 26.2.2+ (current: 32.0.23033.1002)",
        "ROCm nightly builds with WSL2 RDNA4 support",
        "Or wait for official ROCm 7.3+ with RDNA4 WSL2 support"
    ],
    "environment_vars_set": [
        "HSA_ENABLE_DXG_DETECTION=1",
        "HSA_OVERRIDE_GFX_VERSION=12.0.0",
        "LD_LIBRARY_PATH=/usr/lib/wsl/lib:/opt/rocm/lib"
    ],
    "files_created": [
        "/etc/profile.d/rocm.sh",
        "E:/AI-Setup/gemma_realtime/rocm.sh"
    ]
}

# Document Gemma Realtime issues
gemma_realtime_issues = {
    "status": "partially_working",
    "date": datetime.now().isoformat(),
    "working": [
        "Text chat with streaming",
        "TTS (espeak, basic Kokoro)",
        "STT (Faster-Whisper)",
        "File upload and analysis"
    ],
    "issues": [
        {
            "issue": "VAD (Silero VAD) crashes",
            "severity": "high",
            "fix": "Replace with simpler WebRTC VAD or tune Silero"
        },
        {
            "issue": "Voice Import/Download UI not implemented", 
            "severity": "medium",
            "fix": "Add buttons to voice selection dropdown"
        },
        {
            "issue": "Video analysis prompts user instead of auto-selecting",
            "severity": "low",
            "fix": "Implement user preference storage"
        }
    ],
    "next_steps": [
        "Fix VAD by using simpler audio level detection",
        "Add voice import UI",
        "Test with CPU-only mode until ROCm works"
    ]
}

# Save to Redis
r.set("context:rocm_20260423_status", json.dumps(rocm_doc))
r.set("context:gemma_realtime_issues", json.dumps(gemma_realtime_issues))

# Update port registry
ports = {
    "port:gemma-realtime": {
        "port": "5000",
        "protocol": "http",
        "description": "Gemma Realtime Voice AI (working, CPU mode)",
        "status": "running"
    }
}

for key, data in ports.items():
    r.delete(key)
    r.hset(key, mapping=data)

print("Documentation saved to Redis!")
print(f"  - context:rocm_20260423_status")
print(f"  - context:gemma_realtime_issues")