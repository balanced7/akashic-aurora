# Intact recall delivery

Daniel's 2026-09-16 direction: “I don't want anything truncated.” Selected recall
content must arrive at the caller intact, at the action or pull that requested it.
Whole-record selection limits stay; no larger arbitrary cap, separate long mode,
manual spill-file retrieval or new retrieval system.

## Pre-registered acceptance and review

The red tests in `tests/test_recall_intact.py` exercise tails beyond the former
110/160-character item cuts and 900/1200/16000/20000-character delivery cuts,
complete source/count/age/dissent/provenance information, CLI/MCP/hooks, seen
accounting, all four chat histories and the Codex governed read/combo route.
Generic non-recall output remains bounded; empty/no-match and authorization
behavior must remain unchanged. All fixtures and fake model replies are isolated.

Method tier: FULL because the reversible output change crosses `core/comm`.
Author and independent reviewer prepared expanded-scope halves separately before
implementation. Source citations were checked against this checkout before
reconciliation. Findings converged on all clipping sites; the reviewer added the
Codex governed read path and traced the original commit. Design divergence:
discard a string-subclass delivery protocol in favor of a small optional output
transform at ToolBox dispatch, applied before appending recall, plus explicit
recall tool-name exemptions in the other chat loops. The latter keeps existing
string interfaces and does not infer trusted output policy from text markers.

Preserve existing grammar, ACL checks, execution families and selection/ranking.
The command output exception applies only to authorized parsed recall argv;
interactive arbitrary shell output retains its cap. Combo budgets charge only
ordinary sections and must still preserve later recall or a failed recall tail.
The existing `list` alias and simple command-mediated recall share this policy.
Review also exercised malformed tool arguments and ordinary exception output:
neither may crash the chat loop or bypass its generic output bound.

## Origin and limits of the claim

Commit `31a1b6784e03f1d63342a2f9b20ceb1268d0db25` introduced the 110/900 cuts
on 2026-06-29 with compact, pointer-oriented hook presentation. Its comment cited
a purported 10k-character Claude additionalContext limit. Neither an enforced
external limit nor a measured reason for exactly 900 was established by this
investigation. This patch removes application output cuts, not model context
limits. No packet splitting is needed to remove these local constants.

Stored content remains the authority: historical intake overflow may already
contain a prefix and spill pointer. `recall --full` returns that stored record;
this output change does not reconstruct original spilled input. Boot summaries,
generic shell/file output and storage/message intake policies are separate.
Selection/faithfulness is also unchanged: an existing per-line faithfulness gate
can reject multiline recommendations before rendering. The subprocess fixture
uses a single-line recommendation that clears that gate; rendering and full-record
pull tests separately verify multiline content. This patch does not claim to
repair retrieval omissions or storage loss.

Existing long-lived services must load the integrated change before they exhibit
it. Worktree subprocess and fake-model history receipts establish the new code
path, not deployment to an already-running resident.

## Verification receipt (2026-09-17 UTC)

- Fresh focused run: **299 passed, 1 skipped, 3 deselected** in 31.44 seconds.
  All existing recall test modules were included except the explicitly RED
  `test_recall_dimension_recurrence_red.py`, whose target module is absent (16
  expected failures observed in the preceding run). Additional coverage included
  ToolBox, Kimi/Sol histories, Codex read grammar/combos, guarded execution, generic
  output bounds, and Claude/Cursor hook contracts.
- The three deselections reproduce with original implementations: two tests invoke
  the broken host `py` launcher ("No installed Python found"), and one assumes the
  inherited agent ID is `claude` while this test host inherits `sol`.
- The wider parity check also finds the pre-existing missing MCP `glance` verb.
  Neither the interpreter installation, inherited identity nor parity debt was
  changed by this patch. A Git test was corrected to recognize refusal at the
  start of output, instead of treating the word REFUSED in valid diff text as a
  failed authorization check.
- Real isolated subprocess door: recall-at **4,206 characters**, keyword recall
  **5,454**, full stored record **3,190**; every selected text/source and distinctive
  tail intact. Full-record multiline fields also survive. Fixture storage,
  scratch files and Redis port were isolated; no production lesson was seeded.
- Full suite attempted with `--maxfail=1`: **29 passed, 1 failed** before stopping.
  Failure: `test_agent_interface.py::test_messy_input_is_sanitized` expects an intake
  spill field <=4100 characters; unchanged intake returns 4105 including its
  pointer. This is not a global green-suite or release claim.
- Boundary checker: no new violations. `git diff --check`: clean.

The independent reviewer found and closed ordinary error-output bounding, the
`list` alias, command-mediated recall, malformed argument handling and alternate
authorized script-path spellings. No ranking, faithfulness, source selection,
cursor, authorization or intake policy was changed. Seen-source pins establish
complete text at the harness return boundary, not an external delivery ack.

Raw red/green, subprocess, baseline and full-suite receipts plus the two separate
review halves remain in the implementation worktree's `.task-work/`.

## Local integration receipt

Integrated the 14 reviewed paths into `E:/AI-Setup` on local `master` at base
`91b9315c`, after validating target hashes and `git apply --check`. Eleven modified
source/test files matched the base; the MCP file carried 29 unrelated added lines
(defaults and `glance`) that the one-line documentation patch preserved. The two
new files were absent before application. No broad copy, reset, commit, push,
mailbox consumption or resident restart was performed.

Fresh processes from the saved checkout: **311 passed, 1 skipped, 3 deselected**
in 32.00 seconds, including the long-tail subprocess test and MCP parity. The
saved checkout already had `glance`, so its parity tests pass; the isolated
worktree's earlier parity debt does not apply to that saved file.

Existing connection boundary was measured after integration: the attached MCP
still emitted the old individually clipped recall (899 characters after its final
whitespace strip). Its Python modules remain loaded. A narrow reload/reconnect of
that Aurora MCP server is needed to use the new renderer there. Persistent chat
runners likewise need their normal process reload to use updated delivery code;
no shared resident was interrupted. Newly invoked CLI and hook processes load
the integrated code immediately. External context capacity remains separate.
