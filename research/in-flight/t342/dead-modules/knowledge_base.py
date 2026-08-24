"""
AI Knowledge Base & Documentation System
=========================================
All AI models should use this system to store and retrieve learnings.
This ensures cohesive, non-destructive collaboration.

Features:
- Connection pooling for Redis
- Pipeline support for batch operations
- TTL support for expiring learnings
- DUAL STORAGE: Redis + Vector Store for fast similarity search
- Automatic sync between formats

Usage:
    from knowledge_base import KB
    
    kb = KB()
    kb.write("model_name", "key", "value")  # Write learning (stores in BOTH Redis and Vector)
    kb.write("model_name", "temp_key", "data", ttl=86400)  # With 24h expiry
    kb.read("key")                            # Read learning
    kb.get_all_models()                       # List all models
    kb.get_model_context("model_name")        # Get model context
    kb.search("pattern")                      # Search learnings (uses vector store)
    kb.vector_search("semantic query")        # Vector similarity search
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


def _get_vector_store():
    """Lazy-load vector store to avoid circular imports"""
    global _vector_store
    if _vector_store is None:
        try:
            from vector_store import get_vector_store as _get_vs
            _vector_store = _get_vs()
        except ImportError:
            _vector_store = None
    return _vector_store

_vector_store = None


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
        
        DUAL STORAGE: Stores in BOTH Redis (primary) and Vector Store (for fast search).
        
        Args:
            model_name: Name of the AI model writing this
            key: Unique key for this learning
            value: The learning content (any serializable type)
            category: Category for organization (general, code, config, etc.)
            ttl: Optional TTL in seconds. If None, learning persists until overwritten.
                 Recommended: 86400 (1 day) for temporary, 604800 (1 week) for transient.
        """
        redis_success = False
        
        # Store in Redis
        if self.client:
            try:
                learning = {
                    "model": model_name,
                    "key": key,
                    "value": json.dumps(value),
                    "category": category,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                }
                if ttl is not None:
                    learning["ttl"] = str(ttl)
                
                full_key = f"{self.PREFIX_LEARNING_PREFIX}{key}"
                self.client.hset(full_key, mapping=learning)
                
                if ttl:
                    self.client.expire(full_key, ttl)
                
                model_key = f"{self.PREFIX_MODEL_PREFIX}{model_name}:learnings"
                self.client.sadd(model_key, key)
                if ttl:
                    self.client.expire(model_key, ttl)
                
                redis_success = True
                
            except Exception as e:
                print(f"Error writing learning to Redis: {e}")
        
        # Store in Vector Store (for fast similarity search)
        try:
            vs = _get_vector_store()
            if vs:
                vs.embed_learning(model_name, key, value, category)
        except Exception as e:
            print(f"Warning: Could not embed in vector store: {e}")
        
        return redis_success
    
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
    
    def vector_search(self, query: str, top_k: int = 5, model: str = None) -> List[Dict]:
        """
        Vector similarity search across all learnings.
        Uses FAISS for fast nearest-neighbor search.
        
        Args:
            query: Natural language query
            top_k: Number of results to return
            model: Optional model filter
            
        Returns:
            List of learnings with similarity scores
        """
        try:
            vs = _get_vector_store()
            if vs is None:
                print("Vector store not available, falling back to keyword search")
                return self.search(query)
            
            results = vs.search(query, top_k=top_k, model_filter=model)
            
            # Enrich with full data from Redis
            enriched = []
            for r in results:
                full_learning = self.read(r["key"])
                if full_learning is not None:
                    enriched.append({
                        **r,
                        "value": full_learning
                    })
                else:
                    enriched.append(r)
            
            return enriched
            
        except Exception as e:
            print(f"Vector search error: {e}")
            return self.search(query)
    
    def sync_to_vector_store(self) -> int:
        """
        Sync all learnings from Redis to vector store.
        Useful after vector store initialization or recovery.
        
        Returns:
            Number of learnings synced
        """
        try:
            vs = _get_vector_store()
            if vs is None:
                print("Vector store not available")
                return 0
            
            synced = 0
            if self.client:
                for key in self.client.scan_iter(f"{self.PREFIX_LEARNING_PREFIX}*"):
                    key_name = key.replace(self.PREFIX_LEARNING_PREFIX, "")
                    data = self.client.hgetall(key)
                    
                    if data:
                        model = data.get("model", "unknown")
                        value = data.get("value", "")
                        category = data.get("category", "general")
                        
                        try:
                            value_obj = json.loads(value)
                        except:
                            value_obj = value
                        
                        vs.embed_learning(model, key_name, value_obj, category)
                        synced += 1
            
            vs.save()
            print(f"Synced {synced} learnings to vector store")
            return synced
            
        except Exception as e:
            print(f"Sync error: {e}")
            return 0
    
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