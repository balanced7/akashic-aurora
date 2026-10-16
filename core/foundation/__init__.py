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

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .ledger import FileLedger, HybridLedger, Ledger, RedisLedger, create_ledger
    from .redis_connection import (
        connect_to_redis_with_fail_fast,
        probe_redis_reachable,
    )
    from .relationship_types import RelationshipType, get_relationship_by_name
    from .store import FileStore, HybridStore, RedisStore, Store, create_store

# The names below load on first use (PEP 562), not when the package is imported. Importing any
# foundation submodule runs this file first, and the ledger and store pull in the Redis endpoint
# resolution and the world (~20 ms): a caller that wants only `core.foundation.timeutil` or
# `filelock` (every CLI verb imports timeutil) should not pay for persistence it never opens.
_LAZY = {
    "FileLedger": "ledger",
    "HybridLedger": "ledger",
    "Ledger": "ledger",
    "RedisLedger": "ledger",
    "create_ledger": "ledger",
    "connect_to_redis_with_fail_fast": "redis_connection",
    "probe_redis_reachable": "redis_connection",
    "RelationshipType": "relationship_types",
    "get_relationship_by_name": "relationship_types",
    "FileStore": "store",
    "HybridStore": "store",
    "RedisStore": "store",
    "Store": "store",
    "create_store": "store",
}


def __getattr__(name: str):
    sub = _LAZY.get(name)
    if sub is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    import importlib

    value = getattr(importlib.import_module(f"{__name__}.{sub}"), name)
    globals()[name] = value  # later lookups skip this function
    return value


def __dir__():
    return sorted({*globals(), *_LAZY})


__all__ = [
    "FileLedger",
    "FileStore",
    "HybridLedger",
    "HybridStore",
    # Persistence (Pillar 0): events in sequence
    "Ledger",
    "RedisLedger",
    "RedisStore",
    # Vocabulary
    "RelationshipType",
    # Persistence (Pillar 0): state by key
    "Store",
    # Fail-fast connectivity
    "connect_to_redis_with_fail_fast",
    "create_ledger",
    "create_store",
    "get_relationship_by_name",
    "probe_redis_reachable",
]
