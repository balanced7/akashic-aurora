#!/usr/bin/env python3
"""
Gemma Realtime - STT Processor
Speech-to-text using Faster-Whisper
"""

import io
import numpy as np
import torch
import torchaudio
from typing import Optional, List
from dataclasses import dataclass
import asyncio

@dataclass
class STTConfig:
    model_size: str = "base"  # tiny, base, small, medium, large
    device: str = "cpu"  # cpu, cuda
    compute_type: str = "int8"  # int8, float16, float32
    language: str = "en"
    beam_size: int = 5
    vad_filter: bool = True

class STTProcessor:
    """Speech-to-text using Faster-Whisper"""
    
    def __init__(self, config: STTConfig = None):
        self.config = config or STTConfig()
        self.model = None
        self._loaded = False
    
    async def load(self):
        """Load the Whisper model"""
        if not self._loaded:
            try:
                from faster_whisper import WhisperModel
                
                print(f"[STT] Loading Whisper model: {self.config.model_size}")
                self.model = WhisperModel(
                    self.config.model_size,
                    device=self.config.device,
                    compute_type=self.config.compute_type
                )
                self._loaded = True
                print(f"[STT] Model loaded ({self.config.model_size})")
            except Exception as e:
                print(f"[STT] Failed to load: {e}")
                self._loaded = False
    
    async def transcribe(self, audio_bytes: bytes) -> str:
        """Transcribe audio bytes to text"""
        if not self._loaded or self.model is None:
            return ""
        
        try:
            # Save audio to temporary bytes buffer
            audio_io = io.BytesIO(audio_bytes)
            audio_io.name = "audio.wav"
            
            # Run transcription in thread pool to not block
            segments, info = await asyncio.to_thread(
                self.model.transcribe,
                audio_io,
                language=self.config.language,
                beam_size=self.config.beam_size,
                vad_filter=self.config.vad_filter,
                vad_parameters=dict(min_speech_duration=0.3)
            )
            
            text_parts = []
            async for segment in segments:
                text_parts.append(segment.text)
            
            result = " ".join(text_parts).strip()
            return result
            
        except Exception as e:
            print(f"[STT] Transcription error: {e}")
            return ""
    
    async def transcribe_streaming(self, audio_chunk: bytes) -> str:
        """Quick transcription for streaming audio"""
        # For streaming, we'll accumulate and transcribe periodically
        # This is a simplified version
        return await self.transcribe(audio_chunk)

class STTProcessorManager:
    """Manages multiple STT processors"""
    
    def __init__(self):
        self.primary = STTProcessor(STTConfig(model_size="base", compute_type="int8"))
        self.fast = STTProcessor(STTConfig(model_size="tiny", compute_type="int8"))
        self._active = None
    
    async def load(self):
        """Load models"""
        await self.primary.load()
        await self.fast.load()
        self._active = self.primary
    
    async def transcribe(self, audio_bytes: bytes, fast: bool = False) -> str:
        """Transcribe with optional fast mode"""
        processor = self.fast if fast else self.primary
        return await processor.transcribe(audio_bytes)
    
    def switch_mode(self, fast: bool):
        """Switch between fast and accurate mode"""
        self._active = self.fast if fast else self.primary

# Global instance
stt_processor = STTProcessorManager()

async def init_stt():
    """Initialize STT"""
    await stt_processor.load()
    print("[STT] Initialized")

if __name__ == "__main__":
    asyncio.run(init_stt())