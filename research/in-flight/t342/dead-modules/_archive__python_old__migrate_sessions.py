#!/usr/bin/env python3
"""
Session Archive Migration
========================

Migrates existing session logs to the new archive format:
- sessions/index.json (master index)
- sessions/YYYY-MM-DD/*.md (digests)
- sessions/YYYY-MM-DD/*.jsonl (raw logs)

Usage:
    python migrate_sessions.py
"""

import sys
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict

sys.path.insert(0, r"E:\AI-Setup")

BASE_DIR = Path(r"E:\AI-Setup")
SESSION_LOGS = BASE_DIR / "session_logs"
ARCHIVE_DIR = BASE_DIR / "sessions"
INDEX_FILE = ARCHIVE_DIR / "index.json"


TAG_PATTERNS = {
    "vision": ["vision", "comfyui", "florence", "ocr", "image", "screenshot"],
    "infrastructure": ["redis", "backup", "ha", "sentinel", "docker", "container"],
    "multi-agent": ["mcp", "agent", "comm", "message", "coordinate", "broadcast", "alert"],
    "learning": ["learning", "decision", "experience", "reflection", "reflexion", "context"],
    "architecture": ["consolidat", "refactor", "architecture", "design", "merge", "simplif"],
    "setup": ["install", "setup", "configur", "deploy", "build", "bootstrap"],
    "debugging": ["bug", "fix", "error", "crash", "debug", "issue", "test"],
}


@dataclass
class SessionIndex:
    session_id: str
    date: str
    started_at: str
    ended_at: str
    duration_minutes: int
    tags: List[str]
    summary: str
    key_actions: List[str]
    learnings: List[str]
    decisions: List[str]
    message_count: int
    error_count: int
    digest_file: str
    raw_file: str


def auto_tag(text: str) -> List[str]:
    """Generate tags from text"""
    text_lower = text.lower()
    tags = []
    for tag, patterns in TAG_PATTERNS.items():
        if any(p in text_lower for p in patterns):
            tags.append(tag)
    return tags or ["general"]


def extract_session_info(jsonl_path: Path) -> Dict:
    """Extract session info from JSONL"""
    entries = []
    try:
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    entries.append(json.loads(line.strip()))
                except:
                    pass
    except Exception as e:
        print(f"  Error reading {jsonl_path}: {e}")
        return {}
    
    if not entries:
        return {}
    
    # Get session ID from first entry
    session_id = entries[0].get('session', 'unknown')
    
    # Find timestamps
    started = None
    ended = None
    for e in entries:
        ts = e.get('timestamp', '')
        if ts and not started:
            started = ts
        if ts:
            ended = ts
    
    # Count messages and errors
    message_count = sum(1 for e in entries if e.get('type') == 'chat')
    error_count = sum(1 for e in entries if e.get('type') == 'error')
    
    # Extract actions (skip noise)
    actions = []
    decisions = []
    for e in entries:
        if e.get('type') == 'action':
            desc = e.get('description', '')
            if desc and 'session_continu' not in desc.lower() and 'logger_' not in e.get('action', ''):
                actions.append(desc[:100])
        elif e.get('type') == 'decision':
            decisions.append(e.get('title', e.get('decision', ''))[:100])
    
    # Extract learnings from actions/descriptions
    learnings = []
    for e in entries:
        desc = e.get('description', '')
        if any(kw in desc.lower() for kw in ['learned', 'discovered', 'fixed', 'created', 'completed']):
            learnings.append(desc[:80])
    
    # Generate summary
    meaningful_actions = [a for a in actions if len(a) > 30]
    if meaningful_actions:
        summary = f"Actions: {', '.join(meaningful_actions[:3])}"
    else:
        summary = f"Session with {message_count} messages, {error_count} errors"
    
    # Calculate duration
    duration = 0
    if started and ended:
        try:
            start = datetime.fromisoformat(started)
            end = datetime.fromisoformat(ended)
            duration = int((end - start).total_seconds() / 60)
        except:
            duration = 0
    
    # Extract date from session_id
    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', session_id)
    date = date_match.group(1) if date_match else datetime.now().strftime('%Y-%m-%d')
    
    # Auto-tag
    all_text = ' '.join(actions + decisions + learnings)
    tags = auto_tag(all_text)
    
    return {
        'session_id': session_id,
        'date': date,
        'started_at': started or '',
        'ended_at': ended or '',
        'duration_minutes': duration,
        'tags': tags,
        'summary': summary,
        'key_actions': actions[:10],
        'learnings': learnings[:5],
        'decisions': decisions[:5],
        'message_count': message_count,
        'error_count': error_count,
        'digest_file': '',
        'raw_file': '',
    }


def migrate_jsonl_to_archive(jsonl_path: Path, dry_run: bool = False) -> Optional[SessionIndex]:
    """Migrate a JSONL file to the new archive format"""
    if not jsonl_path.exists():
        return None
    
    info = extract_session_info(jsonl_path)
    if not info:
        return None
    
    session = SessionIndex(**info)
    
    # Set file paths
    date_dir = ARCHIVE_DIR / session.date
    if dry_run:
        date_dir = Path("DRY_RUN") / session.date
    
    date_dir.mkdir(parents=True, exist_ok=True)
    
    session.digest_file = str(date_dir / f"{session.session_id}_digest.md")
    session.raw_file = str(date_dir / f"{session.session_id}_raw.jsonl")
    
    if not dry_run:
        # Copy raw log
        raw_dest = Path(session.raw_file)
        raw_dest.write_bytes(jsonl_path.read_bytes())
        
        # Generate digest
        digest = generate_digest(session)
        Path(session.digest_file).write_text(digest, encoding='utf-8')
    
    return session


def generate_digest(session: SessionIndex) -> str:
    """Generate markdown digest"""
    lines = [
        f"# Session {session.session_id}",
        "",
        f"**Date**: {session.date}",
        f"**Duration**: ~{session.duration_minutes} min",
        f"**Tags**: [{'] ['.join(session.tags)}]",
        "",
        "## Summary",
        session.summary,
        "",
    ]
    
    if session.key_actions:
        lines.append("## Key Actions")
        for a in session.key_actions[:10]:
            lines.append(f"- {a}")
        lines.append("")
    
    if session.learnings:
        lines.append("## Learnings")
        for l in session.learnings[:5]:
            lines.append(f"- {l}")
        lines.append("")
    
    if session.decisions:
        lines.append("## Decisions")
        for d in session.decisions[:5]:
            lines.append(f"- {d}")
        lines.append("")
    
    lines.append(f"---")
    lines.append(f"*Archived: {datetime.now().isoformat()}*")
    
    return "\n".join(lines)


def migrate_summary_md(md_path: Path, session_id: str = None) -> Optional[SessionIndex]:
    """Migrate a SESSION_SUMMARY_*.md file"""
    if not md_path.exists():
        return None
    
    content = md_path.read_text(encoding='utf-8')
    
    # Extract date
    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', md_path.name)
    date = date_match.group(1) if date_match else datetime.now().strftime('%Y-%m-%d')
    
    # Extract tags
    tags = auto_tag(content)
    
    # Extract learnings and decisions
    learnings = []
    decisions = []
    key_actions = []
    mode = None
    
    for line in content.split('\n'):
        if line.startswith('## '):
            section = line[3:].lower()
            if 'learning' in section:
                mode = 'learnings'
            elif 'decision' in section:
                mode = 'decisions'
            elif 'action' in section or 'accomplish' in section:
                mode = 'actions'
            else:
                mode = None
        elif mode and line.strip().startswith('- '):
            text = line.strip()[2:]
            if mode == 'learnings':
                learnings.append(text[:100])
            elif mode == 'decisions':
                decisions.append(text[:100])
            elif mode == 'actions':
                key_actions.append(text[:100])
    
    # Extract summary (first paragraph after Summary header)
    summary_match = re.search(r'## Summary\s*\n+(.+?)(?:\n\n|\n##)', content, re.DOTALL)
    summary = summary_match.group(1).strip()[:200] if summary_match else content[:200]
    
    # Extract duration
    duration_match = re.search(r'(\d+)\s*hour', content)
    hours = int(duration_match.group(1)) if duration_match else 0
    duration_match = re.search(r'(\d+)\s*min', content)
    minutes = int(duration_match.group(1)) if duration_match else hours * 60
    
    sid = session_id or md_path.stem
    started = f"{date}T00:00:00"
    ended = f"{date}T{(minutes or 60):02d}:00:00"
    
    session = SessionIndex(
        session_id=sid,
        date=date,
        started_at=started,
        ended_at=ended,
        duration_minutes=minutes or 60,
        tags=tags,
        summary=summary,
        key_actions=key_actions[:10],
        learnings=learnings[:5],
        decisions=decisions[:5],
        message_count=0,
        error_count=0,
        digest_file=str(ARCHIVE_DIR / date / f"{sid}_digest.md"),
        raw_file=str(ARCHIVE_DIR / date / f"{sid}_raw.md")
    )
    
    # Save digest
    date_dir = ARCHIVE_DIR / date
    date_dir.mkdir(parents=True, exist_ok=True)
    digest_path = date_dir / f"{sid}_digest.md"
    digest_path.write_text(generate_digest(session), encoding='utf-8')
    
    # Copy raw summary
    raw_path = date_dir / f"{sid}_raw.md"
    raw_path.write_bytes(md_path.read_bytes())
    
    session.digest_file = str(digest_path)
    session.raw_file = str(raw_path)
    
    return session


def main():
    print()
    print("=" * 60)
    print("  SESSION ARCHIVE MIGRATION")
    print("=" * 60)
    print()
    
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    
    sessions = []
    
    # Migrate JSONL files
    print("[1] Migrating JSONL logs...")
    for jsonl_path in SESSION_LOGS.glob("*.jsonl"):
        print(f"  Processing: {jsonl_path.name}")
        session = migrate_jsonl_to_archive(jsonl_path)
        if session:
            sessions.append(session)
            print(f"    -> {session.session_id} [{', '.join(session.tags)}]")
    
    # Migrate SESSION_SUMMARY_*.md files
    print()
    print("[2] Migrating session summaries...")
    for md_path in SESSION_LOGS.glob("SESSION_SUMMARY_*.md"):
        print(f"  Processing: {md_path.name}")
        session = migrate_summary_md(md_path)
        if session:
            sessions.append(session)
            print(f"    -> {session.session_id} [{', '.join(session.tags)}]")
    
    # Also check root for summaries
    print()
    print("[3] Checking for root-level summaries...")
    for md_path in BASE_DIR.glob("SESSION_SUMMARY_*.md"):
        print(f"  Processing: {md_path.name}")
        session = migrate_summary_md(md_path)
        if session:
            sessions.append(session)
    
    # Deduplicate by session_id
    seen = set()
    unique = []
    for s in sessions:
        if s.session_id not in seen:
            seen.add(s.session_id)
            unique.append(s)
    sessions = unique
    
    # Save index
    print()
    print(f"[4] Saving index with {len(sessions)} sessions...")
    index_data = [asdict(s) for s in sessions]
    INDEX_FILE.write_text(json.dumps(index_data, indent=2), encoding='utf-8')
    
    print()
    print("=" * 60)
    print("  MIGRATION COMPLETE")
    print("=" * 60)
    print()
    print(f"Sessions archived: {len(sessions)}")
    print(f"Index file: {INDEX_FILE}")
    print()
    print("Tag distribution:")
    from collections import Counter
    tags = Counter()
    for s in sessions:
        for t in s.tags:
            tags[t] += 1
    for tag, count in tags.most_common():
        print(f"  [{tag}]: {count}")
    print()


if __name__ == "__main__":
    import sys
    sys.path.insert(0, r"E:\AI-Setup")
    main()
