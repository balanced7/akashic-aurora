"""Fan presets: a named answer contract bound to the parser that reads it back.

WHY THIS EXISTS, measured 2026-08-08. Five fan-outs ran in one day. Each began with a
hand-written builder to assemble a prompts file and ended with a SECOND throwaway script to
regex the answers apart -- and every error was in the second script, never in the fan:

    read the INTENT line instead of the WILL-YOU field  -> reported "8 of 8" when it was 7 of 8
    a counter read a bulleted "**Yes**" as unclear      -> 4 of 8 rows misfiled
    a grader iterated a JSON string into characters     -> reported an empty distribution

Throwaway parsers are the code nobody pins, written under time pressure, against output whose
shape was only ever in the author's head.

SO A PRESET IS NOT A TYPING SHORTCUT. It is one object holding BOTH the contract sent to the
helper AND the parser that reads the answer, so the two cannot drift apart. Registering a
contract without its parser is refused rather than discouraged -- the moment they can be
separated, someone hand-rolls a regex again and we are back where we started.

THE CLAUSES IN THESE CONTRACTS ARE NOT STYLE. Each was measured this week:
  - "the cheapest thing that would prove you wrong" settled 3 of 7 findings in ONE command each,
    including one that refuted itself.
  - "abstention is a real answer" produced the NOT-EXPLOITABLE that became a control run.
  - "descriptive, not normative" is the T207 danger zone: a grounded helper answering a
    should/better question came back confidently wrong WITH accurate citations.
"""
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional
import os
import re

__all__ = ["Preset", "register", "get", "known", "build_prompts", "read_lens_file"]


@dataclass(frozen=True)
class Preset:
    """A contract and the parser that reads its answers. Never one without the other."""
    name: str
    contract: str
    parse: Callable[[str], Dict[str, Any]]
    describe: str = ""


_REGISTRY: Dict[str, Preset] = {}


def register(name: str, *, contract: str, parse: Optional[Callable] = None,
             describe: str = "") -> Preset:
    """Add a preset. REFUSES a contract with no parser -- that is the drift this module exists
    to prevent, and refusing is the only thing that actually prevents it."""
    if not contract or not str(contract).strip():
        raise ValueError(f"preset {name!r}: a contract cannot be empty")
    if parse is None or not callable(parse):
        raise ValueError(
            f"preset {name!r}: a contract MUST ship with its parser. A contract alone sends "
            f"callers back to hand-rolling a regex against a shape only the author knows, "
            f"which is the exact defect this module exists to remove.")
    p = Preset(name=name, contract=contract, parse=parse, describe=describe)
    _REGISTRY[name] = p
    return p


def get(name: str) -> Preset:
    if name not in _REGISTRY:
        raise KeyError(f"unknown preset {name!r}; known: {sorted(_REGISTRY)}")
    return _REGISTRY[name]


def known() -> List[str]:
    return sorted(_REGISTRY)


# ------------------------------------------------------------------ parsing helpers
def _section(text: str, head: str) -> str:
    """Everything under a heading, up to the next known heading.

    LENIENT ABOUT SHAPE, STRICT ABOUT PRESENCE. Models bullet, bold, number and colon-terminate
    inconsistently, and none of that changes the meaning -- but a MISSING section does, so the
    caller is told rather than handed a silent empty string.
    """
    heads = ("FINDINGS", "REASONING", "CHECK", "BLIND")
    pat = rf"^\s*\**\s*{head}\s*\**\s*:?\s*$|^\s*\**\s*{head}\s*\**\s*:"
    m = re.search(pat, text, re.M | re.I)
    if not m:
        return ""
    rest = text[m.end():]
    nxt = None
    for h in heads:
        if h.lower() == head.lower():
            continue
        n = re.search(rf"^\s*\**\s*{h}\s*\**\s*:?\s*$|^\s*\**\s*{h}\s*\**\s*:", rest, re.M | re.I)
        if n and (nxt is None or n.start() < nxt):
            nxt = n.start()
    return (rest[:nxt] if nxt is not None else rest).strip()


def _items(block: str) -> List[str]:
    """One entry per bullet or numbered line; a bare paragraph counts as one entry."""
    out = []
    for ln in block.splitlines():
        s = ln.strip()
        if not s:
            continue
        s = re.sub(r"^(?:[-*•]|\d+[.)])\s*", "", s)
        s = s.replace("**", "").strip()
        if s:
            out.append(s)
    return out


def _parse_findings(answer: str) -> Dict[str, Any]:
    """FINDINGS / REASONING / CHECK / BLIND -> structured, or ok=False with the raw text kept.

    An answer that ignores the contract is REPORTED, never dropped. A paid branch vanishing into
    a clean-looking result is how a fan starts lying about its own coverage -- the same class as
    a clipped evidence pack that answers fluently about the window it can see.
    """
    text = answer or ""
    findings = _items(_section(text, "FINDINGS"))
    reasoning = _section(text, "REASONING")
    check = _section(text, "CHECK")
    blind = _section(text, "BLIND")
    ok = bool(findings) or bool(reasoning and blind)
    return {"ok": ok, "findings": findings if ok else [], "reasoning": reasoning,
            "check": check, "blind": blind,
            "raw": text if not ok else "",
            "missing": [h for h, v in (("FINDINGS", findings), ("REASONING", reasoning),
                                       ("CHECK", check), ("BLIND", blind)) if not v]}


_FINDINGS_CONTRACT = """

ANSWER FORMAT, strictly:
FINDINGS: numbered, one line each, each citing file:line where the evidence supports it.
REASONING: how you got there and what you ruled out. Another reader gets this WITHOUT your
  evidence, so make the ROUTE legible rather than the conclusion confident.
CHECK: the cheapest thing that would prove you WRONG.
BLIND: what your evidence and your position cannot show you.

Answer DESCRIPTIVELY -- say what the thing DOES, not what would be better. The words
should / better / more / fewer are the tell that you have left the evidence behind.
If the evidence does not support an answer, say UNCLEAR. An abstention is a correct answer
here and is preferred to a confident guess."""

register("findings", contract=_FINDINGS_CONTRACT, parse=_parse_findings,
         describe="facts with citations, plus the cheapest disproof for each")


# ------------------------------------------------------------------ lens plumbing
def build_prompts(preset_name: str, lenses) -> List[str]:
    """One branch per lens, each with the contract appended.

    THE LENS LEADS AND THE CONTRACT FOLLOWS, deliberately: the question is what the helper
    should be holding when it starts, and a wall of format rules ahead of it buries the ask.
    """
    p = get(preset_name)
    # A bare string is ONE lens. Left as-is it is iterable, so `build_prompts(name, "a lens")`
    # fanned out one branch PER CHARACTER -- twelve paid calls asking the model "w", "h", "a".
    # Found by this module's own first real fan-out, fifteen minutes after it was written, and
    # it is the FIFTH instance of this class in one session (ask_many `files`, _note_exclusion
    # `kinds`, a related_to analysis, and here). The class is not a typo, it is a property of
    # the language: iterating a value that MIGHT be a string is silent and plausible when wrong.
    if isinstance(lenses, (str, bytes)):
        lenses = [lenses]
    out = []
    for lens in lenses or []:
        s = str(lens).strip()
        if s:
            out.append(s + p.contract)
    if not out:
        raise ValueError(f"preset {preset_name!r}: no lenses given -- an empty fan is a caller "
                         f"mistake, and zero branches read like 'nothing found'")
    return out


def read_lens_file(path: str) -> List[str]:
    """One lens per line. Blank lines and # comments are skipped so a lens file can be
    annotated with WHY each lens is there -- which is the part that rots first."""
    with open(path, encoding="utf-8") as f:
        lenses = [ln.strip() for ln in f
                  if ln.strip() and not ln.lstrip().startswith("#")]
    if not lenses:
        raise ValueError(f"{os.path.basename(path)} contains no lenses (only blanks/comments) -- "
                         f"refusing rather than running an empty fan")
    return lenses
