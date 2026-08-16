"""THE EYE S7 -- the directive watcher. The organ closes its own founding wound.

THE EYE exists because directives died in the transcript plane: two lost on 2026-08-10, and
recovering them took nine guessed searches. S0-S6 made them FINDABLE. This makes them
SURFACED, which is a different thing -- on 2026-08-11 the organ turned up "remember to fan
out so you dont get bogged down in the mechanics", said twice across two sessions and never
actioned, and it surfaced only because someone was chasing an unrelated defect. Nobody was
looking. Nobody would have.

HOW IT WORKS, and there is no LLM anywhere in the path (the organ's standing law):

  1. MINE the operator axis for phrases that recur. Word n-grams over his utterances only;
     the utterance law collapses the harness's duplicate records first, so a turn recorded
     three times is one voice, not three.
  2. DROP BOILERPLATE by document frequency. "lets keep building" recurs exactly as often
     as a real directive and carries nothing. A phrase appearing across too large a share
     of his utterances is conversational filler by construction -- this is the only
     discriminator available without a model, and it is stated so it can be argued with.
  3. ASK WHETHER ANYTHING CAME OF IT. For each survivor, does any DURABLE plane cite it --
     the task ledger, a lesson, an atom, a commit message? A phrase he has said repeatedly
     that nothing durable references is the exact shape of a directive that evaporated.

THE DESIGN CONSTRAINT THAT OUTRANKS COVERAGE: this thing must be QUIET. A wedge page fired
on a healthy seat the same day this was designed, and the note that followed said it
plainly -- a page that fires on healthy seats trains us to ignore pages. A watcher
surfacing twelve maybes a morning is scrolled past within a week, and after that its
SILENCE reads as all-clear while it is in fact being ignored. So: high precision over
recall, a hard cap, the withheld count stated, and an affirmative all-clear that is
distinguishable from a crash.

AND IT PROPOSES, NEVER RATIFIES. There is no write path in this module -- no task filing,
no lesson writing, no subprocess. It surfaces; the human decides. Four independent arrivals
in this house landed on that law; this one inherits it rather than rediscovering it.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from core.eye.index import _connect, utterance_key

# Phrase length in words. Short enough that a rephrasing still overlaps, long enough that
# the match means something -- 5 words is the floor at which "fence the migration path"
# survives while "I want you to" does not.
_NGRAM = 5
# How much of the clause to keep once anchored at its marker. Long enough to carry the
# instruction, short enough that a rephrasing of the same directive still collides.
_CLAUSE = 9

# A phrase appearing in more than this SHARE of his utterances is filler by construction.
# Deliberately generous: the cap below is the real guard, and an over-tight filter here
# would silently drop real directives, which is the failure mode with no witness.
_MAX_DOC_FREQ = 0.34

# Openers that carry no content on their own. Not a stopword list for the whole phrase --
# a phrase is dropped only if it is ENTIRELY made of these, so "always fence the migration
# path" survives while "can we make sure that" does not.
_FILLER = {
    "i", "you", "we", "it", "the", "a", "an", "to", "of", "and", "or", "is", "are", "be",
    "can", "could", "would", "should", "will", "want", "need", "make", "let", "lets",
    "this", "that", "these", "those", "there", "here", "do", "does", "did", "so", "if",
    "for", "on", "in", "at", "with", "as", "but", "not", "what", "how", "why", "when",
    "just", "really", "very", "please", "thing", "things", "get", "got", "keep", "now",
    "up", "out", "about", "our", "your", "my", "me", "us", "have", "has", "had", "was",
    "were", "then", "them", "they", "he", "she", "its", "it's", "build", "building",
}

_WORD = re.compile(r"[a-z0-9']+")

# THE DIRECTIVE-SHAPE GATE, written down so it can be argued with -- the same contract
# `freq` makes about its verdict thresholds.
#
# Mining recurring phrases finds recurring PHRASES, which is not the same thing as
# directives. The first live run surfaced "i hope you have fun", "is next on the docket"
# and "i'll leave the order up" as top findings: all genuinely repeated, none a standing
# instruction. Without a model the only honest discriminator is grammatical shape, so an
# utterance qualifies when it carries an instruction marker AND is not a question.
#
# This is a HEURISTIC and is reported as one. It trades recall for precision on purpose:
# a watcher that surfaces noise gets ignored, and an ignored watcher's silence reads as
# all-clear, which is strictly worse than having no watcher at all.
_STRONG = ("always", "never", "from now on", "every time", "must", "make sure",
           "remember", "going forward", "stop ", "don't ", "dont ", "do not ",
           "ensure", "avoid")
_WEAK = ("i want", "we should", "you should", "need to", "lets ", "let's ",
         "prefer", "i'd like", "id like", "please ")
_INTERROGATIVE = ("what", "how", "why", "when", "where", "who", "is ", "are ", "can ",
                  "could ", "do ", "does ", "did ", "should we", "any ")


def _marker_starts(text: str) -> List[int]:
    """Token positions where an instruction begins. The clause runs from here forward, so
    "remember to fan out so you dont get bogged" is one candidate rather than forty.

    The FULL marker must match, not its first word. Keying on first words made "i want"
    fire on every "i" and "we should" on every "we", which is how "i am heading to sleep"
    and "we have done a lot" ranked as standing directives on the second live run."""
    words = _tokens(text)
    starts: List[int] = []
    for marker in _STRONG + _WEAK:
        mtok = _tokens(marker)
        if not mtok:
            continue
        for i in range(len(words) - len(mtok) + 1):
            if words[i:i + len(mtok)] == mtok:
                starts.append(i)
    return sorted(set(starts))


def directive_shape(text: str) -> str:
    """'strong' | 'weak' | '' -- how instruction-shaped this utterance is.

    A question is never a directive, however often it recurs: "what is next on the docket"
    is him ASKING, and reporting it as an unheeded instruction would be the instrument
    inventing an obligation he never stated."""
    t = " ".join((text or "").lower().split())
    if not t:
        return ""
    if t.rstrip().endswith("?") or t.startswith(_INTERROGATIVE):
        return ""
    if any(m in t for m in _STRONG):
        return "strong"
    if any(m in t for m in _WEAK):
        return "weak"
    return ""


def _tokens(text: str) -> List[str]:
    return _WORD.findall((text or "").lower())


def _content_ratio(words: Sequence[str]) -> float:
    if not words:
        return 0.0
    return sum(1 for w in words if w not in _FILLER) / len(words)


def _operator_utterances(db_path: Optional[Path]) -> List[Dict[str, Any]]:
    """His voice, deduped to UTTERANCES. The harness records one turn as a queue-operation
    enqueue, a dequeue and a delivered `user` twin; counting rows would treat one sentence
    as three and inflate every verdict built on top.

    AND IT IS HIS VOICE ONLY (authorship fix, RED a5afd360). A subagent's brief arrives
    as a `user` record, so the
    indexer labels it operator by its own rule and wrongly in fact -- the author is the
    dispatching agent. The docstring of this module already named that false-positive class
    and the report already disclaimed it; a disclaimer is not a filter, and on the first
    full-corpus run the class took all three capped slots. `is_subagent` is stamped from the
    source path at ingest, so the discriminator is the same one corpus_coverage() counts by
    rather than a second one invented here -- the two-declarations drift T313 was fixed to
    end.

    NULL COALESCES TO 'HIS'. An unknown row is one whose source rotated away before the
    column existed, and the twenty rescued sessions in that population exist nowhere else.
    Including an unknown risks a little contamination; excluding it risks deleting his voice
    from the only copy, which is the failure this whole organ was built to prevent."""
    con = _connect(db_path)
    try:
        rows = con.execute(
            "SELECT event_id, session, text FROM events WHERE voice='operator' "
            "AND COALESCE(is_subagent, 0) = 0 ORDER BY session, line").fetchall()
    finally:
        con.close()
    seen: Set[Tuple[str, str]] = set()
    out: List[Dict[str, Any]] = []
    for eid, session, text in rows:
        key = utterance_key(session, text)
        if key in seen:
            continue
        seen.add(key)
        out.append({"event_id": eid, "session": session,
                    "text": " ".join((text or "").split())})
    return out


def candidates(db_path: Optional[Path] = None, *, min_utterances: int = 2,
               min_sessions: int = 2) -> List[Dict[str, Any]]:
    """Recurring phrases on the operator axis, boilerplate removed. Mechanical throughout."""
    utts = _operator_utterances(db_path)
    total = len(utts)
    if not total:
        return []

    # phrase -> the utterances containing it (indices, so one utterance counts once)
    index: Dict[str, Set[int]] = {}
    shape_of: Dict[int, str] = {}
    for i, u in enumerate(utts):
        shape = directive_shape(u["text"])
        if not shape:
            continue                          # recurring, but not an instruction
        shape_of[i] = shape
        # THE PHRASE IS THE DIRECTIVE CLAUSE, anchored at its marker -- not every window
        # of the sentence containing one. Sliding a plain n-gram over the whole utterance
        # marked all ~50 windows of a long turn as directives because ONE "always" sat
        # somewhere inside it, which is how "me know what you think" ranked as a standing
        # instruction on the first live run. Cutting from the marker forward yields the
        # clause he actually issued.
        words = _tokens(u["text"])
        for start in _marker_starts(u["text"]):
            # Several window LENGTHS from each marker, not one. Two sessions phrase the
            # same instruction with different tails ("...before shipping it" vs
            # "...before shipping it, this keeps biting us"), so a fixed-width clause
            # yields two strings that never collide and the directive reads as said once.
            # The shorter windows are what match; the merge step below prefers the longest
            # form that all of them share.
            for width in range(_NGRAM, _CLAUSE + 1):
                gram = words[start:start + width]
                if len(gram) < width or _content_ratio(gram) < 0.4:
                    continue
                index.setdefault(" ".join(gram), set()).add(i)

    hits: List[Dict[str, Any]] = []
    for phrase, idxs in index.items():
        if len(idxs) < min_utterances:
            continue
        if len(idxs) / total > _MAX_DOC_FREQ:
            continue                          # filler by construction
        sessions = {utts[i]["session"] for i in idxs}
        if len(sessions) < min_sessions:
            continue
        hits.append({
            "phrase": phrase,
            "utterances": len(idxs),
            "sessions": len(sessions),
            "shape": ("strong" if any(shape_of.get(i) == "strong" for i in idxs)
                      else "weak"),
            "refs": [utts[i]["event_id"] for i in sorted(idxs)][:6],
            "_idxs": idxs,
        })

    # Collapse overlapping n-grams of one sentence into the LONGEST phrase: three
    # overlapping windows of the same directive are one directive, and reporting them
    # separately is exactly the noise the cap exists to prevent.
    hits.sort(key=lambda h: (-len(h["_idxs"]), -len(h["phrase"])))
    kept: List[Dict[str, Any]] = []
    for h in hits:
        merged = False
        for k in kept:
            if k["_idxs"] == h["_idxs"]:
                # same utterance set -- same directive, seen through a different window
                if h["phrase"] not in k["phrase"]:
                    k["phrase"] = _merge(k["phrase"], h["phrase"])
                merged = True
                break
        if not merged:
            kept.append(dict(h))
    for k in kept:
        k.pop("_idxs", None)
    return kept


def _merge(a: str, b: str) -> str:
    """Join two overlapping windows of one sentence back into the longer phrase."""
    aw, bw = a.split(), b.split()
    for overlap in range(min(len(aw), len(bw)) - 1, 0, -1):
        if aw[-overlap:] == bw[:overlap]:
            return " ".join(aw + bw[overlap:])
        if bw[-overlap:] == aw[:overlap]:
            return " ".join(bw + aw[overlap:])
    return a if len(aw) >= len(bw) else b


def _is_cited(phrase: str, durable: Iterable[str]) -> bool:
    """Does any durable artifact actually reference this directive?

    The bar is a CONTIGUOUS run of the phrase's content words, not a bag-of-words overlap.
    A loose match would silence the watcher for free -- 'migration' appearing anywhere in
    the ledger is not evidence the directive was heard -- and a watcher silenced for free
    leaves the directive dead while reporting all-clear."""
    words = [w for w in phrase.split() if w not in _FILLER]
    if not words:
        return False
    need = max(2, int(len(words) * 0.6))
    for text in durable:
        hay = " ".join(_tokens(text))
        for start in range(len(words) - need + 1):
            run = " ".join(words[start:start + need])
            if run and run in hay:
                return True
        # also accept the phrase verbatim, filler included
        if phrase in hay:
            return True
    return False


def unheeded(db_path: Optional[Path] = None, *, durable_texts: Optional[Iterable[str]] = None,
             limit: int = 2, min_utterances: int = 2,
             min_sessions: int = 2) -> Dict[str, Any]:
    """Recurring operator directives that no durable plane cites.

    Returns an envelope that is honest in the empty case: `clear` says the watcher looked
    and found nothing, `checked` says how many candidates it examined, and `withheld` says
    how many real findings the cap suppressed. Empty results and a broken watcher must
    never look the same from the outside."""
    durable = list(durable_texts) if durable_texts is not None else collect_durable()
    cands = candidates(db_path, min_utterances=min_utterances, min_sessions=min_sessions)

    found: List[Dict[str, Any]] = []
    for c in cands:
        if _is_cited(c["phrase"], durable):
            continue
        found.append({**c, "cited": False})

    # Strongest evidence first: his repetition across SESSIONS is the signal (a thing said
    # three times in one sitting is emphasis; across three sittings it is a standing
    # directive), then raw utterance count, then specificity.
    found.sort(key=lambda h: (0 if h.get("shape") == "strong" else 1,
                              -h["sessions"], -h["utterances"], -len(h["phrase"])))
    shown = found[:max(0, int(limit))]
    return {
        "items": shown,
        "checked": len(cands),
        "withheld": max(0, len(found) - len(shown)),
        "clear": not found,
        "durable_sources": len(durable),
    }


def collect_durable(root: Optional[Path] = None) -> List[str]:
    """Every plane where 'we acted on it' would leave a mark: the ledger, lessons, atoms,
    and recent commit subjects. Read-only, and failure of any one source degrades the
    answer rather than the run -- a missing plane means the watcher is MORE likely to
    report something, never less, so the honest direction is preserved."""
    root = Path(root) if root else Path(__file__).resolve().parents[2]
    out: List[str] = []
    for rel in ("state/coord/tasks.json", "session_logs/learnings.jsonl"):
        p = root / rel
        try:
            out.append(p.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            pass
    for sub in ("docs/library", "docs"):
        d = root / sub
        if not d.is_dir():
            continue
        for f in list(d.rglob("*.md"))[:2000]:
            try:
                out.append(f.read_text(encoding="utf-8", errors="replace"))
            except Exception:
                pass
        break
    return out
