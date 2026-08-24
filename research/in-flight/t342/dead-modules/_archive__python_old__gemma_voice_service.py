#!/usr/bin/env python3
"""
Gemma Voice AI Service
==================
Local voice-enabled AI using Gemma, faster-whisper STT, and TTS.
Supports code execution and Redis memory.
"""

import os
import sys
import json
import contextlib
import redis
import subprocess
import threading
import base64
import io
import wave
import ssl
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))

executor = ThreadPoolExecutor(max_workers=4)

redis_client = None
whisper_model = None

def get_redis():
    global redis_client
    if redis_client is None:
        try:
            redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True, socket_connect_timeout=3)
            redis_client.ping()
            print(f"[Redis] Connected to {REDIS_HOST}:{REDIS_PORT}")
        except Exception as e:
            print(f"[Redis] Not connected: {e}")
            redis_client = None
    return redis_client

def get_whisper():
    global whisper_model
    if whisper_model is None:
        try:
            from faster_whisper import WhisperModel
            print("[STT] Loading Whisper model (base, int8)...")
            whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
            print("[STT] Whisper ready!")
        except Exception as e:
            print(f"[STT] Failed to load: {e}")
    return whisper_model

def init_services():
    print("=== Initializing Gemma Voice AI ===")
    get_redis()
    get_whisper()
    print("[Init] Services ready!")

def speak_text(text):
    """Convert text to speech using espeak-ng"""
    try:
        cmd = ["espeak-ng", "-w", "/tmp/tts_output.wav", text]
        subprocess.run(cmd, capture_output=True)
        
        with open("/tmp/tts_output.wav", "rb") as f:
            audio_data = base64.b64encode(f.read()).decode()
        return audio_data
    except Exception as e:
        print(f"[TTS] Error: {e}")
        return None

def transcribe_audio(audio_bytes):
    """Transcribe audio to text using faster-whisper"""
    try:
        model = get_whisper()
        if model is None:
            return "STT not available"
        
        with open("/tmp/input_audio.wav", "wb") as f:
            f.write(audio_bytes)
        
        segments, _ = model.transcribe("/tmp/input_audio.wav")
        text = "".join([s.text for s in segments])
        return text.strip() if text else "Could not understand audio"
    except Exception as e:
        print(f"[STT] Error: {e}")
        return f"Error: {str(e)}"

def query_ollama(prompt, model="gemma2:2b", system_prompt=None):
    """Query Ollama for response"""
    import requests
    
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }
    
    if system_prompt:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "stream": False
        }
    
    try:
        resp = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=120)
        return resp.json().get("response", "No response")
    except Exception as e:
        return f"Ollama error: {str(e)}"

def execute_code(code):
    """Execute Python code in sandbox"""
    import warnings
    warnings.filterwarnings("ignore")
    
    result = {"success": False, "output": "", "error": ""}
    
    try:
        output_lines = []
        
        class OutputCapture:
            def __init__(self):
                self.outputs = []
            def write(self, text):
                self.outputs.append(text)
            def flush(self):
                pass
        
        captured = OutputCapture()
        
        exec_globals = {
            "__builtins__": __builtins__,
            "print": lambda *args: captured.write(" ".join(map(str, args))),
        }
        
        with contextlib.redirect_stdout(captured):
            with contextlib.redirect_stderr(captured):
                exec(code, exec_globals)
        
        result["success"] = True
        result["output"] = "\n".join(captured.outputs) if captured.outputs else "Code executed successfully (no output)"
        
    except Exception as e:
        result["error"] = str(e)
    
    return result

def save_to_memory(key, value):
    """Save learning to Redis"""
    r = get_redis()
    if r:
        try:
            r.set(f"learnings:{key}", json.dumps(value))
            r.set(f"learnings:last_updated", datetime.now().isoformat())
            return True
        except:
            pass
    return False

def get_personality():
    """Get personality from Redis"""
    r = get_redis()
    if r:
        try:
            data = r.get("ai:personality")
            if data:
                return json.loads(data)
        except:
            pass
    
    return {
        "name": "Gemma",
        "system_prompt": "You are Gemma, a helpful AI assistant. Be concise, accurate, and slightly witty. When asked to do something, explain what you'll do first.",
        "traits": ["helpful", "knowledgeable", "proactive"]
    }

@app.route("/health", methods=["GET"])
def health():
    r = get_redis()
    redis_ok = r is not None
    whisper_ok = whisper_model is not None
    
    return jsonify({
        "status": "ok",
        "redis": "connected" if redis_ok else "disconnected",
        "stt": "ready" if whisper_ok else "loading",
        "ollama": OLLAMA_URL,
        "timestamp": datetime.now().isoformat()
    })

@app.route("/chat", methods=["POST"])
def chat():
    """Main chat endpoint"""
    data = request.json
    user_message = data.get("message", "")
    use_code = data.get("execute_code", False)
    
    personality = get_personality()
    system_prompt = personality.get("system_prompt", "")
    
    if use_code and "```python" in user_message:
        code_start = user_message.find("```python") + 10
        code_end = user_message.find("```", code_start)
        code = user_message[code_start:code_end]
        
        result = execute_code(code)
        llm_prompt = f"""The user ran this code and got this result: {result['output'] if result['success'] else result['error']}
Explain the result and what the code does."""
        
        response = query_ollama(llm_prompt, system_prompt=system_prompt)
    else:
        response = query_ollama(user_message, system_prompt=system_prompt)
    
    return jsonify({
        "response": response,
        "personality": personality.get("name", "Gemma"),
        "timestamp": datetime.now().isoformat()
    })

@app.route("/voice/input", methods=["POST"])
def voice_input():
    """Accept audio and transcribe"""
    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400
    
    audio_file = request.files["audio"].read()
    text = transcribe_audio(audio_file)
    
    return jsonify({
        "text": text,
        "timestamp": datetime.now().isoformat()
    })

@app.route("/voice/output", methods=["POST"])
def voice_output():
    """Convert text to speech"""
    data = request.json
    text = data.get("text", "")
    
    if not text:
        return jsonify({"error": "No text provided"}), 400
    
    audio_b64 = speak_text(text)
    
    if audio_b64:
        return jsonify({
            "audio": audio_b64,
            "format": "wav",
            "timestamp": datetime.now().isoformat()
        })
    else:
        return jsonify({"error": "TTS failed"}), 500

@app.route("/tts/speak", methods=["GET"])
def tts_speak():
    """Quick TTS endpoint"""
    text = request.args.get("text", "Hello! I am ready.")
    audio_b64 = speak_text(text)
    
    if audio_b64:
        return jsonify({"audio": audio_b64})
    return jsonify({"error": "TTS failed"}), 500

@app.route("/memory/save", methods=["POST"])
def memory_save():
    """Save learning to memory"""
    data = request.json
    key = data.get("key", "")
    value = data.get("value", "")
    
    if not key or not value:
        return jsonify({"error": "key and value required"}), 400
    
    success = save_to_memory(key, value)
    return jsonify({"success": success, "key": key})

@app.route("/memory/search", methods=["GET"])
def memory_search():
    """Search memories"""
    query = request.args.get("q", "")
    r = get_redis()
    
    if not r:
        return jsonify({"error": "Redis not connected"}), 500
    
    results = []
    try:
        for key in r.scan_iter("learnings:*"):
            if query.lower() in key.lower():
                results.append({"key": key, "value": r.get(key)})
    except:
        pass
    
    return jsonify({"results": results[:20]})

@app.route("/code/execute", methods=["POST"])
def code_execute():
    """Execute Python code"""
    data = request.json
    code = data.get("code", "")
    
    if not code:
        return jsonify({"error": "No code provided"}), 400
    
    result = execute_code(code)
    return jsonify(result)

@app.route("/models", methods=["GET"])
def list_models():
    """List available Ollama models"""
    import requests
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=10)
        return jsonify(resp.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/generate", methods=["POST"])
def generate():
    """Direct Ollama generate"""
    data = request.json
    prompt = data.get("prompt", "")
    model = data.get("model", "gemma2:2b")
    
    response = query_ollama(prompt, model=model)
    
    return jsonify({
        "response": response,
        "model": model
    })

if __name__ == "__main__":
    init_services()
    
    print("\n=== Gemma Voice AI Service ===")
    print("Endpoints:")
    print("  POST /chat          - Chat with Gemma")
    print("  POST /voice/input  - Transcribe audio")
    print("  POST /voice/output - Text to speech")
    print("  POST /code/execute - Execute Python")
    print("  POST /memory/save  - Save to Redis")
    print("  GET  /models     - List Ollama models")
    print("  GET  /health     - Health check")
    print("")
    print("Running on http://0.0.0.0:5000")
    
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)