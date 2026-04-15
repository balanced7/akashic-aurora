"""
Breakthrough Stack Configuration
================================
Centralized configuration for GPU provider switching.

Supports:
- OLLAMA: Local Ollama (current, works on Windows)
- VLLM: vLLM server (future, requires WSL2+ROCm)
- API: Remote API (cloud/bare metal)

Usage:
    from config import GPU_CONFIG, get_provider, get_base_url
    
    provider = get_provider()  # Returns 'OLLAMA', 'VLLM', or 'API'
    base_url = get_base_url()  # Returns appropriate endpoint
"""

import os
from typing import Dict, Any
from dataclasses import dataclass
from enum import Enum


class GPUProvider(Enum):
    """GPU inference providers"""
    OLLAMA = "ollama"      # Local Ollama (current)
    VLLM = "vllm"         # vLLM server (future)
    API = "api"            # Remote API (cloud)


@dataclass
class ProviderConfig:
    """Configuration for a GPU provider"""
    name: str
    base_url: str
    api_key: str = ""
    timeout: int = 120
    max_retries: int = 3


# Provider configurations
PROVIDERS: Dict[GPUProvider, ProviderConfig] = {
    GPUProvider.OLLAMA: ProviderConfig(
        name="Ollama (Local)",
        base_url="http://localhost:11434/v1",
        timeout=120,
        max_retries=3
    ),
    GPUProvider.VLLM: ProviderConfig(
        name="vLLM (Local)",
        base_url="http://localhost:8000/v1",
        timeout=120,
        max_retries=3
    ),
    GPUProvider.API: ProviderConfig(
        name="Remote API",
        base_url=os.environ.get("API_BASE_URL", "https://api.openai.com/v1"),
        api_key=os.environ.get("API_KEY", ""),
        timeout=60,
        max_retries=3
    ),
}


def get_provider() -> GPUProvider:
    """
    Get current GPU provider from environment variable.
    
    Returns:
        GPUProvider enum value
    """
    provider_str = os.environ.get("GPU_PROVIDER", "OLLAMA").upper()
    
    try:
        return GPUProvider[provider_str]
    except KeyError:
        print(f"[config] Unknown GPU_PROVIDER: {provider_str}, defaulting to OLLAMA")
        return GPUProvider.OLLAMA


def get_config() -> ProviderConfig:
    """Get current provider configuration"""
    provider = get_provider()
    return PROVIDERS[provider]


def get_base_url() -> str:
    """Get current base URL for API calls"""
    return get_config().base_url


def get_api_key() -> str:
    """Get API key for current provider"""
    return get_config().api_key


def is_local() -> bool:
    """Check if using local provider (Ollama or vLLM)"""
    provider = get_provider()
    return provider in [GPUProvider.OLLAMA, GPUProvider.VLLM]


# Hardware configuration
HARDWARE = {
    "gpu": "AMD 9070 XT (16GB VRAM)",
    "cpu": "AMD 9950X3D",
    "ram": "32GB DDR5",
    "vram_total": 16.0,
    "vram_reserve": 4.5,  # Always keep free
    "vram_threshold_warning": 12.0,
    "vram_threshold_critical": 14.5,
}

# Model configurations
MODELS = {
    "generator": {
        "name": "deepseek-ai/deepseek-coder-v2-16b",
        "size_gb": 8.9,
        "provider": GPUProvider.OLLAMA,
        "context_length": 16384,
    },
    "analyst": {
        "name": "meta-llama/Llama-3.2-3B-Instruct", 
        "size_gb": 2.0,
        "provider": GPUProvider.OLLAMA,
        "context_length": 8192,
    },
    "vision": {
        "name": "microsoft/Florence-2-base",
        "size_gb": 0.5,
        "provider": GPUProvider.OLLAMA,
        "context_length": 2048,
    },
}

# Paths
PATHS = {
    "setup": r"E:\AI-Setup",
    "model_cache": r"E:\AI-Setup\model_cache",
    "dockerized_ai": r"E:\AI-Setup\dockerized-ai",
    "session_logs": r"E:\AI-Setup\session_logs",
    "blackboard_data": r"E:\AI-Setup\blackboard_data",
    "escalations": r"E:\AI-Setup\blackboard_data\escalations",
    "screenshots": r"E:\AI-Setup\session_screenshots",
}

# VRAM budget
VRAM_BUDGET = {
    "generator": 8.9,   # DeepSeek-Coder-V2-16B
    "analyst": 2.0,    # Llama 3.2-3B
    "vision": 0.5,      # Florence-2 (when active)
    "total_models": 11.4,  # With vision active
    "reserve": 4.6,     # Headroom
    "max_utilization": 0.90,  # 90% GPU memory
}


def print_config():
    """Print current configuration"""
    config = get_config()
    print("=" * 50)
    print("BREAKTHROUGH STACK CONFIGURATION")
    print("=" * 50)
    print(f"GPU Provider: {config.name}")
    print(f"Base URL: {config.base_url}")
    print(f"Timeout: {config.timeout}s")
    print()
    print("Hardware:")
    for k, v in HARDWARE.items():
        print(f"  {k}: {v}")
    print()
    print("VRAM Budget:")
    print(f"  Generator: {VRAM_BUDGET['generator']}GB")
    print(f"  Analyst: {VRAM_BUDGET['analyst']}GB")
    print(f"  Vision: {VRAM_BUDGET['vision']}GB")
    print(f"  Total: {VRAM_BUDGET['total_models']}GB")
    print(f"  Reserve: {VRAM_BUDGET['reserve']}GB")
    print("=" * 50)


# Quick test
if __name__ == "__main__":
    print_config()
    
    print()
    print("Switching demo:")
    print(f"  Current provider: {get_provider().value}")
    print(f"  Base URL: {get_base_url()}")
    print(f"  Is local: {is_local()}")
