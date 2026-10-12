"""AXI bench spec: `fence` -- fence workspaces (slots, seals, the M1-PV citation pass).

Fences live in files under AKASHIC_FENCE_ROOT (default: <repo>/fences). The bench points that
variable at a temporary directory outside the repo and builds the fixture here, at import,
through core.coord.fence_workspace itself: SEED cannot do it through the CLI, because seeding
runs once per side and a second `fence write` into a sealed slot is refused. The runs are read
paths (list, status) plus a seal that its checks refuse, which writes nothing.
"""

import os
import tempfile

_ROOT = tempfile.mkdtemp(prefix="axi-fence-")
os.environ["AKASHIC_FENCE_ROOT"] = _ROOT  # inherited by every CLI run the harness makes

from core.coord import fence_workspace as fw  # noqa: E402 -- reads the root set above

_BRIEF = "CHARTER\nx\nINPUTS\nx\nRULES OF ENGAGEMENT\nx\nTHE QUESTION\nx\nOUTPUT CONTRACT\nx\n"
_HALF = "V1. the bus keeps order [CERTAIN] see core/comm/bus.py:10\nV2. routing moves [INFERRED]\n"

fw.open_fence("t054-design", question="Should routing move into the bus?", tier="full", by="claude")
fw.write_slot("t054-design", "brief", _BRIEF, by="claude")
fw.seal("t054-design", "brief", by="claude")
fw.write_slot("t054-design", "half_a", _HALF, by="kimi")
fw.seal("t054-design", "half_a", by="kimi")
fw.write_slot("t054-design", "half_b", _HALF + "V3. see core/fake/nothing.py [UNCERTAIN]\n", by="deepseek")
fw.run_pv("t054-design")

fw.open_fence("t060-lite", question="Is the wake seat per session?", tier="lite", by="sol")
fw.write_slot("t060-lite", "brief", "CHARTER\nx\nINPUTS\nx\n", by="sol")

fw.open_fence("t070-closed", question="Retire the HMAC bridge?", tier="full", by="claude")
fw.write_slot("t070-closed", "brief", _BRIEF, by="claude")
fw.seal("t070-closed", "brief", by="claude")
for _slot, _who in (("half_a", "kimi"), ("half_b", "deepseek")):
    fw.write_slot("t070-closed", _slot, _HALF, by=_who)
    fw.seal("t070-closed", _slot, by=_who)
fw.run_pv("t070-closed")
fw.write_slot("t070-closed", "reconciliation", "Both halves agree: retire it.\n", by="claude")
fw.seal("t070-closed", "reconciliation", by="claude")

# Two words: the conformance checks append a bogus flag to the verb and its required action.
VERB = "fence list"
SEED: list = []
RUNS = {
    "list": ["fence", "list"],
    "status": ["fence", "status", "t054-design"],
    "refused": ["fence", "seal", "t060-lite", "--slot", "brief", "--by", "sol"],
}
EMPTY = None
QUESTIONS = [
    {"run": "list", "q": "How many fences exist?", "a": 3, "grade": "number"},
    {"run": "list", "q": "Which fence is closed? Give its id.", "a": "t070-closed", "grade": "exact"},
    {
        "run": "status",
        "q": "Which slots of fence t054-design are sealed? List them separated by commas.",
        "a": ["brief", "half_a"],
        "grade": "set",
    },
    {"run": "status", "q": "Who wrote the half_b slot?", "a": "deepseek", "grade": "exact"},
    {"run": "status", "q": "How many citations did the PV pass find missing?", "a": 1, "grade": "number"},
    {
        "run": "refused",
        "q": "How many M1-BRIEF sections are missing from the brief that could not be sealed?",
        "a": 3,
        "grade": "number",
    },
]
