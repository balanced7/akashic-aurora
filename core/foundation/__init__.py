"""
Foundation Layer: Core Primitives and Vocabulary

Semantic Relationship: Foundation provides_base_for all other systems

Includes:
- relationship_types.py: 66 standardized relationship types (Dublin Core, OBO, RDF)
- store.py:  persistence as state-by-key (key/value, hash, list, set, zset, TTL)
- ledger.py: persistence as events-in-sequence (append-and-replay streams)

These are the fundamental building blocks. All other systems reference these.

Persistence comes in two shapes, named for the question each answers (the
classic store+ledger pairing):
- Store  -> "what IS the value of X?"   (state you read back by key)
- Ledger -> "what HAPPENED, in order?"  (events you append and replay)
"""

from .relationship_types import RelationshipType, get_relationship_by_name
from .store import Store, RedisStore, FileStore, HybridStore, create_store
from .ledger import Ledger, RedisLedger, FileLedger, HybridLedger, create_ledger
from .redis_connection import (
    connect_to_redis_with_fail_fast,
    probe_redis_reachable,
)

__all__ = [
    # Vocabulary
    "RelationshipType",
    "get_relationship_by_name",
    # Persistence (Pillar 0): state by key
    "Store",
    "RedisStore",
    "FileStore",
    "HybridStore",
    "create_store",
    # Persistence (Pillar 0): events in sequence
    "Ledger",
    "RedisLedger",
    "FileLedger",
    "HybridLedger",
    "create_ledger",
    # Fail-fast connectivity
    "connect_to_redis_with_fail_fast",
    "probe_redis_reachable",
]
