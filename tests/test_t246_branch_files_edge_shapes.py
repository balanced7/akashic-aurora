"""T246 -- what an independent reviewer found in T244, after four self-verified slices.

T242/T243/T244/T245 all shipped self-verified: my pins, my live checks, no second reader. The
first fence run afterwards found two real defects in T244 within one pass, and both are the
SAME defect T244 existed to fix, reappearing through doors the pins did not open.

(a) `{"files": []}` -- an empty list is falsy, so the branch fell through to the fan-wide pack.
    A branch that explicitly asked for NOTHING received everything: verified at 8,815 chars of
    another branch's evidence. "No evidence" and "evidence unspecified" are different claims and
    the code could not tell them apart.

(b) `{"files": "README.md"}` -- a bare string is iterable, so `[str(x) for x in _f]` walked it
    CHARACTER BY CHARACTER and asked build_context for 'R', 'E', 'A', 'D'... The branch got zero
    evidence plus ten missing-file diagnostics that look exactly like real ones.

ADJUDICATED AND REJECTED, recorded so it is not re-filed. The same reviewer flagged that
`["a","b"]` and `["b","a"]` build two packs rather than one, against a docstring promising one
per "unique file set". That behaviour is CORRECT: build_context spends its per-call budget
FIRST-COME, so the two orders genuinely produce different packs -- one may include a file the
other skips. Sorting the cache key, which is the obvious fix, would introduce a real bug. The
words were wrong, not the code. `test_two_orders_stay_two_packs` freezes that so a future
tidy-up cannot quietly "optimise" it.

Note on (b) and T245's lesson. T245 recorded that a coercion at a door destroys capability, and
this fix normalises a string into a list -- which looks like the same move and is not. That
coercion turned a RICHER type into a poorer one and destroyed information (a dict became its own
repr). This one is lossless and unambiguous: a string is exactly one path, there is no second
reading. The test is whether information survives, not whether a conversion happened.
"""
import pytest

from core.comm import ask as ask_mod


class _Msg:
    def __init__(self, content):
        self.content = content


class _Choice:
    def __init__(self, content):
        self.message = _Msg(content)
        self.finish_reason = "stop"


class _Usage:
    prompt_tokens = 10
    completion_tokens = 5


class _Resp:
    def __init__(self, content):
        self.choices = [_Choice(content)]
        self.usage = _Usage()


class RecordingClient:
    def __init__(self):
        self.bodies = []
        outer = self

        class _Completions:
            def create(self, **kwargs):
                outer.bodies.append(kwargs["messages"][-1]["content"])
                return _Resp("ANSWER")

        class _Chat:
            completions = _Completions()

        self.chat = _Chat()


@pytest.fixture
def repo_files(tmp_path):
    (tmp_path / "shared.py").write_text("SHARED_TOKEN = 1\n" * 20, encoding="utf-8")
    (tmp_path / "own.py").write_text("OWN_TOKEN = 2\n", encoding="utf-8")
    return tmp_path


def test_an_explicit_empty_file_list_means_no_evidence(repo_files):
    """"I need nothing" must not be answered with "here is everything".

    Verified before the fix: the branch received 8,815 chars of the fan-wide pack. A declared
    standpoint that silently inherits another branch's evidence is exactly what T244 shipped
    to end -- this is that defect, one door over.
    """
    c = RecordingClient()
    ask_mod.ask_many([{"prompt": "I need nothing", "files": []}],
                     with_files=[str(repo_files / "shared.py")],
                     context_root=str(repo_files), client=c)

    assert "SHARED_TOKEN" not in c.bodies[0], (
        "a branch declaring files=[] inherited the fan-wide pack. An empty list is an "
        "ASSERTION that this branch needs no evidence; only an absent key means unspecified.")


def test_an_absent_files_key_still_inherits_the_shared_pack(repo_files):
    """The other half. Absent means unspecified, and unspecified still means shared."""
    c = RecordingClient()
    ask_mod.ask_many([{"prompt": "unspecified"}],
                     with_files=[str(repo_files / "shared.py")],
                     context_root=str(repo_files), client=c)
    assert "SHARED_TOKEN" in c.bodies[0], (
        "a dict with no files key must behave exactly like a plain string prompt")


def test_a_bare_string_is_one_path_not_a_bag_of_letters(repo_files):
    """Verified before the fix: missing = ['R','E','A','D','M','E','.','m', ...]."""
    c = RecordingClient()
    out = ask_mod.ask_many([{"prompt": "q", "files": str(repo_files / "own.py")}],
                           context_root=str(repo_files), client=c)

    branch = (out.detail or {})["branches"][0]
    ctx = branch.get("context") or {}
    included = [i.get("path", "") for i in ctx.get("included", [])]
    missing = [m.get("path", "") for m in ctx.get("missing", [])]

    assert not missing, (
        f"a bare string was walked character by character: {missing[:8]}")
    assert len(included) == 1 and included[0].endswith("own.py"), (
        f"the single named file should be the only evidence: {included}")
    assert "OWN_TOKEN" in c.bodies[0], "the branch never received the file it named"


def test_two_orders_stay_two_packs(repo_files, monkeypatch):
    """FREEZES A REJECTED FINDING. Do not "optimise" this into one pack.

    build_context spends its per-call budget FIRST-COME, so ["big","small"] and
    ["small","big"] genuinely differ -- one may include a file the other skips. Sorting the
    cache key would merge two different packs into one and hand a branch evidence it never
    received. The docstring said "unique file set"; the words were wrong, not the code.
    """
    calls = []
    real = ask_mod.build_context

    def counting(paths, **kw):
        calls.append(tuple(paths))
        return real(paths, **kw)

    monkeypatch.setattr(ask_mod, "build_context", counting)

    a, b = str(repo_files / "shared.py"), str(repo_files / "own.py")
    c = RecordingClient()
    ask_mod.ask_many([{"prompt": "q1", "files": [a, b]},
                      {"prompt": "q2", "files": [b, a]}],
                     context_root=str(repo_files), client=c)

    assert len(calls) == 2, (
        f"the two orders must remain two packs, got {len(calls)} build(s): {calls}. "
        "The budget is spent first-come, so order changes what a branch actually sees.")
