"""
Bifrost Console -- unit tests for the pure helpers (the interactive TUI is run by a human).

Bar: input parsing routes broadcast vs @direct vs /command; sender colors are stable; a message
formats to readable text. No TTY / prompt_toolkit needed here (those imports are lazy in the app).

Run: py -m pytest tests/test_bifrost_console.py -q
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import bifrost_console as bc


def test_parse_input_routes():
    assert bc.parse_input("hello all") == {"action": "send", "to": "*", "kind": "chat", "body": "hello all"}
    assert bc.parse_input("@claude ship it") == {"action": "send", "to": "claude", "kind": "chat", "body": "ship it"}
    assert bc.parse_input("/who") == {"action": "command", "cmd": "who", "arg": ""}
    assert bc.parse_input("/name bob") == {"action": "command", "cmd": "name", "arg": "bob"}
    assert bc.parse_input("   ")["action"] == "noop"


def test_color_for_is_stable_and_themed():
    assert bc.color_for("claude") == "#d97757"
    assert bc.color_for("cursor") == "#6cb6ff"
    assert bc.color_for("human") == "#7ee787"
    assert bc.color_for("CLAUDE") == "#d97757"               # case-insensitive
    assert bc.color_for("zephyr") == bc.color_for("zephyr")  # deterministic fallback
    assert bc.color_for("zephyr").startswith("#")


def test_format_message_is_readable():
    ft = bc.format_message("claude", "cursor", "handoff", "hello world", "2026-06-28T20:42:00")
    text = "".join(t for _, t in ft)
    for token in ("claude", "cursor", "hello world", "handoff", "20:42"):
        assert token in text
    # broadcast renders as "all"; non-str content is coerced; a bad timestamp doesn't crash
    ft2 = bc.format_message("a", "*", "chat", {"x": 1}, "not-a-date")
    text2 = "".join(t for _, t in ft2)
    assert "all" in text2 and "{'x': 1}" in text2


def test_app_module_imports():
    assert hasattr(bc, "main") and callable(bc.main)


if __name__ == "__main__":
    for fn in [test_parse_input_routes, test_color_for_is_stable_and_themed,
               test_format_message_is_readable, test_app_module_imports]:
        fn()
    print("BIFROST CONSOLE HELPER TESTS PASSED")
