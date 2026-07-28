"""gate_rules (R2 slice 1a) -- three principles about an action's relationship to
knowledge, stated WITHOUT reference to the census sample that motivated them.

The reconciled bar's rules half (kimi's Q1, adopted): a silence rule must be a
generative principle that classifies actions the judges never saw. If a rule can
only be stated by pointing at a sample item, it is a fit, and the anti-fitting pin
(test A1) rejects it structurally -- this module may not contain census case
numbers at all.

THE THREE PRINCIPLES

  no_item_changes_a_count   The command exists to MEASURE repo state: its sinks are
                            counting/measuring filters, or it is an inline transform
                            script over an enumerated file list. No recall item can
                            change what a count returns; the output is fully
                            determined by the command.

  tool_is_the_retrieval     The command queries the knowledge system THROUGH ITS OWN
                            READ DOOR (agent_cli read verbs, --help). recall-at
                            cannot beat the door's own answer -- injecting context
                            about what the door is about to return is circular.
                            DELIBERATELY NARROW: reading arbitrary files with shell
                            tools is an INVESTIGATION, where a lesson genuinely can
                            change what you look for -- that must NOT match. The
                            boundary is "the system's own door", not "reading data".

  (DROPPED: work_already_done. The tripwire killed it honestly -- the pack holds
  two structurally IDENTICAL git-add-and-commit actions carrying OPPOSITE judge
  labels, so the principle is not shape-decidable. kimi's counter predicted this
  ceiling: "the honest ceiling for a SHAPE rule is ~5". Do not resurrect it with
  message-text heuristics; commit text is prose, and prose is the floor's job.)

PLACEMENT (sol's Q4): the gate runs AFTER ranking, BEFORE injection, so a caller
holds the ranking result when it consults this table. The rules themselves are
pure shape predicates; composition with ranking belongs to the gate, and `match`
accepts forward-compat kwargs it does not yet read.

EDITS NEVER MATCH: `query_shape == "path"` returns None from every rule. Whether a
file edit needs its lessons is a RELEVANCE judgment (the floor's business, kimi's
Q2-b); shape cannot see it, and a shape rule that claims to is fitting.

TRIPWIRE REFINEMENTS, recorded because refinement-under-test is half a step from
fitting and the difference is documentation + a hold-out: (a) the door principle
excludes single-named-artifact reads (`note --get <id>`) -- reading a NAMED
knowledge artifact is itself consuming knowledge, and the judges' own split over
such reads proves the demand is sometimes real; STATE renders (mailbox, status,
lists, help) stay in. (b) the door must be the PRIMARY invocation of the action
(first program after a cd/set-location prefix), because pipelines mention doors
without being door queries. Both are stated without case numbers and both face
kimi's ~10-action fresh hold-out before the gate is called green.

RECEIPTS: a match returns {rule, matched_features} where matched_features are
STRUCTURAL facts (which sink, which door, which verb class) -- never raw command
text, because secrets ride argv (sol's Q4).
"""
from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, List, Optional

# ------------------------------------------------------------------ the table
# Structural vocabularies, not sample quotes. Editing these changes table_hash(),
# which every gate-silence receipt records -- so "which table fired" is auditable
# after any edit (a rule NAME alone is mutable semantics).

# sinks whose presence means the pipeline exists to measure, not to act
_COUNT_SINKS = (r"\bwc\s+-l\b", r"\bgrep\s+-r?c\b", r"\bmeasure-object\b",
                r"\|\s*wc\b")
# an inline interpreter transform over an enumerated file list (mechanical byte-map)
_INLINE_TRANSFORM = (r"<<\s*'?eof'?[\s\S]*\bimport\s+re\b",)

# the knowledge system's own READ doors -- STATE renders only. A NAMED-artifact
# read (`note --get <id>`) is deliberately absent: consuming a specific knowledge
# artifact is knowledge work, and adjacent context may matter. WRITE verbs
# (learn/wish/handoff/...) are knowledge-affecting and are excluded in the probe.
_READ_DOORS = (r"agent_cli\.py\s+notes\b",
               r"agent_cli\.py\s+mailbox\b",
               r"agent_cli\.py\s+recall\S*\b",
               r"agent_cli\.py\s+\S+\s+--help\b",
               r"agent_cli\.py\s+status\b", r"agent_cli\.py\s+stats\b",
               r"agent_cli\.py\s+events\b", r"agent_cli\.py\s+promoted\b")

# FAIL-CLOSED ON MUTATION (sol's NO-GO on the first table): a silence rule may only
# classify a command with NO mutating segment ANYWHERE. A count sink at the tail of a
# mutation, a commit wearing a wc suffix, a status render piped into a file -- each is
# an action with effects, and sink-spotting silenced them all. The vocabulary is
# structural (verbs and redirect operators), and ANY hit anywhere kills every rule
# before it is consulted. Enumerating "safe" would rot; enumerating "mutating" fails
# toward FIRING when it rots, which is the bar's law.
_MUTATION = (r"\bgit\s+(add|commit|push|reset|checkout|clean|rm|mv)\b",
             r"\brm\b", r"\bdel\b", r"\bmv\b", r"\bremove-item\b",
             r"\bset-content\b", r"\badd-content\b", r"\bout-file\b",
             r"\bnew-item\b", r"(?<![0-9&12])>(?!&)",
             r"\bmkdir\b", r"\btouch\b", r"\bcp\b", r"\bcopy-item\b",
             r"agent_cli\.py\s+(learn|wish|handoff|bifrost-send|task|doc|log|"
             r"graduate|tag-anti-pattern|lock|unlock|capture|wrap|kata|note|"
             r"recall-feedback|recall-curate|bifrost-ack|bifrost-drain|"
             r"bifrost-skip-to-now|bifrost-nudge|stand-down|unwedge|defer|"
             r"followup|toast|alias|run|bench|tool|episode|fence|triage)\b",
             r"\bmirror\.py\b", r"\bsnapshot_knowledge\b",
             r"\bpip\s+install\b", r"\bnpm\b", r"\bredis-cli\b.*\b(set|del|xadd)\b")


def _mutates(text: str) -> bool:
    return any(re.search(pat, text, re.I) for pat in _MUTATION)


# the door must be the PRIMARY invocation: strip position prefixes (cd /
# set-location, interpreter launch) and require the door at the head of the FIRST
# command segment. Pipelines MENTION doors without BEING door queries; a
# measurement that greps a door's output is still a measurement.
_PREFIX = re.compile(r"^(?:\s*(?:cd|set-location)\s+\S+\s*(?:&&|;)?\s*)*(?:\s*(?:py|pyw|python|python3)\s+)?",
                     re.I)


def _features_count(text: str) -> Optional[Dict[str, Any]]:
    sinks = [pat for pat in _COUNT_SINKS if re.search(pat, text, re.I)]
    inline = [pat for pat in _INLINE_TRANSFORM if re.search(pat, text, re.I)]
    if sinks or inline:
        return {"sinks": len(sinks), "inline_transform": bool(inline)}
    return None


def _features_door(text: str) -> Optional[Dict[str, Any]]:
    head = _PREFIX.sub("", str(text))
    if not re.match(r"agent_cli\.py", head, re.I):
        return None                       # the door is not the primary invocation
    first_seg = re.split(r"&&|;", head, maxsplit=1)[0]
    doors = [pat for pat in _READ_DOORS if re.search(pat, first_seg, re.I)]
    if not doors:
        return None
    # WRITE verbs through the same binary defeat the principle: `learn`, `wish`,
    # `handoff`, `bifrost-send`, `note --retire/--supersedes`, `task` mutate state,
    # and a lesson CAN change what you write. Any write verb present -> no match.
    if re.search(r"agent_cli\.py\s+(learn|wish|handoff|bifrost-send|task|doc|log|"
                 r"graduate|tag-anti-pattern|lock|unlock|capture|wrap|kata)\b", text, re.I):
        return None
    return {"doors": len(doors), "verb_class": "read"}


_RULES = (
    ("no_item_changes_a_count", _features_count),
    ("tool_is_the_retrieval", _features_door),
)


# THE ALLOWLIST GRAMMAR (sol's round-2 inversion): the mutator vocabulary is
# INFINITE, so safety cannot be a denylist -- a denylist fails toward SILENCING
# whenever an unknown mutator wears a known sink (`py destructive_script.py | wc -l`).
# Instead, EVERY command segment and every pipeline stage must be recognised as one
# of the exact read/count primitives below, or the whole action is unmatchable and
# the gate FIRES. Unknown programs, interpreters, heredocs, redirections: all fire.
# The vocabulary rots toward FIRING, which is the bar's law.
_ALLOWED_STAGE = (
    r"cd\s+\S+", r"set-location\s+\S+",
    r"echo(\s|$).*",
    r"ls(\s+\S+)*", r"dir(\s+\S+)*",
    r"wc(\s+-\w+)?(\s+\S+)*", r"head(\s+\S+)*", r"tail(\s+\S+)*",
    r"sort(\s+\S+)*", r"uniq(\s+\S+)*",
    r"grep\s+(?!.*(-exec|--include-dir))\S.*",          # read-only grep forms
    r"select-string(\s+\S+)*", r"select-object(\s+\S+)*", r"measure-object(\s+\S+)*",
    r"cat\s+\S+.*", r"get-content\s+\S+.*", r"get-childitem(\s+\S+)*",
    # the knowledge system's own READ doors, optionally interpreter-launched
    r"(?:pyw?(?:thon)?\s+)?agent_cli\.py\s+(?:notes|mailbox|recall\S*|status|stats|"
    r"events|promoted)(\s+(?!--(?:retire|supersedes|fold|consume))\S+)*",
    r"(?:pyw?(?:thon)?\s+)?agent_cli\.py\s+\S+(\s+\S+)*\s+--help",
    r"2>\s*&?\s*1", r"2>\s*\$?null",                    # stderr merges are reads
)
_STAGE_RE = tuple(re.compile(rf"^\s*(?:{p})\s*$", re.I) for p in _ALLOWED_STAGE)


def _whole_command_readonly(text: str) -> bool:
    """True only when EVERY segment (split on && ; |) matches an allowed read-only
    stage. Any redirection (>, >>, tee/Tee-Object/Set-Content/Out-File) fails at
    the split residue or the stage regexes -- there is no allowed stage containing
    a write. Unparsed anything = False = FIRE."""
    t = str(text)
    if re.search(r"(?<![0-9&12])>(?!&)|<<", t):
        return False                       # file redirection / heredoc: never silence
    segs = [s for s in re.split(r"&&|;|\|(?!\|)", t) if s.strip()]
    if not segs:
        return False
    # A PowerShell one-liner runs `set-location X py agent_cli.py ...` with no
    # separator; strip position prefixes per segment before matching, so the
    # grammar judges the PROGRAM, not the preamble.
    return all(any(rx.match(_PREFIX.sub("", seg)) or rx.match(seg) for rx in _STAGE_RE)
               for seg in segs)


def match(*, query_shape: str, action: str, **_forward_compat) -> Optional[Dict[str, Any]]:
    """The first principle this action satisfies, or None (= the gate must not
    silence on shape grounds; the floor and FAITH gates still apply downstream).

    None on any doubt: empty action, path shape (edits are relevance judgments),
    an unrecognised segment ANYWHERE (the allowlist grammar), or an exception --
    fire-on-uncertainty is the bar's law and it is enforced HERE, not only at
    the gate."""
    try:
        if not action or str(query_shape) != "command":
            return None
        text = str(action)
        if _mutates(text):
            return None                    # belt: known mutators fire fast
        if not _whole_command_readonly(text):
            return None                    # suspenders: UNKNOWN anything fires too
        for name, probe in _RULES:
            feats = probe(text)
            if feats:
                return {"rule": name, "matched_features": feats,
                        "table_hash": table_hash()}
        return None
    except Exception:
        return None


def table_hash() -> str:
    """A stable digest of the STRUCTURE that decides silence -- the vocabularies and
    rule names, not this file's comments. Receipts record it so a decision remains
    explainable after the table is edited (sol's acceptance test)."""
    h = hashlib.sha256()
    for name, _ in _RULES:
        h.update(name.encode())
    for group in (_COUNT_SINKS, _INLINE_TRANSFORM, _READ_DOORS, _MUTATION, _ALLOWED_STAGE):
        for pat in group:
            h.update(pat.encode())
    # _PREFIX changes which command segment the door rule examines -- decision-
    # affecting structure, digested (sol: a hash that misses a deciding regex
    # attributes new behaviour to the old table).
    h.update(_PREFIX.pattern.encode())
    return h.hexdigest()[:16]
