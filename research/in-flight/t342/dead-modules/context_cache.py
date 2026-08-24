"""
In-Memory Context Cache
========================
Caches learnings in RAM for fast retrieval + periodic disk saves.
"""

import json
import time
import threading
from knowledge_base import KB

class ContextCache:
    """In-memory cache with periodic disk saves"""
    
    def __init__(self, save_interval=300):  # Save every 5 minutes
        self.cache = {}
        self.save_interval = save_interval
        self.last_save = time.time()
        self.kb = KB()
        self.lock = threading.Lock()
        self._running = True
        
        # Load initial cache
        self._load_from_kb()
        
        # Start periodic save thread
        self._save_thread = threading.Thread(target=self._periodic_save, daemon=True)
        self._save_thread.start()
    
    def _load_from_kb(self):
        """Load all learnings into RAM"""
        with self.lock:
            for model in self.kb.get_all_models():
                ctx = self.kb.get_model_context(model)
                if ctx.get("learnings"):
                    for key, data in ctx["learnings"].items():
                        self.cache[f"{model}:{key}"] = {
                            "model": model,
                            "key": key,
                            "data": data,
                            "loaded_at": time.time()
                        }
            
            # Load docs
            for doc in self.kb.get_all_docs():
                content = self.kb.read_doc(doc)
                self.cache[f"doc:{doc}"] = {
                    "doc": doc,
                    "content": content,
                    "loaded_at": time.time()
                }
            
            # Load context
            ctx = self.kb.get_all_context()
            for k, v in ctx.items():
                self.cache[f"context:{k}"] = {
                    "key": k,
                    "value": v,
                    "loaded_at": time.time()
                }
    
    def _periodic_save(self):
        """Periodically save cache to disk"""
        while self._running:
            time.sleep(self.save_interval)
            if self._running:
                self._force_save()
    
    def _force_save(self):
        """Save cache to Redis KB"""
        with self.lock:
            if time.time() - self.last_save >= self.save_interval:
                # Cache is already in Redis via KB writes
                # This is just updating the last_save timestamp
                self.last_save = time.time()
                print(f"[CACHE] Periodic save triggered at {time.strftime('%H:%M:%S')}")
    
    def get(self, key):
        """Get from cache (fast RAM lookup)"""
        with self.lock:
            return self.cache.get(key)
    
    def get_learnings(self, model=None):
        """Get learnings, optionally filtered by model"""
        with self.lock:
            results = {}
            for k, v in self.cache.items():
                if model and not k.startswith(f"{model}:"):
                    continue
                if k.startswith("doc:") or k.startswith("context:"):
                    continue
                results[k] = v
            return results
    
    def get_doc(self, doc_name):
        """Get documentation"""
        with self.lock:
            return self.cache.get(f"doc:{doc_name}")
    
    def get_context(self, key=None):
        """Get shared context"""
        with self.lock:
            if key:
                return self.cache.get(f"context:{key}")
            results = {}
            for k, v in self.cache.items():
                if k.startswith("context:"):
                    results[k.replace("context:", "")] = v
            return results
    
    def write(self, model_name, key, value, category="general"):
        """Write to both cache and KB"""
        with self.lock:
            # Write to KB (persists to Redis/Disk)
            self.kb.write(model_name, key, value, category)
            
            # Update cache
            cache_key = f"{model_name}:{key}"
            self.cache[cache_key] = {
                "model": model_name,
                "key": key,
                "data": {
                    "value": json.dumps(value),
                    "category": category,
                    "created_at": time.time()
                },
                "loaded_at": time.time()
            }
    
    def get_all(self):
        """Get entire cache"""
        with self.lock:
            return dict(self.cache)
    
    def get_stats(self):
        """Get cache stats"""
        with self.lock:
            learnings = sum(1 for k in self.cache if ":" in k and not k.startswith("doc:") and not k.startswith("context:"))
            docs = sum(1 for k in self.cache if k.startswith("doc:"))
            context = sum(1 for k in self.cache if k.startswith("context:"))
            return {
                "total_items": len(self.cache),
                "learnings": learnings,
                "docs": docs,
                "context": context,
                "size_bytes": sum(len(str(v)) for v in self.cache.values())
            }
    
    def stop(self):
        """Stop periodic saves"""
        self._running = False

# Global cache instance
_context_cache = None

def get_cache():
    """Get or create global cache"""
    global _context_cache
    if _context_cache is None:
        _context_cache = ContextCache(save_interval=300)  # 5 min saves
    return _context_cache

# Screenshots stored in RAM (not disk)
_screenshot_buffer = []
_max_screenshots = 10  # Keep last 10 in RAM

def capture_to_ram():
    """Capture screenshot to RAM buffer"""
    import mss
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        screenshot = sct.grab(monitor)
        
        # Store raw bytes in RAM (not disk)
        import struct
        img_bytes = bytes(screenshot.rgb)
        
        _screenshot_buffer.append({
            "timestamp": time.time(),
            "width": screenshot.width,
            "height": screenshot.height,
            "data": img_bytes,
            "size_bytes": len(img_bytes)
        })
        
        # Keep only last N
        while len(_screenshot_buffer) > _max_screenshots:
            _screenshot_buffer.pop(0)
        
        return len(_screenshot_buffer)

def get_latest_screenshot():
    """Get latest screenshot from RAM"""
    if _screenshot_buffer:
        return _screenshot_buffer[-1]
    return None

def get_screenshot_count():
    """Get number of screenshots in RAM"""
    return len(_screenshot_buffer)

def clear_screenshot_buffer():
    """Clear screenshot RAM buffer"""
    global _screenshot_buffer
    _screenshot_buffer = []


if __name__ == "__main__":
    # Test the cache
    cache = get_cache()
    print("Context Cache initialized")
    print(f"Stats: {cache.get_stats()}")
    
    # Test screenshot RAM storage
    print("\nTesting RAM screenshot storage...")
    count = capture_to_ram()
    print(f"Screenshots in RAM: {count}")
    latest = get_latest_screenshot()
    if latest:
        print(f"Latest: {latest['width']}x{latest['height']}, {latest['size_bytes']/1024/1024:.2f}MB")