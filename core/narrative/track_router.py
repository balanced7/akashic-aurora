"""
TrackRouter (Slice 2, Tier 0 heuristic) -- infer which domain Track a Beat belongs to,
from cheap signals, and detect when the domain switches. No ML.

Semantic Relationship: Beat routed_to Track (inferred from context)

Inference priority (strongest signal first):
    1. paths      -- a commit's touched files map to a track (core/* -> ai-setup, ...)
    2. strong kw  -- domain product names in task/summary (stemroller, florence, gemma ...)
    3. category   -- a learning/decision category (research -> research, system cats -> ai-setup)
    4. generic kw -- weaker topic words (raptor -> research, store/redis -> ai-setup)
    5. persist    -- no signal: keep the active track (a domain switch needs a reason)

Tier 1 (embeddings via the Ranker relevance_fn seam) is a later slice and must BEAT this
baseline on the fixture (ARI) or it doesn't ship.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

# --- path prefix/substring -> track (domain repos before the ai-setup system itself) ---
PATH_RULES: List[Tuple[str, str]] = [
    ("stemroller", "stemroller"), ("demucs", "stemroller"),
    ("comfyui", "vision"), ("models/vision", "vision"), ("vision_engine", "vision"),
    ("vision_scan", "vision"), ("florence", "vision"),
    ("gemma", "voice"), ("realtime", "voice"),
    ("core/", "ai-setup"), ("context/", "ai-setup"), ("agent", "ai-setup"),
    ("scripts/", "ai-setup"), ("tests/", "ai-setup"), ("docs/", "ai-setup"),
    ("chronicles", "ai-setup"), ("bootstrap", "ai-setup"), ("config", "ai-setup"),
]

# --- strong domain keywords (product/domain names) -> track (beat the category) ---
STRONG_KEYWORDS: List[Tuple[Tuple[str, ...], str]] = [
    (("stemroller", "demucs", "zluda", "stem separation", "vocals"), "stemroller"),
    (("florence", "comfyui", "comfy", "ocr", "directml"), "vision"),
    (("gemma", "whisper", "kokoro", "tts", "voice chat", "realtime voice"), "voice"),
]

# --- category -> track ---
CATEGORY_RULES = {"research": "research", "knowledge_representation": "research"}
AI_SETUP_CATEGORIES = {
    "refactoring_methodology", "project_management", "code_readability", "code_patterns",
    "documentation", "testing", "verification", "infrastructure", "code",
}

# --- generic topic keywords (weaker than category) -> track ---
GENERIC_KEYWORDS: List[Tuple[Tuple[str, ...], str]] = [
    (("raptor", "graphrag", "prior art", "prior-art", "zettelkasten", "arxiv",
      "disentanglement", "paper", "zep"), "research"),
    (("store", "ledger", "redis", "bootstrap", "agent_cli", "narrative", "harmoniz",
      "context pillar", "knowledge store", "snapshot"), "ai-setup"),
]

UNKNOWN_TRACK = "unknown"


@dataclass
class RouteHint:
    paths: List[str] = field(default_factory=list)   # commit touched files
    category: str = ""                               # learning/decision category
    task: str = ""                                   # the agent's active task keyword


@dataclass
class RouteResult:
    track: str
    switched: bool        # did the domain switch at this beat?
    active: str           # active track AFTER this beat (carry into the next)
    basis: str            # which rule decided: path|strong|category|generic|persist|unknown


class TrackRouter:
    def __init__(self, path_rules=PATH_RULES, strong=STRONG_KEYWORDS,
                 category_rules=CATEGORY_RULES, generic=GENERIC_KEYWORDS):
        self.path_rules = path_rules
        self.strong = strong
        self.category_rules = category_rules
        self.generic = generic

    def _infer(self, beat, hint: RouteHint) -> Tuple[Optional[str], str]:
        # 1. paths
        for p in hint.paths or []:
            pl = str(p).lower()
            for needle, track in self.path_rules:
                if needle in pl:
                    return track, "path"
        text = f"{hint.task} {getattr(beat, 'summary', '')} {getattr(beat, 'source', '')}".lower()
        # 2. strong domain keywords
        for kws, track in self.strong:
            if any(kw in text for kw in kws):
                return track, "strong"
        # 3. category
        c = (hint.category or "").lower()
        if c in self.category_rules:
            return self.category_rules[c], "category"
        if c in AI_SETUP_CATEGORIES:
            return "ai-setup", "category"
        # 4. generic keywords
        for kws, track in self.generic:
            if any(kw in text for kw in kws):
                return track, "generic"
        return None, "persist"

    def route_one(self, beat, hint: Optional[RouteHint] = None,
                  active: Optional[str] = None) -> RouteResult:
        inferred, basis = self._infer(beat, hint or RouteHint())
        if inferred is None:
            track = active or UNKNOWN_TRACK
            return RouteResult(track, False, track, "persist" if active else "unknown")
        switched = active is not None and inferred != active
        return RouteResult(inferred, switched, inferred, basis)

    @staticmethod
    def _smooth(tracks: List[str]) -> List[str]:
        """1-beat median filter: a lone beat differing from two agreeing neighbours is
        noise, not a domain switch -> relabel to the neighbours (segmentation smoothing).
        Removes the spurious double-switch a single ambiguous beat would otherwise cause."""
        t = list(tracks)
        for i in range(1, len(t) - 1):
            if t[i] != t[i - 1] and t[i - 1] == t[i + 1]:
                t[i] = t[i - 1]
        return t

    def route_sequence(self, items, active: Optional[str] = None,
                       smooth: bool = True) -> List[RouteResult]:
        """items: iterable of (beat, hint). Returns a RouteResult per item, threading
        the active track through (domain persistence). `smooth=True` applies the
        isolated-blip filter -- this is how the Chronicler routes a window in batch
        (online `route_one` gives a provisional track, refined here)."""
        raw = []
        a = active
        for beat, hint in items:
            r = self.route_one(beat, hint, a)
            a = r.active
            raw.append(r)
        tracks = self._smooth([r.track for r in raw]) if smooth else [r.track for r in raw]
        out, prev = [], active
        for i, r in enumerate(raw):
            tk = tracks[i]
            out.append(RouteResult(tk, prev is not None and tk != prev, tk, r.basis))
            prev = tk
        return out


_INSTANCE: Optional[TrackRouter] = None


def get_track_router() -> TrackRouter:
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = TrackRouter()
    return _INSTANCE
