"""
Smart Log System v2 - Integrated with Skeptical Chronicle
=======================================================

Flow:
  1. Log everything to raw (session_logger does this)
  2. Auto-detect significant events → chronicle entry (with skepticism)
  3. Learn tags dynamically from content
  4. Track verification status
  5. Auto-summarize sessions (only if meaningful)

Usage:
    from smart_log import log, milestone, decision, failure
    from smart_log import summarize, show_summary, search
    
    log("Implemented feature X")           # Auto-chronicles if significant
    decision("Chose Y over Z", ...)          # Auto-chronicles
    failure("Bug in X", fix="Changed Y")    # Auto-chronicles
    
    summarize()                              # Auto-summarize if meaningful
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict, field
from collections import defaultdict

BASE_DIR = Path(r"E:\AI-Setup")
ARCHIVE_DIR = BASE_DIR / "sessions"
CHRONICLE_DIR = BASE_DIR / "chronicles"
LOG_FILE = BASE_DIR / "session_logs" / "session_all.jsonl"
BACKUP_LOG = BASE_DIR / "session_logs" / "backup_session_all.jsonl"

ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
CHRONICLE_DIR.mkdir(parents=True, exist_ok=True)

INDEX_FILE = ARCHIVE_DIR / "index.json"

SIGNIFICANCE_THRESHOLD = 3
NOISE_PATTERNS = ["session_continu", "logger_startup", "logger_shutdown", "ping", "heartbeat"]


@dataclass
class SessionEntry:
    """Log entry"""
    timestamp: str
    type: str
    content: str
    action_type: str = "working"  # analyzing, planning, coding, etc.
    intent: str = ""  # WHY we're doing this
    efficacy: str = ""  # DID IT WORK? (success, failure, partial)
    tags: List[str] = field(default_factory=list)
    sequence: int = 0
    session: str = ""


@dataclass  
class SessionDigest:
    """Auto-generated session summary"""
    session_id: str
    date: str
    started_at: str
    ended_at: str
    duration_min: int
    tags: List[str]
    summary: str
    actions: List[str] = field(default_factory=list)
    learnings: List[str] = field(default_factory=list)
    action_types: Dict[str, int] = field(default_factory=dict)  # coding: 5, testing: 3, etc.
    efficacy: Dict[str, int] = field(default_factory=dict)  # success: 5, failure: 1, etc.
    chronicles_created: int = 0


# ============ INTEGRATION WITH CHRONICLE ============

SIGNIFICANT_PATTERNS = {
    "milestone_claim": ["completed", "finished", "done", "implemented", "deployed"],
    "milestone_verified": ["tested", "verified", "confirmed", "working", "functional"],
    "decision": ["decided", "chose", "selected", "adopted"],
    "failure": ["failed", "error", "crash", "broke", "exception"]
}

# Action type patterns for filtering
ACTION_TYPES = {
    "analyzing": ["analyzing", "analysis", "assessing", "evaluating", "examining", "reviewing", "inspecting", "exploring"],
    "planning": ["planning", "designing", "architecting", "outlining", "drafting", "mapping out", "preparing"],
    "researching": ["research", "searching", "investigating", "looking up", "finding", "discovering", "exploring"],
    "coding": ["implementing", "coding", "writing", "creating", "building", "developing", "refactoring", "modifying"],
    "testing": ["testing", "tested", "verifying", "validating", "checking", "running", "debugging", "troubleshooting"],
    "deploying": ["deploying", "deploy", "releasing", "shipping", "launching", "publishing", "pushing"],
    "documenting": ["documenting", "documented", "writing docs", "commenting", "annotating", "describing"],
    "learning": ["learning", "learned", "discovered", "figured out", "understood", "gained context"],
    "fixing": ["fixing", "fixed", "bug fix", "patching", "repairing", "correcting", "resolving"],
    "configuring": ["configuring", "configured", "setting up", "installing", "initializing", "bootstrapping"],
    "communicating": ["asking", "telling", "explaining", "summarizing", "sharing", "presenting", "reporting"],
}

# Extract action type from content
def detect_action_type(content: str) -> List[str]:
    """Detect action types from content"""
    content_lower = content.lower()
    detected = []
    for action_type, patterns in ACTION_TYPES.items():
        if any(p in content_lower for p in patterns):
            detected.append(action_type)
    return detected if detected else ["working"]

STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "was", "are", "were", "been",
    "be", "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "must", "shall", "can", "need", "it", "its",
    "this", "that", "these", "those", "i", "we", "you", "he", "she", "they",
    "what", "which", "who", "when", "where", "why", "how", "all", "each",
    "every", "both", "few", "more", "most", "other", "some", "such", "no",
    "not", "only", "same", "so", "than", "too", "very", "just", "now",
    "new", "use", "using", "used", "get", "got", "make", "made",
    "created", "added", "done", "fixed", "tested", "over", "works",
    "file", "files", "path", "code", "data", "value", "class",
    "error", "type", "name", "text", "content", "result"
}

TAG_VOCAB_FILE = CHRONICLE_DIR / "tag_vocabulary.json"
MILESTONES_FILE = CHRONICLE_DIR / "milestones.json"
ADRS_FILE = CHRONICLE_DIR / "adrs.json"
FAILURES_FILE = CHRONICLE_DIR / "failures.json"


class TagVocab:
    """Dynamic tag vocabulary"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load()
        return cls._instance
    
    def _load(self):
        self.vocab: Dict[str, int] = {}
        if TAG_VOCAB_FILE.exists():
            try:
                with open(TAG_VOCAB_FILE, 'r') as f:
                    self.vocab = json.load(f)
            except:
                self.vocab = {}
        self._seed()
    
    def _seed(self):
        known = ["vision", "infrastructure", "learning", "architecture", "setup",
                  "debugging", "automation", "multi-agent", "documentation", "logging",
                  "redis", "mcp", "ocr", "frontend", "florence", "comfyui", "directml"]
        for t in known:
            if t not in self.vocab:
                self.vocab[t] = 1
    
    def _save(self):
        with open(TAG_VOCAB_FILE, 'w') as f:
            json.dump(self.vocab, f, indent=2)
    
    def extract(self, text: str) -> List[str]:
        words = re.findall(r'\b[a-z][a-z0-9_-]+\b', text.lower())
        return [w for w in words if len(w) >= 3 and w not in STOP_WORDS and not w.isdigit()]
    
    def learn(self, text: str):
        for tag in self.extract(text):
            self.vocab[tag] = self.vocab.get(tag, 0) + 1
        self._save()
    
    def match(self, text: str) -> List[str]:
        tags = self.extract(text)
        return [t for t in tags if self.vocab.get(t, 0) >= 1]
    
    def suggest(self, text: str) -> Dict[str, List[str]]:
        tags = self.extract(text)
        known = [t for t in tags if self.vocab.get(t, 0) >= 1]
        potential = [t for t in tags if t not in known]
        potential.sort(key=lambda t: -self.vocab.get(t, 0))
        return {"known": known, "potential": potential[:5]}


class ChronicleEntry:
    """Chronicle entry"""
    def __init__(self, **kwargs):
        self.id = kwargs.get('id', '')
        self.type = kwargs.get('type', '')
        self.title = kwargs.get('title', '')
        self.content = kwargs.get('content', '')
        self.timestamp = kwargs.get('timestamp', '')
        self.status = kwargs.get('status', 'alpha')
        self.confidence = kwargs.get('confidence', 0.5)
        self.verified = kwargs.get('verified', False)
        self.tags = kwargs.get('tags', [])
        self.evidence = kwargs.get('evidence', [])
    
    def to_dict(self):
        return {
            "id": self.id,
            "type": self.type,
            "title": self.title,
            "content": self.content,
            "timestamp": self.timestamp,
            "status": self.status,
            "confidence": self.confidence,
            "verified": self.verified,
            "tags": self.tags,
            "evidence": self.evidence
        }


class SmartLog:
    """
    Smart logging with skeptical auto-chronicle
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance
    
    def _init(self):
        self.entries: List[SessionEntry] = []
        self.sequence = 0
        self.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.started_at = datetime.now().isoformat()
        self._tag_counts = defaultdict(int)
        self._chronicles_created = 0
        self._vocab = TagVocab()
        
        self._connect_redis()
    
    def _connect_redis(self):
        try:
            import redis
            self._redis = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True, socket_connect_timeout=2)
            self._redis.ping()
            self._redis_available = True
        except:
            self._redis = None
            self._redis_available = False
    
    def _gen_id(self, prefix: str) -> str:
        return f"{prefix}_{datetime.now().strftime('%m%d%H%M%S')}"
    
    def _write_entry(self, entry: SessionEntry):
        """Write entry to all destinations"""
        entry_json = json.dumps({
            "timestamp": entry.timestamp,
            "type": entry.type,
            "action_type": entry.action_type,
            "content": entry.content,
            "intent": entry.intent,
            "efficacy": entry.efficacy,
            "tags": entry.tags,
            "sequence": entry.sequence,
            "session": self.session_id
        })
        
        for path in [LOG_FILE, BACKUP_LOG]:
            try:
                with open(path, 'a', encoding='utf-8') as f:
                    f.write(entry_json + '\n')
            except:
                pass
        
        if self._redis_available:
            try:
                self._redis.rpush(f"session:{self.session_id}:log", entry_json)
            except:
                pass
    
    def _auto_tag(self, content: str) -> List[str]:
        suggested = self._vocab.suggest(content)
        for tag in suggested["known"]:
            self._tag_counts[tag] += 1
        return suggested["known"]
    
    def _detect_chronicle_type(self, content: str) -> Optional[str]:
        """Detect if this should create a chronicle entry"""
        content_lower = content.lower()
        
        for type_, patterns in SIGNIFICANT_PATTERNS.items():
            if any(p in content_lower for p in patterns):
                if type_ == "failure":
                    return "failure"
                return "milestone"
        
        return None
    
    def _auto_chronicle(self, entry: SessionEntry):
        """Auto-create chronicle entry if significant"""
        chronicle_type = self._detect_chronicle_type(entry.content)
        if not chronicle_type:
            return
        
        self._vocab.learn(entry.content)
        
        # Determine status based on claims
        content_lower = entry.content.lower()
        
        if any(p in content_lower for p in SIGNIFICANT_PATTERNS["milestone_verified"]):
            status, confidence = "beta", 0.8
        elif any(p in content_lower for p in SIGNIFICANT_PATTERNS["milestone_claim"]):
            status, confidence = "claimed", 0.4  # Skeptical!
        elif chronicle_type == "failure":
            status, confidence = "open", 0.7
        else:
            status, confidence = "alpha", 0.5
        
        # Extract title
        title = entry.content
        if ":" in entry.content:
            parts = entry.content.split(":", 1)
            title = parts[1].strip() if len(parts[1].strip()) > 3 else parts[0]
        title = title[:80]
        
        chronicle_entry = ChronicleEntry(
            id=self._gen_id(chronicle_type[:3].upper()),
            type=chronicle_type,
            title=title,
            content=entry.content,
            timestamp=datetime.now().isoformat(),
            status=status,
            confidence=confidence,
            verified=False,
            tags=entry.tags,
            evidence=[]
        )
        
        # Save to appropriate chronicle file
        file_map = {
            "milestone": MILESTONES_FILE,
            "failure": FAILURES_FILE
        }
        
        file_path = file_map.get(chronicle_type)
        if file_path:
            entries = []
            if file_path.exists():
                try:
                    with open(file_path, 'r') as f:
                        entries = json.load(f)
                except:
                    pass
            
            entries.insert(0, chronicle_entry.to_dict())
            
            with open(file_path, 'w') as f:
                json.dump(entries, f, indent=2)
        
        self._chronicles_created += 1
    
    def log(self, type_: str, content: str, tags: List[str] = None, 
             intent: str = "", efficacy: str = ""):
        """Log an entry - auto-chronicles if significant"""
        self.sequence += 1
        
        action_type = detect_action_type(content)[0] if type_ == "action" else "working"
        
        entry = SessionEntry(
            timestamp=datetime.now().isoformat(),
            type=type_,
            content=content[:200],
            action_type=action_type,
            intent=intent,
            efficacy=efficacy,
            tags=tags or self._auto_tag(content),
            sequence=self.sequence,
            session=self.session_id
        )
        
        self.entries.append(entry)
        self._write_entry(entry)
        self._auto_chronicle(entry)
    
    def action(self, content: str, tags: List[str] = None, intent: str = "", 
               efficacy: str = ""):
        """
        Log an action with optional intent and efficacy tracking.
        
        Args:
            content: What was done
            intent: Why we did it (goal/purpose)
            efficacy: Did it work? (success, failure, partial, unknown)
        """
        self.log("action", content, tags, intent, efficacy)
    
    def error(self, content: str, tags: List[str] = None, intent: str = ""):
        self.log("error", content, tags, intent, "failure")
    
    def success(self, content: str, tags: List[str] = None, intent: str = ""):
        """Log a successful action"""
        self.log("success", content, tags, intent, "success")
    
    def partial(self, content: str, tags: List[str] = None, intent: str = ""):
        """Log a partially successful action"""
        self.log("partial", content, tags, intent, "partial")
    
    def decision(self, title: str, rationale: List[str] = None, tags: List[str] = None):
        """Record a decision - auto-chronicles"""
        content = title
        if rationale:
            content += f" (Because: {', '.join(rationale[:2])})"
        
        self.log("decision", content, tags or ["learning"])
        
        # Create ADR
        self._vocab.learn(title)
        adr_entry = ChronicleEntry(
            id=self._gen_id("ADR"),
            type="decision",
            title=title[:80],
            content=content,
            timestamp=datetime.now().isoformat(),
            status="accepted",
            confidence=0.7,
            verified=False,
            tags=self._vocab.match(title),
            evidence=[]
        )
        
        entries = []
        if ADRS_FILE.exists():
            try:
                with open(ADRS_FILE, 'r') as f:
                    entries = json.load(f)
            except:
                pass
        
        entries.insert(0, adr_entry.to_dict())
        with open(ADRS_FILE, 'w') as f:
            json.dump(entries, f, indent=2)
        
        self._chronicles_created += 1
    
    def failure(self, symptom: str, fix: str = "", learnings: List[str] = None):
        """Record a failure"""
        content = symptom
        if fix:
            content += f" | Fix: {fix}"
        if learnings:
            content += f" | Learnings: {', '.join(learnings)}"
        
        self.log("failure", content, ["debugging"])
        
        fl_entry = ChronicleEntry(
            id=self._gen_id("FL"),
            type="failure",
            title=symptom[:80],
            content=content,
            timestamp=datetime.now().isoformat(),
            status="resolved" if fix else "open",
            confidence=0.8,
            verified=True,
            tags=self._vocab.match(symptom),
            evidence=[fix] if fix else []
        )
        
        entries = []
        if FAILURES_FILE.exists():
            try:
                with open(FAILURES_FILE, 'r') as f:
                    entries = json.load(f)
            except:
                pass
        
        entries.insert(0, fl_entry.to_dict())
        with open(FAILURES_FILE, 'w') as f:
            json.dump(entries, f, indent=2)
        
        self._chronicles_created += 1
    
    def _is_significant(self, entry: SessionEntry) -> bool:
        """Check if entry is significant"""
        if any(p in entry.content.lower() for p in NOISE_PATTERNS):
            return False
        significant = ["created", "completed", "implemented", "fixed", "designed", "decided",
                      "discovered", "learned", "deployed", "established", "verified"]
        return any(p in entry.content.lower() for p in significant) or entry.type in ["decision", "failure"]
    
    def _should_summarize(self) -> bool:
        """Should we create a session digest?"""
        meaningful = [e for e in self.entries if self._is_significant(e)]
        return len(meaningful) >= SIGNIFICANCE_THRESHOLD
    
    def summarize(self) -> Optional[SessionDigest]:
        """Auto-summarize session if meaningful"""
        if not self._should_summarize():
            print(f"[SmartLog] Trivial session ({len(self.entries)} entries) - no digest")
            return None
        
        now = datetime.now()
        
        # Collect significant actions
        significant = [e for e in self.entries if self._is_significant(e)]
        actions = [e.content for e in significant if e.type in ["action", "success", "partial"]][:8]
        
        learnings = [e.content for e in self.entries if e.type == "decision"][:3]
        
        # Action type breakdown
        action_types = defaultdict(int)
        for e in self.entries:
            if e.action_type:
                action_types[e.action_type] += 1
        
        # Efficacy breakdown
        efficacy = defaultdict(int)
        for e in self.entries:
            if e.efficacy:
                efficacy[e.efficacy] += 1
        
        top_tags = sorted(self._tag_counts.items(), key=lambda x: -x[1])[:5]
        tags = [t for t, _ in top_tags if t != "general"] or ["general"]
        
        summary_parts = []
        if actions:
            summary_parts.append(f"Actions: {', '.join(actions[:2])}")
        if efficacy:
            success_count = efficacy.get("success", 0)
            fail_count = efficacy.get("failure", 0)
            if success_count or fail_count:
                summary_parts.append(f"Result: {success_count} success, {fail_count} failure")
        if self._chronicles_created:
            summary_parts.append(f"{self._chronicles_created} chronicles")
        
        summary = " | ".join(summary_parts) if summary_parts else f"{len(self.entries)} entries"
        
        digest = SessionDigest(
            session_id=self.session_id,
            date=now.strftime('%Y-%m-%d'),
            started_at=self.started_at,
            ended_at=now.isoformat(),
            duration_min=max(1, int((now - datetime.fromisoformat(self.started_at)).total_seconds() / 60)),
            tags=tags,
            summary=summary,
            actions=actions,
            learnings=learnings,
            action_types=dict(action_types),
            efficacy=dict(efficacy),
            chronicles_created=self._chronicles_created
        )
        
        self._save_digest(digest)
        print(f"[SmartLog] Digest: {summary[:60]}...")
        
        return digest
    
    def _save_digest(self, digest: SessionDigest):
        """Save digest"""
        date_dir = ARCHIVE_DIR / digest.date
        date_dir.mkdir(parents=True, exist_ok=True)
        
        # Build action type summary
        type_summary = []
        for atype, count in sorted(digest.action_types.items(), key=lambda x: -x[1]):
            type_summary.append(f"{atype}: {count}")
        
        # Build efficacy summary
        eff_summary = []
        for status, count in sorted(digest.efficacy.items(), key=lambda x: -x[1]):
            eff_summary.append(f"{status}: {count}")
        
        lines = [
            f"# Session {digest.session_id}",
            "",
            f"**Date**: {digest.date}",
            f"**Duration**: ~{digest.duration_min} min",
            f"**Tags**: [{'] ['.join(digest.tags)}]",
            "",
            "## Summary",
            digest.summary,
            "",
            "## Action Types",
            " | ".join(type_summary) if type_summary else "N/A",
            "",
            "## Efficacy",
            " | ".join(eff_summary) if eff_summary else "N/A",
            "",
        ]
        
        if digest.actions:
            key_actions = []
            for e in self.entries:
                if e.type in ["action", "success", "partial"] and e.content in digest.actions:
                    key_actions.append(f"- [{e.action_type}] {e.content}")
            lines.extend(["## Key Actions"] + key_actions[:8] + [""])
        
        if digest.learnings:
            lines.extend(["## Decisions"] + [f"- {l}" for l in digest.learnings] + [""])
        
        lines.extend(["---", f"*Generated: {datetime.now().isoformat()}*"])
        
        digest_file = date_dir / f"{digest.session_id}_digest.md"
        digest_file.write_text("\n".join(lines), encoding='utf-8')
        
        # Update index
        index = []
        if INDEX_FILE.exists():
            try:
                with open(INDEX_FILE, 'r') as f:
                    index = json.load(f)
            except:
                pass
        
        index.insert(0, asdict(digest))
        with open(INDEX_FILE, 'w') as f:
            json.dump(index, f, indent=2)


_smart_log: Optional[SmartLog] = None

def get_smart_log() -> SmartLog:
    global _smart_log
    if _smart_log is None:
        _smart_log = SmartLog()
    return _smart_log

def log(content: str, tags: List[str] = None):
    get_smart_log().action(content, tags)

def decision(title: str, rationale: List[str] = None, tags: List[str] = None):
    get_smart_log().decision(title, rationale, tags)

def failure(symptom: str, fix: str = "", learnings: List[str] = None):
    get_smart_log().failure(symptom, fix, learnings)

def summarize():
    return get_smart_log().summarize()


# ============ CLI ============

def cmd_summary():
    """Show recent sessions"""
    if not INDEX_FILE.exists():
        print("No sessions archived.")
        return
    
    with open(INDEX_FILE, 'r') as f:
        sessions = json.load(f)
    
    print()
    print("=== RECENT SESSIONS ===")
    for s in sessions[:10]:
        chronicles = s.get('chronicles_created', 0)
        c_marker = f" [+{chronicles}]" if chronicles else ""
        print(f"[{s['date']}] {s['session_id']}{c_marker}")
        print(f"  Tags: [{'] ['.join(s.get('tags', ['general'])[:3])}]")
        print(f"  {s.get('summary', '')[:70]}...")
        print()

def cmd_chronicles():
    """Show chronicle summary"""
    print()
    print("=== CHRONICLES ===")
    print()
    
    for file_path, label in [(MILESTONES_FILE, "Milestones"), (ADRS_FILE, "Decisions"), (FAILURES_FILE, "Failures")]:
        if file_path.exists():
            with open(file_path, 'r') as f:
                entries = json.load(f)
            print(f"{label} ({len(entries)}):")
            for e in entries[:5]:
                status = {"claimed": "?", "prototype": "P", "alpha": "A", "beta": "B", "verified": "✓"}.get(e.get('status', ''), "")
                print(f"  [{status}] {e.get('title', '')[:50]}")
            print()

def cmd_tags():
    """Show learned tags"""
    vocab = TagVocab()
    print()
    print("=== LEARNED TAGS ===")
    print()
    sorted_tags = sorted(vocab.vocab.items(), key=lambda x: -x[1])[:30]
    for tag, count in sorted_tags:
        print(f"  {tag:20} {count}")

def cmd_search(query: str):
    """Search"""
    results = []
    
    if INDEX_FILE.exists():
        with open(INDEX_FILE, 'r') as f:
            for s in json.load(f):
                if query.lower() in s.get('summary', '').lower():
                    results.append(("session", s))
    
    for file_path in [MILESTONES_FILE, ADRS_FILE, FAILURES_FILE]:
        if file_path.exists():
            with open(file_path, 'r') as f:
                for e in json.load(f):
                    if query.lower() in e.get('title', '').lower():
                        results.append(("chronicle", e))
    
    print()
    print(f"=== SEARCH: '{query}' ({len(results)} results) ===")
    for type_, item in results[:15]:
        if type_ == "session":
            print(f"  [SESSION] {item.get('summary', '')[:60]}...")
        else:
            print(f"  [{type_.upper()}] {item.get('title', '')[:50]}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('cmd', nargs='?', choices=['summary', 'chronicles', 'tags', 'search', 'test'])
    parser.add_argument('query', nargs='*')
    args = parser.parse_args()
    
    if args.cmd == 'summary':
        cmd_summary()
    elif args.cmd == 'chronicles':
        cmd_chronicles()
    elif args.cmd == 'tags':
        cmd_tags()
    elif args.cmd == 'search' and args.query:
        cmd_search(' '.join(args.query))
    elif args.cmd == 'test':
        sl = get_smart_log()
        sl.action("Created vision engine")
        sl.action("Completed Redis backup")
        sl.action("Tested implementation")
        sl.decision("Use Redis", rationale=["Fast"])
        sl.summarize()
    else:
        cmd_summary()
