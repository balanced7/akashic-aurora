py :   read the answer
At line:1 char:328
+ ... :\AI-Setup; py agent_cli.py ask --get 3415d07c *> research\in-flight\ ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : NotSpecified: (  read the answer:String) [], RemoteException
    + FullyQualifiedErrorId : NativeCommandError
 
# ask 3415d07c -- DONE
C1: The two-record join does **not** close the self-grading hole — it merely moves the point of forgery from authoring both records to self-declaring a different `by` for the adjudication. The door has no identity-verification layer, so any resident can assert `by` = any name, including a sock-puppet. The opening position’s own kill condition concedes this.
EVIDENCE: resident-fanout-round2-2026-08-12.md §6 line 154–155 (laundering path acknowledged); residents.py lines 450–453 (`assign`’s `by` field is declared by the caller with no cryptographic binding — provenance is derived from `by`, not verified against a trusted identity source).
CONFIDENCE: high.
AMEND: Adjudication records must either (a) be signed by a known operator (Daniil/conductor) with a verified identity token, or (b) until such a token exists, RC1 ships with adjudication-by-operator-only (kill condition II), explicitly refusing any resident-authored adjudication. The spec already contains this kill condition; make it the default, not the fallback.

C2: At the fleet’s current scale, a per-resident × per-question-shape cell will contain vanishingly few adjudications (<5), rendering any survival-rate point estimate dangerously misleading. Wilson intervals would be so wide as to be uninformative. Pooling across residents first is vital to accumulate signal.
EVIDENCE: resident-fanout-round2-2026-08-12.md §2 (projected ~20 adjudicated verdicts needed per cell), §5 Q2 (asks about statistical honesty), §6 line 157–158 (kill condition concedes per-shape pooling if per-resident n too low); the fan doctrine’s rubric rows (descriptive-read, normative, generative, coverage-claim) are referenced but the truncated file prevents direct citation — the shapes are re-stated in RC2 of the opening doc line 83–84.
CONFIDENCE: high.
AMEND: RC2 should render **per-shape** calibration (across residents) as the primary presentation, with a Wilson 95% confidence interval. Per-resident × per-shape breakdowns appear only when cell-wise verification count ≥ 20, and must always show the interval, not a single number. This also answers the “one number” guard more strongly.

C3: The scout-as-role design is consistent with the identity/role split, because the **role’s** persistent verdicts (filed under role key in RC2) and its charter pack provide the accumulated knowledge — not the wearer’s personal memory. There is no need for a dedicated identity, provided the role-scoped catchup pack is truly independent of the wearer and correctly retrieves role-level data.
EVIDENCE: residents.py line 39 (“Identity ≠ job, by design”); resident-fanout-round2-2026-08-12.md §3 RC3 (verdicts file under both resident and role, and role charter pack is assembled by a helper, so accumulation is in the role’s data store).
CONFIDENCE: med (depends on the implementation of role-scoped retrieval; if the pack only includes the current resident’s personal lessons, the role’s continuity breaks).
AMEND: none — but verify in RC3’s acceptance tests that a scout wearing the role for the SECOND time still sees the verdicts filed by a previous wearer, i.e. the pack is role-scoped, not wearer-scoped.

C4: The ugliest exploit: a resident **selectively opts in** only to easy descriptive questions it is confident will be confirmed, maintaining a 100% survival rate while contributing zero value on hard normative/generative tasks. The per-shape split reveals a hole only if the resident is *offered* tasks of that shape; if it can refuse or self-select, the hole disappears.
EVIDENCE: resident-fanout-round2-2026-08-12.md §3 RC2 lines 92–94 (“a resident optimizing for safe descriptive questions is WORSE… per-shape split is the guard”); the guard relies on the availability of a task assignment log, which does not yet exist.
CONFIDENCE: high.
AMEND: RC2 must incorporate a **selectivity metric** — `verdicts_filed / tasks_assigned` per question-shape, derived from a mandatory fan-task assignment log. A resident that never receives normative asks or that consistently declines them will show a zero or missing selectivity denominator, making the hole visible without depending on the resident’s own choices. Add this metric to the calibration projection and the boot block.

C5 (premise attack): **Calibration is the wrong next slice.** Daniil’s explicit instruction prioritises “managing context and setting up helper functions and roles” for long-horizon tasks. RC1/RC2 measure resident reliability but depend on a steady verdict stream that we do not yet have (kill condition I: <10/week starves the ledger). Building the scout (RC3) and a conductor-assist helper first would *generate* the verdicts as a side-effect, while directly addressing the context-management priority. The marginal routing gain from calibration is tiny compared to the gain of a reliable multi-step execution scaffold.
EVIDENCE: resident-fanout-round2-2026-08-12.md trigger lines 3–6 (Daniil on context management and helper functions); same document §6 line 151–153 (kill condition I: verdict volume <10/week starves calibration).
CONFIDENCE: high.
AMEND: Reorder the build sequence: **RC3 (scout) first, then a task-decomposition/checkpoint role**, leaving RC1/RC2 to be bootstrapped from the verdicts those roles naturally create. Calibration is not abandoned — it becomes a projection-once-there-are-verdicts, not a forced-feed. This avoids paying measurement cost before the fan pipeline is mature.

BLIND: The evidence pack cannot show whether a resident *already* has a route to self-grade via the existing lesson/recall mechanism (e.g., a resident could publish a “confirmation” as a lesson and later cite it as adjudication). The adjudication-verification design as described never mentions the learning store as a back door. Additionally, the pack does not give a live count of how many fan asks actually exist per shape or how many are offered to each resident — needed to assess selectivity/Gaming in practice.
