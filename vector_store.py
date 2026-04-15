"""
Vector Store - Fast Similarity Search for Learnings
=================================================
Provides vector-based storage and retrieval for learnings and logs.

Features:
- Hash-based embeddings (no external ML models needed)
- FAISS support for fast similarity search (optional)
- Dual storage: vectors + original JSON
- Automatic embedding of all learnings

ARCHITECTURE:
- Learnings stored in BOTH formats:
  1. JSON (human-readable, backward compatible)
  2. Vectors (fast similarity search)
- Logs stored with metadata for semantic search

Usage:
    from vector_store import VectorStore, get_vector_store
    
    vs = get_vector_store()
    vs.embed_learning("model_name", "key", {"data": "value"})
    results = vs.search("search query", top_k=5)
"""

import os
import json
import hashlib
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import numpy as np

# Paths
VECTOR_STORE_DIR = r"E:\AI-Setup\blackboard_data\vector_store"
VECTOR_INDEX_FILE = os.path.join(VECTOR_STORE_DIR, "index.faiss")
VECTOR_META_FILE = os.path.join(VECTOR_STORE_DIR, "metadata.json")
EMBEDDINGS_CACHE = os.path.join(VECTOR_STORE_DIR, "embeddings")

# Embedding dimensions
EMBEDDING_DIM = 128  # Hash-based embedding dimension

# Ensure directory exists
os.makedirs(VECTOR_STORE_DIR, exist_ok=True)


def _hash_embedding(text: str, dim: int = EMBEDDING_DIM) -> np.ndarray:
    """
    Create a deterministic hash-based embedding from text.
    Uses multiple hash functions to create a pseudo-embedding.
    This is fast and doesn't require external ML models.
    """
    vector = np.zeros(dim, dtype=np.float32)
    
    # Use multiple hash functions for different dimensions
    for i in range(dim):
        # Create different hash for each dimension
        seed = f"{text}:{i}".encode()
        h = hashlib.sha256(seed).hexdigest()
        # Convert hex to float and normalize
        vector[i] = float(int(h[:8], 16)) / (2**32 - 1)
    
    # L2 normalize for cosine similarity
    norm = np.linalg.norm(vector)
    if norm > 0:
        vector = vector / norm
    
    return vector


def _text_to_embedding(text: str) -> np.ndarray:
    """
    Convert text to embedding using hash-based method.
    """
    return _hash_embedding(text.lower().strip(), EMBEDDING_DIM)


@dataclass
class VectorEntry:
    """A vector entry with metadata"""
    id: str
    key: str
    model: str
    text: str  # Combined text for embedding
    metadata: Dict[str, Any]
    created_at: str
    vector: np.ndarray = field(default_factory=lambda: np.zeros(EMBEDDING_DIM, dtype=np.float32))
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "key": self.key,
            "model": self.model,
            "text": self.text,
            "metadata": self.metadata,
            "created_at": self.created_at
        }


class VectorStore:
    """
    Vector store for fast similarity search of learnings and logs.
    
    Maintains:
    - FAISS index for fast nearest-neighbor search
    - Metadata store for full record retrieval
    - Dual storage format (vectors + JSON for backup)
    """
    
    _instance: Optional['VectorStore'] = None
    
    def __init__(self):
        self.entries: Dict[str, VectorEntry] = {}
        self.faiss_index = None
        self._id_to_key: Dict[int, str] = {}  # FAISS ID -> entry key
        self._next_id = 0
        self._load_index()
    
    @classmethod
    def get_instance(cls) -> 'VectorStore':
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def _load_index(self):
        """Load existing FAISS index if available"""
        try:
            import faiss
            if os.path.exists(VECTOR_INDEX_FILE):
                self.faiss_index = faiss.read_index(VECTOR_INDEX_FILE)
                
                # Load metadata
                if os.path.exists(VECTOR_META_FILE):
                    with open(VECTOR_META_FILE, 'r') as f:
                        meta = json.load(f)
                        self._next_id = meta.get("next_id", 0)
                        
                        # Rebuild id_to_key mapping
                        entries_data = meta.get("entries", {})
                        for idx, entry_key in enumerate(entries_data.keys()):
                            self._id_to_key[idx] = entry_key
                
                print(f"[vector_store] Loaded index with {len(self._id_to_key)} entries")
            else:
                self._create_index()
        except ImportError:
            print("[vector_store] FAISS not available, using fallback search")
            self.faiss_index = None
        except Exception as e:
            print(f"[vector_store] Error loading index: {e}")
            self._create_index()
    
    def _create_index(self):
        """Create new FAISS index"""
        try:
            import faiss
            # Use Inner Product (cosine similarity with normalized vectors)
            self.faiss_index = faiss.IndexIDMap(faiss.IndexFlatIP(EMBEDDING_DIM))
            print("[vector_store] Created new FAISS index")
        except ImportError:
            print("[vector_store] FAISS not installed - similarity search will use fallback")
    
    def _save_index(self):
        """Save FAISS index and metadata"""
        if self.faiss_index is None:
            return
        
        try:
            import faiss
            faiss.write_index(self.faiss_index, VECTOR_INDEX_FILE)
            
            # Save metadata
            entries_data = {k: v.to_dict() for k, v in self.entries.items()}
            meta = {
                "next_id": self._next_id,
                "entries": entries_data,
                "saved_at": datetime.now().isoformat()
            }
            with open(VECTOR_META_FILE, 'w') as f:
                json.dump(meta, f, indent=2)
                
        except Exception as e:
            print(f"[vector_store] Error saving index: {e}")
    
    def _generate_id(self) -> str:
        """Generate unique ID for entry"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique = hashlib.md5(str(time.time()).encode()).hexdigest()[:6]
        return f"vec_{timestamp}_{unique}"
    
    def add_entry(self, key: str, model: str, text: str, metadata: Dict[str, Any] = None) -> str:
        """
        Add a learning/log entry to the vector store.
        
        Args:
            key: Unique key for this learning
            model: Model name (for namespace)
            text: Text content to embed
            metadata: Additional metadata
            
        Returns:
            Entry ID
        """
        entry_id = self._generate_id()
        
        # Create embedding
        vector = _text_to_embedding(text)
        
        # Create entry
        entry = VectorEntry(
            id=entry_id,
            key=key,
            model=model,
            text=text,
            metadata=metadata or {},
            created_at=datetime.now().isoformat(),
            vector=vector
        )
        
        # Store in memory
        self.entries[entry_id] = entry
        
        # Add to FAISS index
        if self.faiss_index is not None:
            try:
                import faiss
                self.faiss_index.add_with_ids(
                    np.array([vector], dtype=np.float32),
                    np.array([self._next_id], dtype=np.int64)
                )
                self._id_to_key[self._next_id] = entry_id
                self._next_id += 1
            except Exception as e:
                print(f"[vector_store] Error adding to FAISS: {e}")
        
        # Save periodically
        if len(self.entries) % 10 == 0:
            self._save_index()
        
        return entry_id
    
    def embed_learning(self, model: str, key: str, value: Any, category: str = "general") -> str:
        """
        Embed a learning from the knowledge base.
        
        Args:
            model: Model name
            key: Learning key
            value: Learning value (will be JSON stringified)
            category: Category for organization
            
        Returns:
            Entry ID
        """
        # Combine key, model, and value for rich text
        text = f"{model}:{key}:{json.dumps(value)}"
        
        metadata = {
            "model": model,
            "key": key,
            "category": category,
            "type": "learning"
        }
        
        return self.add_entry(key=f"{model}:{key}", model=model, text=text, metadata=metadata)
    
    def embed_log(self, action: str, description: str, data: Dict = None) -> str:
        """
        Embed a log entry.
        
        Args:
            action: Action type
            description: Description
            data: Additional data
            
        Returns:
            Entry ID
        """
        text = f"{action}:{description}:{json.dumps(data or {})}"
        
        metadata = {
            "type": "log",
            "action": action,
            "data": data or {}
        }
        
        return self.add_entry(
            key=f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            model="session_logger",
            text=text,
            metadata=metadata
        )
    
    def search(self, query: str, top_k: int = 5, model_filter: str = None) -> List[Dict]:
        """
        Search for similar entries.
        
        Args:
            query: Search query
            top_k: Number of results
            model_filter: Optional model to filter by
            
        Returns:
            List of matching entries with scores
        """
        query_vector = _text_to_embedding(query)
        
        results = []
        
        if self.faiss_index is not None and len(self._id_to_key) > 0:
            try:
                import faiss
                # Search FAISS
                D, I = self.faiss_index.search(
                    np.array([query_vector], dtype=np.float32),
                    min(top_k * 2, len(self._id_to_key))  # Over-fetch for filtering
                )
                
                for i, (dist, idx) in enumerate(zip(D[0], I[0])):
                    if idx < 0:
                        continue
                    
                    entry_key = self._id_to_key.get(int(idx))
                    if not entry_key:
                        continue
                    
                    entry = self.entries.get(entry_key)
                    if not entry:
                        continue
                    
                    # Apply model filter
                    if model_filter and entry.model != model_filter:
                        continue
                    
                    results.append({
                        "id": entry.id,
                        "key": entry.key,
                        "model": entry.model,
                        "text": entry.text,
                        "metadata": entry.metadata,
                        "created_at": entry.created_at,
                        "score": float(dist),  # Cosine similarity
                        "rank": len(results) + 1
                    })
                    
                    if len(results) >= top_k:
                        break
                        
            except Exception as e:
                print(f"[vector_store] FAISS search error: {e}")
        
        # Fallback: simple text search
        if len(results) == 0:
            results = self._fallback_search(query, top_k, model_filter)
        
        return results
    
    def _fallback_search(self, query: str, top_k: int, model_filter: str = None) -> List[Dict]:
        """Fallback text-based search when FAISS unavailable"""
        query_lower = query.lower()
        scores = []
        
        for entry_id, entry in self.entries.items():
            if model_filter and entry.model != model_filter:
                continue
            
            # Simple term overlap scoring
            text_lower = entry.text.lower()
            score = sum(1 for word in query_lower.split() if word in text_lower)
            
            if score > 0:
                scores.append((score, entry))
        
        scores.sort(key=lambda x: x[0], reverse=True)
        
        results = []
        for score, entry in scores[:top_k]:
            results.append({
                "id": entry.id,
                "key": entry.key,
                "model": entry.model,
                "text": entry.text,
                "metadata": entry.metadata,
                "created_at": entry.created_at,
                "score": score / max(len(query.split()), 1),
                "rank": len(results) + 1
            })
        
        return results
    
    def get_by_key(self, key: str, model: str = None) -> Optional[Dict]:
        """Get entry by key"""
        for entry in self.entries.values():
            if entry.key == key:
                if model is None or entry.model == model:
                    result = entry.to_dict()
                    result["score"] = 1.0
                    return result
        return None
    
    def get_recent(self, limit: int = 10, model_filter: str = None) -> List[Dict]:
        """Get recent entries"""
        entries = list(self.entries.values())
        
        if model_filter:
            entries = [e for e in entries if e.model == model_filter]
        
        # Sort by created_at descending
        entries.sort(key=lambda e: e.created_at, reverse=True)
        
        return [
            {
                **e.to_dict(),
                "score": 1.0,
                "rank": i + 1
            }
            for i, e in enumerate(entries[:limit])
        ]
    
    def get_stats(self) -> Dict:
        """Get vector store statistics"""
        return {
            "total_entries": len(self.entries),
            "faiss_available": self.faiss_index is not None,
            "embedding_dim": EMBEDDING_DIM,
            "models": list(set(e.model for e in self.entries.values())),
            "categories": list(set(e.metadata.get("category", "unknown") for e in self.entries.values()))
        }
    
    def sync_from_knowledge_base(self, kb):
        """
        Sync all learnings from knowledge base to vector store.
        Run this to rebuild the vector index from Redis.
        """
        print("[vector_store] Syncing from knowledge base...")
        
        try:
            # Get all learnings from KB
            from knowledge_base import KB
            kb_instance = kb or KB()
            
            # Get all models
            models = kb_instance.get_all_models()
            
            synced = 0
            for model in models:
                # Get model context (includes learnings)
                ctx = kb_instance.get_model_context(model)
                learnings = ctx.get("learnings", {})
                
                for key, data in learnings.items():
                    # Extract value
                    if isinstance(data, dict):
                        value = data.get("value", str(data))
                    else:
                        value = str(data)
                    
                    # Embed
                    self.embed_learning(model, key, value, data.get("category", "general"))
                    synced += 1
            
            self._save_index()
            print(f"[vector_store] Synced {synced} learnings")
            
        except Exception as e:
            print(f"[vector_store] Sync error: {e}")
        
        return synced
    
    def save(self):
        """Explicitly save the index"""
        self._save_index()


def get_vector_store() -> VectorStore:
    """Get VectorStore singleton instance"""
    return VectorStore.get_instance()


# Embedding utilities for text
def embed_text(text: str) -> np.ndarray:
    """Get embedding vector for text"""
    return _text_to_embedding(text)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Calculate cosine similarity between two vectors"""
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))


if __name__ == "__main__":
    # Test vector store
    vs = VectorStore()
    
    # Add some test entries
    vs.embed_learning("test_model", "hello_key", {"message": "Hello world"}, "greeting")
    vs.embed_learning("test_model", "goodbye_key", {"message": "Goodbye world"}, "farewell")
    vs.embed_learning("vision_model", "ocr_key", {"accuracy": 0.95}, "ml")
    
    # Search
    results = vs.search("greeting hello", top_k=3)
    print("\nSearch results for 'greeting hello':")
    for r in results:
        print(f"  [{r['rank']}] {r['key']} (score={r['score']:.3f})")
        print(f"      {r['text'][:60]}...")
    
    # Stats
    print(f"\nVector store stats: {vs.get_stats()}")
