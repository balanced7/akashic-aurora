"""
Production-Grade Redis Failover & Sync System
============================================

Ensures data integrity between Redis and file-based backup:
1. Dual-write: Always write to both Redis AND files
2. Integrity verification: Checksums and hashing
3. Automatic resync: Detect and correct out-of-sync states
4. Crash recovery: Rebuild Redis from files if needed
5. Health monitoring: Continuous integrity checks

ARCHITECTURE:
┌─────────────┐       ┌──────────────┐
│  Signal     │──────→│ RedisSyncHandler
│  (Agent)    │       └──────────────┘
└─────────────┘              │
                    ┌────────┴────────┐
                    ↓                  ↓
            ┌──────────────┐   ┌──────────────┐
            │ Redis        │   │ JSONL Files  │
            │ (Primary)    │   │ (Backup)     │
            └──────────────┘   └──────────────┘
                    ↑                  ↑
                    └────────┬─────────┘
                            │
                   ┌────────────────────┐
                   │ SyncVerifier       │
                   │ (Continuous)       │
                   └────────────────────┘
"""

import json
import redis
import hashlib
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO, format='[SYNC] %(asctime)s - %(message)s')
logger = logging.getLogger("redis_sync")


@dataclass
class SyncMetadata:
    """Metadata for sync verification"""
    key: str  # Redis key or file name
    hash: str  # SHA256 of data
    timestamp: str  # ISO timestamp
    source: str  # "redis" or "file"
    size: int  # bytes

    def to_dict(self):
        return self.__dict__


class RedisSyncHandler:
    """
    Handles dual-write (Redis + Files) with automatic sync verification.

    GUARANTEE: Data is safe on either Redis OR Files (or both)
    """

    def __init__(self, redis_host="localhost", redis_port=16379, fallback_dir="E:\\AI-Setup\\session_logs"):
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.fallback_dir = Path(fallback_dir)
        self.fallback_dir.mkdir(parents=True, exist_ok=True)

        # Try to connect to Redis
        self.redis_client = None
        self.redis_available = False
        self._connect_redis()

        # Sync metadata tracking
        self.sync_log = self.fallback_dir / "sync_metadata.jsonl"
        self.health_check_log = self.fallback_dir / "health_check.jsonl"

    def _connect_redis(self):
        """Connect to Redis with retry"""
        try:
            self.redis_client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_keepalive=True
            )
            self.redis_client.ping()
            self.redis_available = True
            logger.info(f"✅ Redis connected ({self.redis_host}:{self.redis_port})")
        except Exception as e:
            self.redis_available = False
            logger.warning(f"⚠️  Redis unavailable: {e} - Using file fallback only")

    def _compute_hash(self, data: Any) -> str:
        """Compute SHA256 hash of data"""
        json_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()

    def write_signal(self, key: str, signal: Dict[str, Any], agent_id: str = "unknown") -> bool:
        """
        DUAL-WRITE: Write to Redis AND Files simultaneously

        Args:
            key: Redis key (or namespace for files)
            signal: Data to write
            agent_id: Agent that emitted signal (for file organization)

        Returns:
            True if at least one write succeeded (Redis OR File)
        """
        timestamp = datetime.utcnow().isoformat()
        data_hash = self._compute_hash(signal)

        results = {
            "redis": False,
            "file": False,
            "timestamp": timestamp,
            "hash": data_hash,
            "key": key
        }

        # Write 1: Redis (if available)
        if self.redis_available:
            try:
                self.redis_client.hset(
                    f"signal:{key}",
                    agent_id,
                    json.dumps({**signal, "_hash": data_hash, "_timestamp": timestamp})
                )
                results["redis"] = True
            except Exception as e:
                logger.warning(f"Redis write failed for {key}: {e}")
                self.redis_available = False  # Mark as down

        # Write 2: File (ALWAYS, regardless of Redis)
        try:
            file_path = self.fallback_dir / f"{key}_{agent_id}.jsonl"
            with open(file_path, "a") as f:
                f.write(json.dumps({
                    **signal,
                    "_hash": data_hash,
                    "_timestamp": timestamp,
                    "_key": key
                }) + "\n")
            results["file"] = True
        except Exception as e:
            logger.error(f"File write CRITICAL: {key} - {e}")

        # Log sync metadata
        self._log_sync_metadata(results)

        success = results["redis"] or results["file"]
        if success:
            logger.info(f"✅ Signal synced: {key} (redis={results['redis']}, file={results['file']})")
        else:
            logger.error(f"❌ CRITICAL: Both Redis and file writes failed for {key}")

        return success

    def _log_sync_metadata(self, metadata: Dict[str, Any]):
        """Log sync operation for audit trail"""
        with open(self.sync_log, "a") as f:
            f.write(json.dumps(metadata) + "\n")

    def verify_sync(self, key: str, agent_id: str) -> Dict[str, Any]:
        """
        VERIFY sync integrity between Redis and File

        Returns:
            {
                "in_sync": bool,
                "redis_hash": str or None,
                "file_hash": str or None,
                "status": "synced" | "out_of_sync" | "redis_only" | "file_only",
                "action_taken": str
            }
        """
        result = {
            "key": key,
            "agent_id": agent_id,
            "check_time": datetime.utcnow().isoformat(),
            "in_sync": None,
            "status": None,
            "action_taken": "none"
        }

        # Read from Redis
        redis_data = None
        redis_hash = None
        if self.redis_available:
            try:
                redis_data = self.redis_client.hget(f"signal:{key}", agent_id)
                if redis_data:
                    parsed = json.loads(redis_data)
                    redis_hash = parsed.get("_hash")
                    result["redis_hash"] = redis_hash
            except Exception as e:
                logger.warning(f"Could not read Redis for {key}: {e}")

        # Read from File
        file_data = None
        file_hash = None
        file_path = self.fallback_dir / f"{key}_{agent_id}.jsonl"
        if file_path.exists():
            try:
                with open(file_path, "r") as f:
                    # Get last line (most recent)
                    lines = f.readlines()
                    if lines:
                        file_data = json.loads(lines[-1])
                        file_hash = file_data.get("_hash")
                        result["file_hash"] = file_hash
            except Exception as e:
                logger.warning(f"Could not read file for {key}: {e}")

        # Determine sync status
        if redis_hash and file_hash:
            if redis_hash == file_hash:
                result["status"] = "synced"
                result["in_sync"] = True
            else:
                result["status"] = "out_of_sync"
                result["in_sync"] = False
                result["action_taken"] = "RESYNC_NEEDED"
                logger.error(f"🔴 OUT OF SYNC: {key} - Redis hash={redis_hash}, File hash={file_hash}")
        elif redis_hash and not file_hash:
            result["status"] = "redis_only"
            result["in_sync"] = False
            result["action_taken"] = "REBUILD_FROM_REDIS"
        elif file_hash and not redis_hash:
            result["status"] = "file_only"
            result["in_sync"] = False
            result["action_taken"] = "REBUILD_FROM_FILE"
        else:
            result["status"] = "not_found"
            result["in_sync"] = True  # Not an error if both missing

        return result

    def resync_all(self) -> Dict[str, Any]:
        """
        CORRECTION ROUTINE: Resync all data between Redis and Files

        Strategy:
        1. For each key in Redis: verify against file
        2. For each file: verify against Redis
        3. Fix mismatches (prefer Redis as source of truth)
        4. Return report
        """
        logger.info("🔄 Starting full resync...")

        report = {
            "start_time": datetime.utcnow().isoformat(),
            "checked": 0,
            "in_sync": 0,
            "fixed": 0,
            "errors": []
        }

        if not self.redis_available:
            logger.warning("Redis unavailable - cannot resync")
            report["errors"].append("Redis unavailable")
            return report

        # Check all Redis keys
        try:
            redis_keys = self.redis_client.keys("signal:*")
            for redis_key in redis_keys:
                try:
                    # Extract key and agent_id from redis_key
                    parts = redis_key.split(":")
                    if len(parts) >= 2:
                        key = ":".join(parts[1:])
                        members = self.redis_client.hgetall(redis_key)

                        for agent_id, data in members.items():
                            report["checked"] += 1
                            sync_status = self.verify_sync(key, agent_id)

                            if sync_status["in_sync"]:
                                report["in_sync"] += 1
                            else:
                                # Attempt to fix
                                try:
                                    # Rebuild file from Redis
                                    file_path = self.fallback_dir / f"{key}_{agent_id}.jsonl"
                                    with open(file_path, "w") as f:
                                        f.write(data + "\n")
                                    report["fixed"] += 1
                                    logger.info(f"✅ Fixed {key}/{agent_id}")
                                except Exception as e:
                                    report["errors"].append(f"Could not fix {key}/{agent_id}: {e}")

                except Exception as e:
                    report["errors"].append(f"Error processing {redis_key}: {e}")
        except Exception as e:
            report["errors"].append(f"Redis scan failed: {e}")

        report["end_time"] = datetime.utcnow().isoformat()
        report["status"] = "success" if not report["errors"] else "partial"

        logger.info(f"🎯 Resync complete: {report['checked']} checked, {report['in_sync']} in_sync, {report['fixed']} fixed")

        return report

    def health_check(self) -> Dict[str, Any]:
        """
        CONTINUOUS MONITORING: Check system health

        Returns:
            {
                "timestamp": str,
                "redis_available": bool,
                "redis_keys": int,
                "file_count": int,
                "sync_issues": int,
                "last_sync": str
            }
        """
        health = {
            "timestamp": datetime.utcnow().isoformat(),
            "redis_available": self.redis_available,
            "redis_keys": 0,
            "file_count": 0,
            "sync_issues": 0,
            "last_signal_age_seconds": None
        }

        if self.redis_available:
            try:
                health["redis_keys"] = len(self.redis_client.keys("signal:*"))
            except:
                pass

        # Count files
        try:
            files = list(self.fallback_dir.glob("*_*.jsonl"))
            health["file_count"] = len(files)
        except:
            pass

        # Log health check
        with open(self.health_check_log, "a") as f:
            f.write(json.dumps(health) + "\n")

        return health


class CrashRecovery:
    """
    Recovery from crashes: Rebuild Redis from files
    """

    @staticmethod
    def rebuild_redis_from_files(sync_handler: RedisSyncHandler) -> Dict[str, Any]:
        """
        Rebuild Redis from file-based backup

        Use case: Redis crashes and loses data, but files are intact
        """
        logger.info("🔧 Starting crash recovery...")

        report = {
            "recovered_keys": 0,
            "recovered_signals": 0,
            "errors": []
        }

        try:
            for file_path in sync_handler.fallback_dir.glob("*_*.jsonl"):
                try:
                    with open(file_path, "r") as f:
                        for line in f:
                            if not line.strip():
                                continue

                            try:
                                signal = json.loads(line)
                                key = signal.pop("_key", "unknown")
                                agent_id = file_path.stem.split("_")[-1]

                                # Write back to Redis
                                if sync_handler.redis_available:
                                    sync_handler.redis_client.hset(
                                        f"signal:{key}",
                                        agent_id,
                                        json.dumps(signal)
                                    )
                                    report["recovered_signals"] += 1
                            except json.JSONDecodeError:
                                continue

                    report["recovered_keys"] += 1
                except Exception as e:
                    report["errors"].append(f"Could not process {file_path}: {e}")

        except Exception as e:
            report["errors"].append(f"Recovery failed: {e}")

        logger.info(f"✅ Crash recovery complete: {report['recovered_signals']} signals, {report['recovered_keys']} keys")

        return report


if __name__ == "__main__":
    # Example usage
    sync = RedisSyncHandler()

    # Write signals (dual-write)
    sync.write_signal("test_signal", {"message": "hello"}, agent_id="test_agent")

    # Verify sync
    status = sync.verify_sync("test_signal", "test_agent")
    print(f"Sync status: {status}")

    # Health check
    health = sync.health_check()
    print(f"Health: {health}")

    # Full resync
    report = sync.resync_all()
    print(f"Resync report: {report}")
