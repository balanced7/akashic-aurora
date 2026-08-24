#!/usr/bin/env python3
"""
Session Log Migration - Old Format to New
========================================

Converts legacy log entries to the new format with:
- Unified entry format
- Auto-tagging
- Meaningful summaries
- Session digests

Old format: {"unique_id", "action", "description", "source", "checksum"}
New format: {"type", "content", "tags", "data"}

Usage:
    python migrate_logs.py --dry-run  # Preview changes
    python migrate_logs.py           # Execute migration
"""

import sys
import json
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from collections import Counter, defaultdict

sys.path.insert(0, r"E:\AI-Setup")

from config import get_redis_config

BASE_DIR = Path(r"E:\AI-Setup")
LOG_DIR = BASE_DIR / "session_logs"
ARCHIVE_DIR = BASE_DIR / "sessions"
INDEX_FILE = ARCHIVE_DIR / "index.json"

BACKUP_LOG = LOG_DIR / "backup_session_all.jsonl"
PRIMARY_LOG = LOG_DIR / "session_all.jsonl"

TAG_PATTERNS = {
    "vision": ["vision", "comfyui", "florence", "ocr", "image", "screenshot", "directml", "gpu", "amd"],
    "infrastructure": ["redis", "backup", "ha", "sentinel", "docker", "container", "replica", "ollama"],
    "multi-agent": ["mcp", "agent", "comm", "message", "coordinate", "broadcast", "alert", "manifest"],
    "learning": ["learning", "decision", "experience", "reflection", "reflexion", "context", "primer", "knowledge"],
    "architecture": ["consolidat", "refactor", "architecture", "design", "merge", "file", "folder", "logging", "logger", "doc"],
    "setup": ["install", "setup", "configur", "deploy", "build", "bootstrap", "path", "python", "dashboard"],
    "debugging": ["bug", "fix", "error", "crash", "debug", "issue", "problem", "verify", "test", "troubleshoot"],
    "automation": ["automation", "pyautogui", "selenium", "ui", "window", "screenshot", "automation", "react"],
    "ocr": ["ocr", "tesseract", "paddleocr", "easyocr", "text recognition"],
    "decision-log": ["decision", "adr", "chose", "decided", "chosen", "alternative"],
    "fastapi": ["fastapi", "api", "endpoint"],
    "frontend": ["react", "vite", "frontend", "tailwind", "ui component"],
}

NOISE_PATTERNS = [
    "session_continu",
    "logger_startup",
    "logger_shutdown",
    "ping",
    "heartbeat",
]

SIGNIFICANT_ACTION_TYPES = [
    "created", "created:", "updated", "modified", "fixed", "completed",
    "implemented", "designed", "analyzed", "tested", "verified",
    "discovered", "learned", "decided", "migrated", "consolidated",
    "bootstrap", "configured", "deployed", "documented",
]


def auto_tag(text: str) -> List[str]:
    """Generate tags from text"""
    text_lower = text.lower()
    tags = []
    for tag, patterns in TAG_PATTERNS.items():
        if any(p in text_lower for p in patterns):
            if tag not in tags:
                tags.append(tag)
    return tags or ["general"]


def is_noise(entry: Dict) -> bool:
    """Check if entry is noise (session metadata, not actual work)"""
    if not entry:
        return True
    
    desc = entry.get("description", entry.get("content", "")).lower()
    
    for pattern in NOISE_PATTERNS:
        if pattern in desc:
            return True
    
    return False


def is_significant(entry: Dict) -> bool:
    """Check if entry represents significant work"""
    if not entry:
        return False
    
    desc = entry.get("description", entry.get("content", "")).lower()
    
    for pattern in SIGNIFICANT_ACTION_TYPES:
        if pattern in desc:
            return True
    
    return False


def convert_entry(old_entry: Dict) -> Dict:
    """Convert old format entry to new format"""
    desc = old_entry.get("description", "")
    action = old_entry.get("action", "")
    
    entry_type = "action"
    if "error" in action.lower() or "error" in desc.lower():
        entry_type = "error"
    elif "decision" in action.lower() or "decision" in desc.lower():
        entry_type = "decision"
    elif "learn" in desc.lower():
        entry_type = "learning"
    elif old_entry.get("type") in ["chat", "message"]:
        entry_type = "chat"
    
    content = desc
    if not content or len(content) < 10:
        content = action.replace("_", " ").title()
    if not content:
        content = old_entry.get("type", "action")
    
    return {
        "type": entry_type,
        "timestamp": old_entry.get("timestamp", ""),
        "sequence": old_entry.get("sequence", 0),
        "session": old_entry.get("session", ""),
        "content": content[:200],
        "tags": auto_tag(desc + " " + action),
        "data": {
            "original_action": action,
            "unique_id": old_entry.get("unique_id"),
        }
    }


def extract_sessions(entries: List[Dict]) -> Dict[str, List[Dict]]:
    """Group entries by session ID"""
    sessions = defaultdict(list)
    for entry in entries:
        session_id = entry.get("session", "unknown")
        sessions[session_id].append(entry)
    return dict(sessions)


def get_entry_text(entry: Dict) -> tuple:
    """Get text and type from entry (handles both old and new format)"""
    if "content" in entry:
        # New format
        content = entry.get("content", "")
        action = entry.get("data", {}).get("original_action", "")
        return content, action
    else:
        # Old format
        desc = entry.get("description", "")
        action = entry.get("action", "")
        return desc, action


def generate_session_summary(session_entries: List[Dict], session_id: str) -> Dict:
    """Generate summary for a session"""
    if not session_entries:
        return None
    
    timestamps = [e.get("timestamp", "") for e in session_entries if e.get("timestamp")]
    started = min(timestamps) if timestamps else ""
    ended = max(timestamps) if timestamps else ""
    
    duration = 0
    if started and ended:
        try:
            start = datetime.fromisoformat(started)
            end = datetime.fromisoformat(ended)
            duration = int((end - start).total_seconds() / 60)
        except:
            duration = 0
    
    actions = []
    learnings = []
    decisions = []
    errors = []
    all_text_parts = []
    
    for entry in session_entries:
        desc, action = get_entry_text(entry)
        text = (desc + " " + action).lower()
        all_text_parts.append(desc)
        all_text_parts.append(action)
        
        # Check if significant
        is_sig = any(kw in text for kw in SIGNIFICANT_ACTION_TYPES)
        
        if is_sig and desc:
            actions.append(desc[:100])
        
        if "error" in text:
            errors.append(desc[:100] if desc else action[:100])
        
        if "learn" in text or "discovered" in text:
            learnings.append(desc[:100] if desc else action[:100])
        
        if "decision" in text or "decided" in text:
            decisions.append(desc[:100] if desc else action[:100])
    
    all_text = " ".join(all_text_parts)
    
    summary = ""
    if actions:
        summary = f"Actions: {', '.join(actions[:3])}"
    elif errors:
        summary = f"Errors: {len(errors)} - {errors[0][:50]}"
    else:
        summary = f"Session with {len(session_entries)} entries"
    
    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', session_id)
    date = date_match.group(1) if date_match else datetime.now().strftime('%Y-%m-%d')
    
    return {
        "session_id": session_id,
        "date": date,
        "started_at": started,
        "ended_at": ended,
        "duration_minutes": duration,
        "tags": auto_tag(all_text),
        "summary": summary,
        "key_actions": list(dict.fromkeys(actions))[:10],
        "learnings": list(dict.fromkeys(learnings))[:5],
        "decisions": list(dict.fromkeys(decisions))[:5],
        "message_count": len(session_entries),
        "error_count": len(errors),
    }


def migrate_log_file(log_path: Path, dry_run: bool = False) -> List[Dict]:
    """Migrate a single log file"""
    if not log_path.exists():
        print(f"  File not found: {log_path}")
        return []
    
    print(f"  Reading: {log_path.name}")
    
    entries = []
    with open(log_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
                entries.append(entry)
            except:
                pass
    
    print(f"    Found {len(entries)} entries")
    
    converted = []
    for entry in entries:
        if is_noise(entry):
            continue
        converted.append(convert_entry(entry))
    
    print(f"    Significant entries: {len(converted)}")
    
    sessions = extract_sessions(converted)
    print(f"    Sessions: {len(sessions)}")
    
    return converted


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Preview without saving")
    parser.add_argument("--session", help="Migrate specific session only")
    args = parser.parse_args()
    
    print()
    print("=" * 60)
    print("  SESSION LOG MIGRATION")
    print("=" * 60)
    print()
    
    all_converted = []
    
    print("[1] Migrating backup_session_all.jsonl...")
    converted = migrate_log_file(BACKUP_LOG, args.dry_run)
    all_converted.extend(converted)
    
    print()
    print("[2] Migrating session_all.jsonl...")
    converted = migrate_log_file(PRIMARY_LOG, args.dry_run)
    all_converted.extend(converted)
    
    print()
    print("[3] Generating session digests...")
    
    sessions = extract_sessions(all_converted)
    digests = []
    
    for session_id, entries in sessions.items():
        if args.session and session_id != args.session:
            continue
        
        summary = generate_session_summary(entries, session_id)
        if summary:
            digests.append(summary)
            print(f"  {session_id}:")
            print(f"    Date: {summary['date']}, Duration: ~{summary['duration_minutes']}min")
            print(f"    Tags: {summary['tags']}")
            print(f"    Summary: {summary['summary'][:60]}...")
    
    if args.dry_run:
        print()
        print("[DRY RUN] No files written.")
        return
    
    print()
    print("[4] Saving migrated sessions...")
    
    for digest in digests:
        date_dir = ARCHIVE_DIR / digest["date"]
        date_dir.mkdir(parents=True, exist_ok=True)
        
        digest_file = date_dir / f"{digest['session_id']}_digest.md"
        raw_file = date_dir / f"{digest['session_id']}_raw.jsonl"
        
        digest_lines = [
            f"# Session {digest['session_id']}",
            "",
            f"**Date**: {digest['date']}",
            f"**Duration**: ~{digest['duration_minutes']} min",
            f"**Tags**: [{'] ['.join(digest['tags'])}]",
            "",
            "## Summary",
            digest['summary'],
            "",
        ]
        
        if digest['key_actions']:
            digest_lines.extend(["## Key Actions"] + [f"- {a}" for a in digest['key_actions']] + [""])
        
        if digest['learnings']:
            digest_lines.extend(["## Learnings"] + [f"- {l}" for l in digest['learnings']] + [""])
        
        if digest['decisions']:
            digest_lines.extend(["## Decisions"] + [f"- {d}" for d in digest['decisions']] + [""])
        
        digest_lines.extend(["---", f"*Migrated: {datetime.now().isoformat()}*"])
        
        digest_file.write_text("\n".join(digest_lines), encoding='utf-8')
        
        session_entries = [e for e in all_converted if e.get("session") == digest["session_id"]]
        with open(raw_file, 'w', encoding='utf-8') as f:
            for e in session_entries:
                f.write(json.dumps(e) + '\n')
        
        print(f"  Saved: {digest_file.name}")
    
    print()
    print("[5] Updating index...")
    
    existing = []
    if INDEX_FILE.exists():
        try:
            with open(INDEX_FILE, 'r') as f:
                existing = json.load(f)
        except:
            existing = []
    
    existing_ids = {s.get("session_id") for s in existing}
    
    for digest in digests:
        if digest["session_id"] not in existing_ids:
            existing.insert(0, digest)
    
    with open(INDEX_FILE, 'w') as f:
        json.dump(existing, f, indent=2)
    
    print()
    print("=" * 60)
    print(f"  MIGRATION COMPLETE")
    print("=" * 60)
    print()
    print(f"Sessions migrated: {len(digests)}")
    print(f"Entries processed: {len(all_converted)}")
    print()


if __name__ == "__main__":
    main()
