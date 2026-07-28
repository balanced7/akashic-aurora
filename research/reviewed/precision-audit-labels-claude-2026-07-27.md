# RECALL PRECISION AUDIT -- claude's BLIND labels

Pack: research/in-flight/precision-audit-pack-2026-07-27.md (30 cases, 62 items, seed=1)
Labeller: claude (fresh Opus 5 seat, 2026-07-27 ~19:50)
Written BEFORE opening research/reviewed/precision-audit-labels-deepseek-2026-07-27.md.

## CONTAMINATION DISCLOSURE (read this before trusting the number)

Not fully blind. The handoff note I booted on states deepseek's aggregate (precision 0.048)
and the verdict it triggered. I never saw a single one of deepseek's PER-ITEM labels, which is
what the comparison is made of, but I knew the headline before I judged.

Direction of the bias matters: anchoring pulls a second labeller TOWARD the first number.
I landed an order of magnitude AWAY from it. The contamination worked against this result,
so it is not the explanation for the gap.

## THE BAR I APPLIED (state it, because the open question IS the bar)

  on   = the item's CONTENT pertains to the subject matter of the action; a competent agent
         taking that action could act on it, be warned by it, or be pointed somewhere by it.
  off  = the item is a keyword collision -- it shares vocabulary with the action and nothing else.
  skip = genuinely undecidable from the action text.

Explicitly NOT my bar, per the module docstring ("NOT THE SKIM TEST -- usage is not relevance"):
  - not "did the agent use it"          (a dismissed item can be on-point)
  - not "was it useful"                 (a known fact is still on-point)
  - not "did it change the outcome"     (that is a different, harder question)

Applied consistently: a lesson whose TRIGGER CONDITION is false for this actor/action is off
even when the topic matches (see 30:a vs 28:b below -- the same lesson, labelled differently,
because case 30 reveals the message kind and case 28 does not).

## LABELS

case 1  [path] tests/test_filestore_durability.py
  1:a  on    FileStore + "add a test so FileStore cannot mask the mismatch" -- same subsystem,
             same artifact type, and the guidance is executable in that exact file. Weakest of
             my `on` calls: durability != type coherence.

case 2  [command] read a background daemon's output file to see if kimi answered out-of-band
  2:a  on    trigger is "background watcher/daemon dies silently, no output" -- that is the
             literal question the command is asking.

case 3  [command] events --get <id> | head -80
  3:a  off   interactive-UI event-stream rendering. Collides on "events".
  3:b  off   spine Wave1/Wave2 ordering. Roadmap position, not guidance for reading a record.
  3:c  off   span boundary markers. Closest of the three, still about deriving spans, not
             about fetching one event.

case 4  [command] boot claude --task "fresh seat" | grep -ie "directive|handoff|where-we-are"
  4:a  on    names "the fresh-boot stance gap" as the decay mode our curation misses. The
             action IS a fresh boot hunting the directive.
  4:b  off   task propose / visible todos.
  4:c  off   Goodhart under N metrics.

case 5  [command] events --get event:events:raw:<id> | tail -c 4500
  5:a  off   UI main-thread-never-waits.
  5:b  on    about the beat-id provenance stamp ON raw events -- the record being inspected.

case 6  [path] docs/filestore-coherence-design-2026-07.md
  6:a  off   narrative-memory prior art (arxiv list). Collides on "design".

case 7  [command] grep FileStore's write path (os.replace, .tmp, _flush, _load) in store.py
  7:a  off   RAGAS retrieval eval. Collides on "store". Different store, different question.

case 8  [command] fire PreToolUse + trace hooks with synthetic payloads via pyw
  8:a  on    "edit matcher, run one in-scope call, check tempdir for the artifact" -- the method
             the command is executing.
  8:b  on    recall-at-action hook polish incl. Bash recall; the payload is a bash command.
  8:c  on    trace-hook parity from a broad-matcher PreToolUse hook; both hooks under test.

case 9  [path] tests/test_w54_injections_by_family.py
  9:a  off   verb-belt taxonomy (function x altitude). Collides on "family/grouping"; belt
             entries and injection families are different subsystems.

case 10 [path] tests/test_precision_audit.py
  10:a off   a "next:" roadmap bookmark. Shares the retrieval-critic vocabulary, carries no
             content applicable to building the pins.
  10:b on    "topic-adjacency conflates with stance; precision-first; build eval datasets" --
             this is the design brief for the file being written.
  10:c on    "precision-first + silent-when-starved" -- implemented verbatim as STARVED in the
             module under test.

case 11 [command] census of curation verbs (recall-curate/triage/graduate/tag-anti-pattern --help)
  11:a on    weak. Body is mostly FAITH-1; the tail names FC-01 curate.py as the next curation
             slice, which is what a curation census is for. Dispute-prone, flagging it.

case 12 [command] git add readme.md docs/wishlist.md && git commit
  12:a off   "every SHA before the rewrite is dangling" -- applies to docs that CITE shas; this
             commit does not.
  12:b off   TrackRouter tiering.

case 13 [command] sed test_lost_update_is_prevented + filestore.cas
  13:a on    the lost-update hole, 66% loss at 3 processes, RB-8 CAS. Exact.
  13:b off   spine theme-discovery ablation.

case 14 [command] bifrost_runner_deepseek.py --help
  14:a off   gemini-web invisible/--headed flags. Different runner's flags.
  14:b off   gemini-web provider auto. Same.
  14:c on    the deepseek runner's own lock-release semantics.

case 15 [command] bifrost_wake.py --agent claude --session <id>
  15:a on    "expect 2-3 insta-fire arms on a fresh seat, let the sidecar converge". Exact.

case 16 [command] learn ... --experiment failure_count_is_a_function_of_which_tree_you_run_in
  16:a off   algorithmic collusion / multi-gradient design.
  16:b off   GWT hub bottleneck.
  16:c off   silent inline-script parse failure.
             All three off on a WRITE to the lesson store -- see MISS.

case 17 [path] core/comm/storm_detect.py
  17:a on    "was_paused before pausing", filed as amendment K2 to the storm auto-clear ceremony.

case 18 [command] bifrost-send -h
  18:a on    weak. Aimed at someone ADDING a send door, but its payload fact (oversize bodies
             auto-fragment) applies to a sender. See MISS -- the two dead-on lessons for this
             action exist and did not surface here.

case 19 [command] bifrost_wake.py --agent claude --session <id>
  19:a on    wake-seat identity from an inherited env token is re-entrant across twins.
  19:b on    arming the wake watcher, allowlist-denied background launch.
  19:c on    weakest of the three: its trigger says "supervised non-claude seat" and the actor
             is claude, but the subject is this exact command's failure mode.

case 20 [command] events --get event:events:raw:<id> | head -50
  20:a off   CTRL_BREAK / process groups.
  20:b off   as 3:b.
  20:c off   as 3:c.

case 21 [path] docs/wishlist.md
  21:a off   "use verb_noun_purpose naming in all docs" -- a stale to-do, and WISHLIST is an
             append-only wish ledger, not a naming-convention doc. Collides on "documentation".

case 22 [path] scripts/checkers/check_door_parity.py
  22:a on    "a write door must OFFER a field or it stays empty" -- door parity is the checker's
             subject.
  22:b off   mirror-and-file-a-lesson session hygiene.
  22:c off   June architecture punch-list; mentions a door and a sibling checker in passing.

case 23 [path] tests/test_corpus_gap_honesty.py
  23:a on    file refs fail CLOSED, directory refs fail OPEN -- the fails-open honesty disease.
  23:b on    "never validate a search path by fetching a KNOWN key" -- the starved-index case
             this test pins.
  23:c on    empirical census before asserting.

case 24 [command] bifrost-send --to deepseek --kind question, then --to kimi
  24:a on    "asks to deepseek: under ~2.5KB, one question per message". Exact.

case 25 [command] agent_cli.py doc --help | head -25
  25:a off   "never pipe the GATE" -- help text is not a gate.
  25:b off   stale boot directive.
  25:c off   "never pipe a long-running RUNNER through head" -- help text is not a runner.
             25:a and 25:c both fired on the `| head` token; neither trigger holds.

case 26 [path] scripts/bifrost_daemon.py
  26:a off   FAITH-1 roadmap.
  26:b on    "before any correctness verdict on daemon/supervisor/lifecycle code, static reading
             is insufficient". Exact.
  26:c on    daemon dies silently under a concurrent same-name seat.

case 27 [command] bifrost_runner_kimi.py --help
  27:a off   gemini web/AI-mode session notes.
  27:b on    runner startup batch-advances the cursor while handing over only the oldest message.

case 28 [command] bifrost-send --help | head -40
  28:a on    every send body goes through --text-file.
  28:b on    brief-composition law, triggered on bifrost-send. Message kind is unknown here,
             so the guidance is live. Contrast 30:a.
  28:c on    "inspect bifrost-send --help and use only its exposed flags". Literally the action.

case 29 [command] agent_cli.py status | head -40
  29:a off   aimed at WRITERS of terminal branches ("before returning the merged status"); the
             action is a read.
  29:b on    "when any status line reports nothing happened, verify with an independent read" --
             a warning about trusting this exact output.
  29:c off   UI HUD DOM diffing.

case 30 [command] bifrost-send --to claude --to-incarnation 7072fd7f --kind reply (twin concession)
  30:a off   same lesson as 28:b. Here the kind is known: a twin reply, not a brief, build order
             or charter. The trigger does not hold.

## TALLY

  on 30 | off 32 | skip 0 | unlabelled 0
  label coverage 62/62 = 1.000
  precision = 30/62 = 0.484

## RECALL ARM -- lessons that SHOULD have surfaced and did not

Every named lesson below is VERIFIED to exist in the corpus (seen in the pack itself or in this
seat's own boot context). None are invented.

  MISS 1   win_filestore_rename_race_births_orphans -- tmp->rename collisions on the Windows
           FileStore under concurrency. A durability test is where that gets pinned.
  MISS 6   filestore_coherence_hole_reproduced_66pct_loss -- it surfaced at case 13 and is the
           literal subject of the design doc being written at case 6.
  MISS 7   win_filestore_rename_race_births_orphans -- the grep targets os.replace and .tmp,
           which is the rename race by name.
  MISS 12  bifrost_pull_session_hygiene -- "a slice isn't done until it's mirrored (commit+push)".
           It surfaced at case 22 (a checker file) and not at the actual commit.
  MISS 16  nothing about writing lessons surfaced on a write to the lesson store (naming, the
           learn door, the size ceiling). Three web-research lessons surfaced instead.
  MISS 18  bifrost_send_supported_flags AND bifrost_send_always_text_file. Both exist, both are
           dead-on for `bifrost-send -h`, and both surfaced for case 28's near-identical action.
  MISS 30  two_live_seats_split_chunked_bus_delivery -- route directed delivery to a twin through
           a durable door. Case 30 is a twin-addressed send.

  misses in 7 of 30 cases -> misses_rate 0.233

## ONE STRUCTURAL FINDING -- RAISED, THEN RETRACTED BY ITS OWN CHECK

Cases 18 and 28 are the SAME action (`bifrost-send -h` vs `bifrost-send --help | head -40`).
Case 28 surfaced the three on-point send lessons. Case 18 surfaced one tangential lesson and
none of them. I flagged it as possible ranker instability under a trivial reword, and wrote
down what would kill it before checking.

CHECKED. IT IS DEAD. Two disconfirmations, in order:
  1. Anti-repeat suppression is NOT the explanation: the two firings are in DIFFERENT sessions
     (037dac55 @07-24 04:28 vs 09c59642 @07-25 17:12) and anti-repeat is per-session.
  2. But it does not REPRODUCE. Re-run live against the repaired 475-lesson index, both forms
     now return the same on-point set (bifrost_send_always_text_file + conductor_brief_intent_law).
     The divergence was index MEMBERSHIP at 07-24, not ranking under rewording.

RETRACTED. Nobody should build on it. The MISS 18 entry above stands as a historical fact about
that firing and must NOT be counted as a live ranking defect.

## LIVE RE-RUN AGAINST THE REPAIRED INDEX (the one that still bites)

Case 21 is the receipt the recall-index-blindness note cites as the proof of starvation
("editing docs/WISHLIST.md injected the semantic-naming lesson because there was almost nothing
else for the ranker to choose from"). Re-run now, at 475 indexed lessons:

  semantic_documentation_update_strategy is GONE. The note's explanation was correct.
  What replaced it:  conductor_morale_trinity_gate | mcp_boot_hang_c7_4_class_closed |
                     claude_trace_hook_user_vs_project_settings

All three are off-point for appending a wish to a wish ledger. The starved index explained WHICH
stale item surfaced; it does not explain THAT an off-point item surfaces. Repairing membership
changed the noise, not the signal-to-noise. This is the strongest single piece of evidence that
the constraint is ranking, and it is reproducible in one command:

  py agent_cli.py recall-at --path "e:\ai-setup\docs\wishlist.md" --limit 3
