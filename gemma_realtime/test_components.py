#!/usr/bin/env python3
"""Test script for Gemma Realtime"""
import asyncio
import sys

async def test():
    print("[Test] Loading components...")
    
    from stt_processor import init_stt
    from tts_processor import init_tts
    from llm_wrapper import init_llm
    
    print("[Test] Testing STT...")
    await init_stt()
    print("  STT OK")
    
    print("[Test] Testing TTS...")
    await init_tts()
    print("  TTS OK")
    
    print("[Test] Testing LLM...")
    await init_llm()
    print("  LLM OK")
    
    print("[Test] All tests passed!")
    return True

if __name__ == "__main__":
    result = asyncio.run(test())
    sys.exit(0 if result else 1)