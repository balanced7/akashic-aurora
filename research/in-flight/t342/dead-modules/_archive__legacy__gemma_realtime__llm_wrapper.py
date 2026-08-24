#!/usr/bin/env python3
"""
Gemma Realtime - LLM Wrapper
Streaming Ollama integration with interrupt handling
"""

import asyncio
import json
import sys
from typing import Optional, AsyncIterator, Callable
from dataclasses import dataclass
import redis
import requests
from datetime import datetime

sys.path.insert(0, r"E:\AI-Setup")

@dataclass
class LLMConfig:
    model: str = "gemma2:2b"
    base_url: str = "http://localhost:11434"
    temperature: float = 0.7
    max_tokens: int = 512
    stop_on_interrupt: bool = True

class StreamingLLM:
    """Streaming LLM with interrupt support"""
    
    def __init__(self, config: LLMConfig = None):
        self.config = config or LLMConfig()
        self.is_generating = False
        self.should_stop = False
        self.context_buffer = ""  # Store partial response for interrupt handling
        self.redis_client = None
    
    async def load(self):
        """Initialize"""
        try:
            from core.foundation.redis_connection import connect_to_redis_with_fail_fast
            self.redis_client = connect_to_redis_with_fail_fast(
                host="localhost",
                port=6379,
                timeout_seconds=3,
                decode_responses=True,
            )
            if self.redis_client is None:
                raise ConnectionError("Redis not reachable at localhost:6379")
            print("[LLM] Redis connected")
        except Exception as e:
            self.redis_client = None
            print(f"[LLM] Redis not available: {e}")
        
        # Check Ollama
        try:
            resp = requests.get(f"{self.config.base_url}/api/tags", timeout=5)
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                print(f"[LLM] Ollama ready with {len(models)} models")
                for m in models:
                    if m.get("name", "").startswith(self.config.model):
                        print(f"[LLM] Model ready: {m['name']}")
                        return
                # Model not found, try pulling
                print(f"[LLM] Pulling {self.config.model}...")
        except Exception as e:
            print(f"[LLM] Ollama check failed: {e}")
    
    async def chat(
        self, 
        prompt: str, 
        context: str = "",
        files: list = None,
        stream_callback: Optional[Callable] = None,
        audio_callback: Optional[Callable] = None
    ) -> AsyncIterator[str]:
        """Stream chat response"""
        self.is_generating = True
        self.should_stop = False
        self.context_buffer = ""
        
        # Build full prompt with context and files
        full_prompt = self._build_prompt(prompt, context, files)
        
        try:
            # Use streaming API
            payload = {
                "model": self.config.model,
                "prompt": full_prompt,
                "stream": True,
                "options": {
                    "temperature": self.config.temperature,
                    "num_predict": self.config.max_tokens,
                }
            }
            
            async with asyncio.TaskGroup() as tg:
                async def generate():
                    response = requests.post(
                        f"{self.config.base_url}/api/generate",
                        json=payload,
                        stream=True,
                        timeout=120
                    )
                    
                    for line in response.iter_lines():
                        if line:
                            data = json.loads(line)
                            token = data.get("response", "")
                            
                            # Check for interrupt
                            if self.should_stop:
                                break
                            
                            self.context_buffer += token
                            
                            # Callback for streaming
                            if stream_callback:
                                await stream_callback(token)
                            
                            yield token
                            
                            
                            # Check if done
                            if data.get("done", False):
                                break
                
                async for token in generate():
                    yield token
                    
        except Exception as e:
            print(f"[LLM] Error: {e}")
            yield f"Error: {str(e)}"
        finally:
            self.is_generating = False
    
    def _build_prompt(self, prompt: str, context: str = "", files: list = None) -> str:
        """Build full prompt with context"""
        parts = []
        
        if context:
            parts.append(f"Context: {context}")
        
        if files:
            file_info = []
            for f in files:
                file_info.append(f"[File: {f.get('name', 'unknown')}]\n{f.get('content', '')[:500]}")
            parts.append("\n".join(file_info))
        
        parts.append(f"User: {prompt}")
        
        return "\n\n".join(parts)
    
    async def interrupt(self) -> dict:
        """Handle interrupt - stop generation and analyze intent"""
        self.should_stop = True
        
        # Get what we were saying
        partial_response = self.context_buffer
        
        # Analyze the interruption intent
        intent_analysis = self._analyze_interrupt_intent(partial_response)
        
        # Save for potential resume
        if self.redis_client and partial_response:
            await self._save_interrupted(partial_response, intent_analysis)
        
        return {
            "partial_response": partial_response,
            "intent": intent_analysis,
            "can_resume": intent_analysis in ["continue", "modify"]
        }
    
    def _analyze_interrupt_intent(self, response: str) -> str:
        """Analyze what the user interruption means"""
        # This is a simple heuristic - in production, use LLM to classify
        if not response:
            return "stop"
        
        # Check for incomplete sentence
        if response.rstrip().endswith(('.', '!', '?')):
            return "stop"  # Complete sentence, just stop
        
        # Check if mid-sentence
        if len(response.split()) < 3:
            return "stop"
        
        # Could continue or modify
        return "modify_or_stop"
    
    async def _save_interrupted(self, response: str, intent: str):
        """Save interrupted response for potential resume"""
        try:
            key = f"interrupted:{datetime.now().isoformat()}"
            data = {
                "response": response,
                "intent": intent,
                "timestamp": datetime.now().isoformat()
            }
            self.redis_client.set(key, json.dumps(data), ex=300)  # 5 min TTL
        except:
            pass
    
    async def resume(self, modified_prompt: str = None) -> Optional[str]:
        """Get saved interrupted response"""
        if not self.redis_client:
            return None
        
        try:
            # Find most recent interrupted response
            for key in self.redis_client.scan_iter("interrupted:*"):
                data = self.redis_client.get(key)
                if data:
                    return json.loads(data).get("response")
        except:
            pass
        return None
    
    async def generate(
        self, 
        prompt: str,
        stream_callback: Optional[Callable] = None
    ) -> AsyncIterator[str]:
        """Generate with streaming"""
        async for token in self.chat(prompt, stream_callback=stream_callback):
            yield token

# Global instance
llm = StreamingLLM()

async def init_llm():
    """Initialize LLM"""
    await llm.load()
    print("[LLM] Ready")

if __name__ == "__main__":
    asyncio.run(init_llm())