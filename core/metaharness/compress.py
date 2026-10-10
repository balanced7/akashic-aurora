"""Harness compression: shrink a working harness to the pieces that move results (task 11).

Every piece costs context, attention and upkeep, and studies of agent scaffolds find the
"everything on" setup often LOSES to a subset because pieces interfere. In one study 56% of
submodularity checks failed, so greedy one-at-a-time removal is unreliable -- yet main effects
still explained most of the variance (R^2 0.92). So: screen main effects cheaply, then look for
interactions only where they matter. Leave-one-out needs N x R runs and misses redundancy (two
pieces that cover for each other each look useless alone, but removing both hurts).

THE STAGED METHOD
  0  free telemetry   read existing traces: skills, subagents and hooks never used, lessons
                      never surfaced -> drop candidates, at zero new runs
  1  group            pieces into functional groups (a CLAUDE.md section, a skill, a hook
                      family) -- AttriBoT's hierarchy: attribute groups first, items inside later
  2  screen groups    a Plackett-Burman design estimates ALL main effects from the next multiple
                      of 4 above the group count; its FOLDOVER (the negated design) separates
                      main effects from two-factor interactions
  3  inside groups    random keep/drop masks biased to keep ~80% (stay near the working setup),
                      and a sparse linear model (Lasso), as ContextCite does
  4  confirm          noisy delta debugging on the few borderline items, each step a paired
                      sequential test (ddmin assumes a deterministic test; agents are not); then
                      a final NON-INFERIORITY check of the compressed harness against the full
                      one, plus a win on tokens. Then human review (task 06).

A PIECE has an id, a group and a kind, and `apply_mask` builds the overlay that switches any
set of pieces off: instruction-file sections are cut, skill and subagent files are deleted
(replay's overlay deletion list), hook entries are removed from settings.

The pure statistics take an `evaluate(mask, scenario) -> score` function, so the planted test
(5 useful, 2 redundant-pair, 20 useless pieces) runs offline; `replay_evaluator` is the
production adapter, which builds a candidate per mask and replays it (tasks 04, 05).
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import re
import shutil
from collections.abc import Callable
from pathlib import Path
from statistics import fmean, pstdev
from typing import Any

import numpy as np

Evaluate = Callable[[dict[str, bool], str], float]
ROOT_DEFAULT = Path(__file__).resolve().parents[2]


# --------------------------------------------------------------------------- piece registry
def _sections(text: str) -> list[tuple[str, int, int]]:
    """(heading, start, end) of each `## ` section, by character offsets."""
    marks = [(m.group(1).strip(), m.start()) for m in re.finditer(r"^## (.+)$", text, re.M)]
    return [(h, s, marks[i + 1][1] if i + 1 < len(marks) else len(text)) for i, (h, s) in enumerate(marks)]


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40]


def pieces(root: Path) -> list[dict[str, Any]]:
    """Every switchable harness piece under `root` (a live tree or a merged overlay)."""
    out: list[dict[str, Any]] = []
    for doc in ("CLAUDE.md", "AGENTS.md"):
        p = root / doc
        if p.exists():
            for h, _, _ in _sections(p.read_text(encoding="utf-8")):
                out.append(
                    {
                        "id": f"section:{doc}#{_slug(h)}",
                        "group": f"{doc}#{_slug(h)}",
                        "kind": "section",
                        "path": doc,
                        "heading": h,
                    }
                )
    for base in (".agents/skills", ".claude/skills"):
        d = root / base
        if d.exists() and not d.is_symlink():
            out.extend(
                {"id": f"skill:{sk.name}", "group": "skills", "kind": "skill", "path": f"{base}/{sk.name}"}
                for sk in sorted(x for x in d.iterdir() if (x / "SKILL.md").exists())
            )
    ag = root / ".claude" / "agents"
    if ag.exists():
        out.extend(
            {"id": f"subagent:{f.stem}", "group": "subagents", "kind": "subagent", "path": f".claude/agents/{f.name}"}
            for f in sorted(ag.glob("*.md"))
        )
    st = root / ".claude" / "settings.json"
    if st.exists():
        try:
            hooks = json.loads(st.read_text(encoding="utf-8")).get("hooks") or {}
        except ValueError:
            hooks = {}
        for event, entries in sorted(hooks.items()):
            for i, e in enumerate(entries):
                cmd = " ".join(h.get("command", "") for h in e.get("hooks", []))
                name = (re.findall(r"([\w.-]+\.py)", cmd) or [f"{event}-{i}"])[-1]
                out.append(
                    {
                        "id": f"hook:{event}:{name}",
                        "group": f"hooks:{event}",
                        "kind": "hook",
                        "path": ".claude/settings.json",
                        "event": event,
                        "match": name,
                    }
                )
    seen: set[str] = set()
    uniq = []
    for p in out:
        if p["id"] not in seen:
            seen.add(p["id"])
            uniq.append(p)
    return uniq


def apply_mask(root: Path, items: list[dict[str, Any]], keep: dict[str, bool], out: Path) -> Path:
    """Write an overlay into `out` that switches off every piece with keep[id] False."""
    from core.metaharness.replay import OVERLAY_DELETE

    off = [p for p in items if not keep.get(p["id"], True)]
    out.mkdir(parents=True, exist_ok=True)
    deletes: list[str] = []
    for doc in sorted({p["path"] for p in off if p["kind"] == "section"}):
        text = (root / doc).read_text(encoding="utf-8")
        cut = {p["heading"] for p in off if p["kind"] == "section" and p["path"] == doc}
        for h, s, e in reversed(_sections(text)):
            if h in cut:
                text = text[:s] + text[e:]
        (out / doc).write_text(text, encoding="utf-8")
    deletes += [p["path"] for p in off if p["kind"] in ("skill", "subagent")]
    hook_off = [p for p in off if p["kind"] == "hook"]
    if hook_off:
        doc = json.loads((root / ".claude" / "settings.json").read_text(encoding="utf-8"))
        for p in hook_off:
            doc["hooks"][p["event"]] = [e for e in doc["hooks"].get(p["event"], []) if p["match"] not in json.dumps(e)]
        (out / ".claude").mkdir(parents=True, exist_ok=True)
        (out / ".claude" / "settings.json").write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    if deletes:
        (out / OVERLAY_DELETE).parent.mkdir(parents=True, exist_ok=True)
        (out / OVERLAY_DELETE).write_text("\n".join(sorted(deletes)) + "\n", encoding="utf-8")
    return out


# --------------------------------------------------------------------------- stage 0: telemetry
def telemetry(run_dirs: list[Path], items: list[dict[str, Any]]) -> dict[str, int]:
    """Uses per piece id, read from raw traces: Skill and Task (subagent) tool calls, hook
    script names in hook output, and instruction sections whose heading words the agent quotes.
    A piece with zero uses across many runs is a drop candidate at no cost."""
    uses = {p["id"]: 0 for p in items}
    for rd in run_dirs:
        t = rd / "transcript.jsonl"
        if not t.exists():
            continue
        raw = t.read_text(encoding="utf-8", errors="replace")
        for line in raw.splitlines():
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            for b in ((ev.get("message") or {}).get("content") or []) if isinstance(ev, dict) else []:
                if not isinstance(b, dict) or b.get("type") != "tool_use":
                    continue
                inp = b.get("input") or {}
                if b.get("name") == "Skill":
                    sid = f"skill:{inp.get('skill') or inp.get('name') or ''}"
                    if sid in uses:
                        uses[sid] += 1
                if b.get("name") in ("Task", "Agent"):
                    sid = f"subagent:{inp.get('subagent_type') or ''}"
                    if sid in uses:
                        uses[sid] += 1
        low = raw.lower()
        for p in items:
            if p["kind"] == "hook" and p["match"].lower() in low:
                uses[p["id"]] += 1
            if p["kind"] == "section" and len(p["heading"]) > 6 and p["heading"].lower() in low:
                uses[p["id"]] += 1
    return uses


def drop_candidates(uses: dict[str, int], min_runs: int, n_runs: int) -> list[str]:
    """Never-used pieces, once there are enough runs to say "never" with a straight face."""
    return sorted(k for k, v in uses.items() if v == 0) if n_runs >= min_runs else []


# --------------------------------------------------------------------------- stage 2: screening
def _is_prime(n: int) -> bool:
    return n > 1 and all(n % d for d in range(2, int(n**0.5) + 1))


def _paley1(q: int) -> np.ndarray:
    """Hadamard matrix of order q+1, q prime with q % 4 == 3 (Paley construction I)."""
    qr = {(i * i) % q for i in range(1, q)}
    chi = [0] + [1 if i in qr else -1 for i in range(1, q)]
    jac = np.array([[chi[(j - i) % q] for j in range(q)] for i in range(q)])
    h = np.ones((q + 1, q + 1), dtype=int)
    h[1:, 0] = -1
    h[1:, 1:] = jac + np.eye(q, dtype=int)
    return h


def _paley2(q: int) -> np.ndarray:
    """Hadamard matrix of order 2(q+1), q prime with q % 4 == 1 (Paley construction II)."""
    qr = {(i * i) % q for i in range(1, q)}
    chi = [0] + [1 if i in qr else -1 for i in range(1, q)]
    c = np.zeros((q + 1, q + 1), dtype=int)
    c[0, 1:] = 1
    c[1:, 0] = 1
    c[1:, 1:] = np.array([[chi[(j - i) % q] for j in range(q)] for i in range(q)])
    a = np.array([[1, -1], [-1, -1]])
    b = np.array([[1, 1], [1, -1]])
    return np.kron(c, a) + np.kron(np.eye(q + 1, dtype=int), b)


def hadamard(n: int) -> np.ndarray:
    """A Hadamard matrix of order n (n a multiple of 4 within what Sylvester and Paley reach)."""
    if n == 1:
        return np.array([[1]])
    if n % 4 and n != 2:
        raise ValueError("Hadamard order must be 1, 2 or a multiple of 4")
    if n & (n - 1) == 0:
        h = np.array([[1]])
        while h.shape[0] < n:
            h = np.block([[h, h], [h, -h]])
        return h
    if _is_prime(n - 1) and (n - 1) % 4 == 3:
        return _paley1(n - 1)
    if n % 2 == 0 and _is_prime(n // 2 - 1) and (n // 2 - 1) % 4 == 1:
        return _paley2(n // 2 - 1)
    if n % 2 == 0 and (n // 2) % 4 == 0:
        h = hadamard(n // 2)
        return np.block([[h, h], [h, -h]])
    raise ValueError(f"no Hadamard construction here for order {n}")


def _is_hadamard(h: np.ndarray) -> bool:
    n = h.shape[0]
    return bool(np.array_equal(h @ h.T, n * np.eye(n, dtype=int)))


def pb_design(k: int) -> np.ndarray:
    """A Plackett-Burman design for k factors: runs x k of +1 (keep) / -1 (drop), with runs the
    smallest constructible multiple of 4 above k. Columns are mutually orthogonal and balanced."""
    n = 4 * math.ceil((k + 1) / 4)
    while True:
        try:
            h = hadamard(n)
            if _is_hadamard(h):
                break
        except ValueError:
            pass
        n += 4
    h = h * h[:, :1]  # normalise the first column to +1
    return h[:, 1 : k + 1]


def foldover(design: np.ndarray) -> np.ndarray:
    return np.vstack([design, -design])


def main_effects(design: np.ndarray, y: list[float], *, level: float = 0.95) -> list[dict[str, float]]:
    """Per factor: effect = mean(y | keep) - mean(y | drop), with an OLS standard error from the
    residuals of the main-effects model (orthogonal columns: one regression, exact)."""
    x = np.column_stack([np.ones(len(y)), design])
    yv = np.asarray(y, dtype=float)
    beta, *_ = np.linalg.lstsq(x, yv, rcond=None)
    resid = yv - x @ beta
    dof = max(1, len(y) - x.shape[1])
    sigma = math.sqrt(float(resid @ resid) / dof) if len(y) > x.shape[1] else 0.0
    se_beta = sigma / math.sqrt(len(y))
    z = 1.959963984540054 if abs(level - 0.95) < 1e-9 else 1.6448536269514722
    out = []
    for j in range(design.shape[1]):
        eff = 2 * float(beta[j + 1])
        se = 2 * se_beta
        out.append({"effect": eff, "se": se, "lo": eff - z * se, "hi": eff + z * se})
    return out


# --------------------------------------------------------------------------- stage 3: Lasso
def lasso(x: np.ndarray, y: list[float], alpha: float, *, iters: int = 500) -> np.ndarray:
    """Coordinate-descent Lasso on centred columns; returns coefficients (no intercept)."""
    xm = x - x.mean(0)
    yv = np.asarray(y, dtype=float) - float(np.mean(y))
    n, p = xm.shape
    w = np.zeros(p)
    norms = (xm**2).sum(0) / n
    for _ in range(iters):
        prev = w.copy()
        for j in range(p):
            if norms[j] == 0:
                continue
            r = yv - xm @ w + xm[:, j] * w[j]
            rho = float(xm[:, j] @ r) / n
            w[j] = math.copysign(max(abs(rho) - alpha, 0.0), rho) / norms[j]
        if np.max(np.abs(w - prev)) < 1e-7:
            break
    return w


def random_masks(ids: list[str], n: int, *, keep: float = 0.8, seed: int = 0) -> list[dict[str, bool]]:
    rng = random.Random(seed)
    return [{i: rng.random() < keep for i in ids} for _ in range(n)]


# --------------------------------------------------------------------------- stage 4: confirm
def non_inferior(diffs: list[float], margin: float, *, level: float = 0.90) -> bool:
    """One-sided: the lower bound of the mean paired difference (new - full) is above -margin."""
    if len(diffs) < 2:
        return False
    z = 1.2815515655446004 if abs(level - 0.90) < 1e-9 else 1.6448536269514722
    se = pstdev(diffs) * math.sqrt(len(diffs) / (len(diffs) - 1)) / math.sqrt(len(diffs))
    return fmean(diffs) - z * se > -margin


def _paired(
    evaluate: Evaluate, mask: dict[str, bool], full: dict[str, bool], scenarios: list[str], cache: dict[str, float]
) -> list[float]:
    def score(m: dict[str, bool], s: str) -> float:
        key = hashlib.sha256(json.dumps([sorted(k for k, v in m.items() if not v), s]).encode()).hexdigest()
        if key not in cache:
            cache[key] = float(evaluate(m, s))
        return cache[key]

    return [score(mask, s) - score(full, s) for s in scenarios]


def sequential_ok(
    evaluate: Evaluate,
    mask: dict[str, bool],
    full: dict[str, bool],
    scenarios: list[str],
    margin: float,
    cache: dict[str, float],
    *,
    step: int = 5,
) -> bool:
    """Paired sequential test: add scenarios in steps until the removal is shown harmless
    (non-inferior) or harmful (the upper bound sits below -margin), or the scenarios run out."""
    for n in range(step, len(scenarios) + step, step):
        d = _paired(evaluate, mask, full, scenarios[:n], cache)
        if non_inferior(d, margin):
            return True
        if len(d) >= 2:
            se = pstdev(d) * math.sqrt(len(d) / (len(d) - 1)) / math.sqrt(len(d))
            if fmean(d) + 1.2815515655446004 * se < -margin:
                return False
    return False


def noisy_ddmin(candidates: list[str], ok: Callable[[set[str]], bool]) -> set[str]:
    """Delta debugging for the LARGEST removable subset: `ok(removed)` says whether removing
    that set keeps the harness acceptable. Greedy by halves, then single items (ddmin's
    complement step), so redundant pairs are tested together, not only one at a time."""
    removed: set[str] = set()
    pool = list(candidates)
    n = 2
    while pool:
        chunk = max(1, math.ceil(len(pool) / n))
        progressed = False
        for i in range(0, len(pool), chunk):
            part = set(pool[i : i + chunk])
            if ok(removed | part):
                removed |= part
                pool = [x for x in pool if x not in part]
                progressed = True
                break
        if not progressed:
            if chunk == 1:
                break
            n = min(len(pool), n * 2)
    return removed


# --------------------------------------------------------------------------- the pipeline
def compress(
    items: list[dict[str, Any]],
    evaluate: Evaluate,
    scenarios: list[str],
    *,
    uses: dict[str, int] | None = None,
    min_runs_for_telemetry: int = 20,
    n_telemetry_runs: int = 0,
    group_alpha: float = 0.1,
    item_masks: int = 80,
    lasso_alpha: float = 0.01,
    margin: float = 0.03,
    screen_scenarios: int = 20,
    seed: int = 0,
) -> dict[str, Any]:
    """Run stages 0-4 and return the kept / dropped pieces with the evidence for each."""
    ids = [p["id"] for p in items]
    full = dict.fromkeys(ids, True)
    cache: dict[str, float] = {}
    runs = 0

    def ev(mask: dict[str, bool], s: str) -> float:
        nonlocal runs
        key = hashlib.sha256(json.dumps([sorted(k for k, v in mask.items() if not v), s]).encode()).hexdigest()
        if key not in cache:
            runs += 1
            cache[key] = float(evaluate(mask, s))
        return cache[key]

    # stage 0
    stage0 = drop_candidates(uses or {}, min_runs_for_telemetry, n_telemetry_runs)
    # stage 1
    groups: dict[str, list[str]] = {}
    for p in items:
        groups.setdefault(p["group"], []).append(p["id"])
    gnames = sorted(groups)
    # stage 2: groups on/off by PB + foldover, each config on the screening scenarios
    design = foldover(pb_design(len(gnames)))
    screen = scenarios[:screen_scenarios]
    ys = []
    for row in design:
        mask = {i: bool(row[gnames.index(p["group"])] > 0) for p in items for i in [p["id"]]}
        ys.append(fmean(ev(mask, s) for s in screen))
    eff = main_effects(design, ys)
    group_effects = {g: eff[j] for j, g in enumerate(gnames)}
    hot = [g for g in gnames if group_effects[g]["lo"] > 0 or abs(group_effects[g]["effect"]) >= group_alpha]
    cold = [g for g in gnames if g not in hot]
    # stage 3: inside the groups that matter, Lasso over random masks (others held ON)
    inner = [i for g in hot for i in groups[g]]
    coef: dict[str, float] = {}
    if inner:
        masks = random_masks(inner, item_masks, seed=seed)
        y3 = [fmean(ev({**full, **m}, s) for s in screen) for m in masks]
        x3 = np.array([[1.0 if m[i] else 0.0 for i in inner] for m in masks])
        w = lasso(x3, y3, lasso_alpha)
        coef = {i: float(w[k]) for k, i in enumerate(inner)}
    # stage 4: everything in cold groups, stage-0 drops, and zero-coefficient items are
    # candidates; noisy ddmin decides which can go together, by paired sequential tests
    cand = sorted(set(stage0) | {i for g in cold for i in groups[g]} | {i for i, c in coef.items() if abs(c) < 1e-9})

    def ok(removed: set[str]) -> bool:
        return sequential_ok(ev, {**full, **dict.fromkeys(removed, False)}, full, scenarios, margin, cache)

    removed = noisy_ddmin(cand, ok)
    final = {**full, **dict.fromkeys(removed, False)}
    diffs = [ev(final, s) - ev(full, s) for s in scenarios]
    return {
        "kept": sorted(i for i in ids if final[i]),
        "dropped": sorted(removed),
        "stage0_drop_candidates": stage0,
        "group_effects": group_effects,
        "hot_groups": hot,
        "item_coefficients": coef,
        "non_inferior": non_inferior(diffs, margin),
        "mean_diff": fmean(diffs) if diffs else 0.0,
        "task_runs": runs,
        "pb_runs": int(design.shape[0]),
    }


# --------------------------------------------------------------------------- production adapter
def replay_evaluator(
    base: str, root: Path, items: list[dict[str, Any]], *, repo: Path, trials: int = 1, runner: list[str] | None = None
) -> Evaluate:
    """evaluate(mask, scenario) for real: a candidate per distinct mask (cached), replayed and
    graded; the score is the functional grade (correctness for rubric-only scenarios)."""
    from core.metaharness import graders, replay

    made: dict[str, str] = {}

    def candidate_for(mask: dict[str, bool]) -> str:
        off = sorted(k for k, v in mask.items() if not v)
        h = hashlib.sha256(json.dumps(off).encode()).hexdigest()[:10]
        if h not in made:
            name = f"cmp-{base}-{h}"
            card = replay.candidate(base)
            replay.create_candidate(
                name,
                overlay_from=card["overlay"],
                harness=card["harness"],
                model=card.get("model") or "",
                effort=card.get("effort") or "",
                command=card.get("command") or [],
                env=card.get("env") or {},
                memory=card.get("memory") or "",
                parent=base,
                hypothesis=f"compression mask: {len(off)} piece(s) off",
            )
            ov = Path(replay.candidate(name)["overlay"])
            tmp = ov.parent / "mask"
            if tmp.exists():
                shutil.rmtree(tmp)
            apply_mask(root, items, mask, tmp)
            shutil.copytree(tmp, ov, dirs_exist_ok=True)
            shutil.rmtree(tmp)
            made[h] = name
        return made[h]

    def evaluate(mask: dict[str, bool], scenario: str) -> float:
        cand = candidate_for(mask)
        scores = []
        for r in replay.run(cand, scenario, trials=trials, repo=repo):
            if r.get("run_dir"):
                g = graders.grade_run(Path(r["run_dir"]), scenario, repo=repo, runner=runner)
                v = (g.get("functional") or {}).get("score")
                v = (g.get("correctness") or {}).get("score") if v is None else v
                scores.append(float(v or 0.0))
        return fmean(scores) if scores else 0.0

    return evaluate


class RunCapReached(Exception):
    pass


def run_compression(
    base: str,
    scenarios: list[str],
    *,
    repo: Path,
    max_runs: int,
    root: Path | None = None,
    trials: int = 1,
    runner: list[str] | None = None,
    margin: float = 0.03,
    screen_scenarios: int = 20,
    item_masks: int = 80,
) -> dict[str, Any]:
    """Compress candidate `base` for real: registry from its merged config, telemetry from its
    runs, the staged search through replay, then a compressed candidate whose contract records
    every piece's estimated effect -- queued for human review only if it is non-inferior."""
    from core.metaharness import archive, graders, replay, review

    card = replay.candidate(base)
    merged = Path(card["overlay"]).parent / "merged"
    if merged.exists():
        shutil.rmtree(merged)
    src = root or repo
    for rel in ("CLAUDE.md", "AGENTS.md", ".claude/settings.json", ".claude/agents", ".agents/skills"):
        p = src / rel
        if p.is_dir():
            shutil.copytree(p, merged / rel, symlinks=False, dirs_exist_ok=True)
        elif p.exists():
            (merged / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, merged / rel)
    shutil.copytree(card["overlay"], merged, dirs_exist_ok=True)
    items = pieces(merged)
    runs = [rd for s in scenarios for rd in replay.runs_for(base, s)]
    uses = telemetry(runs, items)
    inner = replay_evaluator(base, merged, items, repo=repo, trials=trials, runner=runner)
    spent = {"n": 0}

    def capped(mask: dict[str, bool], s: str) -> float:
        if spent["n"] >= max_runs:
            raise RunCapReached(f"compression stopped at its cap of {max_runs} task-runs")
        spent["n"] += 1
        return inner(mask, s)

    try:
        res = compress(
            items,
            capped,
            scenarios,
            uses=uses,
            n_telemetry_runs=len(runs),
            margin=margin,
            screen_scenarios=screen_scenarios,
            item_masks=item_masks,
        )
    except RunCapReached as e:
        return {"built": False, "why": str(e), "task_runs": spent["n"]}
    keep = {p["id"]: p["id"] in res["kept"] for p in items}
    name = f"compressed-{base}"
    replay.create_candidate(
        name,
        overlay_from=card["overlay"],
        harness=card["harness"],
        model=card.get("model") or "",
        effort=card.get("effort") or "",
        command=card.get("command") or [],
        env=card.get("env") or {},
        memory=card.get("memory") or "",
        parent=base,
        hypothesis=f"compression: drop {len(res['dropped'])} of {len(items)} pieces, non-inferior within {margin}",
    )
    apply_mask(merged, items, keep, Path(replay.candidate(name)["overlay"]))
    contract = {
        "hypothesis": replay.candidate(name)["hypothesis"],
        "edits": [
            {
                "kind": {"section": "instruction", "skill": "skill", "subagent": "subagent", "hook": "hook"}[p["kind"]],
                "path": p["path"],
                "why": f"drop {p['id']}",
            }
            for p in items
            if p["id"] in res["dropped"]
        ],
        "predictions": [{"metric": "pass_rate", "expect": "+0%"}, {"metric": "tokens", "expect": "-5%"}],
        "piece_effects": {"groups": res["group_effects"], "items": res["item_coefficients"], "uses": uses},
        "mode": "compression",
        "proposer": "compressor",
    }
    (archive.cdir(name) / "contract.json").write_text(json.dumps(contract, indent=1), encoding="utf-8")
    out = {
        "built": True,
        "candidate": name,
        **{k: res[k] for k in ("kept", "dropped", "non_inferior", "mean_diff", "task_runs")},
    }
    if res["non_inferior"] and res["dropped"]:
        v = graders.compare(base, name, scenarios)
        it = review.enqueue(name, v, predicted=contract["hypothesis"])
        review.render(it["id"])
        out["queued_for_review"] = it["id"]
    return out
