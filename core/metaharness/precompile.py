"""Precompiler: proven, stable lessons into the native building blocks of each harness (task 09).

Interpretive recall spends context at every action and only helps once the agent is about to
act. Precompiled structure works before anything goes wrong, costs little or no context, and
often transfers across models (AHE: factual structure transfers, prose strategy does not).

ROUTING -- which lesson goes where (`route`):

  guard        a rule a script can check: a forbidden command or flag, named in backticks
               ("never run `git push --force`") -> one PreToolUse guard script + its rules file
  skill        a repeated multi-step procedure with a "Use when" trigger -> a skill whose
               description carries the trigger and whose body loads on demand
  subagent     a recurring kind of sub-task with its own context needs (review, research,
               migration) -> a subagent definition
  tool         a missing capability or awkward tool use -> a TOOL REQUEST note. Code for a new
               tool is a person's (or the proposer's) job; the precompiler names the gap
  instruction  a short, always-true project fact -> one line in the instruction file
  interpretive a rare, narrow or fast-changing lesson -> stays with recall at action

GATES -- a lesson compiles only when all three hold (`gates`): proven effect (task 08: interval
above zero) or strong credit (>= MIN_USEFUL useful votes); a stable scope (not edited for
STABLE_DAYS); and a premise that checks out now (no MISSING anchor -- UNCHECKED passes, said so).

TARGETS, one emitter per harness; a lesson's `harness:` scope decides which harnesses get it:

  claude-code   CLAUDE.md block, .agents/skills/ (CLAUDE.md: .claude/skills is a link to it),
                .claude/agents/, .claude/hooks/ guard + a .claude/settings.json PreToolUse entry
  codex-cli     AGENTS.md block, .agents/skills/, the guard via .codex/hooks.json
  cursor        .cursor/rules/*.mdc (Cursor's preToolUse can only deny; guard rules become rules)
  runner        .aurora/precompiled/runner_prompt.md

GENERATED, NEVER HAND-EDITED: every block and file carries "do not edit" and a source hash, the
way the library marks projections, and `check_drift` reports any hand edit. Hand-written parts
stay outside the markers. The same lessons always rebuild the same bytes.

EVERY COMPILE IS A CANDIDATE (`build`): it writes an archive candidate (overlay + contract with
the lessons it builds on); the loop (07) and a person (06) decide. Each piece cites its lessons,
and review.apply stamps `compiled_into` on each lesson -- the mark recall-at reads in hybrid
mode (task 10) to stop pushing what the harness now carries.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
KINDS = ("guard", "skill", "subagent", "tool", "instruction", "interpretive")
HARNESSES = ("claude-code", "codex-cli", "cursor", "runner")
MIN_USEFUL = 3
STABLE_DAYS = 14
MANIFEST = ".aurora/precompiled/manifest.json"
GUARD = ".claude/hooks/precompiled_guard.py"
RULES = ".claude/hooks/precompiled_rules.json"
_BEGIN = "<!-- BEGIN aurora-precompiled (generated from lessons; do not edit -- recompile) source-hash: {h} -->"
_END = "<!-- END aurora-precompiled -->"
_BLOCK_RE = re.compile(
    r"<!-- BEGIN aurora-precompiled \(generated from lessons; do not edit -- recompile\) source-hash: (\w+) -->\n(.*?)<!-- END aurora-precompiled -->\n?",
    re.S,
)
_NEVER_RE = re.compile(r"\b(?:never|don'?t|do not|must not)\s+(?:run|use|call|pass|type)?\s*`([^`]{3,120})`", re.I)
_ALWAYS_RE = re.compile(
    r"\balways\s+(?:pass|add|use)\s+`([^`]{2,60})`\s+(?:to|with|when running)\s+`([^`]{2,60})`", re.I
)
_SUBAGENT_HINTS = ("review", "research", "migration", "audit", "investigat", "subagent", "delegate")
_TOOL_HINTS = ("no command for", "no tool for", "missing tool", "wish there were", "there is no verb", "awkward tool")


def _h(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:48] or "lesson"


def _src(lesson: dict[str, Any]) -> str:
    return f"learn:experiment:{lesson.get('experiment_name')}"


# --------------------------------------------------------------------------- routing
def guard_rules(lesson: dict[str, Any]) -> list[dict[str, Any]]:
    text = f"{lesson.get('recommendation') or ''} {lesson.get('anti_pattern') or ''}"
    rules = [
        {
            "kind": "deny",
            "contains": m.group(1).strip(),
            "why": str(lesson.get("recommendation") or "")[:300],
            "source": _src(lesson),
        }
        for m in _NEVER_RE.finditer(text)
    ]
    rules += [
        {
            "kind": "require",
            "when": m.group(2).strip(),
            "contains": m.group(1).strip(),
            "why": str(lesson.get("recommendation") or "")[:300],
            "source": _src(lesson),
        }
        for m in _ALWAYS_RE.finditer(text)
    ]
    return rules


def _trigger(lesson: dict[str, Any]) -> str:
    m = re.search(r"\bUse when ([^:.]{4,200})", str(lesson.get("recommendation") or ""), re.I)
    return m.group(1).strip() if m else ""


def _steps(text: str) -> int:
    return len(re.findall(r"(?:^|\s)(?:\d+[.)]|then\b|;\s*then\b|->)", text, re.I))


def route(lesson: dict[str, Any]) -> str:
    rec = str(lesson.get("recommendation") or "")
    blob = " ".join(
        str(lesson.get(k) or "") for k in ("recommendation", "what_tried", "category", "experiment_name")
    ).lower()
    if guard_rules(lesson):
        return "guard"
    if any(h in blob for h in _TOOL_HINTS):
        return "tool"
    if any(h in blob for h in _SUBAGENT_HINTS) and _trigger(lesson):
        return "subagent"
    if _trigger(lesson) and _steps(rec) >= 2:
        return "skill"
    if (
        len(rec) <= 220
        and str(lesson.get("success") or "").lower() in ("yes", "true", "")
        and not re.search(r"\b(sometimes|might|maybe|unless|until)\b", rec, re.I)
    ):
        return "instruction"
    return "interpretive"


# --------------------------------------------------------------------------- gates
def gates(
    lesson: dict[str, Any], *, now: datetime | None = None, use: dict[str, Any] | None = None, root: Path = ROOT
) -> dict[str, Any]:
    """The three compile gates, each with its evidence."""
    now = now or datetime.now(UTC)
    pe = lesson.get("proven_effect") or ""
    try:
        ped = json.loads(pe) if isinstance(pe, str) and pe else (pe or {})
    except ValueError:
        ped = {}
    lo = (ped.get("ci") or [None])[0] if isinstance(ped, dict) else None
    useful = int((use or {}).get("useful") or 0)
    proven = (lo is not None and float(lo) > 0) or useful >= MIN_USEFUL
    try:
        ts = datetime.fromisoformat(str(lesson.get("timestamp") or "")).replace(tzinfo=UTC)
        stable = now - ts >= timedelta(days=STABLE_DAYS)
    except ValueError:
        stable = False
    try:
        from core.recall import anchors

        rv = anchors.review(dict(lesson), root=root)
        premise_ok = not any(v.status == "MISSING" for v in rv.verdicts)
        banner = rv.banner
    except Exception as e:  # noqa: BLE001  # a resolver fault is not a pass
        premise_ok, banner = False, f"[premise check failed: {e}]"
    return {
        "proven": proven,
        "proven_by": "replay" if lo is not None and float(lo) > 0 else ("credit" if useful >= MIN_USEFUL else "none"),
        "stable": stable,
        "premise": premise_ok,
        "premise_banner": banner,
        "pass": proven and stable and premise_ok,
    }


def harnesses_for(lesson: dict[str, Any], wanted: tuple[str, ...] = HARNESSES) -> list[str]:
    """Which harnesses get a lesson: its harness: scope terms, or all when it has none."""
    from core.learning import scope

    terms = [t.partition(":")[2] for t in scope.of(lesson) if t.startswith("harness:")]
    if not terms:
        return list(wanted)
    alias = {"codex-desktop": "codex-cli"}
    named = {alias.get(t, t) for t in terms}
    return [h for h in wanted if h in named or (h == "runner" and any(t.startswith("runner") for t in terms))]


# --------------------------------------------------------------------------- emitters
def _md_block(lines: list[str]) -> str:
    body = "".join(f"{ln}\n" for ln in lines)
    return f"{_BEGIN.format(h=_h(body))}\n{body}{_END}\n"


def put_block(existing: str, lines: list[str]) -> str:
    """Replace the generated block in a hand-written file (or append one). Hand text survives."""
    block = _md_block(lines)
    if _BLOCK_RE.search(existing):
        return _BLOCK_RE.sub(lambda _m: block, existing, count=1)
    return existing.rstrip("\n") + ("\n\n" if existing.strip() else "") + block


def _file_header(sources: list[str], body: str) -> str:
    return f"<!-- generated by aurora precompile from {', '.join(sources)}; do not edit -- recompile. source-hash: {_h(body)} -->\n"


def _instruction_line(lesson: dict[str, Any]) -> str:
    return f"- {str(lesson.get('recommendation') or '').strip()} (source: {_src(lesson)})"


def _with_frontmatter(front: str, body: str, sources: list[str]) -> str:
    """Frontmatter first (skills, subagents and Cursor rules are parsed from line one), then
    the generated-file header, then the body."""
    return f"---\n{front}---\n" + _file_header(sources, body) + body


def _skill(lesson: dict[str, Any]) -> tuple[str, str]:
    name = slug(str(lesson.get("experiment_name")))
    body = (
        f"\n{str(lesson.get('recommendation') or '').strip()}\n\n"
        + (
            f"What was tried before: {str(lesson.get('what_tried') or '').strip()}\n\n"
            if lesson.get("what_tried")
            else ""
        )
        + f"Source: {_src(lesson)}\n"
    )
    front = f"name: {name}\ndescription: Use when {_trigger(lesson)}.\n"
    return f".agents/skills/{name}/SKILL.md", _with_frontmatter(front, body, [_src(lesson)])


def _subagent(lesson: dict[str, Any]) -> tuple[str, str]:
    name = slug(str(lesson.get("experiment_name")))
    body = (
        f"\nYou handle one recurring kind of sub-task for the Aurora repo. {str(lesson.get('recommendation') or '').strip()}\n\n"
        f"Source: {_src(lesson)}\n"
    )
    front = f"name: {name}\ndescription: Use when {_trigger(lesson)}.\n"
    return f".claude/agents/{name}.md", _with_frontmatter(front, body, [_src(lesson)])


def _tool_request(lesson: dict[str, Any]) -> tuple[str, str]:
    name = slug(str(lesson.get("experiment_name")))
    body = (
        f"# Tool request: {lesson.get('experiment_name')}\n\nA lesson says a capability is missing or awkward. Build it as a "
        f"toolbelt kit, a CLI verb or an MCP tool, then graduate the lesson.\n\n{str(lesson.get('recommendation') or '').strip()}\n\nSource: {_src(lesson)}\n"
    )
    return f".aurora/precompiled/tool-requests/{name}.md", _file_header([_src(lesson)], body) + body


GUARD_SCRIPT = '''#!/usr/bin/env python3
"""Generated by aurora precompile: a PreToolUse guard built from lessons. Do not edit -- recompile.

Reads precompiled_rules.json beside it. A `deny` rule blocks a Bash command that contains its
text; a `require` rule warns when a command runs `when` without `contains`. Each message names
the lesson it came from. Fail-open: any error lets the call through.
"""
import json
import os
import sys


def main():
    try:
        data = json.load(sys.stdin)
        cmd = str((data.get("tool_input") or {}).get("command") or "")
        rules = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "precompiled_rules.json")))["rules"]
    except Exception:
        return 0
    for r in rules:
        if r["kind"] == "deny" and r["contains"] in cmd:
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                  "permissionDecisionReason": f"blocked by lesson {r['source']}: {r['why']}"}}))
            return 0
    notes = [f"lesson {r['source']}: {r['why']}" for r in rules if r["kind"] == "require" and r["when"] in cmd and r["contains"] not in cmd]
    if notes:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": " | ".join(notes)}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''


def _settings_with_guard(existing: str, command: str) -> str:
    try:
        doc = json.loads(existing) if existing.strip() else {}
    except ValueError:
        doc = {}
    pre = doc.setdefault("hooks", {}).setdefault("PreToolUse", [])
    pre[:] = [e for e in pre if "precompiled_guard.py" not in json.dumps(e)]
    pre.append({"matcher": "Bash", "hooks": [{"type": "command", "command": command}]})
    return json.dumps(doc, indent=2) + "\n"


def emit(lessons: list[dict[str, Any]], harness: str, live_root: Path = ROOT) -> dict[str, str]:
    """relative path -> file content for one harness. Deterministic: sorted by lesson name."""
    ls = sorted(lessons, key=lambda x: str(x.get("experiment_name")))
    by = {k: [x for x in ls if route(x) == k] for k in KINDS}
    files: dict[str, str] = {}

    def live(rel: str) -> str:
        p = live_root / rel
        return p.read_text(encoding="utf-8") if p.exists() else ""

    instr = [_instruction_line(x) for x in by["instruction"]]
    if harness == "cursor":
        instr += [_instruction_line(x) for x in by["guard"]]  # Cursor's preToolUse cannot inject; say it as a rule
        for x in by["skill"] + by["subagent"]:
            _, text = _skill(x)
            files[f".cursor/rules/precompiled-{slug(str(x.get('experiment_name')))}.mdc"] = text
        if instr:
            body = "".join(f"{ln}\n" for ln in instr)
            files[".cursor/rules/precompiled-facts.mdc"] = _with_frontmatter(
                "description: Project facts compiled from lessons\nalwaysApply: true\n",
                body,
                [_src(x) for x in by["instruction"] + by["guard"]],
            )
        return files
    if harness == "runner":
        if instr or by["skill"]:
            lines = instr + [
                f"- {str(x.get('recommendation') or '').strip()} (source: {_src(x)})"
                for x in by["skill"] + by["subagent"]
            ]
            body = "".join(f"{ln}\n" for ln in lines)
            files[".aurora/precompiled/runner_prompt.md"] = _file_header([_src(x) for x in ls], body) + body
        return files
    if instr:
        rel = "CLAUDE.md" if harness == "claude-code" else "AGENTS.md"
        files[rel] = put_block(live(rel), instr)
    for x in by["skill"]:
        rel, text = _skill(x)
        files[rel] = text
    if harness == "claude-code":
        for x in by["subagent"]:
            rel, text = _subagent(x)
            files[rel] = text
    for x in by["tool"]:
        rel, text = _tool_request(x)
        files[rel] = text
    rules = [r for x in by["guard"] for r in guard_rules(x)]
    if rules:
        files[GUARD] = GUARD_SCRIPT
        doc: dict[str, Any] = {"rules": rules, "source_hash": _h(json.dumps(rules, sort_keys=True))}
        files[RULES] = json.dumps(doc, indent=1, sort_keys=True) + "\n"
        cmd = f'python3 "$CLAUDE_PROJECT_DIR/{GUARD}"'
        if harness == "claude-code":
            files[".claude/settings.json"] = _settings_with_guard(live(".claude/settings.json"), cmd)
        else:
            files[".codex/hooks.json"] = _settings_with_guard(live(".codex/hooks.json"), cmd)
    return files


# --------------------------------------------------------------------------- manifest, drift
def manifest(lessons: list[dict[str, Any]], per_harness: dict[str, dict[str, str]]) -> dict[str, Any]:
    pieces = []
    for h, files in sorted(per_harness.items()):
        for rel, text in sorted(files.items()):
            cites = sorted({x["experiment_name"] for x in lessons if _src(x) in text})
            pieces.append(
                {"harness": h, "path": rel, "lessons": cites, "hash": _h(text), "block": bool(_BLOCK_RE.search(text))}
            )
    lesson_map: dict[str, dict[str, list[str]]] = {}
    for p in pieces:
        for n in p["lessons"]:
            lesson_map.setdefault(n, {}).setdefault(p["harness"], []).append(p["path"])
    return {"pieces": pieces, "lessons": lesson_map, "kinds": {x["experiment_name"]: route(x) for x in lessons}}


def check_drift(root: Path) -> list[str]:
    """Hand edits to generated content under `root` (an overlay or the live tree).

    A block inside a hand-written file must still match the hash in its own marker -- the text
    around it may change freely. A wholly generated file must match the manifest's hash. A
    settings file only has to still carry the guard entry (the rest of it is hand-written)."""
    out = []
    mp = root / MANIFEST
    if not mp.exists():
        return out
    m = json.loads(mp.read_text(encoding="utf-8"))
    for p in m["pieces"]:
        f = root / p["path"]
        if not f.exists():
            out.append(f"{p['path']}: generated file is missing")
            continue
        text = f.read_text(encoding="utf-8")
        if p["path"] in (".claude/settings.json", ".codex/hooks.json"):
            if "precompiled_guard.py" not in text:
                out.append(f"{p['path']}: the generated guard entry was removed by hand")
            continue
        blk = _BLOCK_RE.search(text)
        if p.get("block"):
            if not blk:
                out.append(f"{p['path']}: the generated block was removed by hand")
            elif _h(blk.group(2)) != blk.group(1):
                out.append(f"{p['path']}: the generated block was edited by hand")
        elif _h(text) != p["hash"]:
            out.append(f"{p['path']}: the generated file was edited by hand")
    return out


# --------------------------------------------------------------------------- plan and build
def _use_for(store: Any, lesson: dict[str, Any]) -> dict[str, Any]:
    try:
        from core.recall.at_action import _load_use

        return _load_use(store, _src(lesson))
    except Exception:  # noqa: BLE001  # no counters means no credit
        return {}


def plan(
    lessons: list[dict[str, Any]], *, store: Any = None, now: datetime | None = None, root: Path = ROOT
) -> list[dict[str, Any]]:
    rows = []
    for x in sorted(lessons, key=lambda y: str(y.get("experiment_name"))):
        if str(x.get("graduated") or "").strip() or str(x.get("benched") or "").strip():
            continue
        g = gates(x, now=now, use=_use_for(store, x) if store is not None else {}, root=root)
        rows.append({"lesson": x.get("experiment_name"), "kind": route(x), "harnesses": harnesses_for(x), "gates": g})
    return rows


def build(
    lessons: list[dict[str, Any]],
    *,
    base: str = "baseline",
    name: str = "",
    harnesses: tuple[str, ...] = HARNESSES,
    live_root: Path = ROOT,
    store: Any = None,
    now: datetime | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Compile the lessons that pass the gates (all of them with force=True) into a candidate."""
    from core.metaharness import replay

    rows = {r["lesson"]: r for r in plan(lessons, store=store, now=now, root=live_root)}
    chosen = [
        x
        for x in lessons
        if x.get("experiment_name") in rows
        and rows[x["experiment_name"]]["kind"] != "interpretive"
        and (force or rows[x["experiment_name"]]["gates"]["pass"])
    ]
    if not chosen:
        return {"built": False, "why": "no lesson passed the gates", "plan": list(rows.values())}
    per_h: dict[str, dict[str, str]] = {}
    for h in harnesses:
        mine = [x for x in chosen if h in harnesses_for(x, harnesses)]
        if mine:
            per_h[h] = emit(mine, h, live_root)
    merged: dict[str, str] = {}
    for files in per_h.values():
        merged.update(files)
    man = manifest(chosen, per_h)
    merged[MANIFEST] = json.dumps(man, indent=1, sort_keys=True) + "\n"
    digest = _h(json.dumps(merged, sort_keys=True))
    name = name or f"precompiled-{digest[:8]}"
    card = replay.candidate(base)
    replay.create_candidate(
        name,
        overlay_from=card["overlay"],
        harness=card["harness"],
        model=card.get("model") or "",
        effort=card.get("effort") or "",
        command=card.get("command") or [],
        env=card.get("env") or {},
        parent=base,
        hypothesis=f"precompile {len(chosen)} lesson(s) into {sorted({man['kinds'][x['experiment_name']] for x in chosen})}",
    )
    overlay = Path(replay.candidate(name)["overlay"])
    for rel, text in merged.items():
        (overlay / rel).parent.mkdir(parents=True, exist_ok=True)
        (overlay / rel).write_text(text, encoding="utf-8")

    def piece_kind(p: dict[str, Any]) -> str:
        if p["path"] in (".claude/settings.json", ".codex/hooks.json"):
            return "setting"
        if p["path"] in (GUARD, RULES):
            return "guard"
        return man["kinds"][p["lessons"][0]] if p["lessons"] else "instruction"

    edits = [
        {
            "kind": piece_kind(p),
            "path": p["path"],
            "why": f"compiled from {', '.join(p['lessons']) or 'the guard rules'}",
        }
        for p in man["pieces"]
    ]
    contract = {
        "hypothesis": replay.candidate(name)["hypothesis"],
        "edits": edits,
        "predictions": [{"metric": "tokens", "expect": "-5%"}, {"metric": "pass_rate", "expect": "+0%"}],
        "lessons": sorted(x["experiment_name"] for x in chosen),
        "mode": "precompiled",
        "proposer": "precompiler",
    }
    from core.metaharness import archive

    (archive.cdir(name) / "contract.json").write_text(json.dumps(contract, indent=1), encoding="utf-8")
    return {
        "built": True,
        "candidate": name,
        "lessons": contract["lessons"],
        "kinds": man["kinds"],
        "files": sorted(merged),
        "harnesses": sorted(per_h),
    }


def stamp_compiled(overlay: Path, candidate: str, store: Any = None) -> int:
    """After review.apply: record on each compiled lesson where it now lives. Returns lessons."""
    mp = overlay / MANIFEST
    if not mp.exists():
        return 0
    m = json.loads(mp.read_text(encoding="utf-8"))
    if store is None:
        from core.learning.learning_store import get_learning_store_instance

        store = get_learning_store_instance().store
    n = 0
    for lesson, where in m["lessons"].items():
        key = f"learn:experiment:{lesson}"
        if store.exists(key):
            store.hset(
                key,
                mapping={
                    "compiled_into": json.dumps(
                        {
                            "candidate": candidate,
                            "harnesses": where,
                            "at": datetime.now(UTC).isoformat(timespec="seconds"),
                        }
                    )
                },
            )
            n += 1
    return n


def demote_unused(root: Path, used: dict[str, int]) -> list[str]:
    """Compiled pieces whose usage telemetry (task 11, stage 0) is zero: demotion candidates."""
    mp = root / MANIFEST
    if not mp.exists():
        return []
    return [p["path"] for p in json.loads(mp.read_text(encoding="utf-8"))["pieces"] if not used.get(p["path"])]
