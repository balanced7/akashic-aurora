#!/usr/bin/env python3
"""
Gemma Realtime - Audio Handler
Handles WebSocket audio streams with VAD and processing
"""

import asyncio
import io
import numpy as np
import torch
import torchaudio
from typing import Optional, Callable
from dataclasses import dataclass

@dataclass
class AudioConfig:
    sample_rate: int = 16000
    chunksize: int = 1024
    vad_threshold: float = 0.5
    min_speech_duration: float = 0.3
    min_silence_duration: float = 0.5

class VADProcessor:
    """Voice Activity Detection using Silero VAD"""
    
    def __init__(self, config: AudioConfig = None):
        self.config = config or AudioConfig()
        self.model = None
        self._loaded = False
    
    async def load(self):
        if not self._loaded:
            try:
                self.model, utils = await asyncio.to_thread(
                    torch.hub.load, 
                    "snakers4/silero-vad", 
                    "silero_vad",
                    force_reload=False
                )
                # Handle different API versions
                if len(utils) >= 5:
                    self.get_speech_timestamps = utils[0]
                else:
                    self.get_speech_timestamps = utils
                self._loaded = True
                print("[VAD] Silero VAD loaded")
            except Exception as e:
                print(f"[VAD] Failed to load: {e}")
                self._loaded = False
    
    def process_chunk(self, audio_bytes: bytes) -> dict:
        """Process a single audio chunk and return VAD results"""
        if not self._loaded or self.model is None:
            return {"speech": False, "confidence": 0.0}
        
        try:
            # Convert bytes to waveform
            audio_io = io.BytesIO(audio_bytes)
            waveform, sr = torchaudio.load(audio_io, format="wav")
            
            # Resample if needed
            if sr != self.config.sample_rate:
                waveform = torchaudio.functional.resample(waveform, sr, self.config.sample_rate)
            
            # Convert to float32
            if waveform.dtype == torch.int16:
                waveform = waveform.float() / 32768.0
            
            # Get speech timestamps
            speech_timestamps = self.get_speech_timestamps(
                waveform.squeeze(0),
                self.model,
                sampling_rate=self.config.sample_rate,
                trig_sum=self.config.vad_threshold,
                min_speech_duration_samples=int(self.config.min_speech_duration * self.config.sample_rate),
                min_silence_duration_samples=int(self.config.min_silence_duration * self.config.sample_rate),
            )
            
            has_speech = len(speech_timestamps) > 0
            
            return {
                "speech": has_speech,
                "timestamp": speech_timestamps[0] if has_speech else None,
                "confidence": 1.0 if has_speech else 0.0
            }
        except Exception as e:
            return {"speech": False, "confidence": 0.0, "error": str(e)}
    
    def is_speaking(self, audio_bytes: bytes) -> bool:
        """Quick check if audio contains speech"""
        result = self.process_chunk(audio_bytes)
        return result.get("speech", False)

class AudioBuffer:
    """Circular buffer for accumulating audio"""
    
    def __init__(self, max_duration: float = 30.0, sample_rate: int = 16000):
        self.max_samples = int(max_duration * sample_rate)
        self.sample_rate = sample_rate
        self.buffer = bytearray()
        self.last_speech_end = 0
    
    def add(self, chunk: bytes):
        self.buffer.extend(chunk)
        # Trim if exceeds max
        if len(self.buffer) > self.max_samples * 2:  # *2 for 16-bit audio
            self.buffer = bytearray(self.buffer[-self.max_samples * 2:])
    
    def get_audio(self) -> bytes:
        return bytes(self.buffer)
    
    def clear(self):
        self.buffer.clear()
    
    def get_recent(self, duration: float) -> bytes:
        """Get most recent N seconds of audio"""
        num_bytes = int(duration * self.sample_rate) * 2  # 16-bit
        if len(self.buffer) <= num_bytes:
            return self.get_audio()
        return bytes(self.buffer[-num_bytes:])

class AudioWebSocketHandler:
    """WebSocket handler for real-time audio streaming"""
    
    def __init__(self, vad_processor: VADProcessor = None):
        self.vad = vad_processor or VADProcessor()
        self.buffer = AudioBuffer()
        self.is_recording = False
        self.clients = set()
        self.on_transcript: Optional[Callable] = None
        self.on_interrupt: Optional[Callable] = None
        self._speech_detected = False
        self._silence_count = 0
    
    async def connect(self, websocket):
        await websocket.accept()
        self.clients.add(websocket)
        print(f"[WS] Client connected. Total: {len(self.clients)}")
    
    async def disconnect(self, websocket):
        self.clients.discard(websocket)
        print(f"[WS] Client disconnected. Total: {len(self.clients)}")
    
    async def handle_audio(self, audio_data: bytes):
        """Handle incoming audio chunk"""
        self.buffer.add(audio_data)
        
        # Check VAD
        result = self.vad.process_chunk(audio_data)
        
        if result["speech"]:
            self._speech_detected = True
            self._silence_count = 0
        else:
            self._silence_count += 1
        
        # If we've been speaking and now silence, might be end of utterance
        if self._speech_detected and self._silence_count > 10:  # ~500ms of silence
            # Process the audio for transcription
            if self.on_transcript:
                audio = self.buffer.get_recent(10)  # Last 10 seconds
                await self.on_transcript(audio)
            
            self._speech_detected = False
            self._silence_count = 0
    
    async def broadcast(self, message: dict):
        """Broadcast message to all clients"""
        if not self.clients:
            return
        
        dead_clients = set()
        for client in self.clients:
            try:
                await client.send_json(message)
            except Exception:
                dead_clients.add(client)
        
        for client in dead_clients:
            await self.disconnect(client)
    
    async def interrupt(self):
        """Handle user interruption"""
        self.buffer.clear()
        self._speech_detected = False
        self._silence_count = 0
        
        if self.on_interrupt:
            await self.on_interrupt()

# Global instance
audio_handler = AudioWebSocketHandler()

async def init_audio():
    """Initialize audio components"""
    await audio_handler.vad.load()
    print("[Audio] Initialized")

if __name__ == "__main__":
    asyncio.run(init_audio())