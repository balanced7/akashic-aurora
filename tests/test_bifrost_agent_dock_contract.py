"""Contract pins for the Bifrost composer agent dock.

The browser interaction is dogfooded separately.  These pins keep the load-bearing
parts of that interaction visible in the single-file UI: hover is progressive
enhancement, keyboard/touch remain usable, and an ordinary agent choice can never
silently become multicast or Broadcast.
"""

from pathlib import Path


UI = (Path(__file__).parents[1] / "scripts" / "bifrost_ui.py").read_text(encoding="utf-8")


def _between(start: str, end: str) -> str:
    return UI.split(start, 1)[1].split(end, 1)[0]


def test_agent_avatar_is_an_accessible_listbox_trigger():
    tag = UI.split('id="ash-frame"', 1)[1].split(">", 1)[0]
    assert 'role="button"' in tag
    assert 'tabindex="0"' in tag
    assert 'aria-label="Choose recipient. Current: Broadcast"' in tag
    assert 'aria-haspopup="listbox"' in tag
    assert 'aria-controls="ash-content"' in tag
    assert 'aria-expanded="false"' in tag


def test_fine_pointer_hover_is_enhancement_not_the_only_door():
    wiring = _between("function wireAshPicker()", "function setTargetAndCloseAsh")
    assert "(hover:hover) and (pointer:fine)" in wiring
    assert "pointerenter" in wiring
    assert "pointerleave" in wiring
    assert "keydown" in wiring
    assert "focusin" in wiring


def test_plain_agent_choice_replaces_and_broadcast_is_explicit():
    choose = _between("function chooseAshRecipient", "function setBroadcastAndCloseAsh")
    assert "setTargetAndCloseAsh(aid)" in choose
    assert "event.shiftKey||event.ctrlKey||event.metaKey" not in choose

    broadcast = _between("function setBroadcastAndCloseAsh", "function updateAshLabel")
    assert "setRecipients(['all'])" in broadcast


def test_secondary_roster_is_an_explicit_touchable_multiselect():
    tag = UI.split('id="rosterPop"', 1)[1].split(">", 1)[0]
    assert 'role="listbox"' in tag
    assert 'aria-multiselectable="true"' in tag

    choose = _between("function chooseRosterRecipient", "function toggleRoster")
    assert "accumulateRecipient(aid, true)" in choose
    assert "setTarget(aid)" not in choose
    assert "event.stopPropagation()" in choose
    render = _between("function renderRosterPop", "renderRecipient();")
    assert '<button type="button"' in render
    assert 'data-agent=' in render


def test_picker_is_body_portaled_and_reduced_motion_safe():
    wiring = _between("function wireAshPicker()", "function setTargetAndCloseAsh")
    assert "document.body.appendChild(content)" in wiring
    assert "prefers-reduced-motion:reduce" in UI
    assert ".agent-choice" in UI


def test_escape_focuses_trigger_before_closing_to_avoid_focus_reopen_loop():
    wiring = _between("function wireAshPicker()", "function setTargetAndCloseAsh")
    escape = wiring.split("else if(e.key==='Escape'){", 1)[1].split("}", 1)[0]
    assert escape.index("frame.focus()") < escape.index("closeAsh(false)")


def test_pointer_caused_focus_cannot_double_toggle_touch_picker():
    wiring = _between("function wireAshPicker()", "function setTargetAndCloseAsh")
    assert "_ashPointerFocus=true" in wiring
    assert "if(!_ashPointerFocus" in wiring


def test_multicast_does_not_mark_multiple_primary_picker_options_selected():
    render = _between("function renderAshPicker()", "function positionAshDock")
    assert "singleton=ashSelectedAgent()" in render
    assert "selected=!!singleton&&singleton===aid" in render


def test_floating_avatar_drag_repositions_open_dock():
    drag = _between("function wireModule(el, btn)", "function initResizables")
    assert "el.id==='ash-frame'" in drag
    assert "positionAshDock()" in drag
    close = _between("function scheduleAshClose()", "function toggleAsh")
    assert "classList.contains('mod-drag')" in close


def test_secondary_roster_has_roving_keyboard_and_escape_paths():
    wiring = _between("function wireAshPicker()", "function setTargetAndCloseAsh")
    assert "rosterMoveFocus(e.key)" in wiring
    assert "toggleRoster(true)" in wiring
    assert "closeRoster(true)" in wiring


def test_legacy_click_away_keeps_visibility_and_aria_state_together():
    click_away = _between("document.addEventListener('click', function(e)", "// --- send ---")
    assert "closeRoster(false)" in click_away
    assert "classList.remove('show')" not in click_away
