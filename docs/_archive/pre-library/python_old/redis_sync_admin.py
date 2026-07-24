"""
Redis Sync Admin: Tools for verification, diagnostics, and manual control.

Provides:
- Sync status verification
- Health monitoring dashboard
- Manual resync triggers
- Data migration tools
- Historical analysis
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
from redis_sync_coordinator import RedisSyncCoordinator

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class RedisSyncAdmin:
    """Administrative tools for Redis sync system"""

    def __init__(self, fallback_dir: str = "E:\\AI-Setup\\session_logs"):
        self.fallback_dir = Path(fallback_dir)
        self.coordinator = RedisSyncCoordinator("admin", fallback_dir)

    # ===== VERIFICATION COMMANDS =====

    def verify_sync_status(self) -> None:
        """Verify sync status between Redis and files"""
        print("\n" + "=" * 70)
        print("SYNC VERIFICATION REPORT")
        print("=" * 70)

        report = self.coordinator.verify_all_synced()

        print(f"\nTimestamp: {report['timestamp']}")
        print(f"Total Checked: {report['total_checked']}")
        print(f"Synced:        {report['synced']}")
        print(f"Out of Sync:   {report['out_of_sync']}")
        print(f"Redis Only:    {report['redis_only']}")
        print(f"File Only:     {report['file_only']}")
        print(f"\nHealth: {report['health'].upper()}")

        if report["errors"]:
            print(f"\nErrors:")
            for err in report["errors"]:
                print(f"  - {err}")

        if report["out_of_sync"] > 0:
            print("\n[!] Out-of-sync items detected. Run 'resync' to correct.")
        elif report["health"] == "green":
            print("\n[OK] All systems in sync!")

    def health_check(self) -> None:
        """Display health check"""
        print("\n" + "=" * 70)
        print("HEALTH CHECK")
        print("=" * 70)

        health = self.coordinator.health_check()

        print(f"\nTimestamp: {health['timestamp']}")
        print(f"Instance ID: {health['instance_id']}")
        print(f"Redis Available: {health['redis_available']}")
        print(f"Signals in File: {health['signals_in_file']}")
        print(f"Learnings in File: {health['learnings_in_file']}")
        print(f"Redis Keys: {health['redis_keys']}")

        sync_status = health.get('sync_status', {})
        if sync_status:
            print(f"\nSync Status:")
            print(f"  Health: {sync_status.get('health', 'unknown')}")
            print(f"  Synced: {sync_status.get('synced', 0)}/{sync_status.get('total_checked', 0)}")

    def list_learnings(self, limit: int = 20) -> None:
        """List recent learnings from file"""
        print("\n" + "=" * 70)
        print(f"RECENT LEARNINGS (last {limit})")
        print("=" * 70)

        learning_file = self.fallback_dir / "learnings.jsonl"
        if not learning_file.exists():
            print("No learnings found.")
            return

        learnings = []
        try:
            with open(learning_file, "r") as f:
                for line in f:
                    if line.strip():
                        try:
                            learnings.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass
        except Exception as e:
            print(f"Error reading learnings: {e}")
            return

        learnings = learnings[-limit:]  # Last N

        for learning in learnings:
            exp_name = learning.get("experiment_name", "unknown")
            success = learning.get("success", "unknown")
            timestamp = learning.get("timestamp", "unknown")[:10]

            print(f"\n[{timestamp}] {exp_name}")
            print(f"  Success: {success}")
            print(f"  What Tried: {learning.get('what_tried', '')[:60]}...")
            if learning.get("recommendation"):
                print(f"  Recommendation: {learning.get('recommendation')[:60]}...")

    def list_signals(self, limit: int = 20) -> None:
        """List recent signals from file"""
        print("\n" + "=" * 70)
        print(f"RECENT SIGNALS (last {limit})")
        print("=" * 70)

        # Find agent signal logs
        signal_files = list(self.fallback_dir.glob("signals_*.jsonl"))
        if not signal_files:
            print("No signals found.")
            return

        all_signals = []
        for signal_file in signal_files:
            try:
                with open(signal_file, "r") as f:
                    for line in f:
                        if line.strip():
                            try:
                                all_signals.append(json.loads(line))
                            except json.JSONDecodeError:
                                pass
            except Exception as e:
                print(f"Error reading {signal_file}: {e}")

        # Sort by timestamp and take last N
        all_signals.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        all_signals = all_signals[:limit]

        for signal in all_signals:
            sig_type = signal.get("signal_type", "unknown")
            agent = signal.get("agent_id", "unknown")
            timestamp = signal.get("timestamp", "unknown")[:19]

            print(f"\n[{timestamp}] {sig_type:12} | Agent: {agent}")
            if sig_type == "DECISION":
                print(f"  Decision: {signal.get('decision_name', '')}")
            elif sig_type == "LEARNING":
                print(f"  Experiment: {signal.get('experiment_name', '')}")
            elif sig_type == "BLOCKER":
                print(f"  Blocker: {signal.get('blocker_name', '')}")

    def show_sync_metadata(self, limit: int = 50) -> None:
        """Show recent sync metadata"""
        print("\n" + "=" * 70)
        print(f"SYNC METADATA (last {limit} operations)")
        print("=" * 70)

        metadata_file = self.fallback_dir / "sync_metadata.jsonl"
        if not metadata_file.exists():
            print("No sync metadata found.")
            return

        metadata_entries = []
        try:
            with open(metadata_file, "r") as f:
                for line in f:
                    if line.strip():
                        try:
                            metadata_entries.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass
        except Exception as e:
            print(f"Error reading metadata: {e}")
            return

        metadata_entries = metadata_entries[-limit:]  # Last N

        redis_success = 0
        redis_fail = 0
        file_success = 0
        file_fail = 0

        for entry in metadata_entries:
            if entry.get("redis"):
                redis_success += 1
            elif "redis" in entry:
                redis_fail += 1

            if entry.get("file"):
                file_success += 1
            elif "file" in entry:
                file_fail += 1

        print(f"\nRedis Writes:  {redis_success} success, {redis_fail} failed")
        print(f"File Writes:   {file_success} success, {file_fail} failed")
        print(f"Overall:       {redis_success + file_success} total successful writes")

    # ===== CONTROL COMMANDS =====

    def resync(self, dry_run: bool = False) -> None:
        """Trigger resync routine"""
        print("\n" + "=" * 70)
        print("RESYNC ROUTINE")
        print("=" * 70)

        if dry_run:
            print("[DRY RUN MODE - No changes will be made]")
            report = self.coordinator.verify_all_synced()
            print(f"\nWould fix: {report['out_of_sync']} out-of-sync items")
        else:
            print("\nStarting resync...")
            report = self.coordinator.resync_all()
            print(f"\nResync Complete:")
            print(f"  Checked: {report['checked']}")
            print(f"  Fixed:   {report['fixed']}")
            print(f"  Status:  {report['status']}")
            if report["errors"]:
                print(f"  Errors:")
                for err in report["errors"]:
                    print(f"    - {err}")

    def export_learnings_to_redis(self) -> None:
        """Migrate historical learnings from file to Redis"""
        print("\n" + "=" * 70)
        print("MIGRATE LEARNINGS TO REDIS")
        print("=" * 70)

        if not REDIS_AVAILABLE:
            print("[!] Redis not available. Cannot migrate.")
            return

        learning_file = self.fallback_dir / "learnings.jsonl"
        if not learning_file.exists():
            print("No learnings file found.")
            return

        try:
            redis_client = redis.Redis(
                host="localhost",
                port=16379,
                decode_responses=True,
                socket_connect_timeout=2
            )
            redis_client.ping()
        except Exception as e:
            print(f"[!] Cannot connect to Redis: {e}")
            return

        migrated = 0
        errors = 0

        print("\nMigrating learnings...")
        try:
            with open(learning_file, "r") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        learning = json.loads(line)
                        exp_name = learning.get("experiment_name", "unknown")

                        # Add to Redis
                        redis_client.hset(
                            f"learn:experiment:{exp_name}",
                            mapping={
                                "what_tried": learning.get("what_tried", ""),
                                "expected": learning.get("expected_outcome", ""),
                                "actual": learning.get("actual_outcome", ""),
                                "success": learning.get("success", ""),
                                "timestamp": learning.get("timestamp", ""),
                                "recommendation": learning.get("recommendation", ""),
                                "anti_pattern": learning.get("anti_pattern", ""),
                                "root_cause": learning.get("root_cause", ""),
                                "confidence": learning.get("confidence", ""),
                                "agent_id": learning.get("agent_id", ""),
                                "_hash": learning.get("_hash", "")
                            }
                        )

                        # Add to lists
                        redis_client.lpush("learn:experiments:all", exp_name)
                        if learning.get("agent_id"):
                            redis_client.lpush(f"learn:agent:{learning['agent_id']}", exp_name)

                        migrated += 1
                    except Exception as e:
                        errors += 1
                        print(f"  Error migrating {exp_name}: {e}")
        except Exception as e:
            print(f"[!] Error reading learnings: {e}")
            return

        print(f"\nMigration Complete:")
        print(f"  Migrated: {migrated}")
        print(f"  Errors:   {errors}")

    def show_stats(self) -> None:
        """Show overall statistics"""
        print("\n" + "=" * 70)
        print("SYSTEM STATISTICS")
        print("=" * 70)

        stats = self.coordinator.get_stats()
        for key, value in stats.items():
            print(f"{key:20}: {value}")

    # ===== COMMAND DISPATCHER =====

    def run_command(self, command: str, *args) -> None:
        """Run a command"""
        commands = {
            "verify": (self.verify_sync_status, "Verify sync status"),
            "health": (self.health_check, "Show health check"),
            "learnings": (lambda: self.list_learnings(int(args[0]) if args else 20), "List recent learnings"),
            "signals": (lambda: self.list_signals(int(args[0]) if args else 20), "List recent signals"),
            "metadata": (lambda: self.show_sync_metadata(int(args[0]) if args else 50), "Show sync metadata"),
            "resync": (lambda: self.resync(dry_run="--dry-run" in args), "Run resync routine"),
            "migrate": (self.export_learnings_to_redis, "Migrate learnings to Redis"),
            "stats": (self.show_stats, "Show statistics"),
            "help": (self.show_help, "Show this help")
        }

        if command not in commands:
            print(f"[!] Unknown command: {command}")
            self.show_help()
            return

        try:
            func, desc = commands[command]
            func()
        except Exception as e:
            print(f"[!] Error running {command}: {e}")

    def show_help(self) -> None:
        """Show help"""
        print("""
Redis Sync Admin - Commands:

  verify              Verify sync status between Redis and files
  health              Show health check
  learnings [N]       List last N learnings (default 20)
  signals [N]         List last N signals (default 20)
  metadata [N]        Show last N sync metadata (default 50)
  resync [--dry-run]  Run resync routine (use --dry-run to preview)
  migrate             Migrate historical learnings to Redis
  stats               Show system statistics
  help                Show this help

Examples:
  python redis_sync_admin.py verify
  python redis_sync_admin.py learnings 10
  python redis_sync_admin.py resync --dry-run
  python redis_sync_admin.py migrate
        """)


if __name__ == "__main__":
    admin = RedisSyncAdmin()

    if len(sys.argv) > 1:
        command = sys.argv[1]
        args = sys.argv[2:] if len(sys.argv) > 2 else ()
        admin.run_command(command, *args)
    else:
        # Show summary on default
        admin.show_help()
        admin.health_check()
        admin.verify_sync_status()
