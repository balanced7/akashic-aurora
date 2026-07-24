"""
TagAuditor (Slice G2) -- detect likely mis-tags. FLAG-ONLY: it returns suspects and
NEVER mutates anything (invariant I6). Surfacing candidates feeds the active-learning
loop (a human/agent reviews, confirms a few -> those become permanent gold-fixture rows).

Detectors (cheap, available signals + a seam for the strong one):
  * low_confidence            -- current tag confidence < threshold (persist/generic/unknown).
  * inconsistent_with_neighbors -- a lone tag inside a temporal run whose neighbours agree
    (segmentation consistency; a single off-topic beat is probably mis-routed, not a switch).
  * model_disagreement        -- a pluggable `scorer(beat) -> (track, confidence)` confidently
    predicts a DIFFERENT track. This is the confident-learning hook (Cleanlab-style); plug an
    embedding/LLM scorer here in Slice 6. Without it, the two heuristics above still run.

Confirmed tags are trusted -- never flagged. Read-only on the substrate AND on the tags.
See docs/library/design/20260709_tag-governance-safe-self-improving-taggi_1c9052.md.
"""
import json
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple

from core.foundation.store import Store, create_store
from core.narrative.schema import Beat, beat_key
from core.narrative.tagging import TagHistory

# scorer seam: given a Beat, return (predicted_track, confidence) or (None, 0.0) to abstain.
Scorer = Callable[[Beat], Tuple[Optional[str], float]]


@dataclass
class Suspect:
    beat_id: str
    track: str
    confidence: float
    reasons: List[str] = field(default_factory=list)
    severity: float = 0.0
    summary: str = ""

    def to_dict(self):
        return {"beat_id": self.beat_id, "track": self.track, "confidence": self.confidence,
                "reasons": self.reasons, "severity": round(self.severity, 3), "summary": self.summary}


class TagAuditor:
    def __init__(self, store: Optional[Store] = None):
        self.store = store if store is not None else create_store()

    def _load(self, beat_id: str) -> Optional[Beat]:
        raw = self.store.get(beat_key(beat_id))
        if not raw:
            return None
        try:
            return Beat.from_dict(json.loads(raw))
        except (ValueError, TypeError):
            return None

    def flag_suspect_tags(self, *, low_conf_threshold: float = 0.5,
                          scorer: Optional[Scorer] = None) -> List[Suspect]:
        """Return likely mis-tags, worst-first. NEVER mutates (I6)."""
        ids = self.store.zrange("narr:beats:timeline", 0, -1)        # ascending by time
        beats = [b for b in (self._load(i) for i in ids) if b is not None]
        suspects: List[Suspect] = []
        for idx, b in enumerate(beats):
            cur = TagHistory.from_list(b.tag_history).current()
            conf = cur.confidence if cur else 0.1
            if cur and cur.confirmed:
                continue                                            # confirmed = trusted, never flagged
            reasons: List[str] = []
            if conf < low_conf_threshold:
                reasons.append("low_confidence")
            prev = beats[idx - 1].track if idx > 0 else None
            nxt = beats[idx + 1].track if idx + 1 < len(beats) else None
            if prev and prev == nxt and b.track and b.track != prev:
                reasons.append(f"inconsistent_with_neighbors:{prev}")
            if scorer is not None:
                try:
                    pred, pconf = scorer(b)
                except Exception:
                    pred, pconf = None, 0.0
                if pred and pred != b.track and pconf > conf:
                    reasons.append(f"model_suggests:{pred}")
            if reasons:
                sev = len(reasons) + max(0.0, low_conf_threshold - conf)
                suspects.append(Suspect(b.id, b.track or "unknown", round(conf, 3),
                                        reasons, sev, (b.summary or "")[:80]))
        suspects.sort(key=lambda s: -s.severity)
        return suspects


_INSTANCE: Optional[TagAuditor] = None


def get_tag_auditor(store: Optional[Store] = None) -> TagAuditor:
    global _INSTANCE
    if store is not None:
        return TagAuditor(store)
    if _INSTANCE is None:
        _INSTANCE = TagAuditor()
    return _INSTANCE
