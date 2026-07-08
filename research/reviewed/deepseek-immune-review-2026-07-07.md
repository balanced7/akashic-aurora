**Q1** — No. Root‑scoping + `<!-- rot-ok -->` + allowlist are *too* permissive without lifetime or review.
An allowlist entry stays forever; a `rot-ok` comment is invisible to PR review. After one sprint
the allowlist becomes a dumping ground and the guard passes while real references rot.  
**Fix:** require any `rot-ok` to carry a **expiry date** and warn after expiry; make the allowlist
require a comment linking to an issue that explains *why* the reference is not a repo path. Without
that the guard creates false confidence.

**Q2** — Yes. Mirror should run **only F + G** (stale‑ref + case). A+B (index freshness) require
full index regeneration and compare; they’re heavy and belong in `ship.py`. The publish path is for
documentation commits; letting a stale index through is harmless because `ship.py` will block anything
that goes to production. Latency for F+G is a stat call per referenced path — negligible.

**Q3** — Two‑step rename is safest even on case‑insensitive Windows:  
```
git mv lexicon.md _tmp_lexicon.md
git mv _tmp_lexicon.md LEXICON.md
git commit -m "canonicalize LEXICON.md case"
```
If the OS won’t allow a case‑only rename directly, the intermediate temp name avoids the half‑commit.

**Q4** — (c) “name‑lies” is partially caught by the stale‑ref check (if a docstring references a
deleted module path it fails F), so deferring explicit FAIL for semantic name‑lies is correct.
LEXICON‑coverage (e) is too subjective for FAIL; WARN is right. Nothing load‑bearing is deferred.

**Q5** — Missing vectors:
- **References to docs themselves:** the guard scans only code‑roots, not `docs/` paths. A living doc
  referring to a deleted `docs/FAQ.md` is invisible. Add `docs/` to the scanned roots.
- **Semantic rot where the file exists but content is wrong** (e.g., module docstring says “handles
  authentication” but the code was refactored to authorization). The path exists, so F passes.
  This is the “name‑lies” problem — deferred, but it’s a huge drift hole.
- **References inside Python code** (f‑strings, comments) that mention a missing module. Not caught.
- **Non‑code assets** (`.yaml`, `Dockerfile`) not scanned; references there can rot silently.

---

### (a) Three‑property framing
Missing property: **NON‑EVADABLE** — the guard must prevent its own escape hatches from being
permanently abused. An allowlist or marker that never expires turns the guard into a theatre.
A pillar‑grade immune system must make exemptions **explicit, time‑bound, and reviewable**.  
Thus the proper decomposition is **COMPLETE, UNBYPASSABLE, TRUSTWORTHY, NON‑EVADABLE**.

### (b) Attack — residual holes after shipping
1. **Direct `git push` bypass.** The guard lives in `mirror.py`. Anyone pushing straight to the
   remote (e.g., `git push origin main`) never triggers it. Drift enters the shared repo without
   a peep. The immune system is *bypassed on the main distribution path*.
2. **Allowlist rot.** `REF_ALLOWLIST` and `<!-- rot-ok -->` will accumulate stale exemptions.
   In 6 months every reference is allowlisted and the guard is a silent no‑op.
3. **Stale semantic references.** A module docstring says “depends on `core.auth`” but `auth` was
   deleted and a similarly‑named `core.authz` exists — the path failure is not caught because
   `core/auth` is gone but `core/` exists, so the reference is a stale *sub‑module name*, not a
   full path? Actually the check might catch it if the path `core.auth` is translated to
   `core/auth.py` and that file missing — but it would be caught. The deeper hole is that the
   reference might be “depends on authentication logic in `core/auth.py`” but the module still
   exists but does something else; no check for that.
4. **Case mismatch in code imports, filenames, or CI scripts.** G only guards `docs/`. A case
   error in `core/` module names that is tolerated on the developer’s case‑insensitive FS will
   ship and break on Linux CI — but the immune system won’t notice.
5. **Fail‑soft silently masking guard crashes.** A bug in the scan wrappers causes an exception;
   the guard prints a WARN and returns 0. That is *false green*. Nobody reads the warn output
   unless the commit is blocked, so the immune system rots undetected.

### (c) Wiring point
`mirror.py` is **not** the right chokepoint. It’s a convenience script, not a forced gateway.
The single unbypassable point is the **remote’s pre‑receive hook** (or, if that’s not possible,
a CI check on main‑branch pushes that blocks the merge). At minimum, the guard must run in CI
with **fail‑hard** on every PR that targets main, and direct pushes to main must be disabled.
`mirror.py` is only a local nicety; as a pillar it’s leaky.

### (d) False‑confidence flags
- **Allowlist markers → green but reference is dead.** Adding `<!-- rot-ok -->` to a stale ref
  makes the guard pass. No mechanism ensures the marker is removed when the link is fixed later.
- **Fail‑soft crashes → green but guard is broken.** A stack trace hidden behind a WARN is
  indistinguishable from “everything ok”. This will happen.
- **Git‑tracked case check on docs only → green but code case is wrong.** The guard will happily
  accept `core/UTILS.py` vs `core/utils.py` if it’s in code, giving the illusion of case health.
- **Living doc with stale ref to `docs/OTHER.md` → green because scan roots exclude `docs/` itself.**
  The design misses the most common drift: documentation linking to other documentation that has
  been renamed or deleted. The immune system won’t even look.
