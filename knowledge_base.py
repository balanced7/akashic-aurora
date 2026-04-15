"""
AI Knowledge Base & Documentation System
==========================================
All AI models should use this system to store and retrieve learnings.
This ensures cohesive, non-destructive collaboration.

Features:
- Connection pooling for Redis
- Pipeline support for batch operations
- TTL support for expiring learnings

Usage:
    from knowledge_base import KB
    
    kb = KB()
    kb.write("model_name", "key", "value")  # Write learning
    kb.write("model_name", "temp_key", "data", ttl=86400)  # With 24h expiry
    kb.read("key")                            # Read learning
    kb.get_all_models()                       # List all models
    kb.get_model_context("model_name")        # Get model context
    kb.search("pattern")                      # Search learnings
"""

import redis
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any

# Connection pool - reuse connections across instances
_redis_pool = None

def _get_redis_pool():
    """Get or create Redis connection pool"""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = redis.ConnectionPool(
            host='127.0.0.1',
            port=6379,
            db=0,
            decode_responses=True,
            max_connections=10
        )
    return _redis_pool


class KnowledgeBase:
    """Central knowledge base using Redis for all AI models"""
    
    REDIS_HOST = "127.0.0.1"
    REDIS_PORT = 6379
    REDIS_DB = 0
    
    # Key prefixes for organization
    PREFIX_MODELS = "kb:models"           # List of registered models
    PREFIX_MODEL_PREFIX = "kb:model:"     # Per-model data: kb:model:modelname
    PREFIX_LEARNING_PREFIX = "kb:learning:" # Key-value learnings: kb:learning:key
    PREFIX_DOCS = "kb:docs"               # Documentation
    PREFIX_CONTEXT = "kb:context"         # Global context
    
    def __init__(self):
        try:
            self.client = redis.Redis(connection_pool=_get_redis_pool())
            self.client.ping()
            self.available = True
        except redis.ConnectionError:
            print("WARNING: Redis not available - running in offline mode")
            self.client = None
            self.available = False
    
    def _verify_connection(self):
        """Verify Redis is available - returns bool"""
        if not self.client:
            return False
        try:
            self.client.ping()
            self.available = True
            return True
        except:
            self.available = False
            return False
    
    # ============ MODEL MANAGEMENT ============
    
    def register_model(self, name: str, description: str = "", capabilities: List[str] = None) -> bool:
        """Register a new AI model in the knowledge base"""
        if not self.client: return False
        
        try:
            # Add to models list
            self.client.sadd(self.PREFIX_MODELS, name)
            
            # Store model metadata
            capabilities_str = ",".join(capabilities) if capabilities else ""
            model_data = {
                "name": name,
                "description": description,
                "capabilities": capabilities_str,
                "registered_at": datetime.now().isoformat(),
                "last_active": datetime.now().isoformat()
            }
            self.client.hset(f"{self.PREFIX_MODEL_PREFIX}{name}", mapping=model_data)
            return True
        except Exception as e:
            print(f"Error registering model: {e}")
            return False
    
    def get_all_models(self) -> List[str]:
        """Get list of all registered models"""
        if not self.client: return []
        try:
            return list(self.client.smembers(self.PREFIX_MODELS))
        except:
            return []
    
    def get_model_info(self, name: str) -> Optional[Dict]:
        """Get model metadata"""
        if not self.client: return None
        try:
            data = self.client.hgetall(f"{self.PREFIX_MODEL_PREFIX}{name}")
            return data if data else None
        except:
            return None
    
    def update_model_activity(self, name: str) -> bool:
        """Update model's last active timestamp"""
        if not self.client: return False
        try:
            self.client.hset(f"{self.PREFIX_MODEL_PREFIX}{name}", "last_active", datetime.now().isoformat())
            return True
        except:
            return False
    
    # ============ LEARNING STORAGE ============
    
    def write(self, model_name: str, key: str, value: Any, category: str = "general", ttl: int = None) -> bool:
        """
        Write a learning/knowledge item.
        
        Args:
            model_name: Name of the AI model writing this
            key: Unique key for this learning
            value: The learning content (any serializable type)
            category: Category for organization (general, code, config, etc.)
            ttl: Optional TTL in seconds. If None, learning persists until overwritten.
                 Recommended: 86400 (1 day) for temporary, 604800 (1 week) for transient.
        """
        if not self.client: return False
        
        try:
            # Create structured learning entry
            learning = {
                "model": model_name,
                "key": key,
                "value": json.dumps(value),
                "category": category,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }
            if ttl is not None:
                learning["ttl"] = str(ttl)  # Store as string to avoid Redis None issue
            
            # Store in Redis
            full_key = f"{self.PREFIX_LEARNING_PREFIX}{key}"
            self.client.hset(full_key, mapping=learning)
            
            # Set TTL if specified
            if ttl:
                self.client.expire(full_key, ttl)
            
            # Also add to model's personal namespace (with same TTL)
            model_key = f"{self.PREFIX_MODEL_PREFIX}{model_name}:learnings"
            self.client.sadd(model_key, key)
            if ttl:
                self.client.expire(model_key, ttl)
            
            return True
        except Exception as e:
            print(f"Error writing learning: {e}")
            return False
    
    def read(self, key: str) -> Optional[Any]:
        """Read a learning by key"""
        if not self.client: return None
        
        try:
            full_key = f"{self.PREFIX_LEARNING_PREFIX}{key}"
            data = self.client.hgetall(full_key)
            if data and "value" in data:
                return json.loads(data["value"])
            return None
        except:
            return None
    
    def get_learning_metadata(self, key: str) -> Optional[Dict]:
        """Get metadata about a learning (who wrote it, when, etc.)"""
        if not self.client: return None
        
        try:
            full_key = f"{self.PREFIX_LEARNING_PREFIX}{key}"
            data = self.client.hgetall(full_key)
            data.pop("value", None)  # Remove the actual value
            return data if data else None
        except:
            return None
    
    def search(self, pattern: str, category: str = None) -> List[Dict]:
        """
        Search learnings by key pattern using pipeline for efficiency.
        OPTIMIZED: Uses Redis pipeline instead of N individual calls.
        """
        if not self.client: return []
        
        try:
            # First, find matching keys
            matching_keys = []
            for key in self.client.scan_iter(f"{self.PREFIX_LEARNING_PREFIX}*"):
                key_name = key.replace(self.PREFIX_LEARNING_PREFIX, "")
                if pattern.lower() in key_name.lower():
                    matching_keys.append(key)
            
            if not matching_keys:
                return []
            
            # Use pipeline to fetch all matching entries in one round trip
            pipe = self.client.pipeline()
            for key in matching_keys:
                pipe.hgetall(key)
            results_raw = pipe.execute()
            
            # Build results
            results = []
            for i, key in enumerate(matching_keys):
                key_name = key.replace(self.PREFIX_LEARNING_PREFIX, "")
                data = results_raw[i]
                
                if category:
                    if data.get("category") == category:
                        results.append({"key": key_name, **data})
                else:
                    results.append({"key": key_name, **data})
            
            return results
        except:
            return []
    
    # ============ DOCUMENTATION ============
    
    def write_doc(self, doc_name: str, content: str, model_name: str = "system") -> bool:
        """Write documentation"""
        if not self.client: return False
        
        try:
            doc_data = {
                "name": doc_name,
                "content": content,
                "author": model_name,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            self.client.hset(f"{self.PREFIX_DOCS}:{doc_name}", mapping=doc_data)
            return True
        except:
            return False
    
    def read_doc(self, doc_name: str) -> Optional[str]:
        """Read documentation"""
        if not self.client: return None
        
        try:
            data = self.client.hgetall(f"{self.PREFIX_DOCS}:{doc_name}")
            return data.get("content") if data else None
        except:
            return None
    
    def get_all_docs(self) -> List[str]:
        """List all documentation"""
        if not self.client: return []
        
        try:
            return [k.replace(f"{self.PREFIX_DOCS}:", "") 
                    for k in self.client.scan_iter(f"{self.PREFIX_DOCS}:*")]
        except:
            return []
    
    # ============ CONTEXT SHARING ============
    
    def set_context(self, key: str, value: Any) -> bool:
        """Set shared context that all models can read"""
        if not self.client: return False
        
        try:
            self.client.hset(self.PREFIX_CONTEXT, key, json.dumps(value))
            return True
        except:
            return False
    
    def get_context(self, key: str) -> Optional[Any]:
        """Get shared context"""
        if not self.client: return None
        
        try:
            data = self.client.hget(self.PREFIX_CONTEXT, key)
            return json.loads(data) if data else None
        except:
            return None
    
    def get_all_context(self) -> Dict:
        """Get all shared context"""
        if not self.client: return {}
        
        try:
            data = self.client.hgetall(self.PREFIX_CONTEXT)
            return {k: json.loads(v) for k, v in data.items()}
        except:
            return {}
    
    # ============ MODEL CONTEXT ============
    
    def get_model_context(self, model_name: str) -> Dict:
        """Get complete context for a model (learnings + info)"""
        if not self.client: return {}
        
        try:
            # Get model info
            info = self.client.hgetall(f"{self.PREFIX_MODEL_PREFIX}{model_name}")
            
            # Get model's learnings
            model_key = f"{self.PREFIX_MODEL_PREFIX}{model_name}:learnings"
            learning_keys = list(self.client.smembers(model_key))
            
            learnings = {}
            for lk in learning_keys:
                data = self.client.hgetall(f"{self.PREFIX_LEARNING_PREFIX}{lk}")
                if data:
                    learnings[lk] = data
            
            return {
                "info": info,
                "learnings": learnings
            }
        except:
            return {}
    
    # ============ SYSTEM STATUS ============
    
    def get_status(self) -> Dict:
        """Get knowledge base status"""
        if not self.client:
            return {"status": "offline", "models": 0, "learnings": 0}
        
        try:
            return {
                "status": "online",
                "models": len(self.get_all_models()),
                "learnings": sum(1 for _ in self.client.scan_iter(f"{self.PREFIX_LEARNING_PREFIX}*")),
                "docs": len(self.get_all_docs()),
                "redis_version": self.client.info().get("redis_version", "unknown")
            }
        except:
            return {"status": "error"}
    
    def backup(self) -> Dict:
        """Export all data for backup"""
        if not self.client: return {}
        
        try:
            return {
                "models": self.get_all_models(),
                "learnings": {k: self.read(k) for k in [l.replace(self.PREFIX_LEARNING_PREFIX, "") 
                         for l in self.client.scan_iter(f"{self.PREFIX_LEARNING_PREFIX}*")]},
                "docs": {d: self.read_doc(d) for d in self.get_all_docs()},
                "context": self.get_all_context(),
                "exported_at": datetime.now().isoformat()
            }
        except:
            return {}


# ============ INITIALIZATION ============

def initialize_knowledge_base():
    """Initialize the knowledge base with system documentation"""
    kb = KB()
    
    # Register this system
    kb.register_model(
        "knowledge_base",
        "Central knowledge system for all AI models",
        ["read", "write", "search", "context"]
    )
    
    # Write system documentation
    kb.write_doc("README", """
# AI Knowledge Base System

## Purpose
This system enables multiple AI models to share learnings and context
without destroying each other's work.

## How It Works
1. Each model registers itself on startup
2. Models write learnings with unique keys (model_name:key format)
3. All models can read from shared context
4. Documentation is centrally stored

## Key Principles
- NEVER overwrite another model's learning without explicit permission
- Always prefix your keys with your model name
- Document changes in the knowledge base
- Read existing context before writing

## Usage
```python
from knowledge_base import KB
kb = KB()
kb.write("my_model", "some_key", "some_value")
value = kb.read("some_key")
```

## Available Models
Use kb.get_all_models() to see who's in the system.
""", "system")
    
    # Write setup documentation
    kb.write_doc("setup_status", """
# Setup Status & Journey

## Current Services
- Dashboard: http://127.0.0.1:8501 (Streamlit)
- Ollama: http://127.0.0.1:11434 (WSL2 with ROCm)
- Redis: 127.0.0.1:6379
- Open WebUI: http://127.0.0.1:3000

## Hardware
- GPU: AMD RX 9070 XT
- ROCm: 7.2.1

## Known Issues
- Ollama GPU discovery times out but runs on CPU
- WSL2 IP changes on restart (requires portproxy update)

## Files
- Dashboard: E:\\AI-Setup\\dockerized-ai\\services\\dashboard\\app.py
- Launcher: E:\\AI-Setup\\launch_dashboard.py
- Diagnostic: E:\\AI-Setup\\system_diagnostic.py
""", "system")
    
    return kb

# Alias for convenience
KB = KnowledgeBase

if __name__ == "__main__":
    # Initialize and show status
    kb = initialize_knowledge_base()
    print("Knowledge Base Status:", kb.get_status())
    print("Models:", kb.get_all_models())
    print("Docs:", kb.get_all_docs())