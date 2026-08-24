"""
Patch Log System - Git Commit Style Logging
==========================================

Makes logs look like patch notes / git commits:

Format:
    [system:change_type] Title
      Goal: Why this change
      Result: SUCCESS/FAILURE/PARTIAL
      Version: v1.0 → v1.1

Change Types:
    feat    - New feature
    fix     - Bug fix
    refactor - Code refactoring
    docs    - Documentation
    config  - Configuration
    perf    - Performance
    test    - Testing
    chore   - Maintenance

Systems:
    vision      - Florence-2, ComfyUI, OCR
    redis      - Redis, backup, HA
    logging    - Session logging, chronicles
    learning   - Learning systems
    mcp        - MCP server
    architecture - System design
    bootstrap  - Startup, harness
    etc.

Usage:
    from patch_log import feat, fix, refactor, docs, config
    from patch_log import version_bump, show_changelog
    
    feat("vision", "Implemented Florence-2 GPU acceleration",
         goal="Fast OCR on AMD GPU",
         result="SUCCESS - 0.38s per image")
    
    fix("redis", "Fixed backup corruption",
        goal="Prevent data loss",
        result="PARTIAL - Needs more testing")
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict, field
from collections import defaultdict

BASE_DIR = Path(r"E:\AI-Setup")
PATCH_DIR = BASE_DIR / "patches"
PATCH_DIR.mkdir(parents=True, exist_ok=True)

CHANGELOG_FILE = PATCH_DIR / "CHANGELOG.md"
VERSION_FILE = PATCH_DIR / "version.json"

# Redis integration
REDIS_HOST = "localhost"
REDIS_PORT = 6379

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


# Change type patterns
CHANGE_TYPES = {
    "feat": ["created", "implemented", "added", "built", "established"],
    "fix": ["fixed", "bug", "issue", "resolved", "corrected"],
    "refactor": ["refactored", "restructured", "consolidated", "merged", "simplified"],
    "docs": ["documented", "wrote docs", "commented", "described"],
    "config": ["configured", "setup", "initialized", "bootstrapped"],
    "perf": ["optimized", "improved", "enhanced", "sped up", "faster"],
    "test": ["tested", "verified", "validated", "checked", "debugging"],
    "chore": ["cleaned", "removed", "deleted", "updated", "maintained"],
}

# System patterns
SYSTEM_PATTERNS = {
    "vision": ["vision", "florence", "comfyui", "ocr", "gpu", "image"],
    "redis": ["redis", "backup", "ha", "sentinel", "replica"],
    "logging": ["log", "logger", "session", "chronicle", "archive"],
    "learning": ["learn", "decision", "experience", "reflection", "context"],
    "mcp": ["mcp", "tool", "server", "protocol"],
    "bootstrap": ["bootstrap", "startup", "harness", "primer"],
    "infrastructure": ["docker", "container", "deploy", "service"],
    "architecture": ["architecture", "design", "component", "system"],
    "automation": ["automation", "window", "ui", "screen"],
    "multi-agent": ["agent", "comm", "message", "coordinate"],
}


@dataclass
class PatchEntry:
    """A single patch/changelog entry"""
    id: str
    timestamp: str
    system: str
    change_type: str
    title: str
    goal: str
    result: str  # SUCCESS, FAILURE, PARTIAL, PENDING
    version_from: str
    version_to: str
    tags: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)


@dataclass
class Version:
    """Semantic version tracking"""
    major: int = 0
    minor: int = 1
    patch: int = 0
    
    def __str__(self):
        return f"v{self.major}.{self.minor}.{self.patch}"
    
    def bump_major(self):
        self.major += 1
        self.minor = 0
        self.patch = 0
        return str(self)
    
    def bump_minor(self):
        self.minor += 1
        self.patch = 0
        return str(self)
    
    def bump_patch(self):
        self.patch += 1
        return str(self)
    
    def to_dict(self):
        return {"major": self.major, "minor": self.minor, "patch": self.patch}


def load_version() -> Version:
    if VERSION_FILE.exists():
        try:
            with open(VERSION_FILE, 'r') as f:
                data = json.load(f)
            return Version(**data)
        except:
            pass
    return Version()


def save_version(v: Version):
    with open(VERSION_FILE, 'w') as f:
        json.dump(v.to_dict(), f, indent=2)


def detect_system(text: str) -> str:
    """Detect which system this patch affects"""
    text_lower = text.lower()
    for system, patterns in SYSTEM_PATTERNS.items():
        if any(p in text_lower for p in patterns):
            return system
    return "general"


def detect_change_type(text: str) -> str:
    """Detect what type of change this is"""
    text_lower = text.lower()
    for change_type, patterns in CHANGE_TYPES.items():
        if any(p in text_lower for p in patterns):
            return change_type
    return "chore"


class PatchLog:
    """
    Patch log system - logs changes like git commits / changelog entries
    
    Redis Keys:
        patches:all          - Hash of all patch entries
        patches:index        - Sorted set of patch IDs by timestamp
        patches:by_system:{system} - Sorted set of patch IDs per system
        patches:by_type:{type}    - Sorted set of patch IDs per change type
        patches:by_result:{result} - Sorted set by result (SUCCESS/FAILURE/etc)
        patches:version      - Current version string
    """
    
    _instance = None
    
    # Redis key constants
    KEY_ALL = "patches:all"
    KEY_INDEX = "patches:index"
    KEY_VERSION = "patches:version"
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance
    
    def _init(self):
        self.version = load_version()
        self.entries: List[PatchEntry] = []
        self._redis = None
        self._connect_redis()
        self._load_entries()
    
    def _connect_redis(self):
        """Connect to Redis"""
        if not REDIS_AVAILABLE:
            return
        try:
            self._redis = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=0,
                decode_responses=True
            )
            self._redis.ping()
        except Exception as e:
            self._redis = None
    
    def _redis_store(self, entry: PatchEntry):
        """Store entry in Redis with proper indexing"""
        if not self._redis:
            return
        
        try:
            data = asdict(entry)
            
            # Store in main hash
            self._redis.hset(self.KEY_ALL, entry.id, json.dumps(data))
            
            # Index by timestamp
            ts = datetime.fromisoformat(entry.timestamp).timestamp()
            self._redis.zadd(self.KEY_INDEX, {entry.id: ts})
            
            # Index by system
            self._redis.zadd(f"patches:by_system:{entry.system}", {entry.id: ts})
            
            # Index by change type
            self._redis.zadd(f"patches:by_type:{entry.change_type}", {entry.id: ts})
            
            # Index by result
            result_lower = entry.result.upper().split()[0]
            if result_lower in ["SUCCESS", "FAILURE", "PARTIAL", "PENDING"]:
                self._redis.zadd(f"patches:by_result:{result_lower}", {entry.id: ts})
            
            # Update version in Redis
            self._redis.set(self.KEY_VERSION, str(self.version))
            
        except Exception as e:
            print(f"[PatchLog] Redis store error: {e}")
    
    def _load_entries(self):
        """Load existing entries from Redis (primary) with file failsafe"""
        
        # PRIMARY: Redis
        if self._redis:
            try:
                ids = self._redis.zrevrange(self.KEY_INDEX, 0, -1)
                for pid in ids:
                    data = self._redis.hget(self.KEY_ALL, pid)
                    if data:
                        entry = PatchEntry(**json.loads(data))
                        self.entries.append(entry)
                
                # Get version from Redis
                redis_ver = self._redis.get(self.KEY_VERSION)
                if redis_ver:
                    parts = redis_ver.lstrip('v').split('.')
                    if len(parts) == 3:
                        self.version = Version(int(parts[0]), int(parts[1]), int(parts[2]))
                
                if self.entries:
                    print(f"[PatchLog] Loaded {len(self.entries)} entries from Redis")
                    return
            except Exception as e:
                print(f"[PatchLog] Redis load error: {e} - using failsafe")
        
        # FAILSAFE: Files (only if Redis unavailable or empty)
        print("[PatchLog] Redis unavailable - loading from file failsafe")
        for entry_file in PATCH_DIR.glob("PK_*.json"):
            try:
                with open(entry_file, 'r') as f:
                    data = json.load(f)
                    self.entries.append(PatchEntry(**data))
            except:
                pass
        self.entries.sort(key=lambda e: e.timestamp, reverse=True)
    
    def _gen_id(self) -> str:
        ts = datetime.now().strftime("%m%d%H%M%S")
        return f"PK_{ts}"
    
    def _detect_from_content(self, content: str, system: str = None, change_type: str = None):
        """Auto-detect system and change type from content"""
        return (
            system or detect_system(content),
            change_type or detect_change_type(content)
        )
    
    def feat(self, system: str, title: str, goal: str = "", result: str = "PENDING", 
             tags: List[str] = None) -> str:
        """Log a new feature"""
        return self._log("feat", system, title, goal, result, tags)
    
    def fix(self, system: str, title: str, goal: str = "", result: str = "PENDING",
            tags: List[str] = None) -> str:
        """Log a bug fix"""
        return self._log("fix", system, title, goal, result, tags)
    
    def refactor(self, system: str, title: str, goal: str = "", result: str = "PENDING",
                 tags: List[str] = None) -> str:
        """Log a refactoring"""
        return self._log("refactor", system, title, goal, result, tags)
    
    def docs(self, system: str, title: str, goal: str = "", result: str = "PENDING",
             tags: List[str] = None) -> str:
        """Log documentation"""
        return self._log("docs", system, title, goal, result, tags)
    
    def config(self, system: str, title: str, goal: str = "", result: str = "PENDING",
               tags: List[str] = None) -> str:
        """Log configuration change"""
        return self._log("config", system, title, goal, result, tags)
    
    def test(self, system: str, title: str, goal: str = "", result: str = "PENDING",
             tags: List[str] = None) -> str:
        """Log testing"""
        return self._log("test", system, title, goal, result, tags)
    
    def perf(self, system: str, title: str, goal: str = "", result: str = "PENDING",
             tags: List[str] = None) -> str:
        """Log performance improvement"""
        return self._log("perf", system, title, goal, result, tags)
    
    def chore(self, system: str, title: str, goal: str = "", result: str = "PENDING",
              tags: List[str] = None) -> str:
        """Log maintenance"""
        return self._log("chore", system, title, goal, result, tags)
    
    def _log(self, change_type: str, system: str, title: str, goal: str, 
             result: str, tags: List[str] = None) -> str:
        """Internal logging method - stores to Redis primary, file failsafe"""
        patch_id = self._gen_id()
        
        # Bump version based on change type
        version_from = str(self.version)
        if change_type == "feat":
            version_to = self.version.bump_minor()
        elif change_type in ["fix", "perf"]:
            version_to = self.version.bump_patch()
        elif change_type == "refactor":
            version_to = str(self.version)
        else:
            version_to = str(self.version)
        
        entry = PatchEntry(
            id=patch_id,
            timestamp=datetime.now().isoformat(),
            system=system,
            change_type=change_type,
            title=title[:100],
            goal=goal[:200],
            result=result,
            version_from=version_from,
            version_to=version_to,
            tags=tags or [],
            evidence=[]
        )
        
        self.entries.append(entry)
        
        # PRIMARY: Store to Redis
        self._redis_store(entry)
        
        # FAILSAFE: Also write to file (dual-write ensures persistence)
        self._save_entry(entry)
        self._save_changelog()
        save_version(self.version)
        
        # Print patch format
        print(f"\n[{system}:{change_type}] {title}")
        print(f"  Goal: {goal or 'N/A'}")
        print(f"  Result: {result}")
        print(f"  Version: {version_from} -> {version_to}")
        
        return patch_id
    
    def _save_entry(self, entry: PatchEntry):
        """Save entry to JSON"""
        entries = []
        entry_file = PATCH_DIR / f"{entry.id}.json"
        
        with open(entry_file, 'w') as f:
            json.dump(asdict(entry), f, indent=2)
    
    def _save_changelog(self):
        """Save markdown changelog"""
        lines = [
            "# Changelog",
            "",
            f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
            f"*Current Version: {self.version}*",
            "",
            "---",
            ""
        ]
        
        # Group by date
        by_date = defaultdict(list)
        for entry in self.entries:
            date = entry.timestamp[:10]
            by_date[date].append(entry)
        
        for date in sorted(by_date.keys(), reverse=True):
            lines.append(f"## {date}")
            lines.append("")
            
            for entry in by_date[date]:
                result_marker = {
                    "SUCCESS": "[+]",
                    "FAILURE": "[-]",
                    "PARTIAL": "[~]",
                    "PENDING": "[ ]"
                }.get(entry.result, "[ ]")
                
                lines.append(f"{result_marker} **{entry.system}:{entry.change_type}** {entry.title}")
                
                if entry.goal:
                    lines.append(f"   - Goal: {entry.goal}")
                
                lines.append(f"   - {entry.version_from} -> {entry.version_to}")
                lines.append("")
        
        with open(CHANGELOG_FILE, 'w') as f:
            f.write("\n".join(lines))
    
    def get_changelog(self, system: str = None, limit: int = 20) -> List[PatchEntry]:
        """Get changelog entries, optionally filtered by system"""
        results = self.entries
        if system:
            results = [e for e in results if e.system == system]
        return results[:limit]
    
    def search(self, query: str) -> List[PatchEntry]:
        """Search changelog"""
        query_lower = query.lower()
        return [
            e for e in self.entries
            if query_lower in e.title.lower() or query_lower in e.goal.lower()
        ]
    
    def get_by_system(self, system: str) -> List[PatchEntry]:
        """Get patches for a specific system from Redis"""
        if not self._redis:
            return [e for e in self.entries if e.system == system]
        
        try:
            ids = self._redis.zrevrange(f"patches:by_system:{system}", 0, -1)
            results = []
            for pid in ids:
                data = self._redis.hget(self.KEY_ALL, pid)
                if data:
                    results.append(PatchEntry(**json.loads(data)))
            return results
        except:
            return [e for e in self.entries if e.system == system]
    
    def get_by_type(self, change_type: str) -> List[PatchEntry]:
        """Get patches of a specific change type from Redis"""
        if not self._redis:
            return [e for e in self.entries if e.change_type == change_type]
        
        try:
            ids = self._redis.zrevrange(f"patches:by_type:{change_type}", 0, -1)
            results = []
            for pid in ids:
                data = self._redis.hget(self.KEY_ALL, pid)
                if data:
                    results.append(PatchEntry(**json.loads(data)))
            return results
        except:
            return [e for e in self.entries if e.change_type == change_type]
    
    def get_by_result(self, result: str) -> List[PatchEntry]:
        """Get patches with specific result from Redis"""
        result_upper = result.upper()
        if result_upper not in ["SUCCESS", "FAILURE", "PARTIAL", "PENDING"]:
            return []
        
        if not self._redis:
            return [e for e in self.entries if e.result.upper().startswith(result_upper)]
        
        try:
            ids = self._redis.zrevrange(f"patches:by_result:{result_upper}", 0, -1)
            results = []
            for pid in ids:
                data = self._redis.hget(self.KEY_ALL, pid)
                if data:
                    results.append(PatchEntry(**json.loads(data)))
            return results
        except:
            return [e for e in self.entries if e.result.upper().startswith(result_upper)]


_patch_log: Optional[PatchLog] = None

def get_patch_log() -> PatchLog:
    global _patch_log
    if _patch_log is None:
        _patch_log = PatchLog()
    return _patch_log

# Convenience functions
def feat(system: str, title: str, goal: str = "", result: str = "PENDING"):
    return get_patch_log().feat(system, title, goal, result)

def fix(system: str, title: str, goal: str = "", result: str = "PENDING"):
    return get_patch_log().fix(system, title, goal, result)

def refactor(system: str, title: str, goal: str = "", result: str = "PENDING"):
    return get_patch_log().refactor(system, title, goal, result)

def docs(system: str, title: str, goal: str = "", result: str = "PENDING"):
    return get_patch_log().docs(system, title, goal, result)

def config(system: str, title: str, goal: str = "", result: str = "PENDING"):
    return get_patch_log().config(system, title, goal, result)

def test(system: str, title: str, goal: str = "", result: str = "PENDING"):
    return get_patch_log().test(system, title, goal, result)

def show_changelog(system: str = None, limit: int = 10):
    pl = get_patch_log()
    entries = pl.get_changelog(system, limit)
    
    print()
    print("=" * 70)
    print(f"  CHANGELOG ({pl.version})")
    print("=" * 70)
    
    if not entries:
        print("  No entries yet.")
        return
    
    current_date = None
    for entry in entries:
        date = entry.timestamp[:10]
        if date != current_date:
            print()
            print(f"  {date}")
            current_date = date
        
        result_marker = {
            "SUCCESS": "[+]",
            "FAILURE": "[-]",
            "PARTIAL": "[~]",
            "PENDING": "[ ]"
        }.get(entry.result, "[ ]")
        
        print(f"    {result_marker} [{entry.system}:{entry.change_type}] {entry.title}")
        if entry.goal:
            print(f"         Goal: {entry.goal[:50]}")
    
    print()
    print("=" * 70)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--system', help='Filter by system')
    parser.add_argument('--limit', type=int, default=10)
    parser.add_argument('--test', action='store_true')
    args = parser.parse_args()
    
    if args.test:
        print("Testing patch log...")
        feat("logging", "Implemented auto-chronicle", 
             goal="Reduce manual chronicle entries",
             result="SUCCESS")
        fix("redis", "Fixed backup corruption",
            goal="Prevent data loss",
            result="PARTIAL")
    else:
        show_changelog(args.system, args.limit)
