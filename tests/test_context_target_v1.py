"""W0.1 pins (RED first): context.target.v1, the one key every spine record joins on.

SPEC: research/in-flight/context-system-navi-m1.md (sealed) AS AMENDED BY
      research/in-flight/context-system-navi-m1-amendment-1.md (Navi, 2026-10-02).
      Where the two disagree the amendment wins; these pins encode the amendment.
Wave 0 row W0.1. Builder: claude. Author and blind verifier: Navi (kimi).

WHY THIS EXISTS. Daniel, 2026-08-10: "We need to make all of my words queriable and to have links
to what was around them at the time... queriable not just grepable." And 2026-08-16: "a string
through a forest you can walk with by hand so you dont need to re-discover relationships between
different things." A string can only be walked if every knot on it has one name. Measured in this
tree: one file has at least four live spellings across the planes, `git worktree list` reports 62
worktrees of which the leaf `shadow` collides 48 times and `AI-Setup` twice, and six ref spellings
already ride `refs[]` that no resolver can parse.

HOW THIS SET CAME TO BE, because the method is the point. The builder wrote a first RED set against
the sealed grammar, then ran two blind evidence passes before writing any implementation: one over
this repository, one over outside standards (SARIF, LSP, Bazel, git, OpenTelemetry, fsatrace,
ShellCheck). They returned eighteen contradictions, filed as questions at
research/in-flight/w01-schema-contradictions-2026-10-02.md rather than patched into the sealed
grammar, because the grammar is Navi's. She ruled on all eighteen and amended once, in writing,
after re-verifying the load-bearing claims herself. These pins are that amendment, mechanically.

Hermetic by construction: roots arrive as strings, existence as a callable, and short-sha
resolution as an injected callable. Nothing here touches the disk, the git binary, or Redis.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.coord import target as T  # noqa: E402

MAIN = "E:/AI-Setup"
SUN = "C:/Users/L5/AppData/Local/AkashicAurora/worktrees/sunshine-discord-split"
CODEX = "C:/Users/L5/.codex/worktrees/e5d8/AI-Setup"          # leaf collides with MAIN (A1)
DRY1 = "C:/Users/L5/AppData/Local/Temp/season_dryrun_0qd7ld36/shadow"
DRY2 = "C:/Users/L5/AppData/Local/Temp/season_dryrun_9xk2mm41/shadow"
NEST = "E:/AI-Setup/.claude/worktrees/screenspace-step0"       # nested inside main (A3)

FULL_SHA = "383b8f34c2d53146b69cd6f89e9f4f6be73a677d"


def _sha(short):
    """Injected stand-in for `git rev-parse` (B3): one known short form resolves, nothing else."""
    return FULL_SHA if FULL_SHA.startswith(short.lower()) else None


ROOTS = T.Roots(main=MAIN, worktrees=(SUN, CODEX, DRY1, DRY2, NEST), resolve_sha=_sha)


def p(text, **kw):
    return T.parse(text, roots=ROOTS, **kw)


# ---------------------------------------------------------------- the schema's own constants
def test_schema_name_is_the_sealed_one():
    assert T.SCHEMA == "context.target.v1"


def test_the_ref_set_is_closed_at_eight_kinds():
    # sealed set plus `mem`, admitted by amendment A5. Closed for Wave 0.
    assert set(T.REF_KINDS) == {"event", "sha", "task", "lesson", "mem", "doc", "session", "seat"}


def test_the_action_set_carries_move_and_delete():
    assert set(T.ACTIONS) == {"read", "write", "exec", "search", "move", "delete"}


def test_the_column_unit_is_declared_not_assumed():
    # B1: a column with no declared unit cannot join. SARIF requires columnKind; we pin UTF-16.
    assert T.COL_UNIT == "utf16CodeUnits"


# ---------------------------------------------------------------- four spellings, one key
@pytest.mark.parametrize("spelling", [
    "core/coord/orient.py",
    "./core/coord/orient.py",
    "file:core/coord/orient.py",                 # A5: file: is an alias of the path anchor
    "E:/AI-Setup/core/coord/orient.py",
    r"E:\AI-Setup\core\coord\orient.py",
    r"e:\ai-setup\core\coord\orient.py",         # A10: drive and root fold, below-root does not
])
def test_four_spellings_of_one_file_are_one_key(spelling):
    t = p(spelling)
    assert t.kind == "file"
    assert t.key == "core/coord/orient.py"
    assert t.work is None                        # B2: unprefixed IS the main checkout


def test_case_below_the_root_is_preserved_verbatim():
    # A10 / B7, SARIF's producer rule: preserve the filesystem's casing, fold only drive+root.
    assert p("E:/AI-Setup/core/Coord/Orient.py").key == "core/Coord/Orient.py"
    assert p("core/Coord/Orient.py").key != p("core/coord/orient.py").key


def test_no_work_main_spelling_is_minted():
    # B2: one plane, one key. `work:main:` would be a second key for the same plane.
    with pytest.raises(T.TargetError):
        p("work:main:core/coord/orient.py")


# ---------------------------------------------------------------- foo:3.py, line and column
def test_a_file_named_foo_colon_3_survives_as_a_path():
    t = T.parse("foo:3.py", roots=ROOTS, exists=lambda k: k == "foo:3.py")
    assert t.kind == "file" and t.key == "foo:3.py" and t.line is None


def test_an_existing_colon_digit_path_beats_the_line_rule():
    # B4: on Windows the colon is reserved for NTFS alternate data streams, so `app.py:12` is a
    # legal path. Existence decides; the digit rule is the input convenience, not the authority.
    t = T.parse("app.py:12", roots=ROOTS, exists=lambda k: k == "app.py:12")
    assert t.kind == "file" and t.key == "app.py:12" and t.line is None


def test_the_same_string_parses_as_a_line_when_no_such_path_exists():
    t = T.parse("app.py:12", roots=ROOTS, exists=lambda k: False)
    assert (t.kind, t.path, t.line) == ("file_line", "app.py", 12)


def test_line_suffix_is_parsed_only_when_the_tail_is_all_digits():
    t = p("core/coord/orient.py:12")
    assert (t.kind, t.path, t.line, t.col) == ("file_line", "core/coord/orient.py", 12, None)
    assert t.key == "core/coord/orient.py:12"


def test_line_and_column_carry_the_unit():
    t = p("core/coord/orient.py:12:3")
    assert (t.line, t.col, t.col_unit) == (12, 3, "utf16CodeUnits")
    assert t.key == "core/coord/orient.py:12:3"


def test_path_line_col_are_separate_fields_and_the_key_is_derived():
    # B4: every mature standard keeps these as fields; the colon string is display and input only.
    t = p("core/coord/orient.py:40:7")
    assert t.path == "core/coord/orient.py" and t.line == 40 and t.col == 7
    assert t.key == "core/coord/orient.py:40:7"


def test_line_on_a_windows_absolute_path():
    assert p(r"E:\AI-Setup\core\coord\orient.py:40").line == 40


# ---------------------------------------------------------------- dir by trailing slash
def test_dir_is_marked_by_the_trailing_slash_and_only_by_it():
    d, f = p("core/coord/"), p("core/coord")
    assert (d.kind, d.key) == ("dir", "core/coord/")
    assert (f.kind, f.key) == ("file", "core/coord")
    assert d.key != f.key


def test_backslashed_dir_keeps_its_marker():
    assert p("E:\\AI-Setup\\core\\coord\\").key == "core/coord/"


# ---------------------------------------------------------------- worktrees (A1, A2, A3)
def test_an_uncolliding_worktree_uses_the_bare_leaf():
    t = p(SUN + "/core/comm/bus.py")
    assert t.work == "sunshine-discord-split"
    assert t.key == "work:sunshine-discord-split:core/comm/bus.py"


def test_a_colliding_leaf_is_disambiguated_by_its_parent_segment():
    # A1, verified live by Navi: leaf `AI-Setup` belongs to both the main checkout and a codex
    # worktree. The common case pays nothing; disambiguation is paid only where a collision exists.
    t = p(CODEX + "/core/comm/bus.py")
    assert t.work == "e5d8-AI-Setup"
    assert t.key == "work:e5d8-AI-Setup:core/comm/bus.py"


def test_two_shadow_worktrees_get_distinct_keys():
    a = p(DRY1 + "/x.py")
    b = p(DRY2 + "/x.py")
    assert a.work == "season_dryrun_0qd7ld36-shadow"
    assert b.work == "season_dryrun_9xk2mm41-shadow"
    assert a.key != b.key


def test_a_collision_that_parent_cannot_break_refuses_loudly_never_guesses():
    roots = T.Roots(main=MAIN, worktrees=("C:/a/dup/shadow", "C:/b/dup/shadow"))
    with pytest.raises(T.TargetError) as e:
        T.parse("C:/a/dup/shadow/x.py", roots=roots)
    assert "collision" in str(e.value).lower()


def test_a_worktree_nested_inside_the_main_checkout_is_a_work_key():
    # A3: plane membership is decided by `git worktree list`, not by containment. The longest
    # matching root wins, so the nested worktree beats the main root that contains it.
    t = p(NEST + "/core/x.py")
    assert t.work == "screenspace-step0"
    assert t.key == "work:screenspace-step0:core/x.py"


def test_the_canonical_work_spelling_round_trips():
    t = p("work:sunshine-discord-split:core/comm/bus.py:9")
    assert (t.work, t.path, t.line) == ("sunshine-discord-split", "core/comm/bus.py", 9)
    assert t.key == "work:sunshine-discord-split:core/comm/bus.py:9"


def test_a_worktree_path_is_not_rebased_onto_main():
    assert p(SUN + "/core/comm/bus.py").key != p("core/comm/bus.py").key


def test_a_clone_is_not_a_worktree_and_mints_no_work_key():
    # A2: E:/AI-Setup-Alpha is a separate clone, owned by the WORLD organ, not by `work:`.
    with pytest.raises(T.TargetError) as e:
        p("E:/AI-Setup-Alpha/core/x.py")
    assert "root" in str(e.value).lower()


def test_dotdot_above_the_root_is_clamped_and_flagged_never_followed():
    t = p("../../outside.txt", cwd=MAIN)
    assert "clamped" in t.flags and not t.key.startswith("..")


def test_relative_path_resolves_against_the_captured_cwd():
    assert p("orient.py", cwd=MAIN + "/core/coord").key == "core/coord/orient.py"


# ---------------------------------------------------------------- refs (A4-A9, B3)
def test_a_ref_wins_over_a_path_of_the_same_spelling():
    t = p("task:T418")
    assert (t.kind, t.ref_kind, t.key) == ("ref", "task", "task:T418")


def test_event_ref_takes_the_id_after_the_last_colon():
    # A4: the stream name is itself colonned, so first-two-colons cannot be the general rule.
    t = p("event:events:raw:1790911373414-0")
    assert t.kind == "ref" and t.ref_kind == "event"
    assert t.key == "event:events:raw:1790911373414-0"
    assert t.stream == "events:raw" and t.entry_id == "1790911373414-0"


def test_per_agent_event_stream_also_splits_on_the_last_colon():
    t = p("event:events:claude:raw:1790911373414-0")
    assert t.stream == "events:claude:raw" and t.entry_id == "1790911373414-0"


@pytest.mark.parametrize("text", [
    "sha:" + FULL_SHA, "commit:" + FULL_SHA, "git:" + FULL_SHA, FULL_SHA,
    "sha:383b8f34", "commit:383b8f34", "git:383b8f34",
])
def test_every_sha_spelling_canonicalises_to_one_full_forty_hex_key(text):
    # A7 aliases + B3 full-form storage: a short sha is unique only while the repo stays small.
    t = p(text)
    assert t.kind == "ref" and t.ref_kind == "sha"
    assert t.key == "sha:" + FULL_SHA


def test_an_unresolvable_short_sha_refuses_loudly():
    with pytest.raises(T.TargetError):
        p("sha:deadbee")


def test_learn_experiment_is_an_input_alias_of_the_canonical_lesson_kind():
    canonical = p("lesson:experiment:zero_is_not_no")
    alias = p("learn:experiment:zero_is_not_no")
    assert canonical.key == alias.key == "lesson:experiment:zero_is_not_no"
    assert alias.ref_kind == "lesson"


def test_mem_decision_is_an_admitted_kind():
    t = p("mem:decision:ADR_1001233734_dbdae891")
    assert t.kind == "ref" and t.ref_kind == "mem"
    assert t.key == "mem:decision:ADR_1001233734_dbdae891"


@pytest.mark.parametrize("text,key", [
    ("doc:docs/CONDUCT.md", "doc:docs/CONDUCT.md"),
    ("session:428ba6c4-2217-4008-a2be-ecd9901cc3b2", "session:428ba6c4-2217-4008-a2be-ecd9901cc3b2"),
    ("seat:claude", "seat:claude"),
])
def test_the_remaining_closed_kinds(text, key):
    t = p(text)
    assert t.kind == "ref" and t.key == key


@pytest.mark.parametrize("text", ["bifrost:1790911373414-0", "blob:a1b2c3d4e5f6"])
def test_an_opaque_spelling_is_named_as_opaque_never_silently_demoted(text):
    # A5: these are real join keys the byref index uses, and NOT context.target.v1 refs.
    # "Zero is not no": the resolver says it knows and declines, rather than failing confusingly
    # or quietly parsing them as paths.
    t = p(text)
    assert t.kind == "opaque" and t.key == text
    assert t.ref_kind is None


@pytest.mark.parametrize("bad", ["sha:not-hex", "task:T1", "event:events:raw:", "lesson:"])
def test_a_malformed_ref_is_refused_never_demoted_to_a_path(bad):
    with pytest.raises(T.TargetError):
        p(bad)


def test_task_ids_accept_two_to_four_digits_on_input():
    # A9: lenient on input, tight on emit. T01 is admitted deliberately.
    assert p("task:T01").key == "task:T01"
    assert p("task:T0418").key == "task:T0418"


# ---------------------------------------------------------------- url, verb, question
def test_url_anchor():
    t = p("https://learn.microsoft.com/en-us/windows/")
    assert (t.kind, t.key) == ("url", "https://learn.microsoft.com/en-us/windows/")


def test_verb_anchor():
    assert p("verb:boot").kind == "verb"


def test_bare_prose_is_a_question_routed_to_cast_never_resolved():
    assert p("how does the recall funnel decide what to show?").kind == "question"


# ---------------------------------------------------------------- the extraction contract
EXISTS = {"core/coord/orient.py", "core/comm/bus.py", "scripts/x.py", "a.py", "b.py",
          "x.py", "core/", "core/coord/", "notes.md", "out.txt", "log.txt"}


def x(cmd, shell="bash", cwd=MAIN):
    return T.extract(cmd, shell=shell, cwd=cwd, roots=ROOTS, exists=lambda k: k in EXISTS)


def pairs(ext):
    return sorted((t.action, t.target.key) for t in ext.targets)


def roles(ext):
    return sorted((t.action, t.role, t.target.key) for t in ext.targets)


def test_an_uninspectable_command_emits_null_not_an_empty_list():
    # B5, SARIF's null-vs-empty distinction, which is this house's "zero is not no" law:
    # null means "cannot see", [] means "looked and there was nothing".
    ext = x("py - <<'EOF'\nimport json\nprint(json.dumps({}))\nEOF")
    assert ext.targets is None
    assert ext.incomplete is True


def test_command_substitution_cannot_be_seen_into_and_says_so():
    ext = x("echo $(cat a.py)")
    assert ext.targets is None and ext.incomplete is True


def test_a_command_that_touched_nothing_emits_a_measured_zero():
    ext = x("cd core && git status")
    assert ext.targets == [] and ext.incomplete is False


def test_a_heredoc_wrapper_is_not_itself_a_target_but_its_redirect_is():
    ext = x("cat > notes.md <<'EOF'\nhello\nEOF")
    assert pairs(ext) == [("write", "notes.md")]


def test_a_write_emits_one_write_target_not_a_read():
    assert pairs(x("sed -i s/a/b/ core/coord/orient.py")) == [("write", "core/coord/orient.py")]


def test_redirections_are_writes():
    assert pairs(x("cat a.py > out.txt")) == [("read", "a.py"), ("write", "out.txt")]
    assert ("write", "log.txt") in pairs(x("echo hi >> log.txt"))


def test_pipeline_stages_are_walked():
    assert pairs(x("grep -rn foo core/ | head -5")) == [("search", "core/")]


def test_exec_is_the_invoked_script():
    assert ("exec", "scripts/x.py") in pairs(x("py scripts/x.py --flag value"))


def test_copy_reads_the_source_and_writes_the_destination():
    assert pairs(x("cp a.py b.py")) == [("read", "a.py"), ("write", "b.py")]


def test_a_move_carries_both_ends_so_a_rename_does_not_look_like_a_create():
    # B6, fsatrace's vocabulary: losing the source makes a file's lifecycle invisible.
    assert roles(x("mv a.py b.py")) == [("move", "from", "a.py"), ("move", "to", "b.py")]


def test_a_delete_is_its_own_action_not_a_write():
    assert pairs(x("rm x.py")) == [("delete", "x.py")]
    assert pairs(x("Remove-Item x.py", shell="powershell")) == [("delete", "x.py")]


def test_a_listing_is_a_search_not_a_read():
    # B6 resolves the question the first pin set deferred.
    assert pairs(x("ls core/")) == [("search", "core/")]
    assert pairs(x("Get-ChildItem core/", shell="powershell")) == [("search", "core/")]


def test_a_glob_is_captured_literally_as_its_directory():
    assert ("search", "core/") in pairs(x("grep -l foo core/*.py"))


def test_a_nonexistent_bare_token_is_not_invented_as_a_read():
    assert pairs(x("echo hello world")) == []


def test_powershell_read_and_write():
    assert pairs(x("Get-Content core/coord/orient.py | Select-Object -First 3",
                   shell="powershell")) == [("read", "core/coord/orient.py")]
    assert pairs(x("Set-Content -Path out.txt -Value 1", shell="powershell")) == [("write", "out.txt")]


def test_extraction_targets_are_typed_targets_carrying_their_worktree():
    ext = x("cat " + SUN + "/core/comm/bus.py")
    (touch,) = ext.targets
    assert touch.action == "read"
    assert touch.target.key == "work:sunshine-discord-split:core/comm/bus.py"
