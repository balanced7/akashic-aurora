#!/usr/bin/env python3
"""
Gemma Realtime - TTS Processor
Text-to-speech using Kokoro and espeak-ng
"""

import io
import asyncio
import subprocess
import base64
from typing import Optional, Callable, AsyncIterator
from dataclasses import dataclass
import json
from pathlib import Path

@dataclass
class TTSConfig:
    engine: str = "kokoro"  # kokoro, espeak
    voice: str = "af_heart"  # Default female voice
    speed: float = 1.0
    language: str = "en-us"

# Kokoro voices - popular ones to pre-download
KOKORO_VOICES = {
    # Female voices
    "af_heart": {"name": "Amy (Heart)", "gender": "female", "lang": "en-us"},
    "af_sarah": {"name": "Sarah", "gender": "female", "lang": "en-us"},
    "af_bella": {"name": "Bella", "gender": "female", "lang": "en-us"},
    "af_nova": {"name": "Nova", "gender": "female", "lang": "en-us"},
    "af_stella": {"name": "Stella", "gender": "female", "lang": "en-us"},
    "am_adam": {"name": "Adam", "gender": "male", "lang": "en-us"},
    "am_eric": {"name": "Eric", "gender": "male", "lang": "en-us"},
    "am_fen": {"name": "Fen", "gender": "male", "lang": "en-us"},
    "bf_emma": {"name": "Emma", "gender": "female", "lang": "en-gb"},
    "bf_isabella": {"name": "Isabella", "gender": "female", "lang": "en-gb"},
}

class KokoroTTS:
    """Kokoro TTS engine"""
    
    def __init__(self, config: TTSConfig = None):
        self.config = config or TTSConfig()
        self.engine = None
        self._loaded = False
        self._voice_loaded = {}
    
    async def load(self):
        """Load Kokoro"""
        if not self._loaded:
            try:
                from kokoro_tts import Kokoro
                
                # Try GPU first, fall back to CPU
                try:
                    self.engine = Kokoro(voice=self.config.voice, device="cuda")
                except:
                    self.engine = Kokoro(voice=self.config.voice, device="cpu")
                
                self._loaded = True
                print(f"[TTS] Kokoro loaded with voice: {self.config.voice}")
            except Exception as e:
                print(f"[TTS] Kokoro failed to load: {e}")
                self._loaded = False
    
    async def speak(self, text: str) -> bytes:
        """Generate speech from text"""
        if not self._loaded or self.engine is None:
            return b""
        
        try:
            # Run in thread to not block
            result = await asyncio.to_thread(
                self.engine.speak,
                text,
                speed=self.config.speed,
                voice=self.config.voice
            )
            return result
        except Exception as e:
            print(f"[TTS] Speak error: {e}")
            return b""
    
    async def speak_streaming(self, text: str) -> AsyncIterator[bytes]:
        """Stream audio chunks"""
        if not self._loaded:
            return
        
        try:
            from kokoro_tts import TextToAudioStream, KokoroEngine
            
            engine = KokoroEngine(
                voice=self.config.voice,
                default_speed=self.config.speed
            )
            
            def on_chunk(chunk):
                yield chunk
            
            stream = TextToAudioStream(engine)
            stream.feed(text)
            
            # This is simplified - real streaming needs callback setup
            audio = await self.speak(text)
            if audio:
                yield audio
                
        except Exception as e:
            print(f"[TTS] Streaming error: {e}")
    
    def list_voices(self) -> dict:
        """List available voices"""
        return KOKORO_VOICES
    
    def set_voice(self, voice: str):
        """Set voice"""
        if voice in KOKORO_VOICES:
            self.config.voice = voice
            if self.engine:
                self.engine.voice = voice

class EspeakTTS:
    """Espeak-ng TTS engine (fallback)"""
    
    def __init__(self, config: TTSConfig = None):
        self.config = config or TTSConfig()
        self.config.engine = "espeak"
    
    async def load(self):
        """Check espeak availability"""
        try:
            result = subprocess.run(
                ["espeak-ng", "--version"],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                self._loaded = True
                print("[TTS] Espeak-ng available")
            else:
                self._loaded = False
        except:
            self._loaded = False
    
    async def speak(self, text: str) -> bytes:
        """Generate speech"""
        if not self._loaded:
            return b""
        
        try:
            # Generate WAV
            proc = await asyncio.create_subprocess_exec(
                "espeak-ng",
                "-w", "/tmp/espeak_output.wav",
                "-s", str(int(self.config.speed * 100)),
                text,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()
            
            # Read the WAV file
            with open("/tmp/espeak_output.wav", "rb") as f:
                return f.read()
        except Exception as e:
            print(f"[TTS] Espeak error: {e}")
            return b""

class TTSProcessor:
    """Unified TTS processor"""
    
    def __init__(self, config: TTSConfig = None):
        self.config = config or TTSConfig()
        self.kokoro = KokoroTTS(config)
        self.espeak = EspeakTTS(config)
        self._loaded = False
    
    async def load(self):
        """Load TTS engines"""
        await self.kokoro.load()
        await self.espeak.load()
        self._loaded = True
        print(f"[TTS] Loaded (engine: {self.config.engine})")
    
    async def speak(self, text: str) -> bytes:
        """Generate speech audio"""
        if self.config.engine == "kokoro" and self.kokoro._loaded:
            return await self.kokoro.speak(text)
        else:
            return await self.espeak.speak(text)
    
    async def speak_streaming(self, text: str) -> AsyncIterator[bytes]:
        """Streaming speech"""
        audio = await self.speak(text)
        if audio:
            yield audio
    
    def list_voices(self) -> dict:
        """List all available voices"""
        voices = dict(KOKORO_VOICES)
        voices.update({
            "espeak_male": {"name": "Espeak Male", "gender": "male", "lang": "en"},
            "espeak_female": {"name": "Espeak Female", "gender": "female", "lang": "en"},
        })
        return voices
    
    def set_voice(self, voice: str):
        """Set voice"""
        self.config.voice = voice
        self.kokoro.set_voice(voice)
    
    def set_engine(self, engine: str):
        """Set TTS engine"""
        if engine in ["kokoro", "espeak"]:
            self.config.engine = engine
    
    def add_voice(self, voice_id: str, voice_data: dict):
        """Add custom voice"""
        KOKORO_VOICES[voice_id] = voice_data

# Global instance
tts_processor = TTSProcessor()

async def init_tts():
    """Initialize TTS"""
    await tts_processor.load()
    print("[TTS] Ready")

if __name__ == "__main__":
    asyncio.run(init_tts())