"""
Sync Reconciler: Detect and heal Redis<->File divergence

Semantic Relationship: SyncReconciler reconciles Redis_with_File

WHY THIS EXISTS (and why it is small)
-------------------------------------
HybridStore already does the runtime dual-write: every write lands in File
(durable) and best-effort in Redis. The one thing it can't do on its own is
recover from a *gap* -- e.g. Redis was down while writes happened, so File is
ahead. When Redis returns, someone has to backfill it.

That healing is the entire remaining job of what used to be the 900-line
RedisSyncCoordinator (which otherwise re-implemented dual-write, indexing, and
heartbeats that now belong to the AgentSignalLedger, LearningStore, and Store). What survives
is this: a thin component that takes a HybridStore and keeps its two backends
consistent. File is always the source of truth.

Usage:
    from core.state.sync_reconciler import create_store_reconciler

    reconciler = create_store_reconciler()      # wraps the default HybridStore
    drift = reconciler.check_divergence()        # what's out of sync?
    report = reconciler.reconcile_divergence()   # backfill Redis from File
"""

import logging
from typing import Any, Dict, Optional

from core.foundation.store import Store, HybridStore, create_store

logger = logging.getLogger("sync_reconciler")


class StoreReconciler:
    """
    Keeps a HybridStore's Redis and File backends consistent.

    Semantic Relationship: StoreReconciler operates_on HybridStore

    Delegates the backend-bridging to HybridStore (which owns both backends);
    this class is the domain-named, swappable handle the state layer exposes.
    """

    def __init__(self, store: Optional[Store] = None):
        self.store = store if store is not None else create_store(prefer_redis=True)

    @property
    def can_reconcile(self) -> bool:
        """Reconciliation only applies to a Hybrid (two-backend) store with Redis up."""
        return isinstance(self.store, HybridStore) and self.store.redis_available

    def check_divergence(self) -> Dict[str, Any]:
        """
        Report what is out of sync between File and Redis (no changes made).

        Semantic Relationship: Divergence derived_from File_vs_Redis
        """
        if not isinstance(self.store, HybridStore):
            return {"applicable": False, "reason": "store is not hybrid"}
        return {"applicable": True, **self.store.check_drift()}

    def reconcile_divergence(self) -> Dict[str, Any]:
        """
        Heal divergence by backfilling Redis from the durable File snapshot.

        Semantic Relationship: Divergence healed_by BackfillFromFile
        """
        if not isinstance(self.store, HybridStore):
            return {"status": "skipped", "reason": "store is not hybrid"}
        report = self.store.reconcile()
        logger.info(f"Reconcile: {report.get('status')} ({report.get('written')})")
        return report


def create_store_reconciler(store: Optional[Store] = None) -> StoreReconciler:
    """
    Create a reconciler over the given (or default Hybrid) Store.

    Semantic Relationship: StoreReconciler derives_from Store
    """
    return StoreReconciler(store)


def sync_state_reconciling_divergence(store: Optional[Store] = None) -> Dict[str, Any]:
    """
    Convenience: reconcile the default (or given) Store in one call.

    Semantic Relationship: State synchronized_by ReconcilingDivergence

    This is the entrypoint the state package has long advertised; it heals any
    Redis<->File gap and returns a report.
    """
    return create_store_reconciler(store).reconcile_divergence()
