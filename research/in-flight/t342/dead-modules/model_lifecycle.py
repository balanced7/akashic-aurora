"""
Model Lifecycle Manager - VRAM-Aware Swap-Shop
============================================
Dynamic model loading/unloading based on VRAM availability and task priority.

Priority Queue:
- HIGH: Text Generation/Reasoning (Generator + Analyst always loaded)
- MEDIUM: Vision/Troubleshooting (Florence-2 loaded on demand)
- BURST: Video Generation (Hunyuan/Wan - deload others first)

VRAM Budget (16GB RX 9070 XT):
- Generator (DeepSeek-Coder-V2-16B): ~8.9GB
- Analyst (Llama 3.2 3B): ~2.0GB
- Florence-2 Base: ~0.5GB
- Reserve: ~4.6GB

Usage:
    from model_lifecycle import ModelLifecycleManager, Priority
    
    mgr = ModelLifecycleManager()
    
    # Check if we can load vision model
    if mgr.can_load(Priority.MEDIUM):
        mgr.load_vision_model()
        
    # After vision task, swap back
    mgr.unload_vision_model()
"""

import os
import sys
import time
import subprocess
import json
import gc
from enum import Enum

import torch
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from datetime import datetime

# Import config for GPU provider settings
sys.path.insert(0, r'E:\AI-Setup')
try:
    from config import (
        get_provider, get_base_url, get_config,
        HARDWARE, VRAM_BUDGET, GPUProvider
    )
    USE_CONFIG = True
except ImportError:
    USE_CONFIG = False
    # Fallback values if config.py not available
    VRAM_TOTAL = 16.0
    VRAM_RESERVE = 4.5
    VRAM_THRESHOLD_WARNING = 12.0
    VRAM_THRESHOLD_CRITICAL = 14.5
    VRAM_THRESHOLD_EMERGENCY = 15.5

# VRAM thresholds (GB) - use config if available
if USE_CONFIG:
    VRAM_TOTAL = HARDWARE.get("vram_total", 16.0)
    VRAM_RESERVE = HARDWARE.get("vram_reserve", 4.5)
    VRAM_THRESHOLD_WARNING = HARDWARE.get("vram_threshold_warning", 12.0)
    VRAM_THRESHOLD_CRITICAL = HARDWARE.get("vram_threshold_critical", 14.5)
    VRAM_THRESHOLD_EMERGENCY = 15.5

# Model sizes (GB)
VRAM_GENERATOR = 8.9
VRAM_ANALYST = 2.0
VRAM_VISION = 0.5
VRAM_VIDEO = 3.0  # Wan2.1 or Hunyuan


class Priority(Enum):
    """Task priority levels"""
    HIGH = 1      # Generator + Analyst (always loaded)
    MEDIUM = 2    # Vision (Florence-2)
    BURST = 3     # Video generation
    IDLE = 4      # Nothing loaded


@dataclass
class ModelInfo:
    """Information about a loaded model"""
    name: str
    size_gb: float
    loaded_at: float = field(default_factory=time.time)
    last_used: float = field(default_factory=time.time)
    priority: Priority = Priority.IDLE


class ModelLifecycleManager:
    """
    Manages model lifecycle based on VRAM availability.
    
    Implements "Swap-Shop" logic:
    1. Check current VRAM usage
    2. Determine if target model can fit
    3. If not, identify models to unload
    4. Execute swap with garbage collection
    """
    
    def __init__(self):
        self.models: Dict[str, ModelInfo] = {}
        self.vision_engine = None
        self.vision_loaded = False
        
        # Register known models
        self.register_model("generator", VRAM_GENERATOR, Priority.HIGH)
        self.register_model("analyst", VRAM_ANALYST, Priority.HIGH)
        self.register_model("vision", VRAM_VISION, Priority.MEDIUM)
        self.register_model("video", VRAM_VIDEO, Priority.BURST)
    
    def register_model(self, name: str, size_gb: float, priority: Priority):
        """Register a model with its VRAM footprint"""
        self.models[name] = ModelInfo(
            name=name,
            size_gb=size_gb,
            priority=priority
        )
    
    def get_vram_usage(self) -> Optional[float]:
        """
        Get current VRAM usage in GB.
        
        Returns None if unable to detect.
        """
        try:
            # Try AMD ROCm (WSL2)
            result = subprocess.run(
                ['wsl', '-d', 'Ubuntu-24.04', '-e', 'rocm-smi', '--showid', '--json'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                for gpu_id, info in data.items():
                    if 'vram_used' in info:
                        return float(info['vram_used'].replace('MB', '')) / 1024
        except:
            pass
        
        try:
            # Try NVIDIA
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=memory.used', '--format=csv,noheader,nounits'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return float(result.stdout.strip()) / 1024
        except:
            pass
        
        return None
    
    def get_loaded_models(self) -> List[str]:
        """Get list of currently loaded model names"""
        return [name for name, info in self.models.items() 
                if info.loaded_at > 0 and info.priority != Priority.IDLE]
    
    def get_available_vram(self) -> float:
        """Get available VRAM in GB"""
        current = self.get_vram_usage() or 0
        return VRAM_TOTAL - current
    
    def can_load(self, model_name: str) -> bool:
        """Check if model can fit in available VRAM"""
        if model_name not in self.models:
            return False
        
        model = self.models[model_name]
        available = self.get_available_vram()
        
        return available >= model.size_gb
    
    def get_models_to_unload(self, target_model: str) -> List[str]:
        """
        Get list of models that should be unloaded to make room.
        
        Priority: Unload lowest priority models first.
        """
        if target_model not in self.models:
            return []
        
        target = self.models[target_model]
        available = self.get_available_vram()
        
        models_to_unload = []
        freed_vram = 0
        
        # Sort models by priority (lowest first)
        sorted_models = sorted(
            self.models.items(),
            key=lambda x: x[1].priority.value,
            reverse=True
        )
        
        for name, model in sorted_models:
            # Don't unload if it's the target or not loaded
            if name == target_model or model.loaded_at == 0:
                continue
            
            # Don't unload HIGH priority unless emergency
            if model.priority == Priority.HIGH and target.size_gb + freed_vram < available:
                continue
            
            models_to_unload.append(name)
            freed_vram += model.size_gb
            
            if freed_vram >= target.size_gb - available + VRAM_RESERVE:
                break
        
        return models_to_unload
    
    def unload_model(self, model_name: str) -> bool:
        """
        Unload a model and free its VRAM.
        
        Returns True if successful.
        """
        if model_name not in self.models:
            return False
        
        model = self.models[model_name]
        
        if model_name == "vision" and self.vision_engine:
            self.vision_engine.unload()
            self.vision_loaded = False
            print("[lifecycle] Vision engine unloaded")
        
        # Force garbage collection
        gc.collect()
        
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        model.loaded_at = 0
        print(f"[lifecycle] Unloaded {model_name}, VRAM freed: {model.size_gb}GB")
        
        return True
    
    def load_vision_model(self, force: bool = False) -> bool:
        """
        Load Florence-2 vision model.
        
        Returns True if loaded or already loaded.
        """
        if self.vision_loaded and not force:
            return True
        
        # Check if we can load
        if not self.can_load("vision"):
            # Try to free up space
            to_unload = self.get_models_to_unload("vision")
            for model_name in to_unload:
                self.unload_model(model_name)
        
        if not self.can_load("vision"):
            print("[lifecycle] Cannot load vision - insufficient VRAM")
            return False
        
        try:
            from vision_engine import VisionEngine
            
            if self.vision_engine is None:
                self.vision_engine = VisionEngine()
            
            if self.vision_engine.load():
                self.models["vision"].loaded_at = time.time()
                self.vision_loaded = True
                print("[lifecycle] Vision model loaded")
                return True
            else:
                return False
                
        except Exception as e:
            print(f"[lifecycle] Failed to load vision: {e}")
            return False
    
    def unload_vision_model(self):
        """Unload vision model"""
        self.unload_model("vision")
    
    def execute_with_vision(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function with vision model loaded.
        
        Automatically loads vision before and unloads after.
        
        Example:
            result = mgr.execute_with_vision(
                my_vision_function,
                screenshot,
                task="error_detection"
            )
        """
        # Load vision if not loaded
        loaded = self.load_vision_model()
        
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            # Always unload after use
            if loaded:
                self.unload_vision_model()
    
    def check_vram_and_warn(self) -> Dict[str, Any]:
        """
        Check VRAM and return warning status.
        
        Returns dict with:
        - usage_gb: Current usage
        - available_gb: Available
        - status: "ok" | "warning" | "critical" | "emergency"
        - models_loaded: List of loaded models
        """
        usage = self.get_vram_usage() or 0
        available = VRAM_TOTAL - usage
        
        if usage >= VRAM_THRESHOLD_EMERGENCY:
            status = "emergency"
        elif usage >= VRAM_THRESHOLD_CRITICAL:
            status = "critical"
        elif usage >= VRAM_THRESHOLD_WARNING:
            status = "warning"
        else:
            status = "ok"
        
        return {
            "usage_gb": round(usage, 2),
            "available_gb": round(available, 2),
            "status": status,
            "models_loaded": self.get_loaded_models(),
            "timestamp": datetime.now().isoformat()
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get full lifecycle manager status"""
        vram_status = self.check_vram_and_warn()
        
        model_status = {}
        for name, info in self.models.items():
            model_status[name] = {
                "size_gb": info.size_gb,
                "priority": info.priority.name,
                "loaded": info.loaded_at > 0,
                "loaded_at": datetime.fromtimestamp(info.loaded_at).isoformat() if info.loaded_at > 0 else None
            }
        
        return {
            "vram": vram_status,
            "models": model_status,
            "vision_engine_ready": self.vision_loaded
        }
    
    def suggest_swap(self, desired_priority: Priority) -> Dict[str, Any]:
        """
        Suggest what models to swap for a given priority.
        
        Returns dict with:
        - action: "keep" | "swap" | "impossible"
        - to_load: Model to load
        - to_unload: Models to unload
        - reason: Explanation
        """
        if desired_priority == Priority.HIGH:
            return {
                "action": "keep",
                "to_load": ["generator", "analyst"],
                "to_unload": [],
                "reason": "HIGH priority - always keep generator + analyst"
            }
        
        if desired_priority == Priority.MEDIUM:
            # Vision task - need ~0.5GB
            available = self.get_available_vram()
            
            if available >= VRAM_VISION:
                return {
                    "action": "keep",
                    "to_load": ["vision"],
                    "to_unload": [],
                    "reason": f"Available VRAM {available:.1f}GB >= {VRAM_VISION}GB needed"
                }
            else:
                # Need to unload something
                to_unload = self.get_models_to_unload("vision")
                if to_unload:
                    return {
                        "action": "swap",
                        "to_load": ["vision"],
                        "to_unload": to_unload,
                        "reason": f"Need {VRAM_VISION}GB, freeing {to_unload}"
                    }
                else:
                    return {
                        "action": "impossible",
                        "to_load": [],
                        "to_unload": [],
                        "reason": "Cannot free enough VRAM for vision"
                    }
        
        return {
            "action": "keep",
            "to_load": [],
            "to_unload": [],
            "reason": "Unknown priority"
        }


def create_lifecycle_manager() -> ModelLifecycleManager:
    """Factory function to create lifecycle manager"""
    return ModelLifecycleManager()


# Quick test
if __name__ == "__main__":
    print("=" * 50)
    print("Model Lifecycle Manager Test")
    print("=" * 50)
    
    mgr = create_lifecycle_manager()
    
    print("\n[1] VRAM Status:")
    status = mgr.check_vram_and_warn()
    print(f"    Usage: {status['usage_gb']}GB / {VRAM_TOTAL}GB")
    print(f"    Available: {status['available_gb']}GB")
    print(f"    Status: {status['status'].upper()}")
    print(f"    Loaded: {status['models_loaded']}")
    
    print("\n[2] Suggest swap for vision:")
    suggestion = mgr.suggest_swap(Priority.MEDIUM)
    print(f"    Action: {suggestion['action']}")
    print(f"    To load: {suggestion['to_load']}")
    print(f"    To unload: {suggestion['to_unload']}")
    print(f"    Reason: {suggestion['reason']}")
    
    print("\n[3] Full status:")
    full_status = mgr.get_status()
    print(f"    Vision ready: {full_status['vision_engine_ready']}")
    for name, info in full_status['models'].items():
        loaded = "LOADED" if info['loaded'] else " unloaded"
        print(f"    {name}: {info['size_gb']}GB ({info['priority']}) - {loaded}")
    
    print("\n" + "=" * 50)
    print("Lifecycle Manager ready")
    print("=" * 50)
