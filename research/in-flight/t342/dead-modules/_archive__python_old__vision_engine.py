"""
Vision Engine - Redis-Cached Screen Understanding
==============================================
GPU-accelerated Florence-2 with Redis caching for multi-agent sharing.

All vision results are cached in Redis for:
- Fast retrieval by other agents
- Reduced GPU usage (don't re-analyze same screen)
- Session persistence
- RAM storage for speed

Usage:
    from vision_engine import VisionEngine, capture_and_analyze
    
    # Single call - captures, analyzes, caches, returns
    result = capture_and_analyze(task="ocr")
    
    # Check cache first
    result = get_cached_analysis(cache_key)
"""

import os
import json
import hashlib
import base64
import io
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

import torch
from PIL import Image, ImageGrab

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

# Redis config
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_PREFIX = "vision:"
CACHE_TTL = 3600  # 1 hour

# Paths
SCREENSHOT_DIR = r"E:\AI-Setup\session_screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# Florence-2 model
FLORENCE_MODEL = "microsoft/Florence-2-base"

# Try DirectML
try:
    import torch_directml
    DIRECTML_AVAILABLE = True
except ImportError:
    DIRECTML_AVAILABLE = False


def get_redis():
    """Get Redis connection"""
    if not REDIS_AVAILABLE:
        return None
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
        r.ping()
        return r
    except:
        return None


def get_device():
    """Get best available device"""
    if DIRECTML_AVAILABLE:
        try:
            dml = torch_directml.device()
            test = torch.tensor([1.0], device=dml)
            return dml, "DirectML"
        except:
            pass
    
    if torch.cuda.is_available():
        return torch.device("cuda"), "CUDA"
    
    return torch.device("cpu"), "CPU"


class VisionEngine:
    """Vision model with Redis caching"""
    
    def __init__(self, model_name: str = FLORENCE_MODEL):
        self.model_name = model_name
        self._device = None
        self._model = None
        self._processor = None
        self._loaded = False
        self._redis = get_redis()
        self._use_dml = False
    
    def load(self) -> bool:
        if self._loaded:
            return True
        
        try:
            from transformers import AutoModelForCausalLM, AutoProcessor
            
            self._device, device_name = get_device()
            self._use_dml = "DirectML" in device_name
            
            print(f"[vision] Loading {self.model_name} on {device_name}")
            
            self._processor = AutoProcessor.from_pretrained(
                self.model_name,
                trust_remote_code=True
            )
            
            self._model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                trust_remote_code=True
            )
            
            if self._use_dml:
                self._model = self._model.to(self._device)
            elif torch.cuda.is_available():
                self._model = self._model.cuda()
            
            self._model.eval()
            self._loaded = True
            print(f"[vision] Model loaded on {device_name}")
            return True
            
        except Exception as e:
            print(f"[vision] Load failed: {e}")
            return False
    
    def unload(self):
        if self._model is not None:
            del self._model
            del self._processor
            self._model = None
            self._processor = None
            self._loaded = False
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
    
    def _analyze_raw(self, image: Image.Image, task: str) -> Dict[str, Any]:
        """Internal analysis without caching"""
        if not self._loaded:
            if not self.load():
                return {"error": "Model not loaded"}
        
        prompts = {
            "caption": "<CAPTION>",
            "detailed_caption": "<DETAILED_CAPTION>",
            "ocr": "<OCR>",
            "ocr_with_region": "<OCR_WITH_REGION>",
            "ui_elements": "<OD>",
            "error_detection": "<GENERAL_OCR>",
        }
        
        prompt = prompts.get(task, "<CAPTION>")
        
        try:
            inputs = self._processor(
                text=prompt,
                images=image,
                return_tensors="pt"
            )
            
            if self._use_dml:
                inputs = {k: v.to(self._device) for k, v in inputs.items()}
            elif torch.cuda.is_available():
                inputs = {k: v.cuda() for k, v in inputs.items()}
            
            with torch.no_grad():
                generated_ids = self._model.generate(
                    input_ids=inputs["input_ids"],
                    pixel_values=inputs["pixel_values"],
                    max_new_tokens=1024,
                    do_sample=False
                )
            
            generated_text = self._processor.batch_decode(
                generated_ids,
                skip_special_tokens=True
            )[0]
            
            return {
                "task": task,
                "result": generated_text,
                "device": str(self._device),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {"error": str(e), "task": task}
    
    def analyze(self, image: Image.Image, task: str = "caption") -> Dict[str, Any]:
        """Analyze with Redis caching"""
        # Generate cache key from image hash + task
        img_hash = hashlib.md5(image.tobytes()).hexdigest()[:12]
        cache_key = f"{REDIS_PREFIX}analysis:{task}:{img_hash}"
        
        # Check Redis cache
        if self._redis:
            cached = self._redis.get(cache_key)
            if cached:
                data = json.loads(cached)
                data["cached"] = True
                return data
        
        # Run analysis
        result = self._analyze_raw(image, task)
        
        # Cache in Redis
        if self._redis and "error" not in result:
            try:
                self._redis.setex(
                    cache_key,
                    CACHE_TTL,
                    json.dumps(result)
                )
                
                # Also store screen hash -> task index for quick lookup
                self._redis.sadd(f"{REDIS_PREFIX}screens:{img_hash}", task)
                self._redis.expire(f"{REDIS_PREFIX}screens:{img_hash}", CACHE_TTL)
            except Exception as e:
                print(f"[vision] Cache write failed: {e}")
        
        result["cached"] = False
        return result
    
    def analyze_full(self, image: Image.Image) -> Dict[str, Any]:
        """Run multiple analyses on same image, cache all"""
        img_hash = hashlib.md5(image.tobytes()).hexdigest()[:12]
        results = {
            "image_hash": img_hash,
            "timestamp": datetime.now().isoformat(),
            "tasks": {}
        }
        
        for task in ["caption", "detailed_caption", "ocr"]:
            results["tasks"][task] = self.analyze(image, task)
        
        return results


def capture_screen() -> Optional[Image.Image]:
    """Capture full screen"""
    try:
        return ImageGrab.grab(include_layered_windows=False)
    except Exception as e:
        print(f"[vision] Capture failed: {e}")
        return None


def save_to_redis(image: Image.Image, tag: str = "capture") -> str:
    """Save screenshot to Redis (RAM) + disk backup"""
    if image is None:
        return None
    
    img_hash = hashlib.md5(image.tobytes()).hexdigest()[:12]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save to disk
    disk_path = os.path.join(SCREENSHOT_DIR, f"screen_{tag}_{timestamp}_{img_hash}.png")
    image.save(disk_path, "PNG")
    
    # Encode to base64
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    b64_data = base64.b64encode(buffer.getvalue()).decode("utf-8")
    
    # Store in Redis
    r = get_redis()
    if r:
        redis_key = f"{REDIS_PREFIX}screenshot:{img_hash}"
        redis_data = {
            "hash": img_hash,
            "tag": tag,
            "timestamp": timestamp,
            "width": image.width,
            "height": image.height,
            "data": b64_data,
            "disk_path": disk_path
        }
        r.setex(redis_key, CACHE_TTL, json.dumps(redis_data))
        r.sadd(f"{REDIS_PREFIX}screenshot_keys", img_hash)
        
        print(f"[vision] Screenshot {img_hash} saved to Redis + disk")
        return img_hash
    
    return disk_path


def get_from_redis(img_hash: str) -> Optional[Dict]:
    """Retrieve screenshot from Redis"""
    r = get_redis()
    if not r:
        return None
    
    data = r.get(f"{REDIS_PREFIX}screenshot:{img_hash}")
    if data:
        return json.loads(data)
    return None


def capture_and_analyze(task: str = "caption") -> Dict[str, Any]:
    """One-shot: capture screen, save to Redis, analyze, cache results"""
    image = capture_screen()
    if image is None:
        return {"error": "Screen capture failed"}
    
    # Save screenshot to Redis
    img_hash = save_to_redis(image, "analysis")
    
    # Analyze
    engine = VisionEngine()
    result = engine.analyze(image, task)
    
    # Add metadata
    result["image_hash"] = img_hash
    result["image_size"] = f"{image.width}x{image.height}"
    
    # Save to Redis under analysis key
    r = get_redis()
    if r:
        analysis_key = f"{REDIS_PREFIX}analysis:{img_hash}:{task}"
        r.setex(analysis_key, CACHE_TTL, json.dumps(result))
    
    engine.unload()
    
    return result


def get_cached_analysis(img_hash: str, task: str = "caption") -> Optional[Dict]:
    """Get cached analysis from Redis"""
    r = get_redis()
    if not r:
        return None
    
    data = r.get(f"{REDIS_PREFIX}analysis:{img_hash}:{task}")
    if data:
        result = json.loads(data)
        result["cached"] = True
        return result
    return None


def get_recent_captures(limit: int = 10) -> List[Dict]:
    """Get recent screen captures from Redis"""
    r = get_redis()
    if not r:
        return []
    
    hashes = r.smembers(f"{REDIS_PREFIX}screenshot_keys")
    captures = []
    
    for img_hash in list(hashes)[:limit]:
        data = get_from_redis(img_hash)
        if data:
            captures.append({
                "hash": img_hash,
                "tag": data.get("tag"),
                "timestamp": data.get("timestamp"),
                "size": f"{data.get('width')}x{data.get('height')}"
            })
    
    return captures


def quick_ocr() -> str:
    """Quick OCR - fastest way to get text from screen"""
    result = capture_and_analyze("ocr")
    return result.get("result", result.get("error", "Failed"))


def quick_caption() -> str:
    """Quick caption - describe what's on screen"""
    result = capture_and_analyze("caption")
    return result.get("result", result.get("error", "Failed"))


def get_screen_context() -> Dict[str, Any]:
    """Get full screen context for agent re-priming"""
    image = capture_screen()
    if image is None:
        return {"error": "Screen capture failed"}
    
    img_hash = save_to_redis(image, "context")
    engine = VisionEngine()
    
    # Run all analyses
    results = {
        "image_hash": img_hash,
        "timestamp": datetime.now().isoformat(),
        "caption": engine.analyze(image, "caption"),
        "detailed_caption": engine.analyze(image, "detailed_caption"),
        "ocr": engine.analyze(image, "ocr")
    }
    
    # Cache in Redis
    r = get_redis()
    if r:
        r.setex(f"{REDIS_PREFIX}context:{img_hash}", CACHE_TTL, json.dumps(results))
    
    engine.unload()
    return results


# CLI test
if __name__ == "__main__":
    print("=" * 60)
    print("Vision Engine - Redis-Cached Analysis")
    print("=" * 60)
    
    print("\n[1] Testing capture and Redis save...")
    image = capture_screen()
    if image:
        print(f"    Captured: {image.size}")
        img_hash = save_to_redis(image, "test")
        print(f"    Hash: {img_hash}")
    else:
        print("    Capture failed")
        exit(1)
    
    print("\n[2] Testing OCR...")
    result = quick_ocr()
    print(f"    OCR: {result[:200] if len(result) > 200 else result}")
    
    print("\n[3] Testing caption...")
    result = quick_caption()
    print(f"    Caption: {result[:200] if len(result) > 200 else result}")
    
    print("\n[4] Testing cached retrieval...")
    if image:
        img_hash = hashlib.md5(image.tobytes()).hexdigest()[:12]
        cached = get_cached_analysis(img_hash, "ocr")
        print(f"    Cached: {cached is not None}")
    
    print("\n[5] Recent captures in Redis...")
    captures = get_recent_captures()
    print(f"    Count: {len(captures)}")
    for c in captures[:3]:
        print(f"    - {c}")
    
    print("\n" + "=" * 60)
    print("Vision Engine complete!")
    print("=" * 60)
