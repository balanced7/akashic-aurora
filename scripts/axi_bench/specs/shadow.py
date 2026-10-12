"""AXI bench spec: `shadow` -- preview a ToolBox action without executing it.

Offline by construction: build_intent_shadow reads the advertised ToolBox schema and the ACL and
never imports the bus writers. The checkout has no security/acl.json, so the bootstrap floor
quarantines `bench` and every preview is refused by authority (the same in both trees).
"""

VERB = "shadow"
SEED = []
SEND = '{"to": "kimi", "kind": "request", "text": "please rerun the suite"}'
RUNS = {
    "send": ["shadow", "toolbox:bifrost_send", "--agent", "bench", "--args-json", SEND],
    "nudge": ["shadow", "toolbox:bifrost_nudge", "--agent", "bench", "--args-json", '{"to": "kimi", "text": "wake"}'],
    "unsupported": ["shadow", "toolbox:delete_everything", "--agent", "bench"],
    "bad_json": ["shadow", "toolbox:bifrost_send", "--agent", "bench", "--args-json", "{bad"],
}
EMPTY = None
QUESTIONS = [
    {"run": "send", "q": "Is the subject allowed to perform this action? Answer yes or no.", "a": "no",
     "grade": "exact"},
    {"run": "send", "q": "Which capability is missing?", "a": ["bus.send"], "grade": "contains"},
    {"run": "send", "q": "What risk level does the preview assign?", "a": "elevated", "grade": "exact"},
    {"run": "send", "q": "How many proposed effects are listed?", "a": 4, "grade": "number"},
    {"run": "nudge", "q": "Was anything actually sent? Answer yes or no.", "a": "no", "grade": "exact"},
    {"run": "unsupported", "q": "Which actions are supported? List them separated by commas.",
     "a": ["toolbox:bifrost_send", "toolbox:bifrost_nudge", "toolbox:bifrost_steer"], "grade": "set"},
]  # fmt: skip
