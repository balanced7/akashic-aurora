"""RED pin: an auto-woken (or explicitly !spawn'd) seat must be TOLD to reply to him.

2026-08-31. Daniil, from Discord: "Vandor that still doesnt fix the reachibility issue.
I have to use your name every time to get a reply." Root-caused by walking
bifrost:inbox:daniil directly: ZERO messages landed there in 9 days (last:
1787424211114-0), spanning dozens of auto-wakes and explicit !spawns -- including ones
he phrased as direct personal questions ("How are things going Vandor?"). Every liveness
signal (roster, worklive, bus attendance) was healthy across that window; wake/spawn
itself worked (proven: "Can you relaunch sunshine?" auto-woke a seat with zero naming).
The gap was never routing -- `_spawn`'s CLI prompt told every seat to "do the task ...
and end with a wrap," and `wrap` (agent_cli.py) distills the SESSION for the next seat;
it has never sent a word to Discord. Whether he got an answer came down to whether the
model, on its own initiative, decided a direct question deserved a reply -- which
`bifrost:inbox:daniil` proves it stopped doing reliably. The fix is not a new organ: an
explicit instruction in the one prompt every spawned seat already reads.

`_spawn` is a closure inside `main()` (needs a live bot token + the `discord` package to
construct), so this pin reads the module's SOURCE TEXT directly rather than executing
it -- the same class of test as reading a docstring for a promised contract, applied to
a prompt template instead of a comment.

Run:  py -m pytest tests/test_spawn_prompt_requires_a_reply.py -v
"""
from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = (REPO / "scripts" / "bifrost_runner_discord.py").read_text(encoding="utf-8")


def _spawn_prompt_block() -> str:
    """The literal source slice that builds `prompt` inside `_spawn`, isolated from the
    rest of the (large) file so a match elsewhere can never fake this pin green."""
    start = SRC.index('prompt = (f"You were spawned by the operator')
    end = SRC.index(")\n", start)
    return SRC[start:end]


def test_the_prompt_names_wrap_as_insufficient():
    """The exact misunderstanding this bug lived in: `wrap` sounds like it closes the
    loop with him. It closes the loop with the NEXT seat."""
    block = _spawn_prompt_block()
    assert "wrap" in block.lower()
    assert "never reaches him" in block or "distills" in block, (
        "the prompt must say, in words, that wrap alone does not reach Daniil -- "
        "otherwise a spawned seat has no reason not to repeat the silent-completion bug")


def test_the_prompt_gives_the_exact_reply_command():
    """A vague 'let him know' degrades to the same silence under load. The command must
    be copy-pasteable: the verb, the recipient, and the channel it rides."""
    block = _spawn_prompt_block()
    assert "bifrost-send" in block, "no concrete reply verb named"
    assert "--to daniil" in block, "no recipient named -- a reply with no --to goes nowhere"


def test_the_prompt_covers_task_shaped_asks_not_just_questions():
    """The regression's sharpest evidence: 'Can you relaunch sunshine?' (a task, not a
    question) got done and wrapped in total silence, while direct questions sometimes got
    answered on the model's own initiative. The instruction must not leave that judgment
    call to chance."""
    block = _spawn_prompt_block()
    assert "task" in block.lower() and (
        "even if" in block.lower() or "task-shaped" in block.lower() or "task rather than" in block.lower()
    ), "the prompt must cover task-phrased asks explicitly, not just question-phrased ones"
