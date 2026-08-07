"""T231 RED: `ask --bg --prompt-file <big>` cannot spawn, because the prompt rides the ARGV.

REPRODUCED 2026-08-07 with a 40,025-char prompt:

    py agent_cli.py ask --bg --prompt-file big.txt
    -> could not spawn background ask: FileNotFoundError: [WinError 206]
       The filename or extension is too long

The parent resolves the prompt (from positional text OR --prompt-file) and then does
`child.append(prompt)`, so the whole prompt becomes one command-line argument. Windows caps a
command line near 32k.

WHY THIS PAIR MATTERS MORE THAN ITS SIZE SUGGESTS. Both flags exist FOR SIZE: --prompt-file
carries a question too big to type, and --bg keeps big work out of the caller's context window.
They are the two flags most worth combining, and they are exactly the pair that breaks. T226 made
--bg forward every flag it accepts; it did not notice that the PROMPT itself does not fit.

CREDIT WHERE IT IS DUE: the door fails LOUD, naming the exception. That is why this is a
capability hole and not a corruption -- nothing is silently truncated, no half-prompt is asked,
and no money is spent. It is the good version of a bug.

HOW IT WAS FOUND, which is the part worth keeping. A cross-learner panel over CONSTANT evidence:
the identical pre-fix code region handed to DeepSeek, Gemini and GPT. All three found the flag
forwarding defect; only DEEPSEEK named this one. My own five-lens fan this morning -- five
different questions, one model -- never surfaced it.

That makes this the first MEASURED support for T229 (fan across learners, not just samples), and
it arrived after I retracted T229's original evidence as a retrofitted story. The correct
experiment vindicated the conclusion by a route I had not predicted, via the very learner I had
written off. Union of learners > any single learner, on held-constant evidence.

THE FIX IS ONE PATH FOR ALL SIZES. No "if len(prompt) > N use a file" branch: a size-dependent
code path is precisely where this class of defect hides, since every small test passes and only
production hits the threshold.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))


def test_the_prompt_never_rides_the_argv():
    """THE PIN, at the source: the child must not receive the prompt as an argument."""
    src = (REPO / "agent_cli.py").read_text(encoding="utf-8", errors="replace")
    i = src.index('if getattr(args, "bg", False):')
    j = src.index("_bg.write_record(", i)
    block = src[i:j]
    assert "child.append(prompt)" not in block, \
        "the resolved prompt is still appended to the child argv -- WinError 206 above ~32k"


def test_a_large_prompt_spawns(tmp_path):
    """End-to-end, and it must not cost a model call: --bg returns as soon as the child starts.

    40k is chosen to sit above the Windows command-line cap while staying small enough that the
    test is fast. The assertion is that the SPAWN succeeds; what the child then does with the
    prompt is T205's business, already pinned there.
    """
    big = tmp_path / "big_t231.txt"
    big.write_text("Reply with one word: OK. " + ("padding " * 5000), encoding="utf-8")
    assert big.stat().st_size > 32767, "precondition: must exceed the Windows argv cap"

    # THE CHILD MUST NOT REACH THE NETWORK. The first cut of this test omitted this and cost
    # $0.0029 of live DeepSeek tokens on every full-suite run -- caught by reading the ask
    # records before closing the task, four billed calls in. A unit test that spends money is
    # unbounded over the life of the repo and smuggles an API key and a network into the suite.
    # The discard port refuses instantly, so the child dies fast; the SPAWN is what is under
    # test here, and the spawn is unaffected by where the child would have posted to.
    env = {**os.environ, "AKASHIC_ASK_BASE_URL": "http://127.0.0.1:9"}

    r = subprocess.run(
        [sys.executable, "agent_cli.py", "ask", "--bg", "--prompt-file", str(big)],
        cwd=REPO, capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=180, env=env)

    assert "could not spawn" not in (r.stdout + r.stderr), \
        f"spawn failed: {r.stderr.strip()[:300]}"
    assert "206" not in r.stderr, "the argv-length error must be gone, not merely rarer"
    assert r.returncode == 0


def test_small_and_large_prompts_take_the_same_path(tmp_path):
    """No size-dependent branch. Every small test passing is how this class survives.

    Checked structurally: the spawn code must not contain a length comparison against the
    prompt, which would reintroduce a threshold nobody exercises.
    """
    src = (REPO / "agent_cli.py").read_text(encoding="utf-8", errors="replace")
    i = src.index('if getattr(args, "bg", False):')
    j = src.index("_bg.write_record(", i)
    block = src[i:j]
    for smell in ("len(prompt) >", "len(prompt)>", "32767", "32000", "8191"):
        assert smell not in block, \
            f"size-dependent spawn path ({smell!r}) -- one path for all sizes, or the big case rots"


def test_the_prompt_is_recoverable_from_the_handle(tmp_path):
    """A prompt that moved out of argv must land somewhere the record can point at.

    Otherwise `ask --get` shows an answer to a question nobody can read back -- trading a loud
    spawn failure for a quiet provenance hole, which would be a worse door than the broken one.
    """
    from core.comm import ask_bg

    assert hasattr(ask_bg, "prompt_path"), \
        "the background prompt needs a handle-scoped location the record can name"
    p = ask_bg.prompt_path("deadbeef")
    assert str(p).endswith(".prompt") and "deadbeef" in str(p)
