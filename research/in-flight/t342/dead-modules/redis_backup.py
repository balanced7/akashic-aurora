"""
Redis Backup System - Routine Export to Local Files
==============================================
Exports Redis data to local files to prevent data loss.

Run as: python redis_backup.py
Or schedule with: Windows Task Scheduler / cron

Backup interval: Every 5 minutes (configurable)
"""

import sys
import os
import json
import time
import redis
from datetime import datetime
from pathlib import Path

# Paths
REDIS_HOST = "localhost"
REDIS_PORT = 6379
BACKUP_DIR = r"E:\AI-Setup\blackboard_data\redis_backups"
os.makedirs(BACKUP_DIR, exist_ok=True)

# Key patterns to backup (empty = all)
INCLUDE_PATTERNS = [
    "kb:*",           # Knowledge base
    "learnings:*",    # Learnings
    "session:*",      # Sessions
    "chat:*",         # Chat history
    "system:*",       # System state
    "errors:*",       # Errors
]

EXCLUDE_PATTERNS = [
    "session:opencode*:actions",  # Skip action logs (too verbose)
]


class RedisBackup:
    """Routine Redis backup to local files"""
    
    def __init__(self):
        self.redis_client = None
        self.connected = False
        self.last_backup_time = None
        self.last_backup_count = 0
        
    def connect(self) -> bool:
        """Connect to Redis"""
        try:
            self.redis_client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                decode_responses=True,
                socket_timeout=5
            )
            self.redis_client.ping()
            self.connected = True
            print(f"[backup] Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
            return True
        except Exception as e:
            print(f"[backup] Failed to connect: {e}")
            self.connected = False
            return False
    
    def scan_keys(self, pattern: str) -> list:
        """Scan keys matching pattern"""
        try:
            keys = []
            cursor = 0
            while True:
                cursor, batch = self.redis_client.scan(cursor, match=pattern, count=100)
                keys.extend(batch)
                if cursor == 0:
                    break
            return keys
        except Exception as e:
            print(f"[backup] Scan error for {pattern}: {e}")
            return []
    
    def get_key_type(self, key: str) -> str:
        """Get Redis key type"""
        try:
            return self.redis_client.type(key)
        except:
            return "unknown"
    
    def export_key(self, key: str) -> dict:
        """Export a single key with its value"""
        key_type = self.get_key_type(key)
        
        try:
            if key_type == "string":
                value = self.redis_client.get(key)
                return {"type": "string", "value": value}
            
            elif key_type == "list":
                value = self.redis_client.lrange(key, 0, -1)
                return {"type": "list", "value": value}
            
            elif key_type == "hash":
                value = self.redis_client.hgetall(key)
                return {"type": "hash", "value": value}
            
            elif key_type == "set":
                value = list(self.redis_client.smembers(key))
                return {"type": "set", "value": value}
            
            elif key_type == "zset":
                value = self.redis_client.zrange(key, 0, -1, withscores=True)
                return {"type": "zset", "value": value}
            
            else:
                return {"type": key_type, "value": None}
                
        except Exception as e:
            return {"type": key_type, "error": str(e), "value": None}
    
    def export_all(self) -> dict:
        """Export all keys matching patterns"""
        if not self.connected:
            if not self.connect():
                return {"error": "Not connected to Redis"}
        
        all_keys = set()
        
        for pattern in INCLUDE_PATTERNS:
            keys = self.scan_keys(pattern)
            all_keys.update(keys)
        
        # Remove excluded
        for pattern in EXCLUDE_PATTERNS:
            excluded = self.scan_keys(pattern)
            all_keys.difference_update(excluded)
        
        print(f"[backup] Exporting {len(all_keys)} keys...")
        
        backup = {
            "export_time": datetime.now().isoformat(),
            "redis_host": REDIS_HOST,
            "redis_port": REDIS_PORT,
            "total_keys": len(all_keys),
            "keys": {}
        }
        
        for key in sorted(all_keys):
            key_clean = key.replace(":", "_")
            backup["keys"][key] = self.export_key(key)
        
        return backup
    
    def save_backup(self, backup: dict) -> str:
        """Save backup to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"redis_backup_{timestamp}.json"
        filepath = os.path.join(BACKUP_DIR, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(backup, f, indent=2, ensure_ascii=False)
        
        print(f"[backup] Saved to {filepath}")
        
        # Also save a "latest" copy
        latest_path = os.path.join(BACKUP_DIR, "redis_backup_latest.json")
        with open(latest_path, 'w', encoding='utf-8') as f:
            json.dump(backup, f, indent=2, ensure_ascii=False)
        
        return filepath
    
    def backup(self) -> str:
        """Do a full backup and save to file"""
        backup = self.export_all()
        
        if "error" in backup:
            print(f"[backup] Backup failed: {backup['error']}")
            return None
        
        filepath = self.save_backup(backup)
        
        self.last_backup_time = datetime.now()
        self.last_backup_count = backup["total_keys"]
        
        return filepath
    
    def get_backup_stats(self) -> dict:
        """Get backup statistics"""
        files = list(Path(BACKUP_DIR).glob("redis_backup_*.json"))
        files = [f for f in files if f.name != "redis_backup_latest.json"]
        
        latest = Path(BACKUP_DIR) / "redis_backup_latest.json"
        
        stats = {
            "backup_dir": BACKUP_DIR,
            "total_backups": len(files),
            "latest_backup_exists": latest.exists(),
            "last_backup_time": self.last_backup_time.isoformat() if self.last_backup_time else None,
            "last_backup_key_count": self.last_backup_count
        }
        
        if latest.exists():
            with open(latest, 'r') as f:
                data = json.load(f)
                stats["latest_backup_time"] = data.get("export_time")
                stats["latest_key_count"] = data.get("total_keys")
        
        return stats


def run_continuous_backup(interval_seconds: int = 300):
    """Run backup continuously"""
    print("=" * 50)
    print("Redis Backup System - Continuous Mode")
    print("=" * 50)
    print(f"Backup interval: {interval_seconds}s")
    print(f"Backup directory: {BACKUP_DIR}")
    print("=" * 50)
    
    backup = RedisBackup()
    
    while True:
        try:
            if backup.connect():
                filepath = backup.backup()
                if filepath:
                    stats = backup.get_backup_stats()
                    print(f"[status] Keys backed up: {stats.get('last_backup_key_count', 0)}")
                
                backup.redis_client.close()
            
        except Exception as e:
            print(f"[backup] Error: {e}")
        
        print(f"[backup] Next backup in {interval_seconds}s...")
        time.sleep(interval_seconds)


def restore_from_backup(backup_file: str) -> bool:
    """Restore Redis from a backup file"""
    print("=" * 50)
    print("Redis Restore")
    print("=" * 50)
    
    if not os.path.exists(backup_file):
        print(f"[error] Backup file not found: {backup_file}")
        return False
    
    with open(backup_file, 'r') as f:
        backup = json.load(f)
    
    print(f"Backup file: {backup_file}")
    print(f"Export time: {backup.get('export_time')}")
    print(f"Total keys: {backup.get('total_keys')}")
    
    confirm = input("This will overwrite Redis data. Continue? (yes/no): ")
    if confirm.lower() != "yes":
        print("Restore cancelled")
        return False
    
    backup_obj = RedisBackup()
    if not backup_obj.connect():
        return False
    
    restored = 0
    skipped = 0
    
    for key, data in backup.get("keys", {}).items():
        try:
            key_type = data.get("type")
            value = data.get("value")
            
            if value is None:
                skipped += 1
                continue
            
            # Delete existing key
            backup_obj.redis_client.delete(key)
            
            if key_type == "string":
                backup_obj.redis_client.set(key, value)
            elif key_type == "list":
                if value:
                    backup_obj.redis_client.rpush(key, *value)
            elif key_type == "hash":
                if value:
                    backup_obj.redis_client.hset(key, mapping=value)
            elif key_type == "set":
                if value:
                    backup_obj.redis_client.sadd(key, *value)
            
            restored += 1
            
        except Exception as e:
            print(f"[error] Failed to restore {key}: {e}")
    
    print(f"[success] Restored {restored} keys, skipped {skipped}")
    backup_obj.redis_client.close()
    return True


def run_once():
    """Run a single backup"""
    print("=" * 50)
    print("Redis Backup - Single Run")
    print("=" * 50)
    
    backup = RedisBackup()
    
    if backup.connect():
        filepath = backup.backup()
        if filepath:
            stats = backup.get_backup_stats()
            print(f"[success] Backed up {stats.get('last_backup_key_count', 0)} keys to:")
            print(f"  {filepath}")
    
    return backup.get_backup_stats()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Redis Backup System")
    parser.add_argument("--once", action="store_true", help="Run single backup and exit")
    parser.add_argument("--interval", type=int, default=300, help="Backup interval in seconds (default: 300)")
    parser.add_argument("--stats", action="store_true", help="Show backup statistics")
    parser.add_argument("--restore", type=str, help="Restore from backup file")
    
    args = parser.parse_args()
    
    if args.restore:
        restore_from_backup(args.restore)
    elif args.stats:
        backup = RedisBackup()
        backup.connect()
        stats = backup.get_backup_stats()
        print(json.dumps(stats, indent=2))
    elif args.once:
        run_once()
    else:
        run_continuous_backup(args.interval)
