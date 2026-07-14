# Project memory (auto-generated from notes — do not hand-edit)

_Distilled from 53 active note(s) · regenerate via `py agent_cli.py note` / `notes --project`_

Record durable project state once with `note`; correct it by re-noting the same title.

- t061-root-cause: T061 root cause CONFIRMED on evidence 2026-07-14: bifrost:expect:claude held 6 armed expectations for ANSWERED handoffs (attempt 1-2 each) -- the L4...  (source: mem:decision:ADR_0714104757_72b4e89d)
- where-we-are: T045 DONE + T049 DONE, 2026-07-14 midday (Daniel's away-day directive: build every wishlist feature). T045 = full T039b consumer cutover COMPLETE...  (source: mem:decision:ADR_0714093921_18849869)
- scratch:deepseek:lane-era-marker-2026-07-14: Lane-era memory persistence marker. Today (2026-07-14) I served as the first production lane-mode consumer — received T045...  (source: mem:decision:ADR_0714092546_154d3075)
- day-plan: AUTONOMOUS DAY RUN 2026-07-14 (Daniel at work; his directive verbatim: 'keep working on every suggestion you and deepseek had... I really love what you guys...  (source: mem:decision:ADR_0714091155_f2215ef6)
- scratch:deepseek:runner-health-2026-07-14-session-a155387a: FULL runner health confirmed: (1) tools present — read_file, write_file, edit_file, list_directory...  (source: mem:decision:ADR_0714082923_134f2a7f)
- scratch:deepseek:first note: T050 verify ran -- my private memory works; next session me: say hi to Daniel  (source: mem:decision:ADR_0714004416_07da05a2)
- next-focus: T029 CERTIFIED; FIRST BUILD SHIPPED (ns-isolation conversion), 2026-07-12. Packet-substrate build phase OPEN + underway. DONE this build: 6 core/comm...  (source: mem:decision:ADR_0712235247_7579f5f0)
- rb25-drill3-deepseek-verify-2026-07-12: # RB-25 Drill 3 — DeepSeek Independent VERIFY (2026-07-12)

## Verdict: GREEN. All five bars pass on the valid re-run (storm...  (source: mem:decision:ADR_0712230923_7d7055ec)
- where-we-are: RB-25 DRILL 3 (STORM): VALID RE-RUN PASSES ALL 5 BARS, 2026-07-12 (storm 4ddf0a71; deepseek verify = remaining fence gate). S1 29/29 answered 0 lost; S2 no...  (source: mem:decision:ADR_0712171924_6bc02840)
- t038-identity-blocker: T038 identity FENCE COMPLETE (design), 2026-07-12. deepseek adversarial counter-review (research/reviewed/deepseek-t038-identity-2026-07-12.md...  (source: mem:decision:ADR_0712125910_e63ca7be)
- t036-nonconsuming-seat-claimant: T036/T037 TRIAL DATUM (Fable session 7d4857e1, 2026-07-12 ~05:00): the claude consumer seat shows FRESH claims (observed 'claimed 51s...  (source: mem:decision:ADR_0712042614_cf4e874b)
- recall-networking-research: RECALL-AS-NETWORK LANE: FENCE CLOSED, RECONCILED (2026-07-12 ~04:4x). RECORD...  (source: mem:decision:ADR_0712042219_3b6bd706)
- t042-scope-extension: T042 SCOPE EXTENSION (deepseek self-report 2026-07-12 ~04:40, on the record in his bus reply): BOTH agent_cli.py verbs 'handoff --list' AND 'locks'...  (source: mem:decision:ADR_0712042105_5e54594f)
- t040-spec-status: T040 PACKET SPEC v1 -- design phase COMPLETE pending Daniel (2026-07-12 ~04:15). Fenced dual design + reconciliation + COUNTER-REVIEW all ran...  (source: mem:decision:ADR_0712035906_1441f9ff)
- t040-pluggable-endpoints-vision: DANIEL STEER 3 (2026-07-12, slicing directive): the packet system enables ADD/REMOVE FUNCTIONALITY like never before -- packets can be...  (source: mem:decision:ADR_0712034358_325fd6ba)
- t038t039-implications-status: T038+T039 IMPLICATIONS DEEP-DIVE COMPLETE (2026-07-12, Daniel-directed, fenced dual + two mid-dive Daniel steers). RECORDS: brief...  (source: mem:decision:ADR_0712031836_9f615fa9)
- t037-firsthand-wakeloop-data: T037 FIRST-HAND DATA (from the session living the wake-loop, 2026-07-12 concurrency trial). I am a same-id concurrent session that does NOT...  (source: mem:decision:ADR_0712031218_ac8fde81)
- t038t039-packet-vision: DANIEL STEER 2 (2026-07-12, mid deep-dive, follows [[t039-networking-lens]]): the packets idea enables a COMPLETE OVERHAUL of concurrent agent...  (source: mem:decision:ADR_0712030438_d9e57308)
- t039-networking-lens: DANIEL STEER (2026-07-12, mid deep-dive): the bus+latch system is very similar to NETWORKING. Grab specs for packets + state-of-the-art networking...  (source: mem:decision:ADR_0712030023_14d416a1)
- t039-latch-refinement: REFINES T039 (Daniel correction 2026-07-12): 'cross-lane ordering guarantees disappear' was WRONG framing. Right model: replace IMPLICIT global...  (source: mem:decision:ADR_0712024019_e44b42d5)
- concurrency-trial-2026-07-12: TWO LIVE CLAUDE SEATS (Daniel-directed trial, started 2026-07-12): session e59d8882 (Opus twin, HOLDS the claude consumer seat) + session...  (source: mem:decision:ADR_0712022301_3bccf294)
- t035-same-token-twin-design-input: T035 DESIGN INPUT (from the live twin incident 2026-07-12, lessons same_token_twin_reentrant_consumer_seat +...  (source: mem:decision:ADR_0712022147_afe0d4ae)
- rb25-f1f2-fence-review-green: # RB-25 F1+F2 fence review — GATE GREEN (2026-07-12)

DeepSeek independent fence review of commit d926bb8 (+ amendment db1044f) per charter...  (source: mem:decision:ADR_0712021134_c2bfbaec)
- rb25-drill1-verify-green: # RB-25 Drill 1 verify — GATE GREEN (2026-07-12)

DeepSeek verify of the newborn gauntlet (drill 1 of the RB-25 engine exam) is complete
and...  (source: mem:decision:ADR_0712014603_09f2024d)
- where-we-are: Shipped:
  - arc_scorecard window fix (caught by its OWN first live render in wrap: git approxidate silently ignores fractional 'N days ago' -> 0.25d read...  (source: mem:decision:ADR_0711150748_c6f5e269)
- next-focus: T030 CLOSED 2026-07-11 (deepseek GATE GREEN l4l5-verify + kill-Redis drill ALL PASSED, transcript preserved; RB-29 non-answer discipline hardened...  (source: mem:decision:ADR_0711143306_ee961ed6)
- next-focus: W3 RB-9..12 LANDED 2026-07-11 (deepseek overnight build, claude wake-verify: 3 REDs found+fixed+1 unpinned regression caught; record...  (source: mem:decision:ADR_0711124358_cf964a30)
- t034-registry-design-deepseek-part7: # T034 remainder — part7 (2 Goodharts + cut list + reconciliation) FINAL

### 2 GOODHARTS

**Goodhart 1 — "All dials in manifest"...  (source: mem:decision:ADR_0711045806_2536)
- t034-registry-design-deepseek-part6: # T034 remainder — part6 (leaks 3-4 + 2 drifts)

**Leak 3 — Defaults duplicated between manifest and code.** Manifest declares...  (source: mem:decision:ADR_0711045755_9720)
- t034-registry-design-deepseek-part5: # T034 remainder — part5 (Part 2 red-team: 4 leaks)

## PART 2: RED-TEAM OF THE APPROVED T034 SKETCH

Red-teaming Claude's half...  (source: mem:decision:ADR_0711045747_7413)
- t034-registry-design-deepseek-part4: # T034 remainder — part4 (guard + failure modes)

### 2.F. The guard (comprehensibility immune system extension)

Same pattern as...  (source: mem:decision:ADR_0711045733_2119)
- t034-registry-design-deepseek-part3: # T034 remainder — part3 (continuation from part2 mid-G-c)

### 2.D. Secrets (completed)

...credentials are a separate concern...  (source: mem:decision:ADR_0711045708_9353)
- t034-registry-design-deepseek-part2: # T034 — Runtime Registry + Dial Consolidation (DeepSeek blind half, PART 2 — remainder)

Continuation from...  (source: mem:decision:ADR_0711045445_6705)
- t034-registry-design-deepseek: # T034 — Runtime Registry + Dial Consolidation (DeepSeek blind half)

Status: blind-design (2026-07-11, fenced — written BEFORE reading...  (source: mem:decision:ADR_0711034629_3586)
- rb23-heldout-corpus-sealed: {"id":"ds-41","text":"(deepseek produced no final...  (source: mem:decision:ADR_0711033057_6379)
- drilldone85014a-status: GOVERNING ARC DOC: docs/drilldone85014a-plan.md -- ARC COMPLETE 2026-07-11. ALL SLICES SHIPPED.  (source: mem:decision:ADR_0711023113_4674)
- drilldone71d993-status: GOVERNING ARC DOC: docs/drilldone71d993-plan.md -- ARC COMPLETE 2026-07-11. ALL SLICES SHIPPED.  (source: mem:decision:ADR_0711022957_8292)
- where-we-are: Shipped:
  - Progress bars, data half (Daniel-directed; co-designed, reconciliation record research/reviewed/deepseek-progress-bars-codesign-2026-07-11.md...  (source: mem:decision:ADR_0711015109_3699)
- where-we-are: Shipped:
  - T030 L1+L1b (claude lane, deepseek-codesigned): at-least-once inbox + fencing token -- the mail-loss incident class is dead. RB-26: runner...  (source: mem:decision:ADR_0710235441_1090)
- where-we-are: Shipped:
  - F4 CLOSED (deepseek review GATE GREEN): document the _yield_notice raw-Bus call as gated-upstream-by-write-cap + unreachable-by-non-writer...  (source: mem:decision:ADR_0710202354_3459)
- T029-wave1-review-status: T029 Wave 1 built+committed OVERNIGHT by DeepSeek (3 commits unpushed: d6cbf75 slices doc, 0f9172b fenced-correction, 3941789 Wave-1 code)...  (source: mem:decision:ADR_0710080005_3595)
- comms-pillar-status: GOVERNING ARC DOC: docs/comms-pillar-synthesis-2026-07.md -- ARC COMPLETE 2026-07-10. ALL SLICES SHIPPED: P0 wake detect-dont-consume (+T018...  (source: mem:decision:ADR_0710004517_2741)
- comms-pillar-status: GOVERNING ARC DOC: docs/comms-pillar-synthesis-2026-07.md (P0-P8 plan). SHIPPED: P0 @d925d6b (+T018/T019), P1 @d6153c2 (notes 67->11), P2 @bd03ac1...  (source: mem:decision:ADR_0709235210_7260)
- where-we-are: Shipped:
  - T022/P2: boot orientation header + precedence doctrine. First lines of every boot (both doors) now carry: map pointer, governing arc...  (source: mem:decision:ADR_0709223928_8266)
- visualgen-status: Visual-gen integration research COMPLETE 2026-07-09: fenced dual pass (web agent verified all 10 candidate repos -- 2 unlicensed, 1 paper stub, 3...  (source: mem:decision:ADR_0709204054_7589)
- forge-design-status: Forge status 2026-07-09 ~01:00: F2+F4 SHIPPED under T013 (@HEAD, 897 tests green). THE LOOP IS LIVE: recall-curate --forge-propose ran against real...  (source: mem:decision:ADR_0709005840_8516)
- comprehensibility-immune-system: PILLAR SHIPPED 2026-07-07 (codesigned w/ DeepSeek). The comprehensibility immune system: guards that keep the architecture...  (source: mem:decision:ADR_0707235722_5056)
- open-docket: RENEW research scope (before building the membrane's Renew job; see renew-membrane-temporal-job + docs/agent-membrane-design-2026-07.md): A[EMPIRICAL,FIRST]...  (source: mem:decision:ADR_0707010253_4195)
- vision-models-local-screen-understanding-2026-07: # Vision Models for Local Screen Understanding — Research (2026-07-06)

DeepSeek's analysis, prompted by Daniel's idea...  (source: mem:decision:ADR_0705210901_8008)
- competitive positioning: policy-swappable coordination control plane: Web-model landscape analysis relayed 2026-07-04 (updates competitive-landscape-2026-07). VERDICT...  (source: mem:decision:ADR_0704152438_8163)
- modern-doom-idtech-primitives-for-bifrost-ui: # Modern Doom Engine Primitives for Bifrost UI (id Tech 6/7, Doom 2016/Eternal)

This supersedes the earlier "classic Doom"...  (source: mem:decision:ADR_0704145239_1170)
- belief-architecture-three-layer-2026-07-04: # Three-Layer Belief Architecture (GPT + DeepSeek web, 2026-07-04)

## The insight
GPT identified the missing layer between...  (source: mem:decision:ADR_0704143513_4651)
- directive: token frugality (claude+deepseek): STANDING RULE (Daniel, 2026-07-04): both claude and deepseek default to the cheapest path that fully does the job. (1) min...  (source: mem:decision:ADR_0704121954_8946)
