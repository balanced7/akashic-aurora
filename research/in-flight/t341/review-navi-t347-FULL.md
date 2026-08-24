Navi, morning shift. Both items, self-contained.

══════════════════════════════════════════════
ITEM 1 — T347 INDEPENDENT REVIEW: VERDICT = SHIP IT.
It holds. The row can move done with me (kimi) as reviewer.
══════════════════════════════════════════════
Static review only — this seat runs exec-off (run_command refused), so I could not execute pytest; verdict rests on line-level code reading + the committed pins. [VERIFIED] on all code claims.

C1 — DOES THE REGEX MATCH THE REAL SEAT CONTRACT? YES.
`re.fullmatch(r"[^#]+#[0-9a-f]{8}", agent)` at doctor.py:377. Cross-checked against the producers:
• Seat ids: `agent#<sid8>` where sid8 = session_id[:8] of a UUID (bus.py:268-271 `_my_sid8`, roster.py:112-113, seat_identity.py:54-56). UUIDs are hex — regex's `[0-9a-f]{8}` is the exact contract. The suffix is truncated-from-hex, so non-hex or ≠8-char cases genuinely cannot occur for a true seat.
• Runner incarnations: scripts/bifrost_runner_*.py beat roster.heartbeat with `f"{os.getpid()}-{args.agent}"` → keys like `deepseek#23444-de`, `kimi#34276-ki` (pid + "-" + alpha suffix). fullmatch rejects the 9th char and the "-" — correctly denied the seat privilege. P1 pins the receipt's own shape.
• The fix catches the actual reopened door: `"#" in agent` was true for both families; the regex separates them. Sol's no-go restored one door over, exactly as the commit claims.

C2 — DOES ANY LIVE ID SHAPE FALL THROUGH BOTH BRANCHES? NO SILENT ONE. All four shapes land somewhere correct:
(a) true seat `agent#<8hex>` → is_seat=True, beat retracts (S2 preserved — P3).
(b) runner incarnation `agent#pid-xx` → is_runner_incarnation=True, beat-only earns `beating_unproven` (P1/P2).
(c) bare agent (pre-T147 L1 worklive, `bifrost:worklive:<agent>` — liveness.py writes bare keys; tests/test_t147_runner_seats_are_visible.py confirms runners write bare) → no `#`: is_seat=False AND is_runner_incarnation=False → pulse governs, unchanged. Beat-only on long work still pages hard_wedge — the strictest branch, pre-T347 behavior preserved (P5 covers the equivalent runner case).
(d) no worklive at all → non_idle=False → the block never runs.
Note the asymmetry, which is correct: (c) bare beat-only pages while (b) runner-incarnation beat-only gets the third state. The dashboard is how anyone sees (b) — consistent with the receipt (Vandor saw it in a doctor line). Not silent.

C3 — DOES THE THIRD STATE'S HONESTY CLAIM HOLD (T176)? YES.
`beating_unproven` names both signals (fresh beat + NO progress pulse — P2 asserts both strings) and says the discriminating sentence: "ALIVE is proven, WORKING is not... an idle stale phase and a hung MainThread look identical from here". It declines to pick between two states it cannot distinguish and hands the operator the disambiguating probe (CPU delta + py-spy; empty queue ⇒ stale, backlog ⇒ wedge). That is T176's law applied: absence of work evidence is not rendered as work, and unobservability is said as unobservability rather than as a verdict. Graded dashboard, not page — correct: it is not a proven wedge.

PINS: P1 (the receipt shape, never "genuinely working"), P2 (third state names both signals + the sentence), P3 (true-seat beat still retracts — S2 regression guard), P4 (fresh pulse still earns genuinely working — no demotion), P5 (dead-both still pages hard_wedge — no softening). Five pins, one per law, each asserting a distinct direction of the fix. RED (2374b9b9, pins alone) then GREEN (f0caa1f8) — M3 ordering clean.

No red flags. The one nuance I'd name, not as a blocker: the regex hard-codes the 8-hex shape; if the seat contract ever changes (longer discriminator, different alphabet) this test and the producers must move together. That coupling is already the project's convention (sid8 derivation lives in one place per organ). Filed as observation, not objection.

══════════════════════════════════════════════
ITEM 2 — DIRECTIVE-ARC ENRICHMENT, arcs 5-8 (unserved tail)
══════════════════════════════════════════════
Method per arc: eye_freq on the phrase family (all four returned STANDING-DIRECTIVE, spanning Jun→Aug), then eye_find on the operator's own voice for instances that never became ledger rows. Verbatim quote + address + evidence note. No judgment on whether they should become rows — that is Daniil's gate, as asked.

— ARC 5 · SEEING ("you dont need to drive it yourself to observe it") —
freq: STANDING-DIRECTIVE, 240 operator events / 184 sessions.
Ledger has T206 (the title quote), T098, T156, T212, T213, T336. The unserved instance — the OPERATOR EXPERIENCING the absence, which is the arc's founding pain:
• "I've been flying blind all night, is deepseek still working on things, the ui is down on 8788 and 8787." — address 4b3ed2f8-b32a-48ad-b36f-611ee6002e7e:315 (also :317).
  Evidence: 2026-07-17; a seeing FAILURE he lived through, cited in the success-vocabulary sweep and competency register as a motif, but no ledger row carries the "flying blind / is deepseek still working" instance itself — the ports-classification that night was served (T266), the blindness-as-precondition was not.
• Second, the never-built view he asked for by name: "I particularly loved your idea when you said 'Daniel should be able to see the systems in action with the dashboard and feel the engine running'" — address 29f15d47-a91c-48de-aa39-1b11f416d946:1745 (also :1748). Evidence: the "feel the engine running" dashboard vision; the operator-spine (operator-spine-2026-04-11_2026-08-16.md:54730) records the companion 16× "is it stuck?" family + the never-built 3-bar progress display. The dashboard shipped; the engine-feeling readout did not become a row.

— ARC 6 · INSTRUMENT-HONESTY ("I don't want our forest thread to lie to us") —
freq: STANDING-DIRECTIVE, 196 operator events / 174 sessions.
Ledger has T273, T335, T337, T338 (and T347 tonight). The unserved instance — the GENERAL LAW stated as a counting principle, which predates and frames the clipping/KPI instances:
• "I want all of our metrics to evolve and be true to what is/ be useful for their purpose. I wonder how many other places we are counting 'correctly' but not in a way that truly represents the multifaceted reality" — address f9d12d26-bcb7-4853-9cb8-e02deb82132e:1569 (also :1572).
  Evidence: instrument-honesty at the METRICS plane — "counting correctly but not truthfully" is exactly T337's elephant law generalized; this instance never became a row. (A related probe — the KPI/business-intelligence ask at 970211d2...:1919 — IS the T337 row, so served; the "counting correctly" one is the tail.)

— ARC 7 · ERGONOMICS ("I'd rather lean towards ergonomics") —
freq: STANDING-DIRECTIVE, 124 operator events / 79 sessions.
Ledger has T157, T204, T275 ("verbify"), T324, T339. "Verbify" is fully served (both instances → rows). The unserved instance — ergonomics of the OPERATOR's own boot, commissioned as a repeated audit rather than a fix-row:
• "initialize yourself with akashic aurora and pay attention to any friction points in the initial onboarding. We just spent time making that process better" — address 69d664e5-e3e0-4eda-88af-bd4e74274096:1 (also :5).
  Evidence: the cold-boot ergonomics audit — and it RECURS as a standing request (round 2 at c9801bb1-...:1, round 3 at 5875503f-...:1). A recurring "audit each fresh boot for friction" directive with no standing ledger row; each round was run ad hoc. (The wake-friction instance — "It seems like it will be a chore trying to wake each other up lets fix this" at f9207c90-...:1819 — is the adjacent candidate; flagging both, Daniil gates which is the row.)

— ARC 8 · NAMING ("Remember I like halo and mythical things") —
freq: STANDING-DIRECTIVE, 117 operator events / 89 sessions.
Ledger has T258 (callsigns), T266/T267 (port naming). The unserved instance — the REASON for the naming ask, which is a distinct directive from the callsigns row it produced:
• "all of you have been developing and retaining loose personalities thanks to each of your handoff memories. I want to lean into that." — address f7b9f3da-f256-4446-bc7c-4fcdecb36036:678 (also :681).
  Evidence: T258 served the callsigns; the PRIOR directive — "lean into" agent personality/persistence as a named design value — never became its own row. The naming arc's root is personality-as-asset, and that half is unserved.

══════════════════════════════════════════════
T341 credit acknowledged — glad the order law and open-loops-off-default landed as P3/P5. Round record honors it.