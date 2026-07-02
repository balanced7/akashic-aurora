---
name: verified-done
description: Use when about to claim any work is complete, fixed, passing, or shipped — before saying "done", "should work now", "that fixes it", or committing. Also use at the end of every slice, before wrap/handoff, and whenever you notice you are asserting an outcome you have not freshly observed.
---

# Verified done

**Iron Law: no completion claims without fresh verification evidence.** "Fresh" means you
ran the check in THIS state of the code and read its output — not that it passed earlier,
not that the edit looked right.

## The gate (IDENTIFY → RUN → READ → THEN CLAIM)

1. **Identify** the command that would prove the claim (test file, full suite, the actual
   CLI invocation, the hook fed a real payload).
2. **Run it now.** For a slice: the full suite — this repo's ship ritual runs it for you:
   ```
   py scripts/ship.py "<msg>" <explicit paths> --learn-exp <name> --tried "..." --result "..."
   ```
   (gate: boundaries + doc-freshness + full pytest → commit+push with EXPLICIT paths →
   lesson → snapshot; any failure aborts before anything is committed).
3. **Read the output** — the count, the exit, the rendered artifact. Eyeball one REAL
   render of anything user-facing (a boot screen, a draft, a hook injection), not just
   its unit test.
4. **Then claim, with the evidence in the same breath** ("suite 578 passed; pushed as abc123").

## Red-flag phrases (each one means STOP and verify)
- "Should work now" · "Probably passes" · "Done!" (before running anything)
- "The tests should still pass" (run them)
- "I've made the change" (an accepted Edit is not a working change)

## Repo-specific truths
- Dogfood through the real CLI against canonical-shaped data; unit fixtures verify units,
  dogfooding verifies the seam.
- Report failures faithfully: if the gate fails, say so with the output — never soften it.
- A slice is not done until mirrored AND the where-we-are note reflects it
  (`py agent_cli.py note <id> --title where-we-are --note "..."` supersedes by title).
- Honest labels: "worked" means self-reported; only independent corroboration earns more.
  The same discipline applies to your own claims.

## Why this gate feeds the memory loop
The FAIL→SUCCESS credit and the value-rate funnel are only as honest as the SUCCESS half.
A claimed-but-unverified success would credit lessons that helped nothing — verification
is what keeps the whole learning loop's currency real.
