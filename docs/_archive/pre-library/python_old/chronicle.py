"""
Chronicle System v2 - Skeptical Auto-Chronicle with Dynamic Tags
============================================================

Core Philosophy:
- AUTO-CHRONICLE significant events (detected by patterns)
- BE SKEPTICAL of completion claims ("complete", "solved", "finished")
- REQUIRE VERIFICATION for milestone claims
- LEARN tags dynamically from context
- Track status progression: prototype → alpha → beta → stable → production

Status Levels:
  - prototype: Initial implementation, likely incomplete
  - alpha: Basic functionality works, untested
  - beta: Tested, known issues
  - stable: Production-ready
  - verified: Independently verified

Auto-Detection Logic:
  "created X" / "implemented X" → chronicle entry with status=prototype
  "completed X" / "finished X" → chronicle entry with status=claimed
  "tested X" / "verified X" / "deployed X" → upgrade status if exists
  "failed X" / "error" → auto-chronicle as failure
  "decided X" / "chose X" → auto-chronicle as ADR

Dynamic Tags:
  - Extract keywords from content
  - Learn new tags based on frequency
  - Store in: chronicles/tag_vocabulary.json
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, asdict, field
from collections import defaultdict

BASE_DIR = Path(r"E:\AI-Setup")
CHRONICLE_DIR = BASE_DIR / "chronicles"
CHRONICLE_DIR.mkdir(parents=True, exist_ok=True)

# Files
MILESTONES_FILE = CHRONICLE_DIR / "milestones.json"
ADRS_FILE = CHRONICLE_DIR / "adrs.json"
FAILURES_FILE = CHRONICLE_DIR / "failures.json"
NARRATIVES_FILE = CHRONICLE_DIR / "narratives.json"
TAG_VOCAB_FILE = CHRONICLE_DIR / "tag_vocabulary.json"
INDEX_FILE = CHRONICLE_DIR / "index.json"


@dataclass
class ChronicleEntry:
    """Base chronicle entry"""
    id: str
    type: str  # milestone, decision, failure
    title: str
    content: str
    timestamp: str
    status: str  # See STATUS_LEVELS
    confidence: float  # 0-1, how confident this is accurate
    verified: bool  # Independently verified?
    tags: List[str] = field(default_factory=list)
    related: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)  # Proof of completion
    superseded_by: str = ""  # If replaced by better solution


STATUS_LEVELS = ["prototype", "alpha", "beta", "stable", "production"]
STATUS_PRIORITY = {s: i for i, s in enumerate(STATUS_LEVELS)}


# ============ AUTO-DETECTION PATTERNS ============

PATTERNS = {
    "milestone_claim": [
        "completed", "finished", "done", "implemented", "deployed",
        "established", "launched", "released", "shipped", "built"
    ],
    "milestone_verified": [
        "tested", "verified", "confirmed", "validated", "passed",
        "working", "functional", "production", "live", "live:"
    ],
    "decision": [
        "decided", "chose", "selected", "adopted", "opted",
        "going with", "using", "based on"
    ],
    "failure": [
        "failed", "error", "crash", "broke", "issue", "bug",
        "problem", "exception", "timeout", "refused"
    ],
    "progress": [
        "created", "started", "began", "initiated", "prototyped",
        "drafted", "outlined", "designed"
    ]
}

# Common words to filter from tag extraction
STOP_WORDS = {
    # Basic
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "was", "are", "were", "been",
    "be", "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "must", "shall", "can", "need", "it", "its",
    "this", "that", "these", "those", "i", "we", "you", "he", "she", "they",
    "what", "which", "who", "when", "where", "why", "how", "all", "each",
    "every", "both", "few", "more", "most", "other", "some", "such", "no",
    "not", "only", "same", "so", "than", "too", "very", "just", "now",
    # Common action words
    "new", "use", "using", "used", "get", "got", "make", "made", "take", "took",
    "give", "gave", "see", "saw", "know", "knew", "think", "thought",
    "come", "came", "want", "wanted", "look", "looked", "use", "using",
    "try", "tried", "call", "called", "keep", "kept", "let", "put", "said",
    "seem", "seemed", "back", "even", "still", "well", "way", "well", "also",
    # Code common
    "file", "files", "path", "code", "data", "value", "class", "function",
    "method", "object", "result", "error", "type", "name", "text", "content",
    # Action words
    "created", "created", "implemented", "added", "done", "fixed", "tested",
    "completed", "over", "using", "works", "work", "working", "failed"
}


# ============ TAG VOCABULARY ============

class TagVocab:
    """Dynamic tag vocabulary that learns from context"""
    
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
        self._seed_initial_tags()
    
    def _seed_initial_tags(self):
        """Seed known good tags"""
        known = [
            "vision", "infrastructure", "learning", "architecture", "setup",
            "debugging", "automation", "multi-agent", "documentation",
            "fault-tolerance", "logging", "redis", "mcp", "ocr", "frontend"
        ]
        for tag in known:
            if tag not in self.vocab:
                self.vocab[tag] = 1
    
    def _save(self):
        with open(TAG_VOCAB_FILE, 'w') as f:
            json.dump(self.vocab, f, indent=2)
    
    def extract_tags(self, text: str) -> List[str]:
        """Extract potential new tags from text"""
        words = re.findall(r'\b[a-z][a-z0-9_-]+\b', text.lower())
        
        tags = []
        for word in words:
            if len(word) < 3 or word in STOP_WORDS:
                continue
            if word.isdigit():
                continue
            tags.append(word)
        
        return list(set(tags))
    
    def learn(self, text: str, count: int = 1):
        """Learn tags from text, incrementing counts"""
        tags = self.extract_tags(text)
        for tag in tags:
            self.vocab[tag] = self.vocab.get(tag, 0) + count
        self._save()
    
    def match(self, text: str, min_count: int = 1) -> List[str]:
        """Find known tags in text"""
        tags = self.extract_tags(text)
        return [t for t in tags if self.vocab.get(t, 0) >= min_count]
    
    def suggest(self, text: str) -> Dict[str, List[str]]:
        """Suggest tags for text: known + potential new"""
        known = self.match(text, min_count=1)
        all_tags = self.extract_tags(text)
        potential = [t for t in all_tags if t not in known]
        
        # Sort potential by their current count (higher = more likely useful)
        potential.sort(key=lambda t: -self.vocab.get(t, 0))
        
        return {
            "known": known,
            "potential_new": potential[:5]  # Top 5 candidates
        }
    
    def get_all(self, min_count: int = 1) -> List[str]:
        """Get all tags sorted by frequency"""
        return sorted(self.vocab.keys(), key=lambda t: -self.vocab.get(t, 0))


# ============ CHRONICLE SYSTEM ============

class Chronicle:
    """
    Skeptical Auto-Chronicle System
    
    Key behaviors:
    1. Auto-detects significant events from actions
    2. Is skeptical of completion claims (status=claimed)
    3. Requires verification to confirm milestones
    4. Learns tags dynamically
    5. Tracks status progression
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance
    
    def _init(self):
        self.entries: List[ChronicleEntry] = []
        self._load_all()
        self._tag_vocab = TagVocab()
    
    def _gen_id(self, prefix: str) -> str:
        ts = datetime.now().strftime("%m%d%H%M%S")
        return f"{prefix}_{ts}"
    
    def _load_json(self, path: Path, cls_type):
        items = []
        if path.exists():
            try:
                with open(path, 'r') as f:
                    for d in json.load(f):
                        items.append(cls_type(**d))
            except:
                pass
        return items
    
    def _save_json(self, path: Path, items: list):
        with open(path, 'w') as f:
            json.dump([asdict(i) for i in items], f, indent=2)
    
    def _load_all(self):
        self.entries = []
        self.entries.extend(self._load_json(MILESTONES_FILE, ChronicleEntry))
        self.entries.extend(self._load_json(ADRS_FILE, ChronicleEntry))
        self.entries.extend(self._load_json(FAILURES_FILE, ChronicleEntry))
    
    def _detect_entry_type(self, content: str) -> Optional[str]:
        """Detect what type of chronicle entry this should be"""
        content_lower = content.lower()
        
        for pattern_type, patterns in PATTERNS.items():
            if any(p in content_lower for p in patterns):
                if pattern_type == "failure":
                    return "failure"
                elif pattern_type in ["milestone_claim", "milestone_verified", "progress"]:
                    return "milestone"
                elif pattern_type == "decision":
                    return "decision"
        
        return None
    
    def _determine_status(self, content: str, entry_type: str) -> tuple:
        """Determine status and confidence based on claims"""
        content_lower = content.lower()
        
        # Check for verified/working claims
        if any(p in content_lower for p in PATTERNS["milestone_verified"]):
            return "beta", 0.8  # Reasonably confident
        
        # Check for completion claims
        if any(p in content_lower for p in PATTERNS["milestone_claim"]):
            # Be skeptical - completion claims need verification
            return "claimed", 0.4  # Low confidence until verified
        
        # Check for just started/implemented
        if any(p in content_lower for p in PATTERNS["progress"]):
            return "prototype", 0.6
        
        return "alpha", 0.5  # Default
    
    def _learn_tags_from_content(self, content: str):
        """Learn tags from content"""
        self._tag_vocab.learn(content)
    
    def auto_chronicle(self, action: str, source: str = "action") -> Optional[ChronicleEntry]:
        """
        Auto-create chronicle entry if action is significant.
        Returns the entry if created, None otherwise.
        """
        entry_type = self._detect_entry_type(action)
        if not entry_type:
            return None
        
        # Learn tags from content
        self._learn_tags_from_content(action)
        suggested_tags = self._tag_vocab.suggest(action)
        
        status, confidence = self._determine_status(action, entry_type)
        
        # Extract title (clean up the action)
        title = action
        if ":" in action:
            title = action.split(":", 1)[1].strip()
        title = title[:80]
        
        # Create entry
        entry = ChronicleEntry(
            id=self._gen_id(entry_type[:3].upper()),
            type=entry_type,
            title=title,
            content=action,
            timestamp=datetime.now().isoformat(),
            status=status,
            confidence=confidence,
            verified=False,
            tags=suggested_tags["known"],
            related=[source],
            evidence=[],
            superseded_by=""
        )
        
        # Set file path based on type
        file_map = {
            "milestone": MILESTONES_FILE,
            "decision": ADRS_FILE,
            "failure": FAILURES_FILE
        }
        
        file_path = file_map.get(entry_type)
        if file_path:
            self.entries.insert(0, entry)
            self._save_json(file_path, [e for e in self.entries if e.type == entry_type])
        
        return entry
    
    def verify(self, entry_id: str, evidence: List[str] = None) -> bool:
        """Verify a chronicle entry (increases confidence)"""
        for entry in self.entries:
            if entry.id == entry_id:
                entry.verified = True
                entry.confidence = min(1.0, entry.confidence + 0.3)
                entry.status = self._upgrade_status(entry.status)
                if evidence:
                    entry.evidence.extend(evidence)
                
                # Save to appropriate file
                file_map = {
                    "milestone": MILESTONES_FILE,
                    "decision": ADRS_FILE,
                    "failure": FAILURES_FILE
                }
                file_path = file_map.get(entry.type)
                if file_path:
                    self._save_json(file_path, [e for e in self.entries if e.type == entry.type])
                
                return True
        return False
    
    def _upgrade_status(self, status: str) -> str:
        """Upgrade status to next level"""
        idx = STATUS_LEVELS.index(status) if status in STATUS_LEVELS else 0
        return STATUS_LEVELS[min(idx + 1, len(STATUS_LEVELS) - 1)]
    
    def claim_complete(self, title: str, evidence: List[str] = None) -> str:
        """Manually claim something as complete (with skepticism)"""
        entry = ChronicleEntry(
            id=self._gen_id("MSC"),
            type="milestone",
            title=title,
            content=f"Claimed complete: {title}",
            timestamp=datetime.now().isoformat(),
            status="claimed",
            confidence=0.5,
            verified=False,
            tags=self._tag_vocab.match(title),
            evidence=evidence or [],
            superseded_by=""
        )
        
        self.entries.insert(0, entry)
        self._save_json(MILESTONES_FILE, [e for e in self.entries if e.type == "milestone"])
        
        return entry.id
    
    def record_failure(self, symptom: str, fix: str = "", learnings: List[str] = None) -> str:
        """Record a failure (auto-chronicles)"""
        content = symptom
        if fix:
            content += f"\nFix: {fix}"
        if learnings:
            content += f"\nLearnings: {', '.join(learnings)}"
        
        entry = ChronicleEntry(
            id=self._gen_id("FL"),
            type="failure",
            title=symptom[:80],
            content=content,
            timestamp=datetime.now().isoformat(),
            status="resolved" if fix else "open",
            confidence=0.8,
            verified=True,
            tags=self._tag_vocab.match(symptom + " " + fix),
            superseded_by=""
        )
        
        self.entries.insert(0, entry)
        self._save_json(FAILURES_FILE, [e for e in self.entries if e.type == "failure"])
        
        return entry.id
    
    def record_decision(self, title: str, rationale: str = "", alternatives: List[str] = None) -> str:
        """Record an architecture decision"""
        content = title
        if rationale:
            content += f"\nRationale: {rationale}"
        if alternatives:
            content += f"\nAlternatives considered: {', '.join(alternatives)}"
        
        entry = ChronicleEntry(
            id=self._gen_id("ADR"),
            type="decision",
            title=title[:80],
            content=content,
            timestamp=datetime.now().isoformat(),
            status="accepted",
            confidence=0.7,
            verified=False,
            tags=self._tag_vocab.match(title + " " + rationale),
            superseded_by=""
        )
        
        self.entries.insert(0, entry)
        self._save_json(ADRS_FILE, [e for e in self.entries if e.type == "decision"])
        
        return entry.id
    
    # ============ QUERY METHODS ============
    
    def get_all(self, type_: str = None) -> List[ChronicleEntry]:
        result = self.entries
        if type_:
            result = [e for e in result if e.type == type_]
        return result
    
    def get_unverified(self) -> List[ChronicleEntry]:
        """Get entries that need verification"""
        return [e for e in self.entries if not e.verified and e.type == "milestone"]
    
    def get_by_tag(self, tag: str) -> List[ChronicleEntry]:
        return [e for e in self.entries if tag in e.tags]
    
    def suggest_verification(self) -> List[Dict]:
        """Suggest entries that need verification"""
        suggestions = []
        for entry in self.entries:
            if entry.status == "claimed":
                suggestions.append({
                    "id": entry.id,
                    "title": entry.title,
                    "status": entry.status,
                    "confidence": entry.confidence,
                    "suggestion": "VERIFY: Was this actually completed? Provide evidence."
                })
        return suggestions
    
    def get_tag_vocabulary(self) -> Dict[str, int]:
        """Get learned tags"""
        return self._tag_vocab.vocab


_chronicle: Optional[Chronicle] = None

def get_chronicle() -> Chronicle:
    global _chronicle
    if _chronicle is None:
        _chronicle = Chronicle()
    return _chronicle


# ============ CLI ============

def show_chronicle(level: str = "all"):
    """Show chronicle entries"""
    c = get_chronicle()
    
    print()
    print("=" * 70)
    print("  SKEPTICAL CHRONICLE")
    print("=" * 70)
    
    # Unverified (needs attention)
    unverified = c.get_unverified()
    if unverified:
        print()
        print("[!] NEEDS VERIFICATION")
        print("-" * 40)
        for e in unverified[:5]:
            print(f"  [{e.id}] {e.title}")
            print(f"      Status: {e.status} | Confidence: {e.confidence:.0%}")
    
    # Milestones
    print()
    print("[MILESTONES]")
    print("-" * 40)
    for e in c.get_all("milestone")[:10]:
        verify_marker = "✓" if e.verified else "?"
        status_marker = {"claimed": "[?]", "prototype": "[P]", "alpha": "[A]", "beta": "[B]", "stable": "[S]", "production": "[!]"}.get(e.status, "[ ]")
        print(f"  {status_marker} {verify_marker} {e.title[:50]}")
    
    # Decisions
    print()
    print("[DECISIONS]")
    print("-" * 40)
    for e in c.get_all("decision")[:10]:
        print(f"  [ADR] {e.title[:50]}")
        if e.tags:
            print(f"       Tags: [{'] ['.join(e.tags[:3])}]")
    
    # Failures
    print()
    print("[FAILURES]")
    print("-" * 40)
    for e in c.get_all("failure")[:10]:
        status_marker = {"open": "[!]", "resolved": "[✓]"}.get(e.status, "[ ]")
        print(f"  {status_marker} {e.title[:50]}")
    
    # Tag vocabulary
    print()
    print("[LEARNED TAGS]")
    print("-" * 40)
    vocab = c.get_tag_vocabulary()
    top_tags = sorted(vocab.items(), key=lambda x: -x[1])[:20]
    print(f"  {', '.join(t for t, _ in top_tags)}")
    
    print()
    print("=" * 70)


def show_vocabulary():
    """Show learned tags"""
    c = get_chronicle()
    vocab = c.get_tag_vocabulary()
    
    print()
    print("=== LEARNED TAG VOCABULARY ===")
    print()
    
    sorted_tags = sorted(vocab.items(), key=lambda x: -x[1])
    for tag, count in sorted_tags:
        dots = "." * min(count, 20)
        print(f"  {tag:20} {count:3} {dots}")


def suggest_verification():
    """Show entries needing verification"""
    c = get_chronicle()
    suggestions = c.suggest_verification()
    
    print()
    print("=== ENTRIES NEEDING VERIFICATION ===")
    print()
    
    if not suggestions:
        print("  All milestones verified!")
    else:
        for s in suggestions:
            print(f"  [{s['id']}] {s['title']}")
            print(f"    {s['suggestion']}")
            print()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--level', choices=['all', 'milestones', 'decisions', 'failures'])
    parser.add_argument('--vocab', action='store_true', help='Show tag vocabulary')
    parser.add_argument('--verify', action='store_true', help='Show unverified entries')
    args = parser.parse_args()
    
    if args.vocab:
        show_vocabulary()
    elif args.verify:
        suggest_verification()
    else:
        show_chronicle(args.level)
