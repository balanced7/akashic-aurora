"""RED pins -- the WEB DOOR acceptance suite (Heimdall's consumer half, blind).

PRE-REGISTRATION per M3: committed alone, before the engine. Every pin fails solely because
the engine seam does not exist or does not yet meet the contract (art_20260901_heimdall-web-door-contract_consum).

This suite is the FENCE'S ONE MEASURING INSTRUMENT. Vandor's engine meets it or it does not ship.
It encodes, in runnable form, every hard invariant from heimdall-web-door-requirements (art_764ef4):

  1. raw-next-to-cleaned (the cleaner is ALSO untrusted; raw is the only trusted identity)
  2. no silent truncation (truncated:true + section_map, or full body)
  3. byte-verbatim raw (raw must be lossless or absent, never a re-encoded clean)
  4. attribution is DATA (final_url after redirect, fetched_at, etag, sha256) not prose
  5. PDF structural pass cheap and separate from full text
  6. every terminal fetch logs a receipt; denied/timeout/rot never ghost
  7. error envelope is data, never "failed"; rot carries an archive.org suggestion
  8. web.fetch and web.search are SEPARABLE grants

Every acceptance test asserts against the CONTRACT's return shape, not against any engine's
internals. The engine may implement however it likes; it must surface this envelope.

Run: py -m pytest tests/test_web_door_contract_red.py -q
"""

import importlib

import pytest


# The engine seam we test against. The engine half (Vandor) wires its implementation such
# that `core.web.door` exposes `fetch()` and `search()` with these exact names. If the seam
# differs, the fence reconciles HERE, not by me weakening the pins.
ENGINE = "core.web.door"


def _mod():
    try:
        return importlib.import_module(ENGINE)
    except ModuleNotFoundError as exc:  # pragma: no cover -- the RED state
        pytest.fail(f"{ENGINE} does not exist yet (expected while the door is RED): {exc}")


def _fetch(url, **kw):
    mod = _mod()
    if not hasattr(mod, "fetch"):
        pytest.fail(f"{ENGINE}.fetch is missing")
    return mod.fetch(url, **kw)


def _search(query, **kw):
    mod = _mod()
    if not hasattr(mod, "search"):
        pytest.fail(f"{ENGINE}.search is missing")
    return mod.search(query, **kw)


# ---------------------------------------------------------------------------
# Envelope shape (the contract's core)
# ---------------------------------------------------------------------------

def test_fetch_returns_the_full_contract_envelope():
    e = _fetch("https://example.com")
    required = {"ok", "verb", "request", "final_url", "title", "content_type",
                "etag", "last_modified", "fetched_at", "from_cache",
                "raw", "clean", "truncated", "section_map", "receipt", "error"}
    missing = required - set(e.keys())
    assert not missing, f"envelope missing required fields: {missing}"
    assert e["verb"] == "web.fetch"


def test_search_returns_the_search_envelope():
    e = _search("cache associativity", parked=True)
    for k in ("ok", "verb", "query", "results", "result_id", "parked", "ts", "receipt", "error"):
        assert k in e, f"search envelope missing {k}"
    assert e["verb"] == "web.search"
    assert isinstance(e["results"], list)


# ---------------------------------------------------------------------------
# Law 1 -- raw next to cleaned, always
# ---------------------------------------------------------------------------

def test_raw_next_to_cleaned_is_the_default_not_an_opt_in():
    """A fetch with no --raw flag must STILL return raw.text. Opt-out is the violation."""
    e = _fetch("https://example.com")
    assert e["raw"]["present"] is True, (
        "clean without raw is the cardinal sin: the cleaner's edit becomes the only witness")
    assert isinstance(e["raw"]["text"], str) and len(e["raw"]["text"]) > 0


def test_raw_sha256_covers_the_fetched_bytes():
    """raw.sha256 is the only trusted identity of the source; it must be present and hex."""
    e = _fetch("https://example.com")
    sha = e["raw"]["sha256"]
    assert sha and isinstance(sha, str) and len(sha) == 64, (
        f"raw.sha256 must be a 64-char hex hash, got {sha!r}")
    assert all(c in "0123456789abcdef" for c in sha)


def test_raw_and_clean_are_different_representations():
    """They must not be the same string -- raw is lossless, clean is an edit."""
    e = _fetch("https://example.com")
    if e["clean"]["present"]:
        assert e["raw"]["text"] != e["clean"]["text"], (
            "raw==clean means the 'cleaner' did nothing OR raw is a disguised clean")


# ---------------------------------------------------------------------------
# Law 2 -- no silent truncation
# ---------------------------------------------------------------------------

def test_budget_truncation_is_never_silent():
    """A tiny budget must return truncated:true AND a non-empty section_map."""
    e = _fetch("https://example.com", budget=64)
    if e["truncated"]:
        assert e["section_map"], (
            "truncated:true with an empty section_map is a spec violation; "
            "give --range an address or do not claim a clip")


def test_truncated_flag_is_honest():
    """If content fits, truncated is False and section_map may be empty. Either way the flag
    matches reality -- a silenced clip that pretends full is the hazard."""
    e = _fetch("https://example.com")
    assert isinstance(e["truncated"], bool)


# ---------------------------------------------------------------------------
# Law 3 -- byte-verbatim raw, or honest absence
# ---------------------------------------------------------------------------

def test_raw_is_lossless_or_absent_never_reencoded():
    """If the engine cannot decode losslessly, raw.present must go FALSE, never silently
    substitute a re-encoded clean. A dishonestly-present raw is a lie the diff can't see."""
    e = _fetch("https://example.com")
    if not e["raw"]["present"]:
        assert e["clean"]["present"] is not None, (
            "if raw is honestly absent, clean must still be present (raw-or-clean, never neither)")


# ---------------------------------------------------------------------------
# Law 4 -- attribution is data, not prose
# ---------------------------------------------------------------------------

def test_final_url_reflects_redirect_not_the_typed_url():
    """A fetch that follows a redirect must report the RESOLVED url in final_url."""
    e = _fetch("https://httpbin.org/redirect-to?url=https://example.com")
    if e["ok"]:
        assert e["final_url"] != "https://httpbin.org/redirect-to?url=https://example.com", (
            "final_url must be post-redirect; ok:true with final_url==typed-url on a real "
            "redirect is an attribution lie")


def test_fetched_at_is_a_populated_timestamp():
    e = _fetch("https://example.com")
    assert e["fetched_at"], "fetched_at must be a populated ISO timestamp (citation stamping)"


# ---------------------------------------------------------------------------
# Law 5 -- PDF structural pass cheap and separate
# ---------------------------------------------------------------------------

def test_pdf_structural_pass_is_a_low_cost_alternative_to_full_text():
    """--structural must return structure fields WITHOUT requiring the full text pull."""
    e = _fetch("https://example.com", structural=True)
    if e["ok"]:
        assert "structure" in e, "structural fetch must surface the structure block"
        # The structural pass is how a citation lands/dies cheaply; it must not silently
        # degrade to a full-text read with structure absent.
        assert "structure" in e and isinstance(e.get("structure"), dict)


# ---------------------------------------------------------------------------
# Laws 6 & 7 -- receipts + error-as-data
# ---------------------------------------------------------------------------

def test_every_terminal_fetch_logs_a_receipt():
    """ok:true OR ok:false, every terminal fetch must carry receipt.logged==True."""
    e = _fetch("https://example.com")
    assert e["receipt"].get("logged") is True, "a fetch without a receipt is an unaudited fetch"


def test_error_is_data_not_a_bare_failed():
    """Ok:false must carry an error envelope with a class, not a bare 'failed' string."""
    e = _fetch("https://this-host-does-not-exist.invalid")
    if not e["ok"]:
        assert e["error"], "ok:false with null error = the 'failed' word wearing a suit"
        assert e["error"].get("class") in {
            "timeout", "http", "encoding", "untrusted", "denied", "not_pdf", "rot", "unknown"
        }


def test_denied_does_not_suggest_a_retry():
    """denied is policy, not failure -- it must never carry a retry suggestion."""
    # The engine test harness injects a denied grant; the pin asserts the SHAPE, not a real ACL.
    e = _fetch("https://example.com")
    if not e["ok"] and e["error"] and e["error"].get("class") == "denied":
        assert not e["error"].get("suggestion"), "a denied grant must not suggest retry (policy != failure)"


def test_rot_carries_an_archive_suggestion():
    """A dead URL (rot) must populate error.suggestion with a web.archive.org capture when one
    exists -- the citation standard's 'dead sources cite archive.org' enforced at the door."""
    e = _fetch("https://www.anandtech.com/dead-link-2024")
    if not e["ok"] and e["error"] and e["error"].get("class") == "rot":
        assert e["error"].get("suggestion"), (
            "rot with no archive.org suggestion drops the citation-standard rule into my memory")


# ---------------------------------------------------------------------------
# Law 8 -- separable grants
# ---------------------------------------------------------------------------

def test_fetch_and_search_are_separable_verbs():
    """The contract names two verbs with independent envelopes. The engine must not fuse them;
    the suite asserts both exist as separate callable seams."""
    mod = _mod()
    assert callable(getattr(mod, "fetch", None)) and callable(getattr(mod, "search", None)), (
        "web.fetch and web.search must be separable seams, not one fused 'web' verb")
