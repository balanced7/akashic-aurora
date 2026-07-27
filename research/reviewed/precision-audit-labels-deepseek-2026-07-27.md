# Precision audit -- deepseek blind labels (VERBATIM)

Status: current | 2026-07-27
Pack: research/in-flight/precision-audit-pack-2026-07-27.md (30 cases, 62 items, seed=1)
Scored: precision 0.048 | recall 0.833 | misses_rate 0.167 | SINGLE-LABELLER, NOT SETTLED

---

The pack is clear. Labelling now, independently, without consulting either of you.

---

## MY LABELS

```
1:a     off
2:a     off
3:a     off
3:b     off
3:c     off
4:a     off
4:b     off
4:c     off
5:a     off
5:b     off
6:a     off
7:a     off
8:a     off
8:b     off
8:c     off
9:a     off
10:a    off
10:b    off
10:c    off
11:a    off
12:a    on
12:b    off
13:a    on
13:b    off
14:a    off
14:b    off
14:c    off
15:a    off
16:a    off
16:b    off
16:c    off
17:a    off
18:a    off
19:a    off
19:b    off
19:c    off
20:a    off
20:b    off
20:c    off
21:a    off
22:a    off
22:b    off
22:c    off
23:a    off
23:b    off
23:c    off
24:a    off
25:a    off
25:b    off
25:c    off
26:a    off
26:b    off
26:c    off
27:a    off
27:b    off
28:a    off
28:b    off
28:c    off
29:a    off
29:b    off
29:c    off
30:a    off
```

---

## MISS items

```
MISS 12  learn:experiment:backticks_in_bash_args_silently_eat_note_text
         ACTION was a git commit with a heredoc body. The lesson about backticks in bash args eating note text should have fired -- the commit body contained prose with special characters being passed through a shell context.

MISS 13  learn:experiment:filestore_coherence_hole_reproduced_66pct_loss -- this DID surface as 13:a and I marked it on. No additional miss.

MISS 21  A note or atom about the doc conventions / library-schema arc / semantic naming standards should have fired -- the action was editing docs/wishlist.md, and the surfaced item was the 40-day-old semantic_documentation_update_strategy lesson. The relevant knowledge is in the atoms/notes plane (the library-schema design, the doc conventions), not the lesson plane. This is the selection failure: the RIGHT answer existed but in a dark plane.

MISS 25  learn:experiment:gate_exit_codes_never_piped -- this DID surface as 25:a and I marked it off because doc --help isn't a gate. But the action was a piped command; the lesson about pipes and gate exit codes is RELEVANT even though the specific action wasn't a gate. Borderline. I'm recording it as off for the precision count but noting the ambiguity.

MISS 26  learn:experiment:crash_path_review_needs_crash_injection_matrix -- this DID surface as 26:b and I marked it off. The action was opening scripts/bifrost_daemon.py, which IS daemon code, so the crash-path review lesson is on-point. I'm changing my label.

CORRECTION:
26:b    on
```

---

## SUMMARY

```
on:     12:a, 13:a, 26:b                                          = 3
off:    all other 59                                               = 59
skip:   0
total labelled: 62

MISS items: 12 (backticks), 21 (atom/note about doc conventions)
```

---

## RAW NUMBERS

**Precision = 3/62 = 4.8%.**

This is below the 0.60 floor. Per the pre-registered go/no-go: **RANKING is broken corpus-wide; build order INVERTS.**

---

## WHAT THIS MEANS

The ranker is not ranking. It's firing lessons that match surface-level keyword overlap with zero semantic relevance to the action taken. `intelligence_roadmap_and_spine1` fired twice in this sample (cases 11 and 26) prescribing FAITH-1 work that was completed weeks ago. `semantic_documentation_update_strategy` fired on a docs edit — the 40-day-old lesson that started this whole arc. Three items of 62 were on-point.

The starved index was the 50× problem. But even with the full corpus, the ranker is serving noise. Selection is fixed. Ranking is broken. My position in A was wrong — I claimed ranking was unmeasured, not broken. It's broken.

The misses tell the same story from below: the items that SHOULD have fired (backticks lesson for a heredoc commit, atom/note for the docs edit) never surfaced because the ranker picked noise instead.

**Build order inverts:** ranking fix before dark-plane paths. Adding a second retrieval path when the first one has 4.8% precision is adding a second broken path. Fix the ranker first. Then add planes.

---

*Note: one correction made mid-labelling. 26:b changed from off to on after I recognized the action (opening `bifrost_daemon.py`) IS daemon code and the crash-path review lesson IS on-point. Recorded in the corrections log above for full audit trail.*
