"""
Adaptive interjection router -- when a human types into a live agent session, decide whether the
message should HALT ongoing work, quietly STEER it, or is a question to ANSWER, then match the action.

The problem (raised on the live console): typing mid-work shouldn't blindly interrupt. Some
interjections are course-corrections that MUST stop the agents ("wait, that's wrong, do X instead");
others are refinements to absorb without halting ("also cover Y", "fyi Z"); others just want an answer
("what are you doing?"). A blanket pause is too blunt; never pausing is unsafe. So classify intent and
act accordingly:

  HALT   -> pause the runners; the human is redirecting. ("stop", "wait", "no", "actually", "wrong")
  STEER  -> deliver without pausing; the agent folds it in next turn. ("also", "make sure", "fyi")
  ASK    -> deliver without pausing; the agent answers alongside its work. ("what", "why", "?")

Heuristic-first: instant, free, deterministic (Principle 3 -- yardstick before mechanism). An optional
cheap-LLM escalation refines only genuinely ambiguous messages (low heuristic confidence), so the
common case costs nothing and the hard case is still adaptive.

  classify_intent("wait, stop -- that's wrong")        -> {"intent": "halt",  ...}
  classify_intent("also make sure to handle nulls")     -> {"intent": "steer", ...}
  classify_intent("what are you working on right now?")  -> {"intent": "ask",   ...}
"""
from __future__ import annotations

import json
import re
from typing import Any, Callable, Dict, Optional

HALT = "halt"
STEER = "steer"
ASK = "ask"
RESUME = "resume"

# Strong stop / redirect signals -> the human is taking the wheel.
_HALT_RE = re.compile(
    r"\b(stop|wait|hold\s+(?:on|up)|halt|abort|cancel|scrap|forget\s+it|never\s?mind|"
    r"no+|nope|don'?t|do\s+not|that'?s\s+wrong|it'?s\s+wrong|not\s+what|not\s+right|"
    r"redo|revert|undo|start\s+over)\b", re.I)
# NB: 'instead'/'actually'/'wrong'/'back up' were dropped from the always-halt set -- they false-fire
# on descriptive text ("...keep triggering INSTEAD of staying put" is a bug report, not a stop command).
# Leading stop words -> near-certain halt (someone slamming the brakes types the verb first).
_HALT_LEAD_RE = re.compile(r"^\s*(stop|wait|hold|halt|no|nope|abort|cancel|don'?t|scrap)\b", re.I)
# Question form -> wants an answer, not a halt.
_ASK_RE = re.compile(
    r"(\?\s*$)|^\s*(what|why|how|when|where|who|which|whose|are\s+you|is\s+(it|this|that)|"
    r"can\s+you|could\s+you|would\s+you|did\s+you|do\s+you|have\s+you|status|explain|show\s+me)\b", re.I)
# Additive / refinement -> steer without stopping.
_STEER_RE = re.compile(
    r"\b(also|and\s+also|additionally|plus|make\s+sure|ensure|fyi|note\s+that|nb|btw|"
    r"by\s+the\s+way|consider|keep\s+in\s+mind|remember\s+to|one\s+more|as\s+well|prefer|"
    r"priorit(?:y|ise|ize)|make\s+it|can\s+you\s+also)\b", re.I)
# A bare resume command (the WHOLE message) -> unfreeze the agents, don't send it as chat.
_RESUME_RE = re.compile(r"^\s*(resume|continue|unpause|go\s+on|keep\s+going|carry\s+on|proceed|"
                        r"go\s+ahead|resume\s+work|go)\s*[.!]*\s*$", re.I)


def classify_intent(text: Any, *, llm: Optional[Callable[[str], str]] = None,
                    threshold: float = 0.55) -> Dict[str, Any]:
    """Classify a human interjection as halt|steer|ask with a confidence and a one-line reason.
    Precedence HALT > ASK > STEER (a brake word dominates a refinement word). If `llm` is given and the
    heuristic is unsure (confidence < threshold), escalate to the model for a nuanced call."""
    t = str(text or "").strip()
    if not t:
        return {"intent": STEER, "confidence": 0.0, "why": "empty message", "source": "heuristic"}
    if _RESUME_RE.match(t):
        return {"intent": RESUME, "confidence": 0.95, "why": "resume command", "source": "heuristic"}

    lead_halt = bool(_HALT_LEAD_RE.search(t))
    halt = lead_halt or bool(_HALT_RE.search(t))
    ask = bool(_ASK_RE.search(t))
    steer = bool(_STEER_RE.search(t))
    shouting = t.isupper() and len(t) > 3

    if halt:
        conf = 0.92 if (lead_halt or shouting) else 0.72
        verdict = {"intent": HALT, "confidence": conf, "why": "stop / redirect signal", "source": "heuristic"}
    elif ask and not steer:
        verdict = {"intent": ASK, "confidence": 0.78, "why": "question form", "source": "heuristic"}
    elif steer:
        verdict = {"intent": STEER, "confidence": 0.76, "why": "additive / refinement signal", "source": "heuristic"}
    else:
        verdict = {"intent": STEER, "confidence": 0.40, "why": "no strong signal -> default steer (don't halt unbidden)",
                   "source": "heuristic"}

    if llm is not None and verdict["confidence"] < threshold:
        refined = _llm_classify(t, llm)
        if refined:
            return refined
    return verdict


def should_pause(intent: str) -> bool:
    """The one action rule the caller needs: only a HALT freezes ongoing work."""
    return intent == HALT


def should_resume(intent: str) -> bool:
    """A bare 'resume'/'continue' typed into the console unfreezes the work."""
    return intent == RESUME


_LLM_PROMPT = (
    "Classify this human interjection into a live AI work session as exactly one of: "
    "halt (stop/redirect the work now), steer (add guidance, keep working), ask (answer a question, "
    "keep working). Reply ONLY as compact JSON: {\"intent\":\"halt|steer|ask\",\"why\":\"<=8 words\"}.\n\n"
    "Message: ")


def _llm_classify(text: str, llm: Callable[[str], str]) -> Optional[Dict[str, Any]]:
    """Escalate an ambiguous message to a cheap model. `llm(prompt) -> str` (JSON). Fail-soft -> None."""
    try:
        raw = llm(_LLM_PROMPT + text)
        start, end = raw.find("{"), raw.rfind("}")
        obj = json.loads(raw[start:end + 1]) if start >= 0 and end > start else {}
        intent = str(obj.get("intent", "")).lower().strip()
        if intent in (HALT, STEER, ASK):
            return {"intent": intent, "confidence": 0.85,
                    "why": str(obj.get("why", "model call"))[:60], "source": "llm"}
    except Exception:
        pass
    return None
