"""PRE-REGISTERED ACCEPTANCE (T181) -- N leaves at once, still no seat behind any of them.

Daniil, 2026-08-05, going to sleep: "I want to see you find a way to start getting value from our
ability of spinning up multiple deepseek instances at once. using that fleet solve the
orchestration problems of running that fleet."

DANIIL'S DESIGN, expanded by Sol at his ask: view the lessons/stores/systems as a graph at rest
that becomes an objective-rooted TREE while working, and disperse a fleet across it by pattern --
breadth wavefront (disjoint sibling leaves + one integrator), fenced triangle (two blind
investigators + one reconciler), branch-and-bound (cheap hypotheses, one adjudicator),
cross-cutting transect. Every one of those needs N concurrent LEAVES. None of them needs a seat.

T171 proved ask is not a seat. This is that thesis from 1 to N, and the reason it is the right
primitive: a seat costs identity, a lock, cursors, a mailbox, a heartbeat, a roster row and reaper
protection -- so N seats cost N of each, and the evidence is nine seat-tasks returning two
findings. N asks cost N HTTP requests.

  K1  N prompts return N answers, in INPUT order
  K2  branches run CONCURRENTLY -- wall time is nearer the slowest branch than the sum
  K3  one branch failing does not kill the fan; the aggregate is PARTIALLY and says how many
  K4  every branch failing is a FAILED aggregate that still says how many
  K5  aggregate spend is the sum of branch spend
  K6  input order is preserved even when COMPLETION order is reversed
  K7  an empty prompt list is a named failure, not an empty success
  K8  ask_many touches no seat machinery (same AST guard as T171 K6)

K3 is the one that matters in practice. A fan-out whose aggregate is binary throws away the
partial result -- which is exactly the T169/T179 defect at fleet scale, and the reason nine
seat-tasks could return two findings and read as a failure.

Run: py -m pytest tests/test_t181_ask_many_is_still_not_a_seat.py -q
"""
import ast
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core.comm import ask as A  # noqa: E402


class _Resp:
    def __init__(self, text, finish="stop", pt=100, ct=50):
        self.choices = [type("C", (), {
            "message": type("M", (), {"content": text})(),
            "finish_reason": finish})()]
        self.usage = type("U", (), {"prompt_tokens": pt, "completion_tokens": ct})()


class _Client:
    """Answers with the prompt echoed back, after an optional per-prompt delay."""

    def __init__(self, delays=None, boom_on=()):
        self.delays, self.boom_on = delays or {}, set(boom_on)

        outer = self

        class _Completions:
            def create(self, model=None, messages=None, max_tokens=None):
                prompt = messages[-1]["content"]
                if prompt in outer.boom_on:
                    raise RuntimeError(f"branch {prompt} refused")
                time.sleep(outer.delays.get(prompt, 0))
                return _Resp(f"answer:{prompt}")

        self.chat = type("Chat", (), {"completions": _Completions()})()


def test_k1_n_prompts_return_n_answers_in_input_order():
    prompts = [f"q{i}" for i in range(5)]
    o = A.ask_many(prompts, client=_Client())
    assert o.ok and not o.partial
    branches = o.detail["branches"]
    assert [b["answer"] for b in branches] == [f"answer:q{i}" for i in range(5)]


def test_k2_branches_actually_run_concurrently():
    """A fan-out that serialises is not a fan-out. Five 0.4s branches must finish nearer 0.4s
    than 2.0s -- ask is I/O-bound, so the whole value here is overlap."""
    prompts = [f"q{i}" for i in range(5)]
    delays = {p: 0.4 for p in prompts}
    t0 = time.time()
    o = A.ask_many(prompts, client=_Client(delays=delays), max_workers=5)
    elapsed = time.time() - t0
    assert o.ok
    assert elapsed < 1.2, (
        f"5 x 0.4s branches took {elapsed:.2f}s -- serial would be ~2.0s. Not running concurrently.")


def test_k3_one_bad_branch_does_not_kill_the_fan():
    """THE ONE THAT MATTERS. A binary aggregate throws away the partial result, which is the
    T169/T179 defect at fleet scale -- nine seat-tasks returning two findings read as failure."""
    prompts = ["good1", "bad", "good2"]
    o = A.ask_many(prompts, client=_Client(boom_on={"bad"}))
    assert o.ok is True, "two of three landed; that is not a failure"
    assert o.partial is True, "nor is it a clean success"
    assert bool(o) is False, "a partial fan is falsy so nobody mistakes it for complete"
    assert "2" in o.why and "3" in o.why, f"the aggregate must say how many landed: {o.why!r}"
    branches = o.detail["branches"]
    assert [b["ok"] for b in branches] == [True, False, True], "order and per-branch verdicts kept"
    assert "refused" in branches[1]["why"], "the failed branch names its own cause"


def test_k4_a_total_wipeout_is_a_failure_that_still_counts():
    o = A.ask_many(["a", "b"], client=_Client(boom_on={"a", "b"}))
    assert o.ok is False
    assert "0" in o.why and "2" in o.why


def test_k5_aggregate_spend_is_the_sum_of_the_branches():
    o = A.ask_many(["a", "b", "c"], client=_Client())
    branches = o.detail["branches"]
    per = [b["usd"] for b in branches]
    assert all(x is not None for x in per), "a priced model must price every branch"
    assert abs(o.detail["usd"] - sum(per)) < 1e-9, "the fan must report what the fan cost"
    assert o.detail["n_ok"] == 3 and o.detail["n"] == 3


def test_k6_input_order_survives_reversed_completion_order():
    """first finishes LAST. Attribution depends on order, so completion order must not leak."""
    o = A.ask_many(["first", "second"],
                   client=_Client(delays={"first": 0.5, "second": 0.0}), max_workers=2)
    assert [b["answer"] for b in o.detail["branches"]] == ["answer:first", "answer:second"]


def test_k7_an_empty_fan_is_a_named_failure():
    o = A.ask_many([], client=_Client())
    assert o.ok is False and o.why, "asking nothing is not the same as asking and hearing nothing"


def test_k8_ask_many_touches_no_seat_machinery():
    """The T171 guard still holds at N. The moment a branch acquires a lock or a cursor it has
    become a seat, and N seats is the path whose failure rate motivated this whole primitive."""
    tree = ast.parse(open(os.path.join(ROOT, "core", "comm", "ask.py"), encoding="utf-8").read())
    forbidden = {"runner_lock", "seed_cursor", "roster", "mailbox", "worklive",
                 "acquire", "bifrost_send", "heartbeat", "role_queue", "expectations"}
    referenced = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                referenced.update(alias.name.split("."))
        elif isinstance(node, ast.ImportFrom):
            referenced.update((node.module or "").split("."))
            for alias in node.names:
                referenced.add(alias.name)
        elif isinstance(node, ast.Attribute):
            referenced.add(node.attr)
        elif isinstance(node, ast.Name):
            referenced.add(node.id)
    assert not sorted(forbidden & referenced)
