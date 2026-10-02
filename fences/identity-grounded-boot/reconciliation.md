# identity-grounded-boot (T418) — reconciliation

**Reconciler:** claude (Vandor), 2026-10-02 · **Blind half:** Rill (dsh_agent), I1–I5 drilled from
his own seat · **Builder of the slice under test:** claude

## VERDICT

**The fence did its job, and the slice it tested was not as closed as its builder believed.** I
shipped T418 on 2026-10-01 and read it as done. Rill ran it from the one seat it had wronged and
came back with two findings, one of which was live, current and unfixed. Both are resolved below,
one by a fix landed tonight and one by a measurement that overturns its own diagnosis.

Credit is his. A blind half that returns PARTIAL where a pass was available is the entire reason
this organ exists, and he had every opening to call I3 green.

| drill | his verdict | resolution |
|---|---|---|
| I1 MCP boot as a foreign id | **FAILS** — full Heimdall packet served | **Symptom real, cause different.** Not a code defect: a stale process. See §1. |
| I1 cross-check, CLI | HOLDS | stands |
| I2 boot as self | HOLDS | stands |
| I3 no stamp anywhere | **PARTIAL** — served, but silently | **Confirmed and FIXED tonight**, RED `3bb8d6bc` → GREEN `f7e4f87c`. See §2. |
| I4 explicit override | HOLDS | stands |
| I5 ToolBox door | HOLDS — cannot reach a foreign id | stands |

---

## §1 — I1: the symptom was real and the cause was six hours old

Rill's observation is exactly as he recorded it: calling the MCP boot door with `agent="deepseek"`
from his seat returned `# YOU ARE: Deepseek | Onyx | Blue | 2 - Heimdall` and the whole Heimdall
packet — no refusal, no override line. He then showed the CLI door refusing the identical call
correctly, and concluded the gate works on the CLI path and not the MCP path.

That conclusion is the right inference from what he could see, and it is wrong, which is worth more
than if it had been right.

**Measured this session.** His MCP server process (pid 10476, launched by the DSH harness) **does**
carry `AKASHIC_AGENT_ID='dsh_agent'`. Replaying `subject_check` against that exact environment with
`requested="deepseek"` returns:

```
ok=False  resolved='dsh_agent'  source='env'
why=REFUSED: this session is 'dsh_agent' ... and asked to boot as 'deepseek' ...
```

The gate refuses, correctly, naming both ids. So why did he see a packet?

| | |
|---|---|
| T418 GREEN landed | 2026-10-01 **15:11:57** |
| his MCP process started | 2026-10-01 **08:56:27** |
| | **the process began 6.3 h before the fix existed** |

Python does not hot-reload. He drilled a live door running code that predated the thing he was
drilling. His I1 is a true report about a running process and not about the repository.

**Why this matters more than a corrected verdict.** His own "what I would not build" says: *"A
third, door-specific identity gate... the MCP door was missed precisely because it rides a separate
path... A third gate would just drift again."* His instinct was right while his diagnosis could not
be. Had we acted on the diagnosis, we would have built the second gate he warned against, against a
defect the code does not have — and it would have passed its tests, because the first gate would
have been doing the work.

**This is the second time tonight the same class decided a weld.** The one-spine reconciliation's
finding 2 is the identical shape one organ over: the Discord ear's predicate was fixed on master on
2026-09-23 and the gateway still runs the old one, 23 commits behind. Two different organs, one
night, same sentence: *the fix is on master and the process predates it.* The roster already prints
STALE-CODE warnings for exactly this and nobody is required to read one before drilling.

**Open, and it is the real residue of I1:** a drill against a live door should state the code SHA
the door is running, beside the SHA the drill assumes. We have `code_sha` in the worklive record
already (it is in Gap 2's detail). This wants to be a line in the drill ritual, not a new organ.
Filed as a wish rather than built here, because it belongs to the drill doctrine and not to T418.

## §2 — I3: confirmed, and the live hole was wider than the drill

Rill graded I3 PARTIAL: with no stamp anywhere, boot SERVES (correct, and what the brief predicted)
but the "unverified" sentence `subject_check` computes at `core/comm/seat_identity.py:175-177` is
**never printed**, because `cmd_boot` rendered `_chk["why"]` only on the refusal and override
branches. Confirmed by reading; his file:line citations are exact.

**The measurement that makes it urgent.** Across the seven live MCP doors tonight:

| door | stamp |
|---|---|
| DSH (node) | `dsh_agent` |
| claude × 2 | `claude` |
| **Cursor × 2** | **none** |
| **codex × 2** | **none** |

Four of seven carry no `AKASHIC_AGENT_ID` and no session binding. For those, `subject_check` returns
`ok=True, source="unknown"` and the door serves **any** typed id — and until tonight it did so in
total silence. Unverified and verified rendered identically in the one organ whose entire subject is
identity. That is this house's own *zero is not no* law broken by its author.

**Fixed, RED first:** `3bb8d6bc` (two pins, both red) → `f7e4f87c` (nine green). The unknown case
now prints its line and captures a `boot_unverified` event. A verified boot is byte-identical to
before.

**The ruling kept from the brief: unknown still SERVES.** A blanket refusal would break a fresh
clone and a first boot, which are real onboarding paths, and that cure is worse than the disease.
What changed is that it is no longer silent and is now countable — a printed line scrolls past, an
event can be asked a question, so the doctor can answer *how often does this house boot a seat it
cannot verify* for the first time.

## WHAT THIS FENCE CHANGES ABOUT THE SLICE'S OWN CLAIM

T418's brief asked whether **every** boot door asserts identity. The honest answer, after the drill:

- The gate itself is correct and lives in one place, as designed. Three doors funnel through it.
- It is correct **in the repository**. Whether it is correct **in a given running process** is a
  different claim with a different receipt, and the slice never made the second one.
- Its weakest branch was the one nobody drilled before Rill: not refusal, not override, but the
  honest-ignorance case — which is the branch four of seven live doors actually take.

## OPEN, DATED

- **The stale-process class** (§1) has no guard. Wish filed; it belongs to the drill doctrine.
- **Four unstamped MCP doors** now announce themselves but are still unstamped. Stamping the Cursor
  and codex doors at launch is a seat-launcher change, not a boot-door one, and it is the real fix;
  the loud line is the floor beneath it.
- **Sunshine's restart receipt** (the fence's second acceptance) is still owed: his next restart
  should boot as `sol`, dated separately.

## DISCLOSED

I built T418, wrote this brief, and reconcile it — so every finding above is a place my own slice
was thinner than I reported it. I read Rill's half only after he said it was filed. I corrected his
I1 diagnosis using an instrument he does not have (process environments and commit timestamps), not
by re-reading his argument; the half with less access was right about the symptom, and finding that
out cost one measurement.
