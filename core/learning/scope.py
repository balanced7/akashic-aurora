"""Lesson scope -- WHERE a lesson applies, as opposed to what it is about.

Meta-harness task 02. A lesson can be on topic and still wrong for the agent about to read it:
it was learned under another harness, another model, another OS, another tool version. That is
relevance versus applicability (Memory-R1; Grounding Agent Memory). `domain` already answers
"which kind of work"; scope answers "under which conditions".

THE LEVELS, broadest first:

    universal                    holds everywhere (also: a lesson with no scope field at all)
    harness:<name>               claude-code, codex-cli, codex-desktop, cursor, runner:<seat>
    model:<family>               claude-opus, claude-sonnet, deepseek ...
    model:<id>                   claude-opus-5-5
    effort:<level>               low, medium, high ...
    os:<name>                    linux, darwin, windows
    tool:<name>@<version>        uv@0.9 -- matched against nothing automatic yet; kept for agents

A lesson may hold several. MATCHING: terms of the same kind are alternatives (OR); different
kinds must all hold (AND). `harness:codex-cli harness:cursor model:deepseek` applies to a
DeepSeek model in either harness. A context value that is unknown never excludes: hiding a
lesson because we could not tell which model we are is the confidently-wrong failure.

`model:<family>` matches any id in the family; `model:<id>` matches only that id.

THE DEFAULT. A lesson recorded without `--scope` gets the PROPOSED scope from its session's
provenance: `harness:<h> model:<family>`. Narrow on purpose (the open question in the task
said: narrowest, plus fast widening by evidence) -- but not narrower: effort is left out,
because almost no lesson is true at one effort and false at another, and every extra term
halves the audience. Evidence widens it (`widening_proposals`). A shell with no harness and
no model proposes `universal`: there is nothing to narrow on.
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterable, Mapping
from typing import Any

UNIVERSAL = "universal"
KINDS = ("harness", "model", "effort", "os", "tool")
_TERM = re.compile(r"^(universal|(harness|model|effort|os|tool):[A-Za-z0-9_.:@/+-]+)$")

#: Model id prefix -> family. Longest prefix wins; an id no prefix knows is its own family.
_FAMILIES = (
    ("claude-opus", "claude-opus"),
    ("claude-sonnet", "claude-sonnet"),
    ("claude-haiku", "claude-haiku"),
    ("claude-fable", "claude-fable"),
    ("gpt-", "gpt"),
    ("o3", "openai-o"),
    ("o4", "openai-o"),
    ("deepseek", "deepseek"),
    ("gemini", "gemini"),
    ("kimi", "kimi"),
    ("moonshot", "kimi"),
    ("qwen", "qwen"),
)


def model_family(model_id: str) -> str:
    m = (model_id or "").strip().lower()
    if not m or m == "unknown":
        return ""
    best = ""
    fam = ""
    for prefix, family in _FAMILIES:
        if m.startswith(prefix) and len(prefix) > len(best):
            best, fam = prefix, family
    return fam or m


def parse(raw: str | Iterable[str] | None) -> list[str]:
    """Normalise a scope from a flag, a stored field or a list. Raises ValueError on a term
    that is not one of the levels, so a typo never silently becomes `universal`."""
    if raw is None:
        return []
    parts = raw.replace(",", " ").split() if isinstance(raw, str) else [str(x) for x in raw]
    out: list[str] = []
    for p in parts:
        t = p.strip()
        if not t:
            continue
        if not _TERM.match(t):
            raise ValueError(
                f"bad scope term {t!r}: use universal, harness:<name>, model:<family|id>, "
                f"effort:<level>, os:<name> or tool:<name>@<version>"
            )
        if t not in out:
            out.append(t)
    if UNIVERSAL in out:
        return [UNIVERSAL]
    return out


def of(lesson: Mapping[str, Any]) -> list[str]:
    """A lesson's scope. Absent or unreadable means universal (every pre-scope lesson)."""
    try:
        return parse(lesson.get("scope") or "") or [UNIVERSAL]
    except ValueError:
        return [UNIVERSAL]


def render(terms: Iterable[str]) -> str:
    return " ".join(terms) or UNIVERSAL


def is_universal(terms: Iterable[str]) -> bool:
    t = list(terms)
    return not t or t == [UNIVERSAL]


def context_from(prov: Mapping[str, Any] | None) -> dict[str, str]:
    """The matching context for a provenance record (task 01). Unknowns are dropped."""
    prov = prov or {}
    ctx: dict[str, str] = {}
    for kind, field in (("harness", "harness"), ("effort", "effort"), ("os", "os")):
        v = str(prov.get(field) or "").strip()
        if kind == "harness" and v == "shell":
            continue  # an operator's own terminal is not a harness: it sees every lesson
        if v and v != "unknown":
            ctx[kind] = v
    model = str(prov.get("model") or "").strip()
    if model and model != "unknown":
        ctx["model"] = model
    return ctx


_CTX_CACHE: dict[str, dict[str, str]] = {}


def current_context() -> dict[str, str]:
    """The context of THIS process, from its session's provenance record, or -- with no
    record -- from the same environment reads, minus the slow parts (git, config hashing),
    because this runs on the recall hot path. Cached per session for the process lifetime.
    Empty when nothing is known, which matches every lesson: the pre-scope behaviour."""
    try:
        import platform

        from core.fleet import provenance

        sid = provenance.current_session_id()
        if sid in _CTX_CACHE:
            return _CTX_CACHE[sid]
        rec = provenance.get(sid) if sid else None
        if not rec:
            env = os.environ
            harness, _ = provenance._harness(env)
            rec = {
                "harness": "" if harness == "shell" else harness,
                "model": provenance._model(env, {}, sid, os.getcwd()),
                "effort": provenance._effort(env, {}),
                "os": platform.system().lower(),
            }
        ctx = context_from(rec)
        _CTX_CACHE[sid] = ctx
        return ctx
    except Exception:  # noqa: BLE001  # fail-soft: no context means no filtering
        return {}


def _term_holds(kind: str, value: str, ctx: Mapping[str, str]) -> bool | None:
    """True/False when the context can decide, None when it cannot (unknown)."""
    have = ctx.get(kind, "")
    if kind == "tool":
        return None  # nothing reports tool versions automatically yet
    if not have:
        return None
    if kind == "model":
        return value.lower() in (have.lower(), model_family(have))
    return value.lower() == have.lower()


def applies(terms: Iterable[str], ctx: Mapping[str, str]) -> bool:
    """Does a lesson with this scope apply in this context? See the module doc for the rule."""
    t = list(terms)
    if is_universal(t):
        return True
    by_kind: dict[str, list[str]] = {}
    for term in t:
        kind, _, value = term.partition(":")
        by_kind.setdefault(kind, []).append(value)
    for kind, values in by_kind.items():
        # Exclude only when the context can decide EVERY alternative and none holds. One
        # undecidable alternative is enough doubt to keep the lesson.
        verdicts = [_term_holds(kind, v, ctx) for v in values]
        if all(v is False for v in verdicts):
            return False
    return True


def lesson_applies(lesson: Mapping[str, Any], ctx: Mapping[str, str]) -> bool:
    return applies(of(lesson), ctx)


def filter_applicable(lessons: Iterable[Mapping[str, Any]], ctx: Mapping[str, str] | None = None) -> list[Any]:
    """The lessons that apply here. `ctx` None means this process's own provenance; an
    empty context keeps everything. `AKASHIC_SCOPE_FILTER=0` switches the filter off."""
    items = list(lessons)
    if os.getenv("AKASHIC_SCOPE_FILTER", "1") == "0":
        return items
    c = current_context() if ctx is None else ctx
    if not c:
        return items
    return [x for x in items if lesson_applies(x, c)]


def propose(prov: Mapping[str, Any] | None) -> list[str]:
    """The default scope for a lesson recorded in this session (see the module doc)."""
    ctx = context_from(prov)
    terms: list[str] = []
    h = ctx.get("harness", "")
    if h and h != "shell":
        terms.append(f"harness:{h}")
    fam = model_family(ctx.get("model", ""))
    if fam:
        terms.append(f"model:{fam}")
    return terms or [UNIVERSAL]


def level(terms: Iterable[str]) -> str:
    """The narrowest level a scope reaches, for the tree view."""
    t = list(terms)
    if is_universal(t):
        return UNIVERSAL
    kinds = {x.partition(":")[0] for x in t}
    for k in ("tool", "os", "effort", "model", "harness"):
        if k in kinds:
            if k == "model":
                vals = [x.partition(":")[2] for x in t if x.startswith("model:")]
                return "model:id" if any(model_family(v) != v for v in vals) else "model:family"
            return k
    return UNIVERSAL


def widen(terms: Iterable[str], kinds: Iterable[str]) -> list[str]:
    """Drop every term of the given kinds (what a widening proposal applies)."""
    drop = set(kinds)
    out = [x for x in terms if x.partition(":")[0] not in drop and x != UNIVERSAL]
    return out or [UNIVERSAL]


# ----------------------------------------------------------------------------- widening
#: Distinct values of one kind a lesson must earn credit (or a repeat) under before widening
#: across that kind is proposed. Two mirrors D5's two-domain rule for `domain`.
WIDEN_AT = 2


def evidence(
    events: Iterable[Mapping[str, Any]], repeats: Iterable[Mapping[str, Any]], get_prov
) -> dict[str, dict[str, set[str]]]:
    """source -> kind -> the distinct harnesses / model families it EARNED something under.

    Earned means: credited by a flip (it was shown, then the failing action succeeded), or a
    recorded repeat (the mistake it warns about happened there too -- evidence the lesson is
    RELEVANT there, which is what widening is about). Events without a provenance pointer
    (everything before task 01) contribute nothing; they cannot say where they happened.
    """
    out: dict[str, dict[str, set[str]]] = {}

    def add(source: str, prov_ptr: str) -> None:
        if not source or not prov_ptr:
            return
        rec = get_prov(prov_ptr.removeprefix("prov:session:")) or {}
        ctx = context_from(rec)
        slot = out.setdefault(source, {})
        if ctx.get("harness"):
            slot.setdefault("harness", set()).add(ctx["harness"])
        fam = model_family(ctx.get("model", ""))
        if fam:
            slot.setdefault("model", set()).add(fam)

    for e in events:
        if e.get("kind") != "flip":
            continue
        d = e.get("detail") or {}
        if not isinstance(d, Mapping):
            continue
        for src in d.get("sources") or []:
            add(str(src), str(d.get("prov") or ""))
    for r in repeats:
        add(f"learn:experiment:{r.get('of')}", str(r.get("prov") or ""))
    return out


def widening_proposals(
    lessons: Iterable[Mapping[str, Any]], ev: Mapping[str, Mapping[str, set[str]]]
) -> list[dict[str, Any]]:
    """Lessons whose scope is narrower than the evidence: a kind they are scoped on, with
    credit or repeats under WIDEN_AT or more distinct values of it."""
    props: list[dict[str, Any]] = []
    for lesson in lessons:
        terms = of(lesson)
        if is_universal(terms):
            continue
        src = str(lesson.get("source") or f"learn:experiment:{lesson.get('experiment_name')}")
        seen = ev.get(src) or {}
        kinds = sorted(
            k
            for k in ("harness", "model")
            if any(t.startswith(f"{k}:") for t in terms) and len(seen.get(k, ())) >= WIDEN_AT
        )
        if kinds:
            props.append(
                {
                    "experiment": lesson.get("experiment_name"),
                    "source": src,
                    "scope": render(terms),
                    "proposed": render(widen(terms, kinds)),
                    "evidence": {k: sorted(seen[k]) for k in kinds},
                }
            )
    return props


def tree(lessons: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, list[str]]]:
    """level -> scope string -> experiment names, broadest level first."""
    order = (UNIVERSAL, "harness", "model:family", "model:id", "effort", "os", "tool")
    out: dict[str, dict[str, list[str]]] = {k: {} for k in order}
    for lesson in lessons:
        terms = of(lesson)
        out[level(terms)].setdefault(render(terms), []).append(str(lesson.get("experiment_name") or "?"))
    return {k: v for k, v in out.items() if v}


def proposals_now(learning_store: Any, *, event_limit: int = 5000) -> list[dict[str, Any]]:
    """Widening proposals from the live record: flip credits on the event firehose and the
    repeat ledger, joined to provenance (task 01)."""
    from core.events.event_log import get_event_log
    from core.fleet import provenance

    try:
        events = get_event_log().scan(limit=event_limit)
    except Exception:  # noqa: BLE001  # fail-soft: no events means no evidence
        events = []
    try:
        repeats = [
            learning_store.store.hgetall(f"learn:repeat:{rid}")
            for rid in learning_store.store.smembers(learning_store.REPEAT_INDEX)
        ]
    except Exception:  # noqa: BLE001
        repeats = []
    ev = evidence(events, repeats, provenance.get)
    return widening_proposals(learning_store.load_all_learnings_from_store(), ev)
