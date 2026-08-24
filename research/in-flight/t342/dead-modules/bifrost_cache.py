"""
Bifrost Semantic Cache - Configuration
=====================================
Semantic caching router to prevent repeat reasoning.

Bifrost is a Go-based intelligent router that:
1. Caches LLM responses by semantic meaning (not exact match)
2. Routes requests to optimal inference backend (vLLM/Ollama)
3. Manages model lifecycle based on intent

For now, this is a Python configuration that can be used
when Bifrost Go service is deployed.

Configuration Format: YAML
"""

import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import hashlib
import json

# Paths
BIFROST_CACHE_DIR = r"E:\AI-Setup\blackboard_data\semantic_cache"
os.makedirs(BIFROST_CACHE_DIR, exist_ok=True)

CACHE_INDEX_FILE = os.path.join(BIFROST_CACHE_DIR, "cache_index.jsonl")


@dataclass
class CacheEntry:
    """A semantic cache entry"""
    prompt_hash: str
    prompt_semantic: str  # Simplified version for display
    response: str
    model_used: str
    intent: str
    created_at: str
    hit_count: int = 0
    last_hit: Optional[str] = None
    ttl_hours: int = 24


class SemanticCache:
    """
    Simple semantic caching implementation.
    
    Uses prompt hashing + embedding similarity for cache hits.
    For full semantic understanding, deploy Bifrost Go service.
    
    Features:
    - MD5 hash of normalized prompt for quick lookup
    - Semantic signature for similarity matching
    - TTL-based expiration
    - Hit tracking for analytics
    """
    
    def __init__(self, cache_dir: str = BIFROST_CACHE_DIR):
        self.cache_dir = cache_dir
        self.index_file = os.path.join(cache_dir, "cache_index.jsonl")
        self.entries: Dict[str, CacheEntry] = {}
        self._load_index()
    
    def _load_index(self):
        """Load cache index from disk"""
        if os.path.exists(self.index_file):
            with open(self.index_file, 'r') as f:
                for line in f:
                    try:
                        entry_data = json.loads(line.strip())
                        entry = CacheEntry(**entry_data)
                        self.entries[entry.prompt_hash] = entry
                    except:
                        pass
    
    def _save_index(self):
        """Save cache index to disk"""
        with open(self.index_file, 'w') as f:
            for entry in self.entries.values():
                f.write(json.dumps(entry.__dict__) + "\n")
    
    def _normalize_prompt(self, prompt: str) -> str:
        """Normalize prompt for consistent hashing"""
        # Lowercase, strip whitespace, remove extra spaces
        normalized = ' '.join(prompt.lower().split())
        return normalized
    
    def _compute_hash(self, prompt: str) -> str:
        """Compute MD5 hash of normalized prompt"""
        normalized = self._normalize_prompt(prompt)
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def _compute_semantic_signature(self, prompt: str) -> str:
        """
        Compute a semantic signature (simplified).
        
        For full semantic matching, use embeddings (OpenAI, local, etc.)
        This is a keyword-based approximation.
        """
        keywords = []
        for word in prompt.lower().split():
            if len(word) > 3:  # Skip short words
                keywords.append(word)
        return "|".join(sorted(keywords)[:20])  # Top 20 keywords
    
    def get(self, prompt: str) -> Optional[str]:
        """
        Get cached response for prompt.
        
        Returns None if no cache hit.
        """
        prompt_hash = self._compute_hash(prompt)
        
        if prompt_hash in self.entries:
            entry = self.entries[prompt_hash]
            
            # Check TTL
            created = datetime.fromisoformat(entry.created_at)
            age_hours = (datetime.now() - created).total_seconds() / 3600
            
            if age_hours > entry.ttl_hours:
                # Expired
                del self.entries[prompt_hash]
                self._save_index()
                return None
            
            # Update hit stats
            entry.hit_count += 1
            entry.last_hit = datetime.now().isoformat()
            self._save_index()
            
            return entry.response
        
        return None
    
    def put(self, prompt: str, response: str, model: str = "unknown",
            intent: str = "general") -> str:
        """
        Cache a response for a prompt.
        
        Returns the prompt hash.
        """
        prompt_hash = self._compute_hash(prompt)
        
        entry = CacheEntry(
            prompt_hash=prompt_hash,
            prompt_semantic=self._compute_semantic_signature(prompt),
            response=response,
            model_used=model,
            intent=intent,
            created_at=datetime.now().isoformat(),
            hit_count=0,
            last_hit=None,
            ttl_hours=24
        )
        
        self.entries[prompt_hash] = entry
        self._save_index()
        
        return prompt_hash
    
    def invalidate(self, prompt: str = None, pattern: str = None):
        """
        Invalidate cache entries.
        
        Args:
            prompt: Specific prompt to invalidate
            pattern: Pattern to match (e.g., "import*")
        """
        if prompt:
            prompt_hash = self._compute_hash(prompt)
            if prompt_hash in self.entries:
                del self.entries[prompt_hash]
                self._save_index()
        
        if pattern:
            # Simple wildcard matching
            pattern = pattern.replace("*", "")
            to_delete = [
                h for h, e in self.entries.items()
                if pattern.lower() in e.prompt_semantic.lower()
            ]
            for h in to_delete:
                del self.entries[h]
            if to_delete:
                self._save_index()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_hits = sum(e.hit_count for e in self.entries.values())
        entries_by_intent = {}
        for e in self.entries.values():
            entries_by_intent[e.intent] = entries_by_intent.get(e.intent, 0) + 1
        
        return {
            "total_entries": len(self.entries),
            "total_hits": total_hits,
            "entries_by_intent": entries_by_intent,
            "cache_dir": self.cache_dir
        }
    
    def clear(self):
        """Clear all cache entries"""
        self.entries.clear()
        self._save_index()


# Global cache instance
_global_cache: Optional[SemanticCache] = None


def get_semantic_cache() -> SemanticCache:
    """Get global semantic cache instance"""
    global _global_cache
    if _global_cache is None:
        _global_cache = SemanticCache()
    return _global_cache


def semantic_cache_get(prompt: str) -> Optional[str]:
    """Quick access to cache get"""
    return get_semantic_cache().get(prompt)


def semantic_cache_put(prompt: str, response: str, 
                      model: str = "unknown", intent: str = "general"):
    """Quick access to cache put"""
    return get_semantic_cache().put(prompt, response, model, intent)


# Bifrost Configuration (for when Go service is deployed)
BIFROST_CONFIG = {
    "version": "1.0",
    "upstreams": {
        "vllm": {
            "url": "http://localhost:8000",
            "health_check_interval": "10s",
            "timeout": "120s"
        },
        "ollama": {
            "url": "http://localhost:11434",
            "health_check_interval": "10s",
            "timeout": "300s"
        }
    },
    "routing": {
        "default": "vllm",
        "intent_rules": {
            "VISION_PRIORITY": "vllm",
            "HIGH_REASONING": "vllm", 
            "IDLE": "ollama",
            "VIDEO_BURST": "vllm"
        }
    },
    "cache": {
        "enabled": True,
        "backend": "semantic",  # semantic or exact
        "ttl_hours": 24,
        "max_entries": 10000
    },
    "semantic": {
        "model": "sentence-transformers/all-MiniLM-L6-v2",  # Local embedding
        "similarity_threshold": 0.85
    }
}


def generate_bifrost_config() -> str:
    """Generate Bifrost configuration YAML"""
    import yaml
    return yaml.dump(BIFROST_CONFIG, default_flow_style=False)


def save_bifrost_config(path: str = "bifrost_config.yaml"):
    """Save Bifrost configuration to file"""
    config = generate_bifrost_config()
    with open(path, 'w') as f:
        f.write(config)
    return config


# Quick test
if __name__ == "__main__":
    print("=" * 50)
    print("Bifrost Semantic Cache Test")
    print("=" * 50)
    
    cache = get_semantic_cache()
    
    # Test cache put/get
    test_prompt = "How do I import a Python module?"
    test_response = "Use the import keyword: import module_name"
    
    print(f"\n[1] Caching response for: '{test_prompt}'")
    cache_hash = cache.put(test_prompt, test_response, model="test", intent="general")
    print(f"    Cache hash: {cache_hash}")
    
    print(f"\n[2] Retrieving cached response...")
    cached = cache.get(test_prompt)
    print(f"    Cached: {cached}")
    
    print(f"\n[3] Stats: {cache.get_stats()}")
    
    print(f"\n[4] Bifrost config preview:")
    config = generate_bifrost_config()
    print(config[:500] + "...")
    
    print("\n" + "=" * 50)
    print("Semantic Cache ready")
    print("=" * 50)
