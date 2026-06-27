#!/usr/bin/env python3
"""
Gemma Realtime - Main Server
FastAPI + WebSocket server for real-time voice chat
"""

import asyncio
import io
import os
import json
import base64
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Import our modules
from audio_handler import audio_handler, init_audio, VADProcessor
from stt_processor import stt_processor, init_stt
from tts_processor import tts_processor, init_tts
from llm_wrapper import llm, init_llm
from file_analyzer import file_analyzer, init_analyzer

app = FastAPI(title="Gemma Realtime")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store connected clients
connected_clients = set()
conversation_history = []
voice_settings = {
    "engine": "kokoro",
    "voice": "af_heart", 
    "speed": 1.0,
    "interrupt_enabled": True
}

# ============================================================================
# HTTP ENDPOINTS
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def get_ui():
    """Serve the GUI"""
    return HTMLResponse(content=get_gui_html(), media_type="text/html")

@app.get("/health")
async def health_check():
    """Health check"""
    return {
        "status": "ok",
        "services": {
            "llm": "ready",
            "stt": "ready", 
            "tts": "ready",
        },
        "timestamp": datetime.now().isoformat()
    }

@app.get("/voices")
async def list_voices():
    """List available voices"""
    voices = tts_processor.list_voices()
    return {"voices": voices, "current": voice_settings}

@app.post("/voices")
async def set_voice(engine: str = Form("kokoro"), voice: str = Form("af_heart"), speed: float = Form(1.0)):
    """Set voice settings"""
    voice_settings["engine"] = engine
    voice_settings["voice"] = voice
    voice_settings["speed"] = speed
    
    tts_processor.set_engine(engine)
    tts_processor.set_voice(voice)
    
    return {"success": True, "settings": voice_settings}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload and analyze a file"""
    content = await file.read()
    
    # Analyze file
    result = await file_analyzer.analyze(content, file.filename)
    
    return result

@app.post("/chat")
async def chat_message(
    message: str = Form(...),
    files: list[UploadFile] = File(None)
):
    """Text chat (non-voice)"""
    files_data = []
    
    # Process uploaded files
    if files:
        for f in files:
            content = await f.read()
            result = await file_analyzer.analyze(content, f.filename)
            files_data.append(result)
    
    # Get conversation history for context
    context = "\n".join([f"USER: {m['user']}\nGEMMA: {m['gemma']}" for m in conversation_history[-3:]])
    
    # Stream response
    response_text = ""
    async for token in llm.chat(message, context=context, files=files_data):
        response_text += token
    
    # Save to history
    conversation_history.append({
        "user": message,
        "gemma": response_text,
        "timestamp": datetime.now().isoformat()
    })
    
    # Generate TTS audio
    audio = await tts_processor.speak(response_text)
    audio_b64 = base64.b64encode(audio).decode() if audio else None
    
    return {
        "response": response_text,
        "audio": audio_b64,
        "timestamp": datetime.now().isoformat()
    }

# ============================================================================
# WEBSOCKET ENDPOINTS  
# ============================================================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time voice"""
    await websocket.accept()
    connected_clients.add(websocket)
    
    print(f"[WS] Client connected. Total: {len(connected_clients)}")
    
    buffer = bytearray()
    is_recording = False
    current_response = ""
    
    try:
        while True:
            data = await websocket.receive_json()
            
            msg_type = data.get("type")
            
            if msg_type == "audio":
                # Receive audio chunk
                audio_b64 = data.get("data", "")
                audio_bytes = base64.b64decode(audio_b64)
                buffer.extend(audio_bytes)
                
                # Check VAD
                if voice_settings.get("interrupt_enabled"):
                    is_speaking = audio_handler.vad.is_speaking(audio_bytes)
                    
                    # If we were generating and user speaks, interrupt
                    if is_speaking and llm.is_generating:
                        interrupt_result = await llm.interrupt()
                        
                        await websocket.send_json({
                            "type": "interrupt",
                            "partial": interrupt_result.get("partial_response", ""),
                            "intent": interrupt_result.get("intent", "stop")
                        })
            
            elif msg_type == "transcribe":
                # Force transcription of buffered audio
                if buffer:
                    text = await stt_processor.transcribe(bytes(buffer))
                    buffer.clear()
                    
                    if text:
                        await websocket.send_json({
                            "type": "transcript", 
                            "text": text
                        })
            
            elif msg_type == "text":
                # Direct text message
                message = data.get("text", "")
                
                if message:
                    # Get context
                    context = "\n".join([
                        f"USER: {m['user']}\nGEMMA: {m['gemma']}" 
                        for m in conversation_history[-3:]
                    ])
                    
                    # Stream response
                    current_response = ""
                    
                    async for token in llm.chat(message, context=context):
                        current_response += token
                        
                        # Send text token
                        await websocket.send_json({
                            "type": "text",
                            "token": token,
                            "partial": current_response
                        })
                        
                        # Stream audio for completed sentences
                        if token.rstrip().endswith(('.', '!', '?')):
                            audio = await tts_processor.speak(token)
                            if audio:
                                await websocket.send_json({
                                    "type": "audio",
                                    "data": base64.b64encode(audio).decode()
                                })
                    
                    # Save to history
                    conversation_history.append({
                        "user": message,
                        "gemma": current_response,
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    # Final audio
                    audio = await tts_processor.speak(current_response)
                    if audio:
                        await websocket.send_json({
                            "type": "audio",
                            "data": base64.b64encode(audio).decode()
                        })
                    
                    await websocket.send_json({
                        "type": "done",
                        "response": current_response
                    })
            
            elif msg_type == "interrupt":
                # User interrupted
                interrupt_result = await llm.interrupt()
                
                # If intent is modify, ask user what they want
                if interrupt_result.get("intent") == "modify":
                    await websocket.send_json({
                        "type": "ask",
                        "question": "You interrupted me. Did you want me to:\nA) Stop completely\nB) Continue from where I was\nC) Say something different?"
                    })
            
            elif msg_type == "video_choice":
                # Handle video analysis choice
                filename = data.get("filename")
                choice = data.get("choice")
                
                result = await file_analyzer.ask_video_choice(filename, choice)
                await websocket.send_json({
                    "type": "video_result",
                    "result": result
                })
    
    except WebSocketDisconnect:
        print("[WS] Client disconnected")
    finally:
        connected_clients.discard(websocket)

# ============================================================================
# GUI HTML
# ============================================================================

def get_gui_html() -> str:
    return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gemma Voice AI</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f0f0f; color: #fff; height: 100vh; display: flex; flex-direction: column;
        }
        header { 
            padding: 1rem; background: #1a1a1a; border-bottom: 1px solid #333;
            display: flex; justify-content: space-between; align-items: center;
        }
        h1 { font-size: 1.2rem; }
        .status { display: flex; align-items: center; gap: 0.5rem; font-size: 0.8rem; color: #888; }
        .status-dot { width: 8px; height: 8px; border-radius: 50%; background: #00ff00; }
        
        #chat { flex: 1; overflow-y: auto; padding: 1rem; display: flex; flex-direction: column; gap: 1rem; }
        .message { max-width: 80%; padding: 0.8rem 1rem; border-radius: 12px; line-height: 1.5; }
        .message.user { align-self: flex-end; background: #0066ff; }
        .message.gemma { align-self: flex-start; background: #222; }
        .attachments { display: flex; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 0.5rem; }
        .attachment { 
            background: #333; padding: 0.3rem 0.6rem; border-radius: 4px; font-size: 0.8rem;
            display: flex; align-items: center; gap: 0.5rem;
        }
        .attachment .remove { cursor: pointer; color: #ff6666; }
        
        #input-area { 
            padding: 1rem; background: #1a1a1a; border-top: 1px solid #333;
        }
        #message-box {
            width: 100%; min-height: 120px; background: #222; border: 2px dashed #444;
            border-radius: 8px; padding: 1rem; color: #fff; font-size: 1rem; resize: none;
            outline: none; transition: border-color 0.2s;
        }
        #message-box:focus { border-color: #0066ff; }
        #message-box.dragover { border-color: #00ff00; background: #1a1a1a; }
        #message-box::placeholder { color: #666; }
        
        .attached { display: flex; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 0.5rem; }
        
        .buttons { display: flex; gap: 0.5rem; margin-top: 0.5rem; justify-content: space-between; }
        .buttons-left, .buttons-right { display: flex; gap: 0.5rem; }
        
        button {
            padding: 0.6rem 1.2rem; border: none; border-radius: 6px; cursor: pointer;
            font-size: 0.9rem; display: flex; align-items: center; gap: 0.5rem;
            transition: all 0.2s;
        }
        button.primary { background: #0066ff; color: #fff; }
        button.primary:hover { background: #0055ee; }
        button.secondary { background: #333; color: #fff; }
        button.secondary:hover { background: #444; }
        button.recording { background: #ff3333; color: #fff; animation: pulse 1s infinite; }
        
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.7; } }
        
        #controls {
            padding: 0.5rem 1rem; background: #151515; border-top: 1px solid #333;
            display: flex; gap: 1rem; flex-wrap: wrap;
        }
        .control-group { display: flex; align-items: center; gap: 0.5rem; }
        .control-group label { font-size: 0.8rem; color: #888; }
        select {
            background: #222; color: #fff; border: 1px solid #444; padding: 0.3rem; border-radius: 4px;
        }
        
        .speaking { color: #00ff00; }
    </style>
</head>
<body>
    <header>
        <h1>Gemma Voice AI</h1>
        <div class="status">
            <span class="status-dot"></span>
            <span>Connected</span>
        </div>
    </header>
    
    <div id="chat"></div>
    
    <div id="input-area">
        <div id="message-box" contenteditable="true" placeholder="Drop files here or type your message..."></div>
        
        <div class="buttons">
            <div class="buttons-left">
                <button id="mic-btn" class="secondary">🎤</button>
            </div>
            <div class="buttons-right">
                <button id="test-audio-btn" class="secondary">🔊 Test</button>
                <button id="send-btn" class="primary">➤ Send</button>
            </div>
        </div>
    </div>
    
    <div id="controls">
        <div class="control-group">
            <label>TTS:</label>
            <select id="engine-select">
                <option value="kokoro">Kokoro</option>
                <option value="espeak">Espeak</option>
            </select>
        </div>
        <div class="control-group">
            <label>Voice:</label>
            <select id="voice-select">
                <option value="af_heart">Amy (Female)</option>
                <option value="af_sarah">Sarah (Female)</option>
                <option value="af_bella">Bella (Female)</option>
                <option value="am_adam">Adam (Male)</option>
                <option value="am_eric">Eric (Male)</option>
            </select>
        </div>
        <div class="control-group">
            <label>Speed:</label>
            <select id="speed-select">
                <option value="0.5">0.5x</option>
                <option value="0.75">0.75x</option>
                <option value="1.0" selected>1.0x</option>
                <option value="1.25">1.25x</option>
                <option value="1.5">1.5x</option>
            </select>
        </div>
    </div>

    <script>
        const messageBox = document.getElementById('message-box');
        const chat = document.getElementById('chat');
        const micBtn = document.getElementById('mic-btn');
        const sendBtn = document.getElementById('send-btn');
        const testAudioBtn = document.getElementById('test-audio-btn');
        let attachedFiles = [];
        let ws = null;
        let isRecording = false;
        let mediaRecorder = null;
        let audioChunks = [];
        
        // WebSocket
        function connect() {
            ws = new WebSocket(`ws://${location.host}/ws`);
            ws.onopen = () => console.log('Connected');
            ws.onclose = () => { console.log('Disconnected'); setTimeout(connect, 2000); };
            ws.onmessage = (e) => {
                const data = JSON.parse(e.data);
                handleMessage(data);
            };
        }
        connect();
        
        // Handle incoming messages
        function handleMessage(data) {
            if (data.type === 'text' || data.type === 'transcript') {
                addMessage('gemma', data.token || data.text);
            } else if (data.type === 'audio') {
                playAudio(data.data);
            } else if (data.type === 'done') {
                // Response complete
            }
        }
        
        // Add message to chat
        function addMessage(role, text) {
            const div = document.createElement('div');
            div.className = `message ${role}`;
            div.textContent = text;
            chat.appendChild(div);
            chat.scrollTop = chat.scrollHeight;
        }
        
        // Play audio from base64
        function playAudio(base64) {
            const audio = new Audio('data:audio/wav;base64,' + base64);
            audio.play();
        }
        
        // Drag and drop
        messageBox.addEventListener('dragover', (e) => {
            e.preventDefault();
            messageBox.classList.add('dragover');
        });
        messageBox.addEventListener('dragleave', () => {
            messageBox.classList.remove('dragover');
        });
        messageBox.addEventListener('drop', async (e) => {
            e.preventDefault();
            messageBox.classList.remove('dragover');
            for (const file of e.dataTransfer.files) {
                attachedFiles.push(file.name);
                addFileChip(file.name);
                // Upload file
                const formData = new FormData();
                formData.append('file', file);
                const resp = await fetch('/upload', { method: 'POST', body: formData });
                const result = await resp.json();
            }
        });
        
        function addFileChip(name) {
            // Add file chip display
        }
        
        // Send message
        sendBtn.onclick = async () => {
            const text = messageBox.textContent.trim();
            if (!text && attachedFiles.length === 0) return;
            
            addMessage('user', text);
            messageBox.textContent = '';
            
            const formData = new FormData();
            formData.append('message', text);
            
            const resp = await fetch('/chat', { method: 'POST', body: formData });
            const result = await resp.json();
            
            addMessage('gemma', result.response);
            if (result.audio) playAudio(result.audio);
        };
        
        // Voice recording
        micBtn.onclick = async () => {
            if (isRecording) {
                stopRecording();
            } else {
                startRecording();
            }
        };
        
        async function startRecording() {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
            audioChunks = [];
            
            mediaRecorder.ondataavailable = (e) => {
                audioChunks.push(e.data);
            };
            
            mediaRecorder.onstop = async () => {
                const audio = new Blob(audioChunks);
                const base64 = await blobToBase64(audio);
                ws.send(JSON.stringify({ type: 'audio', data: base64 }));
            };
            
            mediaRecorder.start();
            isRecording = true;
            micBtn.classList.add('recording');
        }
        
        function stopRecording() {
            if (mediaRecorder) {
                mediaRecorder.stop();
                isRecording = false;
                micBtn.classList.remove('recording');
            }
        }
        
        function blobToBase64(blob) {
            return new Promise((resolve) => {
                const reader = new FileReader();
                reader.onload = () => resolve(reader.result.split(',')[1]);
                reader.readAsDataURL(blob);
            });
        }
        
        // Test audio
        testAudioBtn.onclick = async () => {
            const resp = await fetch('/tts/speak?text=Hello+I+am+Gemma');
            const data = await resp.json();
            if (data.audio) playAudio(data.audio);
        };
    </script>
</body>
</html>'''

# ============================================================================
# MAIN
# ============================================================================

@app.on_event("startup")
async def startup():
    """Initialize all components"""
    print("[System] Starting...")
    
    await init_audio()
    await init_stt()
    await init_tts()
    await init_llm()
    await init_analyzer()
    
    print("[System] All services ready!")
    print("[System] GUI available at http://localhost:5000")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)