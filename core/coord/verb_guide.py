"""verb_guide -- WHEN to reach for each verb, in one table every surface is generated from.

WHY THIS EXISTS. The parser's help strings say WHAT a verb is, mostly in the shorthand of the
slice that built it ("T052 delta door", "task 09"), and nothing anywhere said WHEN to use it.
Measured 2026-10-22 over 27 Claude sessions on the fork, which has 127 verbs: 100 were named
in no skill and no door doc, agents called `discover` more than any other verb, and the
operator named a verb for them 21 times. Every channel the house had was PULL-shaped -- an
agent has to suspect a verb exists before discover, tool search or a skill can hand it over --
and an agent cannot search for what it does not know exists. Recall solved the same problem
for lessons by pushing at the moment of relevance ("the failure is in WHEN, not WHAT"); a verb
is the same kind of knowledge ("when X, do Y"), so it rides the same pushes:

  layer 1  this table: family + a trigger-phrased "Use when ..." line per verb, pinned to the
           live parser by tests/test_verb_guide.py (no verb without a line, no line without a verb)
  layer 2  render_map(): the situation map the SessionStart whisper and the MCP server
           instructions carry, so every session starts knowing the whole surface
  layer 3  the family skills (.agents/skills/aurora-*), whose verb tables are generated from
           here by scripts/generators/gen_verb_skills.py
  layer 4  match_prompt() / hand_rolled(): one suggestion at plan time and one at action time,
           through the existing hooks, silent when nothing fits
  layer 5  mentioned_verbs(): the miss detector -- a verb the operator had to type is logged,
           and core/coord/verb_awareness.py meters the rate

The data lives in verb_guide.json beside this module (127 entries is data, not code). Every
function here is pure and cheap: the hooks call it on every prompt and every shell command,
under a timeout, so nothing here may touch the network, a model, or the parser.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterable

GUIDE_PATH = Path(__file__).with_name("verb_guide.json")

#: The marker on every verb block the harness injects; verb_awareness reads it back out of
#: transcripts to measure follow-through.
MARK = "[aurora verbs]"


@dataclass(frozen=True)
class Family:
    title: str
    situation: str
    skill: str


#: Map order is the order an agent meets these situations in a working session.
FAMILIES: dict[str, Family] = {
    "memory": Family(
        "Shared memory", "starting a task, learning something, leaving work for the next agent", "akashic-memory"
    ),
    "coordinate": Family(
        "Working alongside other agents", "mail, locks, tasks, who is doing what", "aurora-coordinate"
    ),
    "investigate": Family(
        "Understanding this house",
        "finding files, history, past sessions, why something is the way it is",
        "aurora-investigate",
    ),
    "research": Family(
        "Outside knowledge and other models",
        "web pages, second opinions, long reading, video and manuals",
        "aurora-research",
    ),
    "ship": Family("Verifying and recording work", "tests, reports, docs, wishes", "aurora-ship"),
    "fleet": Family(
        "Fleet health and setup", "is everything running, why is a seat stuck, hooks, grants, secrets", "aurora-fleet"
    ),
    "improve": Family(
        "Improving the harness itself", "measuring recall, replaying runs, toolbelt aliases", "aurora-improve"
    ),
}

#: Verbs a working session reaches for most (measured: the top of the 2026-10-22 call counts,
#: plus the coordination floor). The map lists them first, and the MCP door marks their tools
#: always-loaded so their schemas never hide behind tool search.
CORE = (
    "boot",
    "recall",
    "learn",
    "note",
    "handoff",
    "bifrost-sync",
    "bifrost-send",
    "locks",
    "lock",
    "unlock",
    "find",
    "eye",
    "web",
    "status",
    "suite-baseline",
)

#: The next tier: verbs whose situation comes up often in ordinary work. When the map has to
#: shrink, verbs outside CORE and this tier lose their trigger line first (they stay listed).
COMMON = (
    "delta",
    "lookback",
    "wrap",
    "bifrost-standby",
    "bifrost-ack",
    "scout",
    "task",
    "capture",
    "defer",
    "discover",
    "timeline",
    "sweep",
    "events",
    "ask",
    "sift",
    "captions",
    "report",
    "doc",
    "wish",
    "doctor",
    "unwedge",
    "flightdeck",
    "hooks",
    "secret",
    "setup",
    "stats",
    "injections",
)


def _words(text: str) -> frozenset[str]:
    """A word list kept as text: easier to read and extend than a literal of quoted words."""
    return frozenset(text.split())


#: Verb names that are also everyday English or shell words. A message only names one of
#: these AS A VERB when it is spelled as a command (`aurora find`, `agent_cli.py status`).
_AMBIGUOUS = _words(
    "find list log run status setup report task tool review grade loop link secret sha events media "
    "doc wish note notes scope story context ask web compare audit glance sweep orient ground shadow "
    "eye capture alias bench kata toast pulse watch defer kit modes compress corpus replay suite fence "
    "forecast screen manual captions reply boop focus delta stats triage hooks fleet roster grant doctor "
    "episode lock unlock locks recall learn boot handoff college resident discover provenance"
)


@lru_cache(maxsize=1)
def load() -> dict[str, dict[str, Any]]:
    """verb -> {family, when, keywords, args, hand_rolled}. Missing file -> {} (fail-soft: the
    hooks that call this must stay silent rather than break)."""
    try:
        return json.loads(GUIDE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def situation(when: str) -> str:
    """The trigger half of a "Use when X: Y." line -- the part that decides WHEN."""
    s = when.removeprefix("Use when ").strip()
    head, sep, _ = s.partition(": ")
    return (head if sep else s).rstrip(".")


_PAREN = re.compile(r"\s*\([^)]*\)")
_LEAD = re.compile(r"^(?:you(?:'re| are)? |asking |wondering )")


def brief(when: str) -> str:
    """The situation, shortened for the map: parenthesised examples, '; ...' asides and a
    leading 'you'/'asking' go (the skill tables keep the whole line). This is what keeps every
    working family's triggers inside the 10,000-character hook cap beside the whisper."""
    return _LEAD.sub("", _PAREN.sub("", situation(when)).split("; ")[0].strip())


def by_family(guide: dict[str, dict] | None = None) -> dict[str, list[str]]:
    g = load() if guide is None else guide
    out: dict[str, list[str]] = {f: [] for f in FAMILIES}
    for verb, card in g.items():
        out.setdefault(card.get("family", "improve"), []).append(verb)
    rank = {v: i for i, v in enumerate(CORE + COMMON)}
    for verbs in out.values():
        verbs.sort(key=lambda v: (rank.get(v, len(rank)), v))
    return out


def command(verb: str, cli: str, agent: str = "<you>", guide: dict[str, dict] | None = None) -> str:
    g = load() if guide is None else guide
    args = (g.get(verb, {}).get("args") or "").replace("<you>", agent)
    return f"{cli} {verb}" + (f" {args}" if args else "")


# ----------------------------------------------------------------------------- layer 2: map
def render_map(cli: str = "aurora", *, max_chars: int | None = None, guide: dict[str, dict] | None = None) -> str:
    """The situation map: every verb under the situation it serves, trigger half only.

    With `max_chars` it degrades rather than truncating mid-line: verbs lose their trigger line
    one at a time, lowest priority first (outside CORE and COMMON, rarest family first), and a
    verb without one is still named on its family's "also" line -- the reader always sees the
    whole surface and loses detail, never verbs."""
    g = load() if guide is None else guide
    if not g:
        return ""
    fams = by_family(g)
    head = [
        (
            f"{MARK} Your tools in this house: reach for these verbs by default, before hand-rolled "
            f"shell. `{cli} <verb> --help` gives flags; `{cli} discover <words>` searches; each family's "
            "skill has examples and sequences. Use when:"
        ),
    ]

    def block(fam: str, folded: set[str]) -> list[str]:
        f = FAMILIES.get(fam) or Family(fam, "", "")
        verbs = fams.get(fam) or []
        if not verbs:
            return []
        lines = [f"{f.title} ({f.situation}) -- skill {f.skill}:"]
        lines += [f"  {v}: {brief(g[v].get('when', ''))}" for v in verbs if v not in folded]
        rest = [v for v in verbs if v in folded]
        if rest:
            lines.append(("  also: " if len(rest) < len(verbs) else "  ") + ", ".join(rest))
        return lines

    # Fold order: the priority tiers across all families first, then within a tier the
    # later family (map order) before the earlier one, each family from its tail.
    rank = {v: i for i, v in enumerate(CORE + COMMON)}
    fam_pos = {fam: i for i, fam in enumerate(fams)}
    fold_order = sorted(
        (v for vs in fams.values() for v in vs),
        key=lambda v: (v in rank, -rank.get(v, 0), -fam_pos[g[v].get("family", "improve")], v),
    )
    text = ""
    for n in range(len(fold_order) + 1):
        folded = set(fold_order[:n])
        lines = list(head)
        for fam in fams:
            lines += block(fam, folded)
        text = "\n".join(lines)
        if max_chars is None or len(text) <= max_chars:
            return text
    return text[: max(0, max_chars or 0)]


# ----------------------------------------------------------------------- layer 4: matching
_WORD = re.compile(r"[a-z0-9][a-z0-9'-]*")

#: Words that carry no situation. Kept short on purpose: rarity weighting already discounts
#: words many verbs share, so this only removes what would otherwise match everything.
_STOP = _words(
    "a an the and or but if of to in on at by for from with without into onto over under about as is are was were "
    "be been being do does did done have has had having it its this that these those there here what which who whom "
    "whose when where why how i me my we us our you your he him his she her they them their one ones some any all "
    "can could should would will shall may might must not no yes so than then too very just also only own same such "
    "up out off again once more most other others each both few lets let's get got make made use using used want "
    "need needs know see look show tell run thing things something anything way still now right "
    # Measured noise on real operator messages: words that sit in many requests and in some
    # keyword phrase, so they matched everything. 'aurora' names the house, not a situation.
    "work working else full before after first time close everything set reset saved current read write "
    "file files aurora akashic"
)


def _stem(w: str) -> str:
    """Crude suffix fold so 'failing'/'failures'/'failed' meet. Deliberately dumb: the cost
    of a bad fold is one missed suggestion, and the hook budget forbids a real stemmer."""
    w = w.strip("'-")
    for suf in ("ings", "ing", "ers", "er", "ies", "es", "ed", "ly", "s"):
        if len(w) > len(suf) + 3 and w.endswith(suf):
            return w[: -len(suf)] + ("y" if suf == "ies" else "")
    return w


def _tokens(text: str) -> set[str]:
    return {_stem(w) for w in _WORD.findall((text or "").lower()) if w not in _STOP and len(w) > 2}


def _kw_re(kw: str) -> re.Pattern:
    parts = [re.escape(p) for p in kw.lower().split()]
    return re.compile(r"\b" + r"\s+".join(parts) + r"(?:s|es|ed|ing)?\b")


@lru_cache(maxsize=1)
def _index() -> tuple[dict[str, float], tuple[tuple[str, dict[str, float], tuple[re.Pattern, ...]], ...]]:
    """(idf per token, per verb: {token: weight} and its exact keyword phrases).

    Weights: a one-word keyword 2 (chosen to be what people say); a word of a keyword phrase
    or of the verb's own name 1.5 (a hint -- the whole phrase is the evidence); a word of the
    use-when situation 1 (context only, never enough on its own). Rarity across the table
    scales each token, so 'test' (many verbs) says little and 'captions' says a lot."""
    g = load()
    bags: dict[str, dict[str, float]] = {}
    for verb, card in g.items():
        bag: dict[str, float] = {}
        for tok in _tokens(situation(card.get("when", ""))):
            bag[tok] = max(bag.get(tok, 0.0), 1.0)
        for tok in _tokens(verb.replace("-", " ")):
            bag[tok] = max(bag.get(tok, 0.0), 1.5)
        for kw in card.get("keywords") or []:
            single = len(kw.split()) == 1
            for tok in _tokens(kw):
                bag[tok] = max(bag.get(tok, 0.0), 2.0 if single else 1.5)
        bags[verb] = bag
    df: dict[str, int] = {}
    for bag in bags.values():
        for tok in bag:
            df[tok] = df.get(tok, 0) + 1
    n = max(1, len(g))
    idf = {t: math.log(1 + n / c) for t, c in df.items()}
    rows = tuple(
        (verb, bags[verb], tuple(_kw_re(k) for k in (g[verb].get("keywords") or []) if " " in k.strip())) for verb in g
    )
    return idf, rows


#: Tuned on the fixture prompts in tests/test_verb_guide.py: high enough that ordinary coding
#: requests stay silent, low enough that a request in plain words finds its verb. Precision
#: beats recall here -- a wrong suggestion teaches the reader to skip the line.
MATCH_FLOOR = 9.0
#: An exact multi-word keyword is the strongest evidence a message can give.
_PHRASE_BONUS = 8.0
_URL = re.compile(r"https?://\S+")


def match_prompt(prompt: str, k: int = 2, exclude: Iterable[str] = ()) -> list[tuple[str, float]]:
    """The verbs this message's situation fits, best first, at most `k`, floored. Needs at
    least two distinct matching words or one exact phrase, so a lone shared word never fires.
    Verbs the message already names are skipped: the human supplied those (layer 5 counts
    them), and echoing them back is noise."""
    text = _PASTED.sub(" ", prompt or "").lower()
    # A pasted link is said as "this url" in the keywords; the link itself tokenises as noise.
    toks = _tokens(_URL.sub(" url ", text))
    if len(toks) < 2:
        return []
    named = set(mentioned_verbs(prompt, load().keys()))
    skip = set(exclude) | named
    idf, rows = _index()
    # Long messages collect chance overlaps: measured on 74 real operator messages, a fixed
    # floor fired on more than half of them. The bar rises with the log of the message's
    # length, so a one-line request needs one clear signal and a page needs several.
    floor = MATCH_FLOOR * max(1.0, math.log2(len(toks) / 6.0) if len(toks) > 6 else 1.0)
    scored = []
    for verb, bag, phrases in rows:
        if verb in skip:
            continue
        hits = [t for t in toks if t in bag]
        kw_hits = [t for t in hits if bag[t] >= 1.5]
        phrase = any(p.search(text) for p in phrases)
        if len(kw_hits) < 2 and not phrase:
            continue
        s = sum(bag[t] * idf[t] for t in hits) + (_PHRASE_BONUS if phrase else 0.0)
        if s >= floor:
            scored.append((verb, round(s, 2)))
    scored.sort(key=lambda t: -t[1])
    return scored[:k]


_INVOKES_HOUSE = re.compile(r"(?:\baurora|agent_cli\.py)\b")


@lru_cache(maxsize=1)
def _hand_rolled_index() -> tuple[tuple[str, re.Pattern, str], ...]:
    out = []
    for verb, card in load().items():
        for hr in card.get("hand_rolled") or []:
            try:
                out.append((verb, re.compile(hr["pattern"]), hr.get("why", "")))
            except (re.error, KeyError, TypeError):
                continue  # a bad pattern loses its own hint, never the hook
    return tuple(out)


def hand_rolled(command_line: str, exclude: Iterable[str] = ()) -> list[tuple[str, str]]:
    """(verb, why) for a shell command that does by hand what a verb already does. A command
    that already goes through the house door is never second-guessed."""
    cmd = command_line or ""
    if not cmd.strip() or _INVOKES_HOUSE.search(cmd):
        return []
    skip = set(exclude)
    hits: list[tuple[str, str]] = []
    for verb, pat, why in _hand_rolled_index():
        if verb not in skip and verb not in {h[0] for h in hits} and pat.search(cmd):
            hits.append((verb, why))
    return hits


def render_suggestions(verbs: list[str], cli: str, *, header: str, why: dict[str, str] | None = None) -> str:
    """One compact block: each suggested verb as a runnable command plus its trigger line."""
    g = load()
    if not verbs:
        return ""
    lines = [f"{MARK} {header}"]
    for v in verbs:
        card = g.get(v) or {}
        reason = (why or {}).get(v) or card.get("when", "")
        lines.append(f"  `{command(v, cli, guide=g)}` -- {reason}")
    return "\n".join(lines)


# ------------------------------------------------------------------- layer 5: the miss signal
_PASTED = re.compile(r"<pasted_content\b.*?</pasted_content[^>]*>", re.S)


def mentioned_verbs(text: str, verbs: Iterable[str]) -> list[str]:
    """Verbs a human message names AS verbs: `aurora X`, `agent_cli.py X`, an MCP tool name,
    or a backticked verb (`recall`). Everyday-word verbs count only in command form, and
    pasted material is not the human's own words. Order of first appearance, no repeats."""
    vset = set(verbs)
    if not vset or not text:
        return []
    t = _PASTED.sub(" ", text)
    alt = "|".join(sorted((re.escape(v) for v in vset), key=len, reverse=True))
    found: list[str] = []

    def add(v: str) -> None:
        if v in vset and v not in found:
            found.append(v)

    for m in re.finditer(rf"(?:agent_cli\.py|\baurora)\s+({alt})(?![\w-])", t):
        add(m.group(1))
    for m in re.finditer(r"mcp__akashic-aurora__([a-z_]+)", t):
        add(m.group(1).replace("_", "-"))
    for m in re.finditer(rf"`({alt})(?:\s[^`]*)?`", t):
        if m.group(1) not in _AMBIGUOUS or " " in m.group(0):
            add(m.group(1))
    return found
