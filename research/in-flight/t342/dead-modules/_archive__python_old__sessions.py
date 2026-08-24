"""
Session Archive System
=====================

Three-tier logging architecture for full continuity + easy digestion:

1. INDEX (sessions/index.json)     - Master lookup table
2. DIGEST (sessions/YYYY-MM-DD/*.md) - Human-readable summaries  
3. RAW (sessions/YYYY-MM-DD/*.jsonl) - Full logs for troubleshooting

Auto-tagging by keywords:
  - vision, comfyui, florence → [vision]
  - redis, backup, ha → [infrastructure]
  - mcp, agent, comm → [multi-agent]
  - learning, decision, experience → [learning]
  - consolidate, refactor, architecture → [architecture]
  - install, setup, configure → [setup]
  - bug, fix, error → [debugging]
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
from collections import Counter

BASE_DIR = Path(r"E:\AI-Setup")
ARCHIVE_DIR = BASE_DIR / "sessions"
ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
INDEX_FILE = ARCHIVE_DIR / "index.json"


TAG_PATTERNS = {
    "vision": ["vision", "comfyui", "florence", "ocr", "image"],
    "infrastructure": ["redis", "backup", "ha", "sentinel", "docker", "container"],
    "multi-agent": ["mcp", "agent", "comm", "message", "coordinate", "broadcast"],
    "learning": ["learning", "decision", "experience", "reflection", "reflexion"],
    "architecture": ["consolidat", "refactor", "architecture", "design", "merge"],
    "setup": ["install", "setup", "configur", "deploy", "build"],
    "debugging": ["bug", "fix", "error", "crash", "debug", "issue"],
}


@dataclass
class SessionIndex:
    """Entry in the master session index"""
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
    digest_file: str = ""
    raw_file: str = ""


class SessionIndexManager:
    """Manages the master session index"""
    
    def __init__(self):
        self.index_file = INDEX_FILE
        self.sessions: List[SessionIndex] = []
        self._load()
    
    def _load(self):
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r') as f:
                    data = json.load(f)
                    self.sessions = [SessionIndex(**s) for s in data]
            except:
                self.sessions = []
    
    def _save(self):
        with open(self.index_file, 'w') as f:
            json.dump([asdict(s) for s in self.sessions], f, indent=2)
    
    def add(self, session: SessionIndex):
        self.sessions.insert(0, session)
        self._save()
    
    def get_recent(self, limit: int = 10) -> List[SessionIndex]:
        return self.sessions[:limit]
    
    def search(self, query: str, tag: str = None) -> List[SessionIndex]:
        results = self.sessions
        if tag:
            results = [s for s in results if tag in s.tags]
        if query:
            q = query.lower()
            results = [s for s in results if 
                       q in s.summary.lower() or 
                       q in ' '.join(s.key_actions).lower() or
                       q in ' '.join(s.learnings).lower()]
        return results
    
    def get_by_tag(self, tag: str) -> List[SessionIndex]:
        return [s for s in self.sessions if tag in s.tags]
    
    def get_tags(self) -> Dict[str, int]:
        counts = Counter()
        for s in self.sessions:
            for t in s.tags:
                counts[t] += 1
        return dict(counts)


def auto_tag(text: str) -> List[str]:
    """Auto-generate tags based on keywords"""
    text_lower = text.lower()
    tags = []
    for tag, patterns in TAG_PATTERNS.items():
        if any(p in text_lower for p in patterns):
            tags.append(tag)
    return tags or ["general"]


def extract_actions_from_jsonl(jsonl_path: Path) -> List[str]:
    """Extract key actions from raw JSONL log"""
    actions = []
    if not jsonl_path.exists():
        return actions
    
    try:
        with open(jsonl_path, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    if entry.get('type') == 'action' and entry.get('action'):
                        desc = entry.get('description', '')
                        if desc and 'session_continu' not in desc.lower():
                            actions.append(desc[:100])
                    elif entry.get('type') == 'decision':
                        actions.append(f"Decision: {entry.get('title', entry.get('decision', ''))[:80]}")
                except:
                    pass
    except:
        pass
    return actions


def extract_summary_from_jsonl(jsonl_path: Path) -> str:
    """Generate a summary from raw JSONL"""
    actions = extract_actions_from_jsonl(jsonl_path)
    if not actions:
        return "Session recorded"
    
    # Get distinctive actions (not startup noise)
    meaningful = [a for a in actions if len(a) > 20][:5]
    if meaningful:
        return f"Performed: {', '.join(meaningful[:3])}"
    return "Session completed"


class SessionDigest:
    """Generates human-readable session digest"""
    
    @staticmethod
    def generate(session: SessionIndex, actions: List[str] = None) -> str:
        lines = [
            f"# Session {session.session_id}",
            "",
            f"**Date**: {session.date}",
            f"**Duration**: ~{session.duration_minutes} min",
            f"**Tags**: [{'] ['.join(session.tags)}]",
            "",
            "## Summary",
            session.summary or "Session completed.",
            "",
        ]
        
        if session.key_actions:
            lines.append("## Key Actions")
            for action in session.key_actions[:10]:
                lines.append(f"- {action}")
            lines.append("")
        
        if session.learnings:
            lines.append("## Learnings")
            for learning in session.learnings[:5]:
                lines.append(f"- {learning}")
            lines.append("")
        
        if session.decisions:
            lines.append("## Decisions")
            for decision in session.decisions[:5]:
                lines.append(f"- {decision}")
            lines.append("")
        
        lines.append("---")
        lines.append(f"*Digest generated: {datetime.now().isoformat()}*")
        
        return "\n".join(lines)
    
    @staticmethod
    def save(session: SessionIndex, actions: List[str] = None) -> Path:
        date_dir = ARCHIVE_DIR / session.date
        date_dir.mkdir(parents=True, exist_ok=True)
        
        digest_path = date_dir / f"{session.session_id}_digest.md"
        digest_path.write_text(SessionDigest.generate(session, actions), encoding='utf-8')
        
        raw_path = date_dir / f"{session.session_id}_raw.jsonl"
        return digest_path, raw_path


def quick_lookup(query: str = "", tag: str = "", limit: int = 10):
    """Quick session lookup for CLI"""
    manager = SessionIndexManager()
    
    if tag:
        sessions = manager.get_by_tag(tag)
    elif query:
        sessions = manager.search(query)
    else:
        sessions = manager.get_recent(limit)
    
    if not sessions:
        print("No sessions found.")
        return
    
    print()
    print("=== SESSION LOOKUP ===")
    print()
    
    for s in sessions[:limit]:
        print(f"[{s.date}] {s.session_id}")
        print(f"  Tags: [{'] ['.join(s.tags)}]")
        print(f"  {s.summary[:80]}...")
        if s.learnings:
            print(f"  Learnings: {s.learnings[0][:60]}...")
        print()


def show_session(session_id: str = None):
    """Show full session digest"""
    manager = SessionIndexManager()
    
    if session_id:
        sessions = [s for s in manager.sessions if s.session_id == session_id]
    else:
        sessions = manager.get_recent(1)
    
    if not sessions:
        print("Session not found.")
        return
    
    session = sessions[0]
    print()
    print("=" * 60)
    print(f"  SESSION: {session.session_id}")
    print("=" * 60)
    print()
    print(f"Date: {session.date}")
    print(f"Duration: ~{session.duration_minutes} min")
    print(f"Tags: [{'] ['.join(session.tags)}]")
    print()
    print("## Summary")
    print(session.summary)
    print()
    
    if session.key_actions:
        print("## Key Actions")
        for a in session.key_actions[:10]:
            print(f"  - {a}")
        print()
    
    if session.learnings:
        print("## Learnings")
        for l in session.learnings[:5]:
            print(f"  - {l}")
        print()
    
    if session.decisions:
        print("## Decisions")
        for d in session.decisions[:5]:
            print(f"  - {d}")
        print()
    
    print(f"Messages: {session.message_count}, Errors: {session.error_count}")
    print()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('query', nargs='*', help='Search query')
    parser.add_argument('--tag', help='Filter by tag')
    parser.add_argument('--session', help='Show specific session')
    parser.add_argument('--tags', action='store_true', help='Show all tags')
    args = parser.parse_args()
    
    if args.tags:
        manager = SessionIndexManager()
        tags = manager.get_tags()
        print("Tags:")
        for tag, count in sorted(tags.items(), key=lambda x: -x[1]):
            print(f"  {tag}: {count}")
    elif args.session:
        show_session(args.session)
    elif args.query:
        quick_lookup(' '.join(args.query), args.tag)
    elif args.tag:
        quick_lookup(tag=args.tag)
    else:
        quick_lookup()
