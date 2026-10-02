# t386-pre-execute-recall-gate — RECONCILIATION — Vandor / claude

Independence: I hold no half here and did not author the brief, so this fence has cleaner
separation than t385 (where I declared a conflict). One note for the record: the brief was
authored by dsh_agent, who also holds half_b, and half_a argues the brief's premise DOWN. That
is not misconduct — this fence predates the seat-note principle doors-design established — but
it is the configuration where a brief can shape the answer that shares its seat, so I have
weighted half_a's dissent on its evidence rather than discounting it as contrarian.

---

## 1. VERDICT: half_a's architecture, on half_b's evidence — and neither could see that

**Do not build a new pre-execute gate. Extend the veto layer that already exists.**

This is half_a's position (V0/position statement: "the gate already exists, and it is
deny-with-teaching on classed dangers"). I ratify it — but the decisive argument for it is
**half_b's M2**, which half_a could not have cited and half_b did not draw this conclusion from.

The two halves were not blind only to each other. **They had asymmetric access to evidence.**
half_a states it plainly in V0: the brief's seam citations resolve to the DSH *runtime bundle*
under `$DSH_HOME`, which is not in this repo and not readable from half_a's seat. half_b, on
the harness seat, could read it. So half_a reasoned about a contract it was structurally unable
to measure.

And what half_b measured settles it:

> **M2.** the pre-execute waterfall is wrapped in a try/catch that converts ANY listener throw
> into `toolErrorResult(error)` — a throwing pre-execute listener **BRICKS the tool call**.

That is the strongest possible argument for half_a's conclusion. Registering a *new* listener
on that waterfall puts a fresh failure mode in the path of every tool call, where any
unhandled exception in our code bricks the call rather than degrading. Extending a veto layer
that is already wired, already multi-harness, and already fails open is strictly safer.

**half_b's evidence supports half_a's design.** Neither half could see it, because seeing it
required both the runtime measurement and the architectural position at once. That is the
fence paying for itself.

---

## 2. VERIFICATION — half_a's central claim, checked from source

half_a asserts the gate already exists. Confirmed, and it is more built out than the half says:

* `agent/harness/guards.py` — `git_veto(command)` and `lock_veto(path, agent_id, id_hint)`,
  with the teaching text owned centrally so "the verdict text comes from here" regardless of
  harness.
* Already wired into **three** adapters: `agent/harness/hooks/claude_pretooluse.py` (:203,
  :213), `cursor_beforeshell.py` (:41), `cursor_pretooluse.py` (:54, :56).

So deny-with-teaching at pre-execute is not a thing to design. It is deployed, shared, and
has an established shape. The open question the brief *should* have asked is narrower and
better: **can the veto layer's fuel be extended from two hardcoded classes to lesson-declared
scopes** (the t385 output), without changing its seam?

---

## 3. THE BRIEF'S NON-NEGOTIABLE CONSTRAINT IS ALREADY FALSE, CORRECTLY

Both halves work under the brief's fail-open constraint. half_a leans on it ("keeps the
non-negotiable fail-open constraint trivially satisfiable"). It is not absolute in the code
that exists, and the exception is deliberate:

> `guards.py` docstring: "Both guards fail OPEN when their policy layer is unavailable
> (advisory by design), **but the lock guard fails CLOSED on an un-verifiable lock**: a
> silently-unset agent id must not disable peer protection." (RC-01)

`git_veto` fails open on any policy exception. `lock_veto` fails open on an unavailable lock
layer — **and fails CLOSED when it cannot verify who you are**, teaching the fix in the deny
text.

That is the right rule and the brief's framing would have argued it away. **Correction to the
brief:** the constraint is not "always fail open." It is *fail open when the POLICY is
unavailable; fail closed when IDENTITY is unverifiable.* An unavailable policy means we know
nothing and must not block. An unverifiable identity means we cannot tell your edit from a
peer's, and allowing it silently disables protection for someone else. Those are different
failures and the existing code already distinguishes them.

Any lesson-scoped extension must inherit **that** rule, not the flattened version.

---

## 4. WHAT SURVIVES FROM HALF_B REGARDLESS

half_b's measurements are not wasted by the ruling — they become the implementation contract
for the DSH adapter of the extended veto layer:

* **M1**: `{kind:"deny", reason: TEXT}` materialises as `isError:true` with the text verbatim
  in the tool result the model reads next. **The feedback channel IS the injection channel** —
  no `additionalContexts` needed. That is the single most useful line in either half and it
  applies to the veto layer exactly as it would have to a new gate.
* **M2**: fail-open cannot be satisfied by the harness; the **adapter** must catch its own
  exceptions and return allow. Every adapter of the veto layer needs this, and the two Cursor
  adapters and the Claude adapter should be audited for it — a Python hook that raises has a
  different blast radius than a JS listener that throws, and nobody has checked.
* **M3**: the plugin registers zero `tools/pre-execute` listeners today, so the DSH side of
  the veto layer is unbuilt. That is the actual gap, and it is smaller than a new gate.

---

## 4b. M1-PV: 7 MISSING, and again none of them is a false claim

PV reports 14 verified / 7 MISSING. I checked all seven. **Zero are fabrications**, and five
of them are the very thing half_a diagnosed in V0.

**OUT-OF-REPO BUT REAL — the DSH runtime bundle.** half_a's V0 says these "resolve outside
this repo... not readable from this seat." Correct, and they exist. Found at
`C:\Users\L5\.dsh\profiles\node_modules\@deepseek-ai\`:

* `dsh-tools/lib/index.js` — **exists, 3,577 lines** (cited at :3105 and :3345)
* `dsh-tool-cordis/lib/index.js` — **exists, 7,594 lines** (cited at :5394)

I verified half_b's load-bearing M1 down to the line rather than trusting it. `dsh-tools/lib/index.js:3105`:

    const gate = await this.ctx.waterfall(carrier, "tools/pre-execute", exec, () => Promise.resolve({ kind: "allow" }));

That is M1 exactly: the pre-execute waterfall defaults to allow. **half_b's measurement is
confirmed against the deployed runtime**, which is the one piece of evidence half_a was
structurally unable to obtain and on which §1's ruling turns.

**SHORTENED RE-REFERENCE:** `lib/index.js` — exists at `agent/harness/dsh_plugin/lib/index.js`,
cited in full elsewhere in the same half. Same PV bug as t385.

**PLAN FILE:** `tests/test_t386_veto.py` — proposed, correctly not yet existing.

**No section retired. All seven stand.**

**SECOND FENCE, SECOND 100% FALSE-POSITIVE RATE.** t385 produced 9/9 false; this produces 7/7.
Sixteen consecutive false reds across two fences whose halves both obeyed their briefs. This
adds a sixth category to the taxonomy in
`a_gate_whose_reds_are_all_false_trains_you_to_mutilate_correct_work`: **out-of-repo but real**
— a dependency bundle a half can legitimately measure and cite, which PV cannot resolve because
it only walks the project root. For a house with a foreign-harness seat, that category is not
an edge case; it is half the evidence the DSH seat can uniquely provide.

## 5. PINS

* The veto layer's fuel becomes lesson-declared scopes (t385's output); its **seam does not
  change**.
* Every adapter catches its own exceptions and returns allow — pinned per adapter, not once.
  (M2, generalised.)
* The fail-open/fail-closed split is preserved as **policy-unavailable vs identity-unverifiable**
  (§3), not flattened.
* Teaching text stays owned by `guards.py` so the verdict is identical across harnesses.
* Fatigue: the deny classes stay few. A veto that fires on scope-matched lessons at large is
  the alert-fatigue failure the brief itself names — and t385's §4 finding (the derivation
  matches shell plumbing) means a scope-fed veto would inherit those false positives *as
  denials*. **Do not wire lesson scopes into a DENY path until t385's plumbing-strip ships.**
  That ordering is load-bearing and neither fence could state it alone.

---

## 6. FOR DANIIL'S GATE

1. **Ratify half_a's architecture** — extend the veto layer, do not add a gate. The dissent was
   right and half_b's own measurement is why.
2. **Correct the brief's fail-open constraint** to the two-case rule in §3.
3. **Sequence t385 before t386.** A deny path fed by a derivation that matches `tail` would
   convert tonight's false-positive finding into blocked tool calls. This is the one place
   where these two fences must be read together, and it is my finding rather than either
   half's.
