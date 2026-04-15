# AI Model Recommendations for AMD RX 9070 XT (16GB VRAM)

## Current System Status

You have a powerful setup:
- **GPU**: AMD RX 9070 XT (16GB VRAM) - RDNA4 (gfx1201)
- **RAM**: 32GB DDR5
- **ROCm**: 7.2.1 with librocdxg working
- **Docker**: GPU passthrough functional

---

## 1. Music Generation & Stem Separation Models

### Stem Separation (extract vocals, drums, bass, instruments)

| Model | Type | Best For | VRAM Needed | Notes |
|-------|------|----------|-------------|-------|
| **Demucs HTDemucs FT** | Open Source | Best overall quality | 4-6GB | Current gold standard for open-source. Use `htdemucs_ft` |
| **BS-RoFormer** | Open Source | Vocal isolation (best) | 4-6GB | Current SOTA for vocals (~10.9dB SDR) |
| **Spleeter** | Open Source | Fast/CPU fallback | 2GB | Older but reliable, fast |
| **StemForge** | All-in-one UI | Combined pipeline | 6-8GB | Includes Demucs, BS-RoFormer, MIDI extraction, Stable Audio Open |

### Music Generation

| Model | Type | Best For | VRAM Needed | Notes |
|-------|------|----------|-------------|-------|
| **Stable Audio Open** | Open Source | Text-to-audio generation | 8GB | Up to 47 seconds, text conditioning |
| **MusicGen** | Meta | Music generation | 6-8GB | Also supports stem generation |
| **RVC (Retrieval-based Voice Conversion)** | Open Source | Voice transformation | 4GB | For voice cloning/conversion |
| **Suno** | Cloud | Full music production | N/A | Not local - subscription |

### Recommended Local Setup:
1. **StemForge** (GitHub) - Combines Demucs, BS-RoFormer, MIDI extraction, Stable Audio Open
2. Run via Docker with ROCm - requires StemForge's GPU-accelerated pipeline

---

## 2. Coding & Agentic LLM Models

### Best Local-Runnable Models (for Ollama/LM Studio)

| Model | Size | Coding Ability | VRAM Needed | Notes |
|-------|------|----------------|-------------|-------|
| **DeepSeek Coder V2** | 16B/236B | Excellent | 8-16GB | Best open-source for coding |
| **CodeLlama 70B** | 70B | Excellent | 14-16GB (FP16) | Meta's coding model |
| **Qwen2.5-Coder** | 14B | Very good | 8GB | Good balance |
| **Phi-4-mini** | 3.8B | Good | 4GB | Fast, smaller footprint |

### Best Cloud/API Models (via Ollama or API)

| Model | Provider | Coding Ability | Best Use |
|-------|----------|----------------|----------|
| **Claude Opus 4.6** | Anthropic | BEST overall | Complex multi-file tasks, agentic |
| **Claude Sonnet 4.6** | Anthropic | Excellent | Daily coding, balanced |
| **GPT-5.2-Codex** | OpenAI | SOTA coding | Agentic coding, production |
| **Gemini 3 Pro** | Google | Strong backend | Architecture, docs |

### Recommended Coding Setup:
- **DeepSeek Coder V2** (16B) - for local Ollama (best open-source coder)
- **Claude Opus 4.6** - for complex tasks (API)
- **Claude Sonnet 4.6** - for daily coding (API)

---

## 3. Other Useful AI Models

### Speech-to-Text (STT)

| Model | Type | Notes |
|-------|------|-------|
| **Whisper** (large-v3) | OpenAI | Best STT, runs locally |
| **faster-whisper** | Optimized | Faster version of Whisper |

### Text-to-Speech (TTS)

| Model | Type | Notes |
|-------|------|-------|
| **Coqui TTS** | Open Source | High quality, local |
| **Piper** | Open Source | Lightweight, fast |
| **Edge-TTS** | Microsoft | Cloud, very natural |

### Vision/OCR

| Model | Type | Notes |
|-------|------|-------|
| **PaddleOCR** | Baidu | Full OCR pipeline |
| **TrOCR** | Microsoft | Transformer-based OCR |

### Image Generation

| Model | Type | Notes |
|-------|------|-------|
| **Stable Diffusion** | Stability AI | Local image gen (needs ~10GB) |
| **FLUX.1** | BlackForest | New SOTA image generation |

---

## 4. Recommended Model Stack for Your System

### Priority 1: Install Now
1. **Ollama** - Already running at port 11434
   - `ollama pull deepseek-coder-v2:16b` - Best open-source coding model
   
2. **StemForge** - Docker container for music AI
   - Demucs + BS-RoFormer for stem separation
   - Stable Audio Open for music generation
   - BasicPitch for MIDI extraction

### Priority 2: Next Steps
1. **Whisper** - Already in your services folder
2. **Coqui TTS** - For local voice output

### Priority 3: Cloud APIs
1. Set up Claude API key for Opus/Sonnet
2. Use GPT-5.2-Codex for complex agentic tasks

---

## 5. Memory Management Strategy

With 16GB VRAM, manage as:
- **Music AI**: 8-10GB (Demucs + Stable Audio)
- **Coding LLM**: 8-16GB (DeepSeek Coder 16B or CodeLlama)
- **Combined**: Use services sequentially, not simultaneously

---

## 6. Quick Start Commands

### Pull coding model to Ollama:
```bash
docker exec ai-ollama ollama pull deepseek-coder-v2:16b
```

### Test stem separation (Demucs):
```bash
docker run --device=/dev/dxg -v /path/to/songs:/input -v /path/to/output:/output \
  -e HSA_ENABLE_DXG_DETECTION=1 \
  ghcr.io/facebookresearch/demucs:lightweight \
  -d htdemucs_ft /input/song.mp3
```

---

This gives you a comprehensive AI music and coding workstation with your 9070 XT!