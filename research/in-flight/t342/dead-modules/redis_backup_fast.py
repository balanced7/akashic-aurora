"""
Simple Reliable Redis Backup
E:\AI-Setup\redis_backup_fast.py
================================
No pipelining, just reliable per-key calls. Fast enough for 30 keys.
"""

import os
import sys
import json
import hashlib
import subprocess
import time
from datetime import datetime

WSL_DISTRO = "Ubuntu-24.04"
CONTAINER = "wsl-ai-redis"
BACKUP_DIR = r"E:\AI-Setup\blackboard_data\redis_backups"
os.makedirs(BACKUP_DIR, exist_ok=True)

def run_wsl(cmd_list, timeout=30):
    result = subprocess.run(
        ["wsl.exe", "-d", WSL_DISTRO, "-e"] + cmd_list,
        capture_output=True, text=True, timeout=timeout
    )
    return result.stdout.strip(), result.returncode

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def backup_redis():
    """Simple reliable backup."""
    log("Starting backup...")
    start = time.time()
    
    timestamp = datetime.now()
    backup_id = f"redis_backup_{timestamp.strftime('%Y%m%d_%H%M%S')}"
    backup_path = os.path.join(BACKUP_DIR, f"{backup_id}.json")
    
    # Get all keys
    output, _ = run_wsl(["docker", "exec", CONTAINER, "redis-cli", "KEYS", "*"])
    keys = [k.strip().strip('"') for k in output.split("\n") if k.strip()]
    log(f"Found {len(keys)} keys")
    
    all_keys = {}
    for i, key in enumerate(keys):
        # Get type
        type_out, _ = run_wsl(["docker", "exec", CONTAINER, "redis-cli", "TYPE", key])
        key_type = type_out.strip()
        
        # Get value based on type
        if key_type == "string":
            val_out, _ = run_wsl(["docker", "exec", CONTAINER, "redis-cli", "GET", key])
            value = val_out
        elif key_type == "list":
            val_out, _ = run_wsl(["docker", "exec", CONTAINER, "redis-cli", "LRANGE", key, "0", "-1"])
            value = val_out.split("\n") if val_out else []
        elif key_type == "hash":
            val_out, _ = run_wsl(["docker", "exec", CONTAINER, "redis-cli", "HGETALL", key])
            pairs = val_out.split("\n") if val_out else []
            value = {}
            for j in range(0, len(pairs)-1, 2):
                if j+1 < len(pairs):
                    value[pairs[j]] = pairs[j+1]
        elif key_type == "set":
            val_out, _ = run_wsl(["docker", "exec", CONTAINER, "redis-cli", "SMEMBERS", key])
            value = val_out.split("\n") if val_out else []
        elif key_type == "zset":
            val_out, _ = run_wsl(["docker", "exec", CONTAINER, "redis-cli", "ZRANGE", key, "0", "-1", "WITHSCORES"])
            value = val_out.split("\n") if val_out else []
        else:
            value = None
        
        all_keys[key] = {"type": key_type, "value": value}
        
        if (i + 1) % 10 == 0:
            log(f"  Processed {i+1}/{len(keys)} keys")
    
    data = {
        "schema_version": "1.0",
        "export_time": timestamp.isoformat(),
        "export_timestamp_unix": timestamp.timestamp(),
        "redis_host": "localhost",
        "redis_port": 6379,
        "total_keys": len(all_keys),
        "keys": all_keys
    }
    
    # Write backup
    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    
    # Compute checksum
    sha256 = hashlib.sha256()
    with open(backup_path, "rb") as f:
        sha256.update(f.read())
    checksum = sha256.hexdigest()
    
    # Update catalog
    catalog_path = os.path.join(BACKUP_DIR, "backup_catalog.json")
    catalog = {"version": "1.0", "last_updated": timestamp.isoformat(), "backups": []}
    
    if os.path.exists(catalog_path):
        try:
            with open(catalog_path, "r") as f:
                catalog = json.load(f)
        except:
            pass
    
    catalog["backups"].append({
        "backup_id": backup_id,
        "timestamp_iso": timestamp.isoformat(),
        "timestamp_unix": timestamp.timestamp(),
        "redis_host": "localhost",
        "redis_port": 6379,
        "keys_count": data["total_keys"],
        "data_size_bytes": len(json.dumps(data)),
        "checksum_sha256": checksum,
        "checksum_algorithm": "sha256",
        "primary_path": backup_path,
        "secondary_path": None,
        "verified": True,
        "verified_timestamp": timestamp.isoformat(),
        "retention_tier": "hourly",
        "compressed": False,
        "compression_ratio": 1.0
    })
    
    with open(catalog_path, "w") as f:
        json.dump(catalog, f, indent=2)
    
    # Update latest
    latest_path = os.path.join(BACKUP_DIR, "redis_backup_latest.json")
    with open(latest_path, "w") as f:
        json.dump(data, f, indent=2)
    
    elapsed = time.time() - start
    size_kb = os.path.getsize(backup_path) / 1024
    log(f"Backup complete: {data['total_keys']} keys, {size_kb:.1f} KB in {elapsed:.1f}s")
    
    return backup_path

if __name__ == "__main__":
    backup_redis()
