"""ask -- a synchronous helper call, with no seat behind it (T171).

Daniil, 2026-08-04: "what if you could quickly invoke with a verb a deepseek instance to help you
with something... this might help reduce your cognitive load if you could quickly ask for help
yourself."

THE EVIDENCE THIS IS NEEDED. Across two multi-seat rounds that night, NINE seat-tasks produced TWO
findings that reached the conductor. The rest died to cursor tail-seeding, dedup collapse, budget
exhaustion returning "", and wedges -- and most of the session went on seat plumbing rather than on
getting help. Asking had become more expensive than doing it myself, so I stopped asking.

ASK IS NOT A SEAT, AND THAT IS THE WHOLE DESIGN. A seat carries identity, a singleton lock, cursors,
a mailbox, a heartbeat, a roster row, a wake listener and reaper protection. Every one of those
exists so a peer can be addressed ASYNCHRONOUSLY and survive without the caller. A synchronous ask
needs none of it: it is born, it answers, it dies inside one call. Today every ask has to become a
seat, which is why asking costs what it costs.

DELIBERATELY ABSENT IN v1, each for a reason:
  * TOOLS -- a tool loop is the seat path (budget, hops, wedges). Single turn first; see how it
    actually gets used before adding the machinery that broke the last two rounds.
  * PERSISTENT MEMORY -- persistence is what makes a seat. Memory that must cross invocations
    belongs in the store (learn/note) where the whole fleet can inspect it, not in N private
    shadow histories nobody can audit.
  * WRITE ACCESS -- a helper that can write is a seat with extra steps, and needs all the
    machinery back.

IT RETURNS A BoundaryOutcome, which is the point of having built one. In particular a response cut
off by `finish_reason == "length"` comes back as PARTIALLY -- the T169 lesson generalized: a helper
that ran out of room hands back what it has, marked, instead of looking complete or returning "".
"""
from __future__ import annotations

import concurrent.futures
import os
import re
import time
from pathlib import Path
from typing import Optional

from core.outcome import BoundaryOutcome

DEFAULT_MODEL = os.getenv("AKASHIC_ASK_MODEL", "deepseek-v4-pro")
# 0 == UNLIMITED: omit max_tokens from the request entirely and let the model run to its
# own ceiling. Daniil 2026-08-06: "make an unlimited version and we can figure out scaling
# down from there."
#
# WHY THIS IS THE RIGHT DEFAULT NOW, and was not before. A ceiling existed to protect the
# CALLER'S CONTEXT -- a long answer was expensive because it landed in the conductor's
# window whole. That is a reason to bound DELIVERY, not GENERATION, and it produced the
# worst possible failure: measured twice today, a reasoning model spent the entire budget
# thinking and returned zero visible tokens, having been billed for all of it. A truncated
# answer costs full price for nothing, then costs a retry that pays for the whole prompt
# again (8662 tokens with --with).
DEFAULT_MAX_TOKENS = int(os.getenv("AKASHIC_ASK_MAX_TOKENS", "0"))
BASE_URL = os.getenv("AKASHIC_ASK_BASE_URL", "https://api.deepseek.com")
# T181 fan width. 6 is a DECISION, not a measurement: merge attention at the junction binds
# before generation does, so a fan wider than an integrator can absorb produces merge debt
# rather than progress. Raise it once something downstream is proven able to consume more.
DEFAULT_FAN_WORKERS = int(os.getenv("AKASHIC_ASK_FAN_WORKERS", "6"))
KEY_FILE = Path(__file__).resolve().parents[2] / ".secrets" / "deepseek.key"
DEFAULT_SYSTEM = (
    "You are a helper called synchronously by claude, the conductor of the Akashic Aurora fleet. "
    "You have no memory of previous calls and no tools. Answer the question directly and briefly. "
    "If you cannot answer from what you were given, say exactly what is missing -- a stated gap is "
    "worth more than a confident guess."
)


def _load_key() -> Optional[str]:
    """Env first, then the gitignored key file -- the same order and the same two sources
    scripts/deepseek_chat.py uses. Resolved HERE so core does not have to reach into scripts
    for a credential; runner_lib takes explicit parameters precisely so callers own this.
    """
    v = os.getenv("DEEPSEEK_API_KEY")
    if v and v.strip():
        return v.strip()
    try:
        return KEY_FILE.read_text(encoding="utf-8").strip() or None
    except Exception:
        return None


def _usd(model: str, prompt_tokens: int, completion_tokens: int) -> Optional[float]:
    """Cost in USD, or None when the model has no sourced rate.

    None is a DESIGNED state, not a failure: runner_token_journal's own comment says an absent
    entry stays unpriced rather than borrowing another vendor's number.
    """
    try:
        # DIRECTION SEAM, filed rather than normalized: the canonical price table lives in
        # scripts/, so this is a core -> scripts import, which is backwards. It resolves
        # through every real door (agent_cli.py and the pins both put the repo root on
        # sys.path), and the except below makes an unresolvable import behave exactly like
        # an unpriced model -- None, never a borrowed rate. The table belongs in core; moving
        # it touches agent_cli and runner_token_journal, so it is a follow-up task and NOT a
        # a path hack here -- which was this module's original boundary violation.
        # (This comment cannot NAME that hack: check_boundaries greps raw text, so writing
        #  the literal token would flag the very line explaining its removal -- K6's
        #  reflexivity bug, one function away. Filed as a follow-up against the checker.)
        from scripts.runner_token_journal import price_of
        rate = price_of(model)
        if not rate:
            return None
        return round(prompt_tokens / 1e6 * float(rate["prompt"])
                     + completion_tokens / 1e6 * float(rate["completion"]), 6)
    except Exception:
        return None


#: Per-CALL ceiling for inlined source. Shared by every file in one ask, first-come, so a
#: huge first file cannot silently starve the rest -- starvation is reported, never quiet.
DEFAULT_CONTEXT_CHARS = int(os.getenv("AKASHIC_ASK_CONTEXT_CHARS", "40000"))
_REPO_ROOT = Path(__file__).resolve().parents[2]


def build_context(paths, *, budget_chars: Optional[int] = None, root=None):
    """Inline source files for a helper to reason about. Returns (block, meta) (T203).

    THE PROBLEM THIS SOLVES, measured on this session's own fences: four times a helper was
    asked to attack a design from a PROSE description, because it has no file access. Twice
    it was wrong, and both times the error was settled by four lines of source it could not
    see. Its blindness, not its intelligence, capped every fence.

    LINE NUMBERS ARE THE POINT. A helper that can write `bifrost_api.py:252` produces a
    claim verifiable in seconds; the same claim from prose costs a manual investigation.

    Never raises, and never lies about what it sent: an unreadable path is NAMED in both
    the prompt and the meta, truncation is confessed to the model AND the caller, and a
    file starved by the budget is reported rather than dropped. A context assembler that
    silently omits is worse than none -- it turns a blind helper into a confident one.
    """
    budget = int(budget_chars if budget_chars is not None else DEFAULT_CONTEXT_CHARS)
    # The containment boundary is a PARAMETER, not a global: a hardcoded root is a
    # security control that cannot be exercised by a test, and an unexercised control is
    # an assumption. Defaults to the repo so callers get containment without asking.
    base = Path(root).resolve() if root else _REPO_ROOT
    included, missing, skipped, refused = [], [], [], []
    parts, spent, truncated = [], 0, False

    for raw in (paths or []):
        p = str(raw)
        try:
            full = Path(p).expanduser().resolve()
        except Exception:
            missing.append({"path": p, "why": "unresolvable path"})
            continue
        # A prompt assembler reads whatever it is handed, so keep it inside the repo: a
        # stray path must not be able to lift a key or a secret into a model prompt.
        try:
            full.relative_to(base)
        except ValueError:
            refused.append({"path": p, "why": "outside the repo root"})
            continue
        try:
            text = full.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            missing.append({"path": p, "why": f"{e.__class__.__name__}: {e}"})
            continue

        room = budget - spent
        if room <= 0:
            skipped.append({"path": p, "why": "no room left in the per-call budget"})
            continue
        cut = len(text) > room
        body = text[:room]
        if cut:
            truncated = True
        numbered = "\n".join(f"{i:>5}  {ln}"
                             for i, ln in enumerate(body.splitlines(), start=1))
        header = f"--- BEGIN {full.name} ({p}) ---"
        footer = (f"--- END {full.name} [TRUNCATED at {room} chars of {len(text)}; you are "
                  f"seeing a PARTIAL file -- say so if it limits your answer] ---"
                  if cut else f"--- END {full.name} ---")
        parts.append(f"{header}\n{numbered}\n{footer}")
        spent += len(body)
        included.append({"path": str(full), "chars": len(body), "truncated": cut})

    for m in missing + refused:
        parts.append(f"--- COULD NOT READ {m['path']} ({m['why']}) -- "
                     f"do not assume its contents ---")
    for s in skipped:
        parts.append(f"--- NOT INCLUDED {s['path']} ({s['why']}) ---")

    block = ""
    if parts:
        block = ("The following repository files are provided so you can cite evidence.\n"
                 "CITE `filename:line` for any claim about this code; if you are inferring "
                 "rather than reading, say so explicitly.\n\n" + "\n\n".join(parts))
    return block, {"included": included, "missing": missing, "skipped": skipped,
                   "refused": refused, "truncated": truncated, "chars": spent}


def unusable_evidence_notice(ctx_meta: Optional[Dict[str, Any]]) -> str:
    """What the caller must be told about evidence that did not arrive whole. "" when all did.

    T225, found by running the fan at its own door 2026-08-07. T218 closed this asymmetry for
    ONE of build_context's four outcomes and stated the law generally: "a clip is only safe if
    the party who will draw a conclusion from it is told." The other three stayed silent, and
    the silence was measured -- three refused files, 0 bytes of stderr, $0.065 spent, one lens
    structurally unable to answer.

    FOUR OUTCOMES, FOUR DIFFERENT NEXT MOVES, WHICH IS WHY THEY DO NOT MERGE:
      CLIPPED  the file arrived partial      -> narrow the question or cite line ranges
      REFUSED  outside the repo root         -> move it in, or pass a path that is inside
      MISSING  unreadable / no such path     -> fix the path (a typo is the common case)
      SKIPPED  budget spent by earlier files -> reorder, raise the budget, or ask twice

    A count is not actionable, so every file is NAMED. The reason is carried too: "refused"
    without "outside the repo root" leaves the caller guessing at the fix.

    Kept beside build_context for the reason T218 gave: the notice and the meta it describes
    drift the moment they live in different modules.
    """
    if not ctx_meta:
        return ""
    lines = []

    cut = [i for i in ctx_meta.get("included", []) if i.get("truncated")]
    if cut:
        bits = []
        for i in cut:
            name = os.path.basename(str(i.get("path", "?")))
            shown = i.get("chars")
            total = i.get("total_chars") or i.get("of") or _file_chars(i.get("path"))
            bits.append(f"{name} ({shown} of {total} chars)" if total else f"{name} ({shown} chars)")
        lines.append(
            "EVIDENCE CLIPPED: " + ", ".join(bits) +
            " -- the helper saw a PARTIAL file, so anything it reported as missing or "
            "absent may be outside the window rather than outside the code. Narrow the "
            "file set or cite line ranges before concluding absence.")

    for key, label, move in (
        ("refused", "EVIDENCE REFUSED",
         "-- these were NOT sent, so any answer grounded in them is void, not merely "
         "degraded. The helper was told not to assume their contents. Pass a path inside "
         "the repo, or copy the file in."),
        ("missing", "EVIDENCE MISSING",
         "-- these could not be read and were NOT sent. Check the path (a typo is the "
         "common case) and re-ask; nothing about them was seen."),
        ("skipped", "EVIDENCE SKIPPED",
         "-- the per-call character budget was spent by earlier files before these were "
         "reached. Reorder the file list, raise the budget, or split into two asks."),
    ):
        rows = ctx_meta.get(key) or []
        if not rows:
            continue
        # THE PATH AS THE CALLER TYPED IT, not the basename. A clipped file arrived and is
        # identified by its name; these three did NOT arrive, and the caller's next move is to
        # fix the string they passed -- which they cannot do if the notice shows a basename.
        # (Caught by this slice's own pin: "no/such/file/t225.py" rendered as "t225.py",
        # which is exactly the information a typo hides in.)
        bits = [f"{r.get('path', '?')} ({r.get('why', 'no reason recorded')})" for r in rows]
        lines.append(f"{label}: " + ", ".join(bits) + " " + move)

    return "\n".join(lines)


def _file_chars(path) -> Optional[int]:
    try:
        return len(Path(path).read_text(encoding="utf-8", errors="replace"))
    except (OSError, TypeError):
        return None


def attach_evidence(detail: Dict[str, Any], ctx_meta: Optional[Dict[str, Any]]) -> None:
    """Put the evidence meta AND its notice on the outcome, at the BOUNDARY (T242).

    T218/T225 built the notice and T237 gave JSON callers a discoverable `warnings` list --
    and all three landed in agent_cli.py. `unusable_evidence_notice` had three call sites,
    every one of them at the CLI door, so anything that IMPORTED this module received
    `context` and no warning at all. That is most of what this fleet runs.

    It was paid for twice in one day (2026-08-08): a harness called `ask_many` directly, was
    clipped at 40,000 chars -- line 744 of an 889-line file -- and every branch went blind on
    exactly the region under study, while `context.truncated` sat True in the returned detail
    both times. Same class as T160 one level up: the function IS called, but only on the path
    a human takes.

    So the notice is minted where the metadata is minted. The door RENDERS what it is handed
    and must not recompute it: a second implementation drifts from the first, which is the
    exact risk `unusable_evidence_notice`'s own docstring gives as the reason it lives beside
    `build_context`.

    ABSENT WHEN CLEAN, deliberately -- T237's rule, and it is load-bearing. A `warnings` key
    that always appears is a banner, and a banner is how a real warning goes unread.

    Daniil, 2026-08-08, on the general shape: a fact must be glanceable and must carry the
    SENSE it is true in. "The clipped-evidence warning exists" was TRUE at the CLI door and
    FALSE at this boundary; stated unqualified it did not merely omit, it told a caller it was
    protected while it was not.
    """
    if ctx_meta is None:
        return
    # Which files this answer was based on. Without it a cited claim cannot be traced back to
    # the version of the file that was actually read.
    detail["context"] = ctx_meta
    notice = unusable_evidence_notice(ctx_meta)
    if notice:
        detail["warnings"] = [notice]


def ask(prompt: str, *, system: Optional[str] = None, model: Optional[str] = None,
        max_tokens: Optional[int] = None, client=None, with_files=None,
        context_root=None, continue_on_cut: bool = False,
        max_continuations: int = 2) -> BoundaryOutcome:
    """Ask a helper one question, synchronously. Never raises.

    Returns a BoundaryOutcome whose `detail["answer"]` carries the text. done / partially / failed
    are the three real states, and every one of them can say why.

    continue_on_cut DEFAULTS FALSE HERE AND TRUE ON THE CLI, AND THAT IS DELIBERATE (T204,
    re-affirmed T226 2026-08-07). It reads like drift and it is not, so the reason lives here
    now -- because its absence is what made two readers call it a bug on the same day.

      LIBRARY (this default, False): "spending extra calls must be asked for" -- T204's ruling,
      pinned by test_t204_untruncate.test_continuation_is_opt_in. A programmatic caller has no
      human watching the spend line, so an automatic extra completion is money nobody agreed to.
      MCP, ToolBox, sift and every runner arrive through here.

      CLI (--no-continue, default True): a door may choose a policy FOR its user, and this one
      does, with the argument in its help text -- with no token ceiling a cut means the model hit
      its OWN limit, so stitching costs one completion while a re-ask pays for the whole prompt
      again (8662 tokens with --with, measured). A human sees the spend line and can say no.

    So the invariant is NOT "both defaults agree". It is: the CLI passes its choice EXPLICITLY to
    every path it owns (single ask AND fan), and the library never continues unasked. T226 pins
    that, because the fan was silently getting neither.

    """
    if not str(prompt or "").strip():
        return BoundaryOutcome.failed("empty prompt -- nothing to ask")
    model = model or DEFAULT_MODEL
    # T203: source first, question last. The question is what the model should still be
    # holding when it starts generating, and a wall of code between them buries it.
    ctx_meta = None
    if with_files:
        block, ctx_meta = build_context(with_files, root=context_root)
        if block:
            prompt = f"{block}\n\n=== QUESTION ===\n{prompt}"
    t0 = time.time()
    try:
        if client is None:
            key = _load_key()
            if not key:
                return BoundaryOutcome.failed(
                    "no DEEPSEEK_API_KEY and no .secrets/deepseek.key -- the door is closed, "
                    "which is a configuration state and not a model failure")
            # core -> core. runner_lib is the G4/L0 anti-wedge factory, so ask inherits the
            # per-read timeout AND lands in the T156 wire journal for free.
            from core.comm.runner_lib import make_openai_compat_client
            client = make_openai_compat_client(key, BASE_URL)
        kwargs = {
            "model": model,
            "messages": [{"role": "system", "content": system or DEFAULT_SYSTEM},
                         {"role": "user", "content": prompt}],
        }
        cap = DEFAULT_MAX_TOKENS if max_tokens is None else int(max_tokens)
        if cap > 0:                      # 0 -> omit entirely: the model's own ceiling
            kwargs["max_tokens"] = cap
        resp = client.chat.completions.create(**kwargs)
    except Exception as e:
        return BoundaryOutcome.caught(e, where=f"ask({model})")

    elapsed = round(time.time() - t0, 2)
    try:
        choice = resp.choices[0]
        answer = (choice.message.content or "").strip()
        # T243: reasoning models return the TRACE alongside the answer and we were paying for
        # it and dropping it -- `reasoning_tokens` is counted twenty lines below. Kept because
        # a reader of a helper's ROUTE catches what a reader of its VERDICT cannot: measured
        # 2026-08-08, a helper reached a true conclusion through a false premise, and a
        # disagreement between two helpers' routes is what located a truncated evidence pack.
        # Falsy -> absent, never "": an empty trace presented as a trace is the same
        # fabricated measurement that `reasoning_tokens` uses None-never-0 to avoid.
        reasoning = getattr(choice.message, "reasoning_content", None) or None
        finish = getattr(choice, "finish_reason", None)
        usage = getattr(resp, "usage", None)
        pt = int(getattr(usage, "prompt_tokens", 0) or 0)
        ct = int(getattr(usage, "completion_tokens", 0) or 0)
        rt = _reasoning_tokens(usage)
    except Exception as e:
        return BoundaryOutcome.caught(e, where="ask(parse response)")

    # T204: a cut answer has TWO causes and they need opposite moves. CUT means the model
    # said something and stopped -- continuing costs one completion. STARVED means
    # reasoning consumed the budget before a visible token appeared, so there is nothing
    # to continue and only a bigger budget helps. Measured both in one session.
    continuations = 0
    if finish == "length" and answer and continue_on_cut:
        answer, continuations, finish, pt, ct, rt = _continue_answer(
            client, model, system or DEFAULT_SYSTEM, prompt, answer,
            cap, int(max_continuations), pt, ct, rt)

    truncation = None
    if finish == "length":
        truncation = "CUT" if answer else "STARVED"
    detail = {"answer": answer, "model": model, "prompt_tokens": pt,
              "completion_tokens": ct, "usd": _usd(model, pt, ct),
              "elapsed_s": elapsed, "finish_reason": finish,
              # None, never 0: a provider that does not report reasoning must not read as
              # "reasoned zero" -- the fabricated-measurement lie, one field down.
              "reasoning_tokens": rt, "truncation": truncation,
              "continuations": continuations}
    if reasoning:
        # STATED LIMIT: this is the trace of the FIRST completion. When _continue_answer
        # stitches a cut answer, later hops carry their own reasoning and it is not merged
        # here -- a concatenation would read as one continuous train of thought that never
        # happened. Recorded rather than silently approximated.
        detail["reasoning"] = reasoning
    attach_evidence(detail, ctx_meta)

    if not answer:
        if truncation == "STARVED":
            # Name the cause and the size of it. "The answer was cut" is not actionable;
            # "reasoning used 1200 of 1200" says raise the budget, and by how much.
            spent = f"{rt} of {ct}" if rt is not None else f"all {ct}"
            where = (f"this call had max_tokens={cap}" if cap > 0 else
                     "this call was UNLIMITED, so the model hit its own ceiling -- "
                     "narrow the question or trim the inlined context")
            return BoundaryOutcome.failed(
                f"STARVED: reasoning consumed {spent} completion tokens before any "
                f"visible output -- there is nothing to continue ({where})", **detail)
        return BoundaryOutcome.failed(
            f"model returned an empty answer (finish_reason={finish})", **detail)
    if finish == "length":
        # The T169 lesson, generalized: out of room is a PARTIAL, never a silent complete.
        # Still PARTIALLY after exhausted continuations -- a stitched-but-incomplete
        # answer rendered as done would hide precisely what the stitching failed to fix.
        cont = (f" after {continuations} continuation(s)" if continuations else "")
        ceiling = f"the {cap}-token ceiling" if cap > 0 else "the model's own ceiling"
        return BoundaryOutcome.partially(
            f"answer cut at {ceiling}{cont} (finish_reason=length) -- ask again "
            f"narrower, or allow more continuations", **detail)
    return BoundaryOutcome.done(**detail)


def _reasoning_tokens(usage):
    """Hidden reasoning tokens, or None when the provider does not report them (T204).

    A zero-cost field we have always discarded: the T156 wire survey listed
    completion_tokens_details.reasoning_tokens among seven free fields we never read, and
    named it the diagnosis for content-empty-because-thinking-ate-the-budget. None rather
    than 0 for an absent field -- "did not report" is not "reasoned nothing".
    """
    try:
        d = getattr(usage, "completion_tokens_details", None)
        v = getattr(d, "reasoning_tokens", None)
        return int(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _continue_answer(client, model, system, prompt, partial, max_tokens, budget,
                     pt, ct, rt):
    """Resume a CUT answer, bounded. Returns (answer, continuations, finish, pt, ct, rt).

    The partial rides back as an ASSISTANT turn: a continuation that cannot see what was
    already said will restart or repeat itself. Cheaper than re-asking, which with --with
    means paying for the whole inlined context again (8662 tokens, measured).

    Never raises: a continuation that fails leaves the original partial intact, because
    losing a real partial answer while trying to improve it is strictly worse than
    returning it cut.
    """
    finish = "length"
    done = 0
    for _ in range(max(0, int(budget))):
        try:
            resp = client.chat.completions.create(
                model=model, **({"max_tokens": max_tokens} if max_tokens > 0 else {}),
                messages=[{"role": "system", "content": system},
                          {"role": "user", "content": prompt},
                          {"role": "assistant", "content": partial},
                          {"role": "user", "content":
                           "Continue from exactly where you stopped. Do not repeat any "
                           "text you already wrote, and do not restate the question."}])
            choice = resp.choices[0]
            more = (choice.message.content or "").strip()
            finish = getattr(choice, "finish_reason", None)
            usage = getattr(resp, "usage", None)
            pt += int(getattr(usage, "prompt_tokens", 0) or 0)
            ct += int(getattr(usage, "completion_tokens", 0) or 0)
            more_rt = _reasoning_tokens(usage)
            if more_rt is not None:
                rt = (rt or 0) + more_rt
        except Exception:
            return partial, done, "length", pt, ct, rt
        done += 1
        if more:
            partial = f"{partial} {more}" if not partial.endswith(("\n", " ")) else partial + more
        if finish != "length":
            break
    return partial, done, finish, pt, ct, rt


# T182 bands, CALIBRATED on known-outcome controls rather than chosen. The first cut used one
# threshold at 0.6 and MISSED the case it was built for: three answers that restated one idea in
# different words scored 0.19 and read as "diverse". Lexical overlap is brutal on paraphrase.
#
#   control                                    score   must read as
#   identical strings                          1.00    collapsed
#   same question x3, paraphrased (REAL case)  0.19    cannot tell -> UNKNOWN
#   five-position wavefront                    0.011   distinct
#   disjoint nonsense                          0.00    distinct
#
# So the honest instrument has THREE outputs, not two. Between the bands it does not know, and
# saying "distinct" there is the same defect this measurement exists to catch: a detector
# coercing "I cannot tell" into "all clear".
COLLAPSE_AT = float(os.getenv("AKASHIC_ASK_COLLAPSE_AT", "0.85"))
DISTINCT_AT = float(os.getenv("AKASHIC_ASK_DISTINCT_AT", "0.05"))
_STOPWORDS = frozenset("""
that this these those with from into onto upon which where when what whom whose
have will would could should must been being were where there their they them then than
your yours ours only also just very much more most some such each other another
about above after again against because before below between during under while
""".split())


def diversity_prescription(verdict, homogeneous, *, n_compared=0, score=None) -> str:
    """What to DO about a diversity verdict. The number is mode-blind; this is not (T228).

    THE VERDICT MEANS OPPOSITE THINGS IN THE TWO FAN SHAPES, and only the prescription can say
    so. Same prompt N times: agreement is self-consistency over CORRELATED samples (nothing here
    sets temperature, seed or top_p), and disagreement means the model is unstable. N different
    prompts: low agreement is what different questions produce BY CONSTRUCTION and licenses
    nothing, while high agreement is the real alarm -- the differences were not engaged.

    DELIBERATELY NOT A THRESHOLD CHANGE. T182's bands were calibrated mode-blind and stay exactly
    where they were; re-tuning them per mode would be a guess with no controls behind it. The
    number was never the defect. The NEXT MOVE was, in one shape, where it told the reader to
    adjudicate answers to questions that were never the same.
    """
    if not verdict:
        return ""
    n = n_compared or 0
    if homogeneous:
        if verdict == "collapsed":
            return (f"COLLAPSED: {n} samples of ONE model on ONE prompt agree. That is "
                    f"self-consistency, NOT independent verification -- the samples are "
                    f"correlated by construction, so they fail together as readily as they "
                    f"succeed together. Vary the POSITION (a different question or different "
                    f"evidence per branch), not the seed.")
        if verdict == "distinct":
            return (f"UNSTABLE: {n} samples of the same prompt disagreed. Read them -- the "
                    f"number cannot tell genuine ambiguity in the question from noise in the "
                    f"model, and those need opposite responses.")
        return (f"read them, or adjudicate with one more call -- {n} samples of one prompt sit "
                f"between the bands, which is exactly where word overlap cannot resolve "
                f"paraphrase.")
    if verdict == "collapsed":
        return (f"ALARM: {n} DIFFERENT questions produced near-identical answers. That is the "
                f"signature of boilerplate, or of helpers ignoring what differs between your "
                f"prompts -- suspect the evidence pack answered all of them the same way, or "
                f"that the prompts differ less than you think.")
    if verdict == "distinct":
        return (f"EXPECTED: {n} different questions produced different answers, which is what "
                f"different questions do. This says nothing about whether any of them is any "
                f"good -- the measure cannot speak to quality here, only to boilerplate.")
    return (f"read them -- {n} different questions were never asked the same thing, so there is "
            f"no disagreement here for another call to settle.")


def _content_words(text):
    """Words a reader would call the substance: 4+ chars, stopwords dropped."""
    return {w for w in re.findall(r"[a-z0-9']+", str(text or "").lower())
            if len(w) > 3 and w not in _STOPWORDS}


def _agreement(answers):
    """(mean pairwise Jaccard over content words, how many answers were compared).

    None for fewer than two answers, because one answer cannot corroborate itself and 1.0
    there would be a fabricated corroboration -- the exact reading this measurement exists to
    prevent.

    WHAT IT CAN AND CANNOT DO, measured rather than asserted. It separates near-verbatim
    duplication (1.00) from unrelated text (0.00) reliably and for free. It does NOT separate
    "one idea, three phrasings" (0.19 on the real control) from genuinely different answers
    (0.011) with any margin worth gating on. That is why the caller gets a BAND, and why the
    middle band is UNKNOWN rather than a guess: this function is not entitled to a verdict it
    cannot support.
    """
    sets = [s for s in (_content_words(a) for a in answers if a) if s]
    if len(sets) < 2:
        return None, len(sets)
    total = pairs = 0
    for i in range(len(sets)):
        for j in range(i + 1, len(sets)):
            union = sets[i] | sets[j]
            total += (len(sets[i] & sets[j]) / len(union)) if union else 0.0
            pairs += 1
    return round(total / pairs, 4), len(sets)


def ask_peer(sender, peer, prompt, *, wait_s: float = 120.0, poll_s: float = 2.0,
             within_s: int = 1800, kind: str = "request", launch: bool = False,
             launch_wait_s: float = 60.0):
    """One durable ask to a SEAT, ergonomically synchronous (T196c). Never raises.

    Sol's front door: `ask` and `ask_peer` are one verb with two transports -- the
    stateless helper dies in the call; this one rides the bus with the full T030/T117
    settle machinery underneath, invisibly. Send + arm + poll: expectations.sweep() is
    the ACTOR (transitions), ask_state.state_of() the ORACLE (readout) -- the verb is
    the T196d state machine in a loop, so verb and readout can never disagree.

    THE ASYMMETRY IS THE POINT: wait_s is the short interactive patience; within_s is
    the long durable expectation. When the wait gives up, nothing is abandoned -- the
    record stays armed, redrives fire on their own schedule, and the caller holds a
    handle (`ask --status <id>`) instead of an error. An OPEN ask is a normal state,
    so the timeout path returns PARTIALLY, never failed.

    NON-CONSUMING BY LAW (two-live-seats): the poll reads answers from the stream
    position via the expectations anchor, never advances a lane cursor -- concurrent
    sibling sessions keep their mail; the seat's normal sync consumes later.

    T197 -- IT NOW ASKS WHETHER ANYONE IS HOME, AND SAYS SO AT t=0. The friction reader
    measured 32 closed episodes with 0 ANSWERED and 26 DEAD (81.2%) on 2026-08-06; every
    launchable agent sat at never_launched. The verdict that would have explained it
    already existed (liveness.attendance, T155) and bus.send already printed it -- to
    stderr, where this transaction discarded it. Now it is observed here, returned in
    detail["peer_at_ask"], and armed onto the record so the death event can carry it.

    OBSERVING IS NOT GATING, AND THE DIFFERENCE IS LOAD-BEARING. An UNATTENDED verdict
    NEVER stops the send (fenced with deepseek, whose argument won): a peer absent now
    can be alive by the second redrive, so refusing fast would conflate "down right now"
    with "never coming" -- destroying both the late-binding window the 30-minute
    expectation exists to catch AND the durable dead-ask evidence that found this bug.
    The caller loses nothing and learns in one second what used to cost thirty minutes
    and a forensic dig.
    """
    from core.outcome import BoundaryOutcome as _BO   # local alias for clarity only

    if not str(prompt or "").strip():
        return _BO.failed("empty prompt -- nothing to ask")
    sender, peer = str(sender), str(peer)
    t0 = time.time()
    # Preflight: OBSERVE, never gate. Fail-open -- a probe that cannot be read must not
    # cost the ask, so an unreadable verdict is UNKNOWN and the send proceeds unchanged.
    try:
        from core.comm import liveness as _liveness
        _att = _liveness.attendance(peer)
        peer_state, peer_why = str(_att.state), str(_att.reason or "")
    except Exception as e:
        peer_state, peer_why = "UNKNOWN", f"attendance probe unreadable ({e.__class__.__name__})"
    # T197c, opt-in: don't just REPORT that nobody is home -- make someone be home. The
    # launcher's ergonomics become the front door (Sol's recommendation), so the caller
    # names a peer and a question and never learns the words runner, lock, tag or lane.
    # Opt-in because spawning a process is the one irreversible thing on this path, and
    # `launched` records what was actually done so the outcome never implies more.
    launched = None
    if launch and peer_state != "ATTENDED":
        try:
            from core.comm.peer_ready import ensure_peer
            launched = ensure_peer(peer, wait_s=launch_wait_s)
            if launched.get("attending"):
                # It is attending NOW, so that is the honest ask-time verdict; `launched`
                # is what says we are the reason.
                peer_state = "ATTENDED"
                peer_why = f"launched {launched.get('tag')} -- {launched.get('why')}"
        except Exception as e:
            launched = {"action": "launch_refused", "attending": False,
                        "why": f"ensure_peer raised ({e.__class__.__name__})"}
    try:
        from core.comm.bus import Bus
        from core.comm.expectations import arm, sweep, _answers_since
        from core.comm.ask_state import state_of
        b = Bus(sender)
        anchor = b.tail().get("inbox", "0")
        mid = b.send(peer, kind, prompt)
        if not mid:
            return _BO.failed(f"send to {peer} failed -- bus offline or refused the message",
                              peer_at_ask=peer_state, peer_at_ask_why=peer_why)
        armed = arm(sender, mid, peer, kind, prompt, int(within_s),
                    peer_state=peer_state, peer_why=peer_why)
    except Exception as e:
        return _BO.caught(e, where="ask_peer(send+arm)")

    deadline = t0 + max(0.0, float(wait_s))
    st = None
    while True:
        try:
            sweep(sender)                    # actor: clear answered / redrive / kill
            st = state_of(sender, mid)       # oracle: the honest readout
        except Exception as e:
            return _BO.caught(e, where="ask_peer(poll)", ask_id=str(mid))
        if st["terminal"] or time.time() >= deadline:
            break
        time.sleep(max(0.05, float(poll_s)))

    detail = {
        "ask_id": str(mid), "peer": peer, "state": st["state"],
        "elapsed_s": round(time.time() - t0, 2), "armed": bool(armed),
        "redrives": st.get("redrives"),
        "peer_at_ask": peer_state, "peer_at_ask_why": peer_why,
        "launched": launched,
        "how_to_check": f"py agent_cli.py ask --status {mid} --as {sender}",
    }
    # T202: when it did NOT settle, name WHICH failure this is and what to do -- the
    # caller used to work that out by hand thirty minutes later. Computed only on the
    # unhappy path, so a healthy ask pays nothing (the wake_worthy discipline: the one
    # check that costs a round trip runs only for the case that needs it). DIAGNOSIS
    # ONLY -- nothing here changes send or redrive policy (deepseek's law: a redrive is
    # still a send, so skipping one is gating a decision point later).
    if st["state"] not in ("CLOSED.ANSWERED", "CLOSED.ECHO"):
        try:
            detail["diagnosis"] = _diagnose(peer, peer_state)
        except Exception:
            detail["diagnosis"] = None      # a diagnosis must never cost the outcome
    if st["state"] == "CLOSED.ANSWERED":
        answer = None
        try:
            for m in _answers_since(sender, anchor):     # anchored, non-consuming
                if getattr(m, "frm", None) == peer:
                    answer = getattr(m, "content", None) # newest from the peer wins
        except Exception:
            answer = None
        if answer is None:
            answer = ("(answer settled but its body is outside the stream window -- "
                      "follow answer_id)")
        return _BO.done(answer=answer, answer_id=st.get("answer_id"), **detail)
    if st["state"] == "CLOSED.ECHO":
        return _BO.done(answer=None, settle=(st.get("evidence") or {}).get("settle"),
                        **detail)
    if st["state"] == "CLOSED.DEAD":
        return _BO.failed(
            f"{peer} never answered {mid} -- redrives exhausted (the durable "
            f"expectation_dead event has the record)", **detail)
    if st["state"] == "UNKNOWN":
        return _BO.partially(
            "the record vanished mid-wait (evidence lost or trimmed) -- re-ask; the "
            "old transaction is unresolvable", **detail)
    return _BO.partially(
        f"not settled within {wait_s}s -- the ask stays armed, redrives continue on "
        f"their own schedule; check later with ask --status", **detail)


def _diagnose(peer: str, peer_state: str):
    """Gather the observations failure_class.classify needs, then classify (T202).

    Observation split from decision, the T025 idiom: every probe happens HERE and the
    taxonomy stays pure. Each read is independently guarded -- a missing observation
    becomes None and the classifier falls to a weaker but honest verdict, rather than the
    whole diagnosis vanishing because one probe was unreachable.
    """
    from core.comm.failure_class import base_form, classify

    base = base_form(peer)
    base_attending = None
    if base:
        try:
            from core.comm.liveness import attendance
            base_attending = attendance(base).state == "ATTENDED"
        except Exception:
            base_attending = None
    launchable = None
    try:
        from core.comm.launcher import get_launcher
        from core.comm.peer_ready import resolve_tag
        launchable = bool(resolve_tag(peer, get_launcher().registry())["ok"])
    except Exception:
        launchable = None
    # known_seat stays None -- DELIBERATELY UNOBSERVED HERE. Two earlier cuts were wrong
    # in opposite directions. The first derived it from `launchable or attending`, which
    # is absence-of-evidence wearing a boolean, and declared kimi, sol and deepseek-review
    # nonexistent. The second read the roster for a real witness and got the right answer
    # -- but referencing seat machinery from this module violates the T171 law that an ask
    # is not a seat, and that law is worth more than this field.
    #
    # None is also the honest value: UNKNOWN_PEER asserts "nothing identifies a reader",
    # a claim about the world that needs positive evidence we rarely hold. classify()
    # therefore falls to SEAT_DOWN, whose advice (launch it, or leave the ask armed) is
    # sound even for an id that never existed. A caller holding a real witness can still
    # pass known_seat=False and get the sharper verdict.
    known_seat = None
    return classify(peer, attending=(peer_state == "ATTENDED"),
                    base_attending=base_attending, launchable=launchable,
                    known_seat=known_seat)


def _fan_client(client):
    """ONE client for the whole fan, or a named configuration failure for the whole fan.

    Shared deliberately: the SDK's httpx client is thread-safe and pools connections, so N
    branches cost N requests rather than N clients. A missing key is ONE configuration state,
    not N model failures, and saying so is cheaper to act on than N identical branch errors.
    """
    if client is not None:
        return client, None
    key = _load_key()
    if not key:
        return None, ("no DEEPSEEK_API_KEY and no .secrets/deepseek.key -- the door is closed "
                      "for the WHOLE fan; that is a configuration state, not N model failures")
    from core.comm.runner_lib import make_openai_compat_client
    return make_openai_compat_client(key, BASE_URL), None


def ask_many(prompts, *, system: Optional[str] = None, model: Optional[str] = None,
             max_tokens: Optional[int] = None, client=None,
             max_workers: Optional[int] = None, with_files=None,
             context_root=None, continue_on_cut: bool = False,
             max_continuations: int = 2) -> BoundaryOutcome:
    """Ask N helpers at once. Still no seat behind any of them (T181). Never raises.

    THE PRIMITIVE THE FLEET PATTERNS NEED. Daniil's design, expanded by Sol at his ask: the
    corpus is a graph at rest that becomes an objective-rooted TREE while working, traversed by
    dispersal pattern -- breadth wavefront (disjoint sibling leaves, one integrator), fenced
    triangle (two blind investigators, one reconciler), branch-and-bound (cheap hypotheses, one
    adjudicator), cross-cutting transect (one invariant across every branch). All of them need N
    concurrent LEAVES. None of them needs a seat.

    WHY NOT N SEATS. A seat carries identity, a singleton lock, cursors, a mailbox, a heartbeat,
    a roster row and reaper protection -- so N seats cost N of each, and the measured result on
    this repo was nine seat-tasks returning two findings. N asks cost N HTTP requests.

    THE AGGREGATE IS THREE-STATE AND THAT IS THE POINT. A binary fan verdict discards the
    partial result, which is exactly how "nine tasks, two findings" reads as failure instead of
    as two findings. done only when every branch landed; PARTIALLY with counts when some did;
    failed with counts when none did. Per-branch verdicts live in detail["branches"], in INPUT
    order regardless of completion order, because attribution depends on order.

    Branches are dicts rather than BoundaryOutcomes so the whole aggregate stays JSON-
    serialisable for the CLI door; the aggregate itself keeps the one vocabulary.
    """
    prompts = [str(p) for p in (prompts or [])]
    if not prompts:
        return BoundaryOutcome.failed(
            "empty fan -- no prompts to ask. Asking nothing is not the same as asking and "
            "hearing nothing back.")

    model = model or DEFAULT_MODEL
    workers = max(1, min(int(max_workers or DEFAULT_FAN_WORKERS), len(prompts)))
    client, why = _fan_client(client)
    if client is None:
        return BoundaryOutcome.failed(why, n=len(prompts), n_ok=0, branches=[])

    t0 = time.time()
    results = [None] * len(prompts)

    # T216, found while playing: --with was accepted on the fan path and SILENTLY did
    # nothing, because with_files was threaded into the single-ask call and never here.
    # Five helpers correctly reported they had been given no files; the flag had simply
    # evaporated. Built once per fan rather than per branch -- N branches share one
    # context, so the read and the budget are paid once.
    shared_ctx, ctx_meta = ("", None)
    if with_files:
        shared_ctx, ctx_meta = build_context(with_files, root=context_root)

    def _one(i):
        body = (f"{shared_ctx}\n\n=== QUESTION ===\n{prompts[i]}"
                if shared_ctx else prompts[i])
        try:
            # T226: continue_on_cut/max_continuations were accepted by the CLI and reached
            # NOTHING here -- the T216 shape one flag over, and it bit hardest on the fan,
            # where N branches share one budget-shaped prompt and so tend to cut together.
            return ask(body, system=system, model=model,
                       max_tokens=max_tokens, client=client,
                       continue_on_cut=continue_on_cut,
                       max_continuations=max_continuations)
        except Exception as e:      # ask() does not raise Exception; never lose a slot anyway
            return BoundaryOutcome.caught(e, where=f"ask_many(branch {i})")

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_one, i): i for i in range(len(prompts))}
        for fut in concurrent.futures.as_completed(futures):
            i = futures[fut]
            try:
                results[i] = fut.result()
            except BaseException as e:                              # noqa: BLE001
                results[i] = BoundaryOutcome.caught(
                    e if isinstance(e, Exception) else RuntimeError(repr(e)),
                    where=f"ask_many(future {i})")

    branches, total_usd, priced_all = [], 0.0, True
    n_ok = n_partial = 0
    for i, o in enumerate(results):
        d = o.detail or {}
        usd = d.get("usd")
        if usd is None:
            priced_all = False
        else:
            total_usd += float(usd)
        n_ok += 1 if o.ok else 0
        n_partial += 1 if o.partial else 0
        branches.append({
            "i": i, "prompt": prompts[i][:300], "ok": o.ok, "partial": o.partial,
            "why": o.why, "answer": d.get("answer"), "usd": usd,
            "prompt_tokens": d.get("prompt_tokens"), "completion_tokens": d.get("completion_tokens"),
            "elapsed_s": d.get("elapsed_s"), "model": d.get("model"),
        })

    # T182: does this fan carry N findings, or one finding N times? Measured over the branches
    # that LANDED -- an outage is not a dissenting voice, and counting it as one would
    # manufacture diversity out of a failure.
    agreement, n_compared = _agreement([b["answer"] for b in branches if b["ok"]])
    if agreement is None:
        diversity = None                       # one answer cannot agree or disagree with itself
    elif agreement >= COLLAPSE_AT:
        diversity = "collapsed"                # near-verbatim: one answer billed N times
    elif agreement <= DISTINCT_AT:
        diversity = "distinct"                 # genuinely different answers
    else:
        diversity = "unknown"                  # lexical overlap cannot tell paraphrase apart
    collapsed = diversity == "collapsed"

    n = len(prompts)
    detail = {
        "n": n, "n_ok": n_ok, "n_partial": n_partial, "branches": branches,
        "answers": [b["answer"] for b in branches],
        "lexical_agreement": agreement, "n_compared": n_compared,
        "diversity": diversity, "collapsed": collapsed,
        # T228: DERIVED, never declared -- a caller adds nothing and cannot get it wrong.
        # The verdict is the same number in both shapes; what to DO about it is not.
        "homogeneous": len(set(prompts)) == 1,
        "diversity_next": diversity_prescription(
            diversity, len(set(prompts)) == 1, n_compared=n_compared, score=agreement),
        # None, never a guess: one unpriced branch makes the fan total unknowable, and a
        # partial sum presented as a total is the same lie one layer up.
        "usd": round(total_usd, 6) if priced_all else None,
        "elapsed_s": round(time.time() - t0, 2), "model": model, "workers": workers,
    }
    attach_evidence(detail, ctx_meta)

    if n_ok == 0:
        return BoundaryOutcome.failed(
            f"the whole fan failed: {n_ok} of {n} branches landed. First reason: "
            f"{branches[0]['why'] or 'unreported'}", **detail)
    if n_ok < n or n_partial:
        lost = [b["i"] for b in branches if not b["ok"]]
        cut = [b["i"] for b in branches if b["partial"]]
        bits = [f"{n_ok} of {n} branches landed"]
        if lost:
            bits.append(f"failed: {lost}")
        if cut:
            bits.append(f"truncated: {cut}")
        return BoundaryOutcome.partially(" | ".join(bits), **detail)
    return BoundaryOutcome.done(**detail)
