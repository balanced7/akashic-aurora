#!/usr/bin/env python3
"""
Simple Session Logger - CLI Interface
==================================
Usage:
    log.py action "Did X" --tags gpu,rocm --data gpu=RX9070
    log.py decision "Chose X because..." --reason "fast","simple"
    log.py error "Something failed" --fix "Fixed by..."
    log.py learning "Learned X"
"""

import sys
import json
import redis
from datetime import datetime
from pathlib import Path
import argparse
import os

import os

# Setup paths - handle WSL mount
BASE_DIR = Path(r"E:\AI-Setup")
LOG_DIR = BASE_DIR / "session_logs"

# Create log directory if it doesn't exist
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "session_all.jsonl"
BACKUP_FILE = LOG_DIR / "backup_session_all.jsonl"
SESSION_ID = f"opencode_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

def get_redis():
    """Get Redis connection"""
    try:
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True, socket_connect_timeout=2)
        r.ping()
        return r
    except:
        return None

def log_to_file(entry, filepath):
    """Log to JSONL file"""
    try:
        with open(filepath, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry) + '\n')
        return True
    except Exception as e:
        print(f"FILE ERROR: {e}", file=sys.stderr)
        return False

def log(type_, content, tags=None, data=None):
    """Main logging function"""
    entry = {
        "type": type_,
        "timestamp": datetime.now().isoformat(),
        "sequence": 1,
        "session": SESSION_ID,
        "unique_id": f"{SESSION_ID}_log",
        "content": content[:200],
        "tags": tags or [type_],
        "data": data or {}
    }
    
    # Count destinations
    destinations = 0
    
    # 1. Redis
    r = get_redis()
    if r:
        try:
            key = f"session:{SESSION_ID}:actions"
            r.rpush(key, json.dumps(entry))
            r.set("learnings:last_updated", datetime.now().isoformat())
            destinations += 1
            print(f"✓ Redis")
        except Exception as e:
            print(f"✗ Redis: {e}", file=sys.stderr)
    
    # 2. Primary file
    if log_to_file(entry, LOG_FILE):
        destinations += 1
        print(f"✓ {LOG_FILE.name}")
    
    # 3. Backup file
    if log_to_file(entry, BACKUP_FILE):
        destinations += 1
        print(f"✓ {BACKUP_FILE.name}")
    
    print(f"Logged: {destinations}/3 destinations")
    return destinations >= 2

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simple session logger")
    parser.add_argument("type", choices=["action", "decision", "error", "learning"], help="Log type")
    parser.add_argument("content", help="Log content")
    parser.add_argument("--tags", help="Comma-separated tags")
    parser.add_argument("--data", help="Data as key=value,key=value")
    
    args = parser.parse_args()
    
    tags = args.tags.split(",") if args.tags else []
    data = dict(x.split("=") for x in args.data.split(",")) if args.data else {}
    
    success = log(args.type, args.content, tags, data)
    sys.exit(0 if success else 1)