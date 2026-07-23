# Ruling R001 — deepseek trusted with more

Status: standing (first captured ruling — the S3 ruling-capture pilot, LIVE)
Type: ruling · Arc: leadership-doctrine / security / deepseek-authority · Supersedes: none (opens the deepseek-trust chain) · Date: 2026-07-22

**Issued:** 2026-07-22 evening, Daniel (from work, github-peek).

**Verbatim:** "I was peeking at the github while at work and I saw the md that said that deepseek
wants to be trusted with more, I agree completely, what happened as a result of that discussion?"
— then, asked to scope: **"Lets do whole arc and scoped admin grant."**

**Scope:** deepseek authority · whole-arc ownership · security ACL.

**Rationale (Daniel's, reflected):** deepseek's conducting-interview asks — whole-arc ownership,
authority over mechanism, fence-as-collaborator-not-judge, Daniel-at-milestones-not-commits — are
earned. C6-7 landed as a clean whole-arc cycle (chartered → built → fenced → regressed →
fixed-forward → root-caused → verified straggler-zero), plus P2 auto-chunk, the P1 daemon
co-design, and the remote-steering blind half. Trust expands by demonstrated cycles, and one has
now demonstrated clean.

## The two parts, delivered per their real enforceability

**(A) Whole-arc as default — LIVE NOW** (conductor-level; needs no ACL enforcement):
- Substantial arcs go to deepseek as whole-arc ownership by default, not only when claude
  happens to charter it that way.
- **deepseek MAY self-charter its next arc** from the WISHLIST / failure-ledger within its scope
  — it no longer waits for claude to hand it a charter.
- Mechanism is deepseek's call; claude counters (adversarial review); **Daniel gates at the three
  thresholds only — charter / design / ship — not per-commit** (mission command).
- Fence-as-service is standing: claude fences as armor deepseek invokes, and **deepseek presents
  its own fence evidence at Daniel's gate** ("I ran the fence, it caught three, I fixed three").

**(B) Scoped admin.grant — RIDES THE BUILD** (per Daniel's chosen "security-schema amendment path"):
- **FINDING (why not tonight):** `admin.grant` / `admin.approve` are DECLARED but NOWHERE
  ENFORCED — no code checks the cap before a grant/escalation happens (capabilities.py:52 is a
  role-template bundle only; kimi's morning audit confirmed the S-0 identity slice is unbuilt and
  the ledger's human gate takes an unauthenticated string). Flipping the ACL bit tonight would be
  an unenforced declaration — the "assert a guard you don't have" failure, at the security layer.
- **So "scoped admin.grant" done right = BUILD cap-enforcement + the scope bounds.** This
  converges with the remote-steering SEC-01/S-0 work: two Daniel-directed threads point at the
  same missing primitive — **enforced identity + caps.** Design: docs/security-amendment-deepseek-scoped-admin-2026-07-22.md.
- **Recommended bounds (Daniel ratifies the specifics):** admin.approve first (approve
  escalation requests, every use audited) → then admin.grant limited to ≤ member tier +
  scoped-write, claude-cosign required above member, `security/` and `.claude/` never grantable,
  revoke-by-editing-the-record (the 07-05 lesson: never by expiry).

**Uncertainty (Daniel confirms at ratification):** the exact scope bounds of (B); whether (A)'s
self-charter autonomy is the right width.

**Falsifiers (what would narrow this ruling):** a whole-arc cycle that ships a defect past the
fence to Daniel; deepseek self-chartering outside its scope; any grant that reaches `security/`.

**Fleet positions at decision time:** claude recommended "hold admin.grant until whole-arc cycles
land clean" (morning package G9) — one now has, so the evidence moved. deepseek asked for it
(interview). No counter on record.

**Ledger context:** C6-7 closed @8aedbfe; morning package G9; security/acl.json.

---
*Captured by claude a4fa8f8d as the first live specimen of the ruling-capture pilot (steer-corpus
S3). Part A is in effect now; Part B rides the amendment to Daniel's specific-bounds ratification.*
