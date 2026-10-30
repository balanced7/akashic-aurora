# Lesson portability across Akashic Aurora instances: the census and the design (2026-10-29)

Workflow run wf_c10b9f4d-cd8 (task w054a09r7). Daniel, verbatim: "Order is up to you, lets take a methodical approach to the recall lessons and use this as an exercise in improving the functionality and ease of setup and transfer of our recall system and lessons. so that lessons can be safely classified and exported / imported across akashic aurora instances". Grounded in Heimdall's repository split plan (docs/library/design/20261029_repository-split-plan.md). Stage 1 of a methodical order: a read-only census in four lanes, then one design; next comes a fenced review with Heimdall, then a dry run in the sandbox, then the build. Nothing in the canonical store was written. Verbatim; local paths shortened.

**The sensitivity lane is NOT in this public record.** It names which lessons are personal or relational, so it is kept private at state/research-private/lesson-portability-sensitivity-2026-10-29.md (git-ignored). Its counts appear in the design below.

Vandor's read: the census found the store's own integrity needs fixing before portability: Redis is the only complete copy of the lessons (the SQLite mirror lacks content for 258 of 1,658), the mirror checker passes falsely (it compares modification times), 28 lessons from the July split-brain are empty shells whose content was found nowhere, seats that do not inherit AKASHIC_STORE_BACKEND write to the lossy JSON file store, and lesson ids carry no instance namespace. As a first protective step, Vandor made a read-only backup of every lesson hash and memory decision to a private file (state/backups/lessons-readonly-20261029-215448.jsonl: 1,686 lesson records, 1,977 memory decisions, 9,702,784 bytes, sha256 abd5f0dcd96cd9fba27c6fcc74c01cd56c36f29f043b56036fa2403688bf1855).

---

## The design (verbatim)

# Lesson portability across Akashic Aurora instances: design draft

Status: draft design for review, 2026-10-29. Nothing has been ratified. This stage was read-only: nothing was written to the store, the sandbox or the repo.

**Inputs**
- Four census lanes (store-schema, citations, sensitivity, prior-art), run today against Redis db 0 on :16379 and master at 4ca16c8c8.
- My own bounded re-reads of:
  - the split plan and AGENTS.md;
  - `core/world_seed.py` lines 1-190 and 222-263;
  - the clearance spec, lines 16-125 and 198-267;
  - `core/trust/private_plane.py` lines 1-60;
  - `core/learning/learning_store.py` lines 305-345 and its field mapping at 740-741;
  - `core/coord/target.py` (matching lines) and `core/library/legacy_map.py:49`;
  - `core/context/relevance_budget.py:43`;
  - the capability names in `security/acl.json`;
  - `pipeline-summary.json` from the September sanitizer;
  - the git status of `research/in-flight/seed-sanitize-2026-09-01/`.
- League of Legends.exe was running the whole time, so all my own checks were bounded reads.

**Grading**
- [S] means a cited source (file:line or URL).
- [S:local] means measured on this machine today, by a census lane or by me.
- [I] means inference.
- Where the lanes disagree, I say so rather than pick one.

---

## The design in plain language

1. **The lessons are in shape to share, but the shelves are mislabelled.**
   - "1,930 lessons" is really 1,658 lessons plus their indexes.
   - 77 records are not lessons at all.
   - The backup copy is missing content for about one lesson in six.
2. **Every lesson gets a label card, kept beside it and never written into it.** The card says:
   - which part of the house the lesson talks about;
   - how sensitive it is;
   - where it is true;
   - which files it points at;
   - which seat wrote it;
   - whether it is still current.
3. **A program fills in most cards.** It cannot decide about 10% of them. Those go to a queue:
   - Daniel decides anything personal or about other people.
   - A seat decides house facts and facts about itself.
   - Anything nobody has decided stays home.
4. **Lessons keep pointing at files exactly as they do now** (for example "core/comm/bus.py").
   - A small lookup table tells recall which of the four future repos holds a path.
   - When a file has moved or died, recall says so instead of pretending it is still there.
5. **Lessons travel as a "lesson pack".** This is a folder with one line per lesson, a fingerprint for each, a list of what was left out (counts only, for anything sensitive), and optionally a signature.
6. **Importing a pack never overwrites anything and never trusts the sender's labels.**
   - The same safety gates run again on arrival.
   - Lessons wait in quarantine until a local seat or Daniel accepts them.
   - Vote counts start at zero, because trust is earned in each house.
7. **A new instance gets the public starter pack with one command.** Before any of this touches the real store, it is proven on a sandbox copy against pass/fail bars written down in section 6, before the run.

---

## 1. What the census found that shapes everything

| # | Finding | Design consequence |
|---|---|---|
| 1.1 | The headline counts count keys, not records. "1,930 learnings" is every `learn:*` key [S agent_cli.py:8585; S:local]. There are 1,686 lesson hashes, of which 1,658 have content and 28 are empty husks [S:local]. "1,214 agent memory" is the number of `mem:*` keys. The real figure is 1,977 decisions in `mem:decisions`, 690 of them superseded [S:local]. | Every gate and every pack manifest counts records, by class. Fixing `status` is slice S0. |
| 1.2 | Redis is the only complete copy. The SQLite mirror is missing content for 258 of the 1,658 lessons: 28 are absent and 230 are husks holding only narrative fields [S:local, store-schema lane]. It is also missing 125 decisions [S:local]. `check_dual_authority` reports PASS because it compares only file modification times [S check_dual_authority.py:60-95]. The lanes disagree on one detail. Store-schema and sensitivity say the 28 lessons absent from SQLite are real lessons. Prior-art read the 1,658 SQLite keys as excluding the 28 Redis ghosts. On memory, prior-art counted 64 missing head-pointer keys, which is a different unit from 125 records [S:local]. | The exporter reads Redis through a read-only client. Step 0 of the dry run settles the disagreement. |
| 1.3 | A fresh install starts on the JSON file store unless `AKASHIC_STORE_BACKEND=sqlite` is set. That variable is set only at user level on this machine and is not mentioned in DEPLOY.md or AGENTS.md [S store.py:1198-1232; S:local]. The JSON store was measured losing 65.6% of concurrent writes [S, per the store-schema lane]. [I] The likely cause of the mirror gap is seat processes that do not inherit the variable (store-schema lane). | Setup must pin the backend in a config file, not an environment variable (section 5). |
| 1.4 | There are 77 non-lessons in the canonical store: 28 husks and 49 test leftovers [S:local]. A fixture named `newest`, dated 2026-12-01, sits at the head of `learn:experiments:all` [S:local]. | Classification has a "not a lesson" class. Tests need a guard against db 0. |
| 1.5 | Metadata is thin. `category` has 91 values and 51% say `uncategorized`. 41% of lessons have no `domain`. There are 59 distinct `agent_id`s, with codex alone under 6 or more. `confidence` uses a mixed vocabulary. All timestamps are naive. No lesson has a supersession field [S:local]. | Classification cannot lean on existing fields. Author seat needs an alias map. The pack normalizes confidence and time in its envelope and keeps the raw values. |
| 1.6 | Citations are mostly prose. Between 473 and 548 lessons cite a repo path, depending on the extractor (the three lanes got 473, 505 and 548) [S:local]. `files_affected` is filled on 56 lessons [S:local]. About 95% of path citations are in prose [I, citations lane]. | The resolver must parse prose, using one shared extractor with measured precision (39 of 40 in a sample) [S:local]. |
| 1.7 | Rot already exceeds anything the split will cause. 22.1% of all path citations (lessons and memory, 1,108 of 5,010) point at paths missing on master. For lessons alone it is 90 of 482 distinct paths (18.7%) [S:local]. One commit, 425cf527a, explains a third of it. The committed legacy map resolves 187 of those citations. The other 119 paths all resolve by the module's own body-suffix rule once its `docs/` filter is widened [S:local; S legacy_map.py:49]. | No stored text needs rewriting. Widening an existing map recovers the biggest block. |
| 1.8 | The split plan overstates arsenal and understates research. Arsenal is 1.6% of path citations (81), not "constantly" as the plan says [S:local vs S plan:44-45]. 48 lessons and 251 citations point into `research/`, against the plan's claim that "nothing cross-cites it" [S:local vs S plan:73-74]. The plan also contradicts itself on `research/`: its table splits reviewed from in-flight, but execution step 1 moves all of it [S plan:30-32 vs :73]. | The lane table must decide the research sub-folders explicitly (decision D7). |
| 1.9 | No credential was found in any lesson or note, across three rule sets plus an entropy check [S:local, sensitivity and prior-art lanes]. Two shape matches need a human look: lesson `public_push_scope_is_the_whole_unpushed_backlog` and decision `ADR_0824212136_c1e54879`. The sensitivity lane judged both to be placeholders; the store-schema lane called them inconclusive [S:local]. The rule lists have forked: the push gate has 9, the relay has 3, and the sanitizer has a fourth list [S check_secrets.py:48-60; discord_bridge.py:131-136; S:local]. The `learn` door has no secret scan [S:local]. | One shared egress-rule module (section 2.5). |
| 1.10 | Private content is real and keyword rules alone cannot find it. 26 lessons were flagged; reading them confirmed 20 (77% precision). An estimated 13-25 more were missed [S:local; I]. The private-plane markers caught 1 lesson and 5 notes that every other rule missed [S:local; S private_plane.py:105-110]. Medical and family words are mostly metaphors here: "doctor" in 259 records is the house's doctor command [S:local]. | Rules set a floor and a human sets the ceiling. Unreviewed private-candidates stay home. |
| 1.11 | Memory notes are a different kind of record. 607 are `scratch:<seat>` notes. 52% are seat-private or instance state by title alone. 1,169 of the 1,977 name the operator [S:local]. | Notes are excluded from v1 packs (decision D2). |
| 1.12 | The sensitivity lane's draft rubric sorts lessons as: 77 not a lesson, 0 secret, 26+ private, 105 seat, 87 machine, 811 house, 580 universal. About 10% need judgement; 2.3-3.0% need Daniel specifically [S:local; I]. | The review queue is small enough to finish. |
| 1.13 | No transfer path is portable today. A snapshot restore wipes the target first. `world_seed` copies with DUMP/RESTORE, downward only, on the same machine, filtering by key prefix only [S world_seed.py:46-73, 109-150]. DUMP output is Redis-version-specific [S https://redis.io/docs/latest/commands/dump/]. The legacy JSONL importer reads `actual_outcome`, but exports carry `actual`, so a re-import blanks `actual` [S learning_store.py:313-345, 740-741]. The clearance predicate is documented as "enforced at seed time", but the seed code has no such check [S bootstrap_world.py:38-41; S:local grep]. | Reuse world_seed's laws, content hash and manifest. Replace DUMP with JSONL. |
| 1.14 | There is prior art to reuse. The 2026-09-01 sanitizer exported 1,294 records, produced 1,228 seed records with 0 residual identity records, and kept top-10 recall overlap at 59/60 (57/60 at the same rank) [S pipeline-summary.json]. | Its six probe queries become part of the pre-registered acceptance set. |
| 1.15 | Ids are stable joins but carry no namespace. `experiment_name` is a free-text slug, and a seeded lesson is "byte-identical to a native one: same schema, same id" [S world_seed.py:157-163]. Prose references to ids almost never dangle: 3 of 509 lesson references and 0 of 386 decision references [S:local]. | Keep names exactly as they are and add the origin instance as provenance. |
| 1.16 | Daniel's prior rulings bind this design. Q1: a graduated lesson ships with its enforcement, or neither ships. Q2: no permanent provenance stamp on lessons; a manifest join instead, so "the lesson stays clean". Recall counters never seed, and earned counters start at zero [S clearance spec:70-119]. The inventory is id + sha256 + generation, kept in the manifest [S spec:198-257]. | Labels go in a sidecar card, not on the lesson (section 2.2). Imported votes do not rank. |
| 1.17 | The security schema has `kb.recall` and `kb.learn`, and no `kb.export` or `kb.import` [S:local acl.json]. Unlisted agents are quarantined to read-only [S AGENTS.md lines 7-9]. Only 2 of 14 grants have `expires_at` [S:local, prior-art lane]. | Add a new time-boxed `kb.import` capability. |

---

## 2. Classification

**Plain version.** Each lesson gets a label card that answers six questions. A program answers most of them and a person answers the rest. The card sits next to the lesson, so the lesson's text is never changed. The card decides how far a lesson may travel.

### 2.1 The six axes

| Axis | Values | How it is set |
|---|---|---|
| **lane** | A set drawn from: substrate, knowledge, creative, research, runtime, home (untracked `security/`, `.secrets/`, `private/`), unassigned. `none` if the lesson cites nothing. | Derived from its citations through the lane table (section 3.2). Recomputed when the table version changes. |
| **sensitivity** (harm if it leaks) | Five levels, most severe first:<br>- `secret`: a credential value.<br>- `private`: personal, relational, health, family or emotionally situated content about the operator; anything about a third-party human; platform ids or contacts; references into the private plane; sensitive-subject research.<br>- `pointer`: says where credentials live. 17 lessons [S:local].<br>- `attributed`: names the operator or a seat only as the one who asked, decided or learned something. 253 lessons [S:local].<br>- `clear`. | Rules R1, R2 and the attribution label (section 2.3). |
| **portability** (where it is true) | `not_a_lesson`, `seat:<callsign>`, `instance` (bound to this machine), `house` (true for any Aurora install at a compatible substrate version), `universal`. | Rules R0 and R3-R6. |
| **citation dependency** | `none`, `resolves`, `partial`, `dead`, `local_only`, with per-status counts and the lane set. | Computed by the resolver against a named lane-table version and substrate commit. |
| **author seat** | Canonical callsign: vandor, heimdall, rill, navi, sunshine, asta, neo, operator, test, unknown. | From an alias map over the 59 raw `agent_id`s [S:local]. The raw `agent_id` is never changed, because it is part of the content hash (section 4.3). |
| **freshness** | Age bucket; lifecycle (active / benched / graduated + `enforced_by`); credited-ever (read from local vote counters, never exported as rank); citation rot; `supersedes` / `superseded_by` edges (new, sidecar only); `stale_verdict` when the content hash has changed since a human decided. | Computed, except the supersession edges, which a seat writes. |

**Derived: the distribution ceiling.** This is how far a lesson may travel. The levels are TLP-shaped [S https://www.first.org/tlp/]:

- `none`: may not travel at all.
- `home` (RED): stays on this instance.
- `house` (AMBER+STRICT): this instance and its twins.
- `peer` (AMBER): named Aurora instances.
- `public` (CLEAR): anyone.

The ceiling is the minimum of three:

| Input | Gives this ceiling |
|---|---|
| sensitivity | `secret`: none, and it is an incident (rotate the credential).<br>`private`: home; only Daniel may raise it.<br>`pointer`: house.<br>`attributed`: peer, and public only through the declared operator-to-role transform (section 4.3).<br>`clear`: public. |
| portability | `not_a_lesson`: none.<br>`seat`: house, meaning the same seat's lineage on this house's twins. It never goes into another instance's seat; "false autobiography is worse than amnesia" is the house's identity law, recorded in memory rather than a repo doc.<br>`instance`: house. Peer only by a seat's verdict that the lesson is portable as written.<br>`house`: peer and the starter pack, since every new install is an Aurora instance.<br>`universal`: public. |
| citations | `local_only`: house. All other statuses add no cap but are shown to readers. |

### 2.2 Where the card lives (deep level; decision D1)

**Recommendation:** a sidecar hash `learn:class:<experiment_name>`, plus append-only ledger events `lesson_classified` and `lesson_verdict`.

- **It honours "without rewriting the lesson text" and Q2's "the lesson stays clean"** [S spec:89-92]. The lesson hash is never touched. As a result, world_seed's content hash, recall, and the 16-field re-record behaviour are all unaffected [I].
- **It has two halves.**
  - `auto`: derived and rebuildable, like `recall:`. It can be thrown away and recomputed in seconds for 1,686 records [I].
  - `verdict`: authored and expensive. It must be durable, so it lives in both the hash and the ledger.
- **It sits under `learn:` so it travels to twins with `world_seed`** [S world_seed.py:51-59], and twins keep Daniel's verdicts. It does not match `learn:experiment:*`, so nothing that scans for lessons picks it up [I]. It depends on the `status` count fix first; otherwise "learnings" jumps by about 1,686 more misleading keys [I].
- **Verdicts are pinned to a content hash.** Re-recording a lesson overwrites its 16 base fields [S learning_store.py:715-806, per the store-schema lane], which changes the hash and marks the verdict stale. Staleness is a ratchet:
  - A stale `private` verdict drops back to `home` until re-reviewed.
  - A stale release verdict drops back to the automatic result.
- **Card fields:**
  - `auto.{lanes, sensitivity, portability, ceiling, labels[], rules_fired[], citations[], classifier_version, rule_set_sha, content_sha, at}`
  - `verdict.{ceiling, sensitivity, portability, by, at, content_sha, reason}`
  - `origin` (for imported lessons; see D1)
  - `grounded` (for imported lessons)
- **Alternatives Daniel may prefer:**
  - Fields on the lesson hash, set by partial write the way `benched` and `graduated` are [S spec:33]. Readers are simpler, but the record is touched and every scanner sees the fields.
  - No stored card, recomputed at every export. This loses human verdicts, so I do not recommend it.

### 2.3 The automatic classifier's decision rules

Rules run in order. The first match sets the primary class, but every label is kept, because 36 lessons and 193 notes carry two or more restrictive flags [S:local]. The rules start from the sensitivity lane's draft rubric and include the corrections it discovered.

| Rule | Fires when | Result | Reviewer |
|---|---|---|---|
| **R0 not a lesson** | Body (`what_tried` + `actual` + `recommendation`) is under 40 characters; OR the name matches the measured test-residue patterns (`pin_*`, `flow_exp_*`, `slice2_learn_*`, `stable_N`, `m_one`…, `orphan_*`, `older/newer/newest`); OR there is no `agent_id`; OR the timestamp is in the future [S:local]. | Ceiling none. Proposed for benching, never deletion. | Any seat |
| **R1 secret** | The shared egress module (2.5) matches, or a high-entropy token sits near key/token/secret words, minus fingerprinted benign matches that each carry a reason. | Ceiling none; open an incident. | Daniel (or claude) for anything inconclusive |
| **R2 private** | Any of: a private-plane marker (derived from what is actually in `private/` [S private_plane.py:25-28]); a redaction-manifest hit; a third-party name from an untracked private name list; platform user, server or message ids; contact details not on a project allowlist; the operator's name near interiority, health or family words, after the calibrated metaphor exclusions (the doctor command, symptom/diagnose trigger phrasing, git parents) [S:local]; a sensitive-subject term; a citation into `private/` or `charters/<person>/`. | Ceiling home; held. | **Daniel** |
| **R3 seat** | A callsign or seat-only id plus an identity, grant or character word, or a `scratch:<seat>`-style framing. About 29% of the sampled hits are truly seat-only; the rest just name a seat as the source [S:local]. | `seat:<x>`; ceiling house. | **That seat** |
| **R4 instance** | Drive paths outside the repo, user or host name, hardware, PIDs, OS posture, LAN IPs, ports, Redis db numbers, dated instance counts [S:local]. | `instance`; ceiling house. | Any local seat answers one question: "is the remedy the path itself?" |
| **R5 house** | The lesson *body* cites a repo path, uses at least two house terms, or carries instance-config markers. The body only, because the `source` field contains `learn:` on every lesson [S:local]. | `house`. | Auto; a seat for borderline cases |
| **R6 universal** | Everything else, after R1, R2 and the private-plane guard have run (one lesson in the universal bin tripped that guard) [S:local]. | `universal`. | Auto |
| **A (secondary)** | The operator's name or a seat name appears as who asked, ruled or learned something. | Sensitivity `attributed`. Independent of R3-R6. | Auto |

**Manners**
- The classifier reads text inside its own process and prints only ids, counts and rule ids. This follows "the finder must not become the leak" [S check_secrets.py:12-25]. The census lanes printed context windows while calibrating, and that is the mistake not to repeat [S:local, sensitivity lane's own disclosure].
- `classifier_version` and `rule_set_sha` (a hash of the rule file) are stamped on every card. A change to either marks every `auto` half stale for recomputation [I].

### 2.4 The review path

- **Daniel decides:**
  - every R2 private candidate;
  - inconclusive R1 hits;
  - the sensitive-subject research lesson;
  - any release of attributed content to the public tier;
  - anything that mentions the operator of a peer instance (consent is per subject).
  - Estimated load: 39-51 lessons [S:local; I].
- **The named seat decides its own R3 facts**, because it is that seat's autobiography: 105 lessons [S:local]. If that seat is not live, for example after a grant expires, the lesson stays home.
- **Any local seat with `kb.learn` decides:** R4 cases (about 17-22), R5/R6 borderline cases, and R0 benching proposals [S:local; I].
- **When two seats disagree, Daniel decides.**
- **Silence means hold.** An unreviewed card keeps its restrictive automatic ceiling indefinitely; no timeout ever releases anything [S lesson `consent_does_not_transfer_across_subjects_in_a_shared_bundle`, per the prior-art lane].
- **The door:** `py agent_cli.py classify queue --for <seat|operator>` shows one lesson at a time in a local terminal, with the rule that fired. The answers are home, house, peer, public, not-a-lesson, or skip.
  - For Daniel, there is optionally a local-only HTML page under `state/` (gitignored). It is never a hosted artifact, because its content is exactly what must not leave the machine [I].
  - A verdict writes the card and a ledger event. It never edits the lesson.
- **A zero-work option for Daniel:** "everything private stays home; I review nothing". The cost is about 2-3% of lessons missing from packs [I].
- **Calibration bar:** if the dry run puts more than 60 lessons in Daniel's queue, the rules are too loose. They get recalibrated before he is asked anything (bar B12).

### 2.5 One egress-rule module (deep level)

Proposed home: `core/trust/egress_rules.py`.

**What it contains:**
- the union of `check_secrets.PATTERNS` (9) and `discord_bridge._SECRET_PATTERNS` (3);
- additional rules for webhook URLs, JWTs, Discord bot tokens, Telegram tokens, URLs carrying passwords, and unquoted assignments;
- the entropy check;
- a benign allowlist keyed by a hash of the match, never the literal, with every entry carrying its reason (the pattern at [S check_secrets.py:109-112]);
- three result states: match, benign-fingerprinted, unchecked. This borrows from TruffleHog without its live verification step, which sends the secret to the issuer [S https://github.com/trufflesecurity/trufflehog; I].

**Who calls it:** the pre-push secret check, the bridge relay, the classifier, pack export, pack import, and later the `learn` door as a warning. Each vendor shape gets one pinned synthetic example.

**The identity half loads from an untracked file in `private/`**, so tracked code holds no literal names [I].

The September sanitizer is the anti-example. `research/in-flight/seed-sanitize-2026-09-01/` is untracked, and only its `.jsonl` file is gitignored [S:local, git status `??`, check-ignore]. A broad `git add` would therefore commit three files that carry identity strings:
- `diff-sample.md`
- `seed_pipeline.py` (literal identity regexes)
- `pipeline-summary.json`, whose transform labels contain names [S:local, read today]

---

## 3. The citation resolver

**Plain version.** Lessons keep saying "core/comm/bus.py". A small table says which repo each folder lives in after the split, and a short checklist finds files that moved. When a file is truly gone, recall shows a one-line note rather than hiding it or guessing.

### 3.1 Format: keep what is stored

- **Stored citations stay exactly as written.** 4,970 of 5,010 path citations are already plain repo-relative paths [S:local]. The canonical store needs no migration.
- **Structured citations are derived into the card only.** Each is `{kind, raw, norm, lane, status, via, witness?}`.
  - Kinds: `path`, `dir`, `art`, `lesson`, `mem`, `sha`, `url`, `port`, `abs`, `proc`.
  - `url`, `port`, `abs` and `proc` are instance facts. They feed rule R4 rather than resolution [I].
- **Witness, not identity.** For new lessons, the card records, at learn time, the commit sha and git blob id of each cited file.
  - It is for recovery, not as the lesson's identity. Hot files change constantly (agent_cli.py has 321 commits), and 831 citations are directories, which have no stable hash [S:local].
  - Content is the strongest recovery signal once a file is gone: body-suffix matching recovered 119 of 119 paths, against 21 of 517 by filename [S:local].
- **Knowledge-lane citations prefer `art_` ids.**
  - That is the library's own convention, and the natural experiment already happened: in one reconciled report, the frontmatter `art_` citations all survived a move while all four body path citations died [S:local, prior-art lane].
  - 72 of 168 `docs/library` path citations have id-shaped filenames and convert mechanically, in the card [S:local].
- **No `lane:path` spelling ever enters the store.**
  - `REF_KINDS` is closed at eight, and "a resolver may NOT mint new ref kinds" [S target.py:21, 52].
  - Experiment names already embed `research:`, so the prefix would be ambiguous in prose [S:local].

### 3.2 The map: the lane table

The lane table is a versioned, tracked data file in the substrate (proposal: `core/library/lanes.v1.json`). The longest matching prefix wins.

| Prefix | Lane | Repo after the split | Note |
|---|---|---|---|
| `arsenal/` | creative | aurora-arsenal | [S plan:31, :75] |
| `docs/library/`, `chronicles/`, `research/reviewed/`, `docs/_archive/` | knowledge | content repo | [S plan:30] |
| `research/in-flight/` | research (ephemeral) | aurora-research | [S plan:32] |
| `research/briefs/`, `research/drafts/`, `research/reference/`, `research/` root | **UNDECIDED** | (none yet) | The plan contradicts itself [S plan:30-32 vs :73]. Decision D7. |
| `store/docs/` | **UNDECIDED** | (none yet) | Tracked maps the resolver needs (`legacy_map.json`, `migration_map.json`), but the plan calls `store/` runtime [S plan:39; S:local]. Decision D7. |
| `state/`, `session_logs/` | runtime | never tracked | [S plan:39] |
| `security/`, `.secrets/`, `private/` | home | never tracked | Citations into these resolve here only and feed R1/R2. |
| `scripts/vfx*`, `scripts/piano*`, `design/vfx-*` | substrate for now; creative cadence | D7 | 120 citations [S:local] |
| everything else | substrate | akashic-aurora | "What's left IS the substrate" [S plan:79] |

An instance-local mount file, `state/world/lanes.local.json`, is written by setup and maps each lane to its local checkout root. Before the split, every lane points at `E:\AI-Setup`. After it, each lane points at its sibling checkout [I].

**The key requirement on the split (deep level; D7):** each new repo should keep its full original paths. That means filtering by path rather than re-rooting, so `arsenal/keylab/README.md` is still `arsenal/keylab/README.md` inside aurora-arsenal.
- With paths preserved, the citation namespace never changes. Resolution becomes "find the mount, join the path", and no stored string changes [I].
- The plan's rule 1 says "keep relative paths intact within each repo" but does not say which way it means [S plan:49-51].
- If the repos are re-rooted, the table's `mount` field can strip `arsenal/`. The cost is that every agent working inside aurora-arsenal would produce `keylab/...` paths that recall has to map back on every lookup [I].
- Recommendation: preserve the paths.

### 3.3 How recall, recall-at and boot resolve after the split

- **One shared extractor replaces the ad hoc regexes.** `_PATHISH` recognises only .py, .md, .json, .yaml, .toml and .txt [S relevance_budget.py:43]. It misses 51 of 81 creative citations and 154 of 252 runtime citations [S:local].
- **The incoming side** is the path an agent is about to edit. The resolver turns the absolute path into a canonical one by finding the mount that contains it. For example, `E:\aurora-arsenal\arsenal\web\glider\physics.js` becomes `arsenal/web/glider/physics.js` [I].
  - `target.py` currently refuses absolute paths into a separate clone, saying the clone "is a WORLD" [S target.py:306-310].
  - That needs a ratified amendment: mounts listed in `lanes.local.json` are part of this world, not separate worlds (D7).
- **recall-at** already queries with path words [S at_action.py:1774, per the citations lane]. With paths preserved, the split does not change its ranking. The resolver only adds a status line.
- **The boot ladder's exact-path rung (0.7)** compares canonical paths to canonical paths, so it keeps working across mounts [S relevance_budget.py:74-121, per the store-schema lane; I].
- **Anchor and staleness checks** call `resolve()` instead of checking whether the file exists.
- **Faithfulness gate.** Today it checks only that a lesson id resolves [S, per the store-schema lane]. It gains citation status as information, not as a demotion.
- **What a reader sees** when a lesson's citation is dead is one plain line, such as "cites X, which no longer exists (deleted in <sha>)" or "moved to Y". Changing ranking on that basis is a separate, measured slice [I].

### 3.4 Resolution order, with measured coverage

1. **Normalize.**
   - Convert backslashes.
   - Turn absolute paths into the repo into relative ones (109 cases).
   - Turn worktree paths into `work:` form (13).
   - Split `path:line` and `path.symbol`; the extractor's one false positive was `core/foundation/timeutil.to_epoch`.
   - Fold case for matching only (11 paths appear in two casings) [S:local].
2. **Exact match on the mount:** 77.9% of path citations [S:local].
3. **Legacy map, widened beyond `docs/` to `research/*`,** plus the reader for `migration_map.json`. That map has 664 entries, covers 621 of the 621 paths deleted in 425cf527a, and today is read only by the script that writes it [S:local]. Translate to an `art_` id, then to the current path. Coverage reaches about 85.2% [S:local].
4. **Git rename history** in the lane's repo: 34 more records [S:local].
5. **The witness blob id,** searched with `git log --find-object`. New citations only [I].
6. **`local_only`:** the file exists on disk but is untracked. 130 paths in 243 records, for example `security/acl.json` cited by 58 records [S:local]. It resolves here and is marked non-transferable.
7. **`dead`, with a reason:** deleted in history (208 paths) or never in history (288) [S:local]. In the ephemeral research lane, a dead citation is normal (`dead_ephemeral`) and raises no alarm [S plan:32 "discard freely"].

### 3.5 How it is tested

- Unit pins for each step, using synthetic paths.
- A golden fixture of (lesson id, raw citation, expected status, via) generated in-process from the real corpus. Citations into `private/`, `.secrets/` and `charters/` are left out of tracked fixtures [I].
- Property tests: resolution is idempotent, and lane order cannot change the result.
- A split simulation (section 6, step 8). The bar is that no citation that resolves before the split stops resolving after it.
- Rot tracked by month as a regression series. By the month a record was written: June 33.6%, July 24.5%, August 12.2%, September 12.4%, October 8.3% [S:local].

---

## 4. The portable lesson pack

**Plain version.** A pack is a folder. It holds one line per lesson, a fingerprint of each lesson, a list of what was left out and why, and optionally a signature that proves which house made it. The receiving house checks everything again itself and holds the lessons in a waiting room until someone local says yes.

### 4.1 Layout

The layout is shaped after BagIt [S https://www.rfc-editor.org/rfc/rfc8493].

```
aurora-lessons_<instance-label>_<generation>/
  bagit.txt             declaration: format name and version
  pack.json             manifest (4.2)
  lessons.jsonl         one lesson per line, UTF-8  [S https://jsonlines.org/]
  tombstones.jsonl      retractions {key, formerType, deleted, reason}  [S ActivityStreams Tombstone]
  enforcement.jsonl     Q1 pairs: lesson -> enforced_by -> {repo, path, blob}
  refused.json          the Dawe report: counts by class and rule
  manifest-sha256.txt   sha256 of every payload file
  pack.sig              optional Ed25519 signature over manifest-sha256.txt plus a trusted comment
```

**`refused.json` carries counts only for the secret, private and seat classes.** "Existence metadata is a leak": ids and titles alone can expose private material [S private_plane.py:17-23]. Only house-tier packs, which go to twins on the same machine, may list the ids of what they refused.

### 4.2 `pack.json`

- **Format and schema:** `"format": "akashic-lesson-pack"`, `"schema": "1-0-0"`.
  - Versions are SchemaVer, MODEL-REVISION-ADDITION [S https://docs.snowplow.io/docs/api-reference/iglu/common-architecture/schemaver/].
  - Readers refuse a newer MODEL loudly, the same rule LIBRARY.md uses for atoms [S LIBRARY.md:131-134, per the prior-art lane].
- **Generation and prerequisites,** for example `"prerequisites": ["<instance>/starter-2"]` [S https://git-scm.com/docs/git-bundle].
- **Source instance:** a random 128-bit id plus a human label. It is pseudonymous: never the operator's name, which is why keyless Sigstore is avoided [S https://docs.sigstore.dev/cosign/signing/signing_with_blobs/].
- **Where it was cut:** `created_at` in UTC, plus the substrate git sha, lane-table version, classifier version and rule-set sha. This follows the savepoint law "both planes or neither" [S world_savepoint.py header, per the prior-art lane].
- **Audience:** the audience tier, and counts carried and refused per class.
- **Hash algorithm id:** `aurora-content-v1+sha256`.

### 4.3 The per-lesson record

```json
{"key": "<experiment_name exactly as stored>",
 "origin": {"instance": "<id>", "minted_at": "<utc>", "content_sha_at_source": "...",
            "derived_from": [{"instance": "...", "pack": "...", "content_sha": "..."}]},
 "content": {"what_tried": "...", "actual": "...", "expected": "...", "recommendation": "...",
             "root_cause": "...", "anti_pattern": "...", "category": "...", "domain": "...",
             "agent_id": "...", "source": "...", "metrics": "...", "files_affected": "..."},
 "content_sha": "aurora-content-v1+sha256:<hex>",
 "lifecycle": {"success": "...", "confidence_raw": "...", "confidence": "low|medium|high",
               "timestamp_raw": "...", "timestamp_utc": "...", "tz_assumed": true,
               "benched": "...", "graduated": "...", "enforced_by": "...", "related_to": "..."},
 "author_seat": "heimdall",
 "classification": {"lanes": [], "sensitivity": "...", "portability": "...", "ceiling": "...",
                    "labels": [], "classifier_version": "...",
                    "verdict": {"by_role": "seat|operator", "at": "...", "content_sha": "..."}},
 "citations": [{"kind": "path", "raw": "...", "norm": "...", "lane": "...", "status": "...", "via": "..."}],
 "transform": [],
 "evidence": {"as_of": "...", "surfaced": 0, "useful": 0, "helped": 0, "noise": 0}}
```

The provenance fields borrow PROV-O meanings (wasAttributedTo, wasDerivedFrom, generatedAtTime) without the RDF wire format [S https://www.w3.org/TR/prov-o/]. Narrative fields ride in house-tier packs only.

**The content hash (deep level).** It is exactly world_seed's `_content_bytes`: the same 12 fields, with the same normalization of `metrics` and `files_affected` [S world_seed.py:224-263]. The seed inventory and the pack fingerprint are therefore one number per lesson, not two.
- **It is not RFC 8785 JCS.** The outer `json.dumps` uses Python's default ASCII escaping [S world_seed.py:263]. Any lesson with non-ASCII text, which is common here because of dashes and arrows, would hash differently in a JCS implementation [S https://www.rfc-editor.org/rfc/rfc8785; I].
- **Keep it anyway:** name it `aurora-content-v1` and ship test vectors. Because the algorithm name travels inside the hash string, a later JCS-based v2 is an ADDITION, not a breaking change [S https://docs.ipfs.tech/concepts/content-addressing/; I].
- **Caveat:** `agent_id` is one of the hashed fields. An importer must never "fix" aliases inside the content; author seat lives on the card [I].

**Transforms.** Only declared, deterministic transforms may run on outbound copies, for example `operator->role` in public packs. When one runs, the pack keeps both `content_sha` (as shipped) and `origin.content_sha_at_source`, and the canonical store is never rewritten [I].
- LLM paraphrase is never used. Paraphrase is exactly how private material escapes a filter [S private_plane.py:185-198, per the prior-art lane; S https://docs.mem0.ai/platform/features/memory-export].
- Credential values are never carried; Letta's export rule is that "secrets are set to null" [S https://github.com/letta-ai/agent-file]. Here, R1 refuses the record outright.

### 4.4 What each audience tier may carry

| Tier | Audience | Lessons | Memory notes | Narrative | Evidence counters | Signature |
|---|---|---|---|---|---|---|
| **house** | This instance's twins (today's world_seed audience) | Ceiling house or wider | No in v1 (D2) | Yes | As evidence only | Optional |
| **peer** | A named Aurora instance on the trust list | Ceiling peer or wider: sensitivity clear or attributed, portability house or universal, no `local_only` citations | No | No | Optional | **Required** |
| **public / starter** | Any new Aurora install | Ceiling public. That means clear (or attributed after the operator-to-role transform), house or universal, and every citation resolving on the public substrate at the pinned sha. Benched lessons are excluded, per the clearance predicate [S spec:53-64]. | No | No | No | Recommended |

In every tier, a graduated lesson rides only if its enforcement entry resolves on the target. Q1 is "both or neither" [S spec:70-81].

### 4.5 Export, with gate 1 of 2

Command: `py agent_cli.py pack export --tier house|peer|public [--to <peer-label>] --out <dir>`

1. **Read Redis through a read-only client** with a command allowlist (HGETALL, SCAN, LRANGE, ZRANGE, GET, TYPE, EXISTS), which raises an error on anything else.
   - It never instantiates `LearningStore`, because that class runs the legacy JSONL importer on startup [S learning_store.py:308-310].
   - SQLite is opened only with `mode=ro`. The lanes measured that "read" doors write [S:local; I].
2. **Take lessons with content only,** and compute the inventory from the same read as the copy. This avoids seed_world's race between copying and taking inventory [S seed_world.py:64, 74, per the prior-art lane; I].
3. **Classify fresh, in-process, and compare with the stored card.** If the fresh result is more restrictive than a stored verdict, the lesson is held and reported.
4. **Filter by tier**, then **apply declared transforms**.
5. **Run the egress module on the exact outbound bytes.**
6. **Resolve citations** into the record.
7. **Write the files, manifests and refusal report,** then sign if a key exists.
8. **Self-validate:** re-read the pack, recompute every hash, and re-run the egress module. Any non-benign match fails the export.

### 4.6 Import, with gate 2 of 2

Commands: `pack import <dir>` (to quarantine), then `pack review`, then `pack accept|reject`.

1. **Verify the pack.**
   - The bag is complete and valid [S RFC 8493].
   - The schema MODEL is not newer than ours.
   - For peer packs, the signature checks against a key on `state/world/peers.json`, a trust list that Daniel approves.
   - The signed trusted comment matches the manifest, which blocks downgrades [S https://jedisct1.github.io/minisign/].
   - Prerequisites are present.
2. **Re-run the egress module and the local classifier on every record.** The sender's labels are never trusted. Anything the local classifier puts below the pack's tier is refused and counted.
3. **Stage into quarantine** under `import:<generation>:<key>`.
   - That prefix is not in `KNOWLEDGE_PREFIXES`, so staged lessons never seed down.
   - It is not under `learn:`, so recall, boot and recall-at cannot see staged lessons [S world_seed.py:49-59; I].
4. **Match.** The stable key is (origin instance, key), plus the content hash.

   | Situation | Outcome |
   |---|---|
   | Same origin, key and hash already accepted | No-op (idempotent) |
   | Same origin and key, new hash, local copy unchanged since the last import | Staged as a revision (wasRevisionOf) |
   | Same origin and key, new hash, local copy edited here | Conflict: the local copy stays the winner and the import is kept in a conflicts set, so no text is lost [S https://automerge.org/docs/reference/documents/conflicts/] |
   | Same key, different origin (a free-text name collision) | Staged as `<key>__<origin-short>`, with an alias recorded [S https://retorque.re/zotero-better-bibtex/citing/] |
   | Different key, same hash | Linked as duplicate-of; nothing added |
   | Tombstone for a lesson from that origin, not edited here | Benched locally with reason "retracted at origin"; never deleted (the standing ask-before-deleting rule) |

5. **Confirm.** A local seat holding a new, time-boxed `kb.import` grant accepts batches. The grant is approved by the super-admin (claude) or the human, per the security schema [S AGENTS.md lines 7-20; S:local acl.json]. Daniel confirms anything attributed or mentioning a peer's operator. For the starter pack on a fresh install, the installing human confirms once, with the summary on screen.
6. **Accept.**
   - Promote the lesson to `learn:experiment:<key>` (or its alias).
   - Write its card with the origin and "accepted by <seat>".
   - Append `{id, sha256, generation}` to `world:import:manifest:<generation>`, the same shape as the seed inventory [S spec:226-238].
   - When the starter pack goes into an empty world, write `world:seed:manifest` itself, so the bootstrap self-check and the recall-at canary work unmodified [S spec:123-160].
   - **A peer lesson is a claim, not a fact.** `grounded: false` until a local seat re-checks it, under world_seed's doctrine that "upward is a claim" [S world_seed.py:8-15]. Recall shows it as "from <peer label>, not yet grounded here".
7. **Handle votes and stats honestly.**
   - Local `recall:use` counters start at zero [S spec:107-119].
   - The sender's counts ride as evidence in the import manifest and are never written to `recall:*`.
   - The seeded-versus-organic view from Q2 joins against the manifest [S spec:94-99].
   - The dry run measures the shift in recall's fixed relevance floor, because an absolute threshold on raw scores is not portable [S lesson `absolute_threshold_on_a_raw_relevance_score_is_not_portable`, per the prior-art lane].

### 4.7 The round-trip guarantee

Take a pack P exported from instance A, imported into an empty instance B, accepted, and re-exported from B as P':

1. Every record carried in P appears in P' with the same key, byte-identical content and the same hash.
2. Lifecycle fields are identical, except for declared differences: evidence is absent or zero, and `origin.derived_from` gains exactly one hop.
3. Records carried plus records refused, per class, equals A's count of lessons with content ("complete", in the BagIt sense).
4. Importing P twice changes nothing.
5. For every accepted lesson, HGETALL in B equals the record's content and lifecycle fields. No field is dropped, which is the opposite of the legacy importer [S learning_store.py:740-741].

The bar is 0 records and 0 fields lost.

**Memory notes are not in v1.** A later "decision pack" would need its own rubric: there are 607 scratch notes and 1,169 notes that name the operator [S:local] (D2).

---

## 5. Ease of setup

**Plain version.** A new house runs one command, sees a short summary of what it is about to receive and what was left out, says yes once, and ends up with a working memory that proves it works.

### 5.1 A brand-new instance

Command: `py agent_cli.py setup --starter`, which wraps `bootstrap_world`. It runs these steps:

1. Pin the durable backend to SQLite in a config file under `state/`, not a user-level environment variable. This closes the fresh-install hole on the JSON store [S store.py:1198-1232, per the store-schema lane; I].
2. Mint the instance id.
3. Write `lanes.local.json`, using identity mounts or discovered sibling checkouts.
4. Find the starter pack at `packs/starter/<generation>/` in the knowledge checkout.
   - Packs are append-only, content-addressed and never force-pushed, which is exactly the knowledge lane's lifecycle [S plan:30].
   - The repo already ships no lessons, since `session_logs/` and `*.jsonl` are ignored [S, per the store-schema lane]. The starter pack becomes the one reviewed thing that does ship.
5. Verify the pack, run import gate 2, show the summary (counts by class, what was refused, signature status), and take one confirmation.
6. Accept the pack and write `world:seed:manifest`.
7. Run `bootstrap_world --self-check`. The memory tier moves from "UNCHECKED, no seed manifest yet" to "recall-at surfaced seeded lesson <id>" with a matching hash [S bootstrap_world.py:144, 173; S spec:278-283].

It needs no network beyond the clone the user already made [I].

### 5.2 Between existing instances

Three commands: `pack export --tier peer --to <label>`, then `pack import`, then `pack review` / `pack accept`.

### 5.3 What the four-repo split needs from this

1. Preserve full original paths inside each split repo, or declare mounts in the lane table (D7).
2. Commit lane table v1 before split step 1, with the research sub-folders, creative content outside `arsenal/`, and `store/docs` decided (D7).
3. Have setup write `lanes.local.json` on every instance.
4. Amend `target.py` so that mounts are part of this world, not separate worlds [S target.py:306-310].
5. Run a citation census before and after each execution step. The bar is that no citation that resolves before a step stops resolving after it.
6. Keep packs in the knowledge repo.
7. Treat the research lane as ephemeral, with a pre-step for split step 1: list every in-flight file a lesson cites (30 lessons today [S:local]) and archive it to reviewed before anything is discarded.
8. Correct the plan's claim that nothing cross-cites research: 48 lessons and 251 citations do [S:local].

---

## 6. Dry run on the real corpus

**Where.**
- **Prefer** the E:/AI-Setup-Sandbox Redis on :16380, a separate server, so a flush against the wrong database cannot reach prod. Use db 1 as the source mirror and db 2 as the fresh target.
- **Allowed but not preferred:** db 15 on :16379 [S AGENTS.md "Trial mode"], because it shares the prod server.
- **Never** db 0.
- Run the dry run when no game is running, or at below-normal priority with bounded reads.

**Steps**
- **Step 0, preflight.**
  - Prove the read-only client: a unit test shows HSET raises, and the client logs every command it issues.
  - Settle the census disagreements: whether the 28 lessons absent from SQLite are ghosts or real, and records versus keys for memory.
  - Confirm :16380 is up.
- **Step 1.** Export a raw house-tier pack from db 0 to files in the sandbox directory.
- **Step 2.** Load it into sandbox db 1 in mirror mode (no quarantine). This is round trip 1: Redis to pack to Redis, with HGETALL compared for equality.
- **Step 3.** Classify in db 1, so cards are written there only. Print counts by class and rule only.
- **Step 4.** Plant synthetic canaries in db 1 only, all invented text:
  - 10 private-shaped (an invented third-party name, interiority wording, a fake platform id);
  - 6 secret-shaped (documented fake vendor sample shapes);
  - 4 instance-bound;
  - 4 seat-bound;
  - 3 test-residue.
- **Step 5.** Export house, peer and public packs from db 1.
- **Step 6.** Import each pack into db 2, flushed between tiers (flushing only ever on :16380). Then quarantine, scripted accept by a dry-run seat, re-export, and diff.
- **Step 7.** Run recall parity on the fixed query set below.
- **Step 8.** Simulate the split: identity mounts against per-lane sparse checkouts in the sandbox directory.
- **Step 9.** Run the fresh-install drill: an empty world, the starter pack, then the self-check.
- **Step 10 (optional, after the bars pass).** A fresh-eyes seat, not the classifier's author, reads a stratified sample of 100 public-pack lessons in-process. Zero private findings would put the true rate under about 3% at 95% confidence (rule of three) [I]. Daniel's sample review is his call.

**Fixed query set, pre-registered here (60 queries)**
- **QA, 6 queries:** the sanitizer's probes [S pipeline-summary.json]:
  - "wake watcher arm failure lane"
  - "green suite dirty tree verification claim"
  - "operator correction curate corpus seed onboarding scatter"
  - "redaction privacy knowledge store identity split"
  - "discord message silent drop webhook feed"
  - "commit push gate refused baseline stale attribution"
- **QB, 22 queries:** `recall-at --path` for the 22 most-cited paths in the citations lane's §5, from agent_cli.py through state/coord/tasks.json. `security/acl.json` stays in the set as the `local_only` probe [S:local].
- **QC, 20 queries:** `recall "<category>"` for the 20 most frequent categories other than `uncategorized`, ranked by count at run time, ties broken by name [I].
- **QD, 12 queries:** `recall-at --command` for:
  - "git push", "git add -A", "git commit --no-verify"
  - "py agent_cli.py learn", "py agent_cli.py boot"
  - "py scripts/mirror.py", "py scripts/seed_world.py", "py scripts/bifrost_wake.py", "py scripts/ops/snapshot_knowledge.py"
  - "py -m pytest", "redis-cli flushdb", "es.exe"
- **Baselines:** (a) db 1 restricted to the lesson set the pack carries, compared with the import target; (b) the resolver on versus off.

**Acceptance bars (pre-registered).** If B1, B2, B3 or B4 fails, no pack leaves the sandbox. If any other bar fails, fix and rerun.

| Bar | Criterion |
|---|---|
| **B1** | 0 non-read commands issued against db 0 by any dry-run process, according to the client log. Failing this stops the run. |
| **B2** | 0 non-benign egress matches in any outbound pack, at export and on the import re-scan. 6 of 6 secret canaries caught and excluded. |
| **B3** | 0 records with an R2 label or a Daniel "home" verdict in peer or public packs. 10 of 10 private canaries excluded. The private-plane-marker lesson absent. 0 residual identity strings in the public pack, matching the 0 the sanitizer achieved [S pipeline-summary.json]. |
| **B4** | 0 records and 0 fields lost, Redis to pack to Redis and pack to B to pack'. The content-hash sets are equal. |
| **B5** | A second import of each pack makes 0 changes. |
| **B6** | 5 of 5 synthetic conflict scenarios (revision, local edit, name collision, duplicate content, tombstone) produce the outcome in the 4.6 table. |
| **B7** | Recall parity: mean top-10 set overlap of at least 0.95 across the 60 queries, and no single query below 0.70. This applies to the house pack and to the transformed public pack, each against its restricted baseline (the precedent is 59/60, or 0.983 [S pipeline-summary.json]). With the resolver on versus off, recall-at's top 5 is identical for at least 57 of 60 queries. |
| **B8** | At least 85% of path citations resolve (against a 77.9% exact-match baseline [S:local]). The split simulation loses 0 citations that resolved before. Extractor precision is at least 95% on a 60-item random sample (the precedent is 39/40). |
| **B9** | Carried plus refused per class equals the total. Every gate reports either "ran" or "unchecked" explicitly; a gate that did not run never reports zero ("zero is not no"). |
| **B10** | The fresh-install self-check reports the memory tier VERIFIED, with a matching hash. |
| **B11** | Run logs contain 0 hits from the in-process identity list and no text from any R2 record. |
| **B12** | Daniel's review queue is 60 lessons or fewer, and the seat queues are reported. |
| **B13** | Class counts fall within ±15% of the sensitivity lane's figures (77 / 0 / 26 / 105 / 87 / 811 / 580), or the difference is explained [S:local]. |

---

## 7. Build slices with receipts, and the decisions only Daniel can make

Each gated slice ships under the method baseline: fenced dual passes and pre-registered acceptance [S AGENTS.md "The method" paragraph, pointing to docs/method-baseline-2026-07.md].

| Slice | What it builds | Receipt | Writes to |
|---|---|---|---|
| **S0** Honest counts and a read-only door | `status` counts records: lessons with content, husks, live and superseded decisions. The command-allowlist Redis client. `check_dual_authority` compares record sets instead of modification times, and also runs directly as a script. | `status` shows 1,658 / 28 / 1,977. The checker turns **red** on today's 258-lesson gap; a checker that fails on known damage is the receipt. | repo only |
| **S1** Egress-rule module | The union rules, the fingerprinted benign list and pinned vendor examples. The push gate and the relay call it. | The existing tests of both callers stay green, and the synthetic examples are caught. | repo only |
| **S2** Citation resolver v1 | The shared extractor, lane table v1, the widened legacy map, the `migration_map` reader, rename history, and a read-only `cite check`. `_PATHISH` call sites move to the shared extractor. | B8 | repo only |
| **S3** Classifier v1 and cards | The rules, the card schema, and the `classify queue` door. Sandbox only. | B12, B13 | repo, sandbox |
| **S4** Pack v1 | The writer, validator, importer (quarantine, accept, conflicts, tombstones) and the `kb.import` capability. | B4-B6 on synthetic packs | repo, sandbox |
| **S5** Dry run | Section 6, end to end. | All bars, filed as one report in research/reviewed | sandbox, report |
| **S6** Setup | `setup --starter`, the SQLite default, the instance id, and starter pack generation 1 (built after D4). | The fresh-clone drill (`check_fresh_clone --clone` [S plan:29]) plus B10 | repo, knowledge repo |
| **S7** Canonical rollout | The first write to db 0, gated on Daniel's go (D9): cards written into db 0, review sessions, cards and witnesses stamped at learn time, the mirror repaired (`durable_reconcile.py --plan` first), test residue benched (never deleted), and a test guard against db 0. | The mirror matches Redis 100% on record sets. New lessons arrive with cards. | canonical |
| **S8** Split support | The `target.py` amendment, lane mounts, and the per-step citation census. Ships before split step 1. | 0 citations lost per step | repo |
| **S9** Signing and the peer trust list | Built at the first real peer exchange. A peer instance, Mnemosyne, already ran an 11-item "Aurora Transfer" from this house [S research/reviewed/mnemosyne-provenance-archaeology-2026-10-03.md, per the prior-art lane]. Python `cryptography` 46.0.7 (Ed25519) and `ssh-keygen -Y` are already present [S:local]. | A signed pack verifies, and a tampered pack is refused. | repo, `.secrets/` (key never printed) |

**Small, independent repairs a seat can do in passing:**
- Fix the legacy importer's field names (`actual_outcome` and `expected_outcome`). Fix it in place rather than delete it.
- The leaked `newest` and `older` fixtures.
- The ghost counters `recall:use:l` and `recall:use:pull_test`.
- The clearance predicate, which is documented as enforced but is not implemented.
- The three untracked files in the sanitizer folder that carry identity strings (D11).

### Decisions only Daniel can make

The ones marked "deep level" are worth his time at the mechanism level.

- **D1 (deep level). Where the label card lives.** Recommendation: the sidecar `learn:class:<id>` (section 2.2). Also, whether his Q2 ruling ("no permanent provenance stamp") extends to sidecars, which decides whether an imported lesson's origin is recorded per lesson on its card or only in the import manifest.
- **D2. Whether memory notes ever travel.** Recommendation: not in v1.
- **D3. The private review.** He either reviews about 39-51 lessons or rules "all private stays home". Also the consent rule for third parties, including the operator of a peer instance.
- **D4. Whether a public starter pack should exist at all,** and whether the operator-to-role transform may run on outbound copies.
- **D5. Votes for peer imports.** Confirm that counters start at zero, extending his seed ruling, or allow a damped prior from the peer's evidence.
- **D6. Signing.** Whether to have a per-instance key, and who holds it.
- **D7 (deep level; with Heimdall). The split.**
  - Preserve paths or re-root the repos.
  - Where research briefs, drafts, reference and the research root go.
  - Whether `scripts/vfx*`, `scripts/piano*` and `design/vfx-*` move with creative.
  - Where the `store/docs` maps live.
  - Ratifying the `target.py` amendment.
- **D8. `kb.import`.** Create it, set its default duration, and say who may hold it.
- **D9. Go or no-go on the first canonical write (S7),** after the dry run.
- **D10. Who looks at the two shape matches** (one lesson, one decision) and the sensitive-subject research lesson.
- **D11. The three untracked sanitizer files.** Gitignore them or move them into `private/`. Either way it is a repo edit he should approve.

**Seat-decidable:** the alias map, lane-table entries for clear cases, category normalization, R3/R4/R5 reviews, and proposals to bench test residue.

**Not checked in this stage, because a game was running:**
- the Redis dumps inside the snapshots;
- the clone drill;
- the `durable_reconcile` plan;
- whether the :16380 sandbox is up.

All four are UNCHECKED and belong to step 0 of the dry run.

**Census working files (read-only probes; ids and counts, no text):** `<scratch>\`
- `labels.json`, `classify.py`, `final_run.txt` (sensitivity lane)
- `cite_census.json`, `analysis.txt`, `legacy.txt` (citations lane)
- `census_out*.json` (store-schema lane)
- `ro_*.py` (prior-art lane)

---

## Census lane: storage and schema (verbatim)

**Store-schema census: Akashic Aurora lessons and memories (read-only, measured 2026-10-29)**

Grading: [S] cited from source, [S:local] measured here, [I] inference.

## Bottom line

1. **The headline counts are key counts, not record counts.** "~1,930 learnings" is every key under `learn:*`. "~1,214 agent-memory records" is every key under `mem:*`. The `status` command counts keys that way (`agent_cli.py:8585`) [S]. The real figures [S:local]:
   - 1,686 lesson hashes. 1,658 have content; 28 are empty husks.
   - 1,977 memory decisions in one hash (`mem:decisions`). 690 of them are superseded. Experiences, reflections and approaches have zero keys.
2. **Redis is the only complete copy of the lessons.** The SQLite mirror is missing content for 258 of 1,658 lessons (15.6%): 28 are absent and 230 are husks holding only the narrative fields [S:local]. It also lacks 125 memory decisions (it has 1,852 of 1,977) [S:local].
   - The checker built for this (`check_dual_authority`) reports PASS, because it only compares file modification times within a 24-hour window [S:local; `check_dual_authority.py:60-95`].
   - Run directly as `py scripts/checkers/check_dual_authority.py`, it crashes with `ModuleNotFoundError: core`. It only runs as `py -m scripts.checkers.check_dual_authority` [S:local].
3. **No current path can export lessons from one Aurora instance and import them into another.**
   - Snapshots copy the whole world: everything, unclassified, and restoring one wipes the target first.
   - `seed_world` only seeds down a tier on the same machine, and it refuses to seed into prod.
   - The only importer, the legacy `learnings.jsonl` reader, does not accept the format that `recall --json` writes. Details in the export section below.
4. **A fresh install starts with an empty memory and the store that loses writes.** No lessons ship in git. Without an undocumented environment variable, the durable layer is the file store that was measured losing 65.6% of concurrent writes [S].

## Where lessons live

**Redis db 0 on port 16379** holds 122,622 keys [S:local]:

| Prefix | Keys | What it is |
|---|---|---|
| `events` | 82,714 | `events:raw:*` index strings |
| `bifrost` | 26,995 | live message bus |
| `narr` | 5,676 | 4,746 beat strings, 908 chapters, 10 tracks, 6 themes |
| `learn` | 1,930 | lessons and their indexes (below) |
| `recall` | 1,644 | 1,642 vote counters, plus `recall:surface` (6,007 entries) and `recall:outcome` (20,004 entries) |
| `artifact` | 1,520 | artifacts |
| `mem` | 1,214 | memory decisions (below) |
| `embed` | 82 | cached vectors |
| `residents` | 13 | |
| `lookback` | 9 | |

There is also test-run residue in prod: prefixes like `t-w43-*`, `t-w16-*` and `bifrost_d224_*` [S:local].

**Lesson keys** [S] `learning_store.py:17-24`; counts [S:local]:
- `learn:experiment:{id}`: one hash per lesson, 1,686 keys.
- `learn:experiments:all`: a list of 1,686 ids, rebuilt from the hashes. No orphans in either direction.
- `learn:experiments:success`: a sorted set of 1,665 members; 4 name no lesson.
- `learn:category:*` (90 sets), `learn:agent:*` (60 lists), `learn:anti_pattern(s)` (62), `learn:repeat(s)` (28).

**Lesson writers** [S] `learning_store.py`:
- `_index_learning` (lines 715-806) writes 16 fields.
- The partial updates `tag_anti_pattern`, `mark_graduated`, `mark_benched`, `mark_related` and the forge family (lines 475-675) add fields without touching the rest.
- `chapter_lifecycle.write_learning_chapter_backlinks` adds `narrative_chapter` and `narrative_track` (lines 89-112).

**Store wrapper** [S] `store.py`:
- The default store writes the file layer first, then Redis on a best-effort basis, and reads from Redis first (lines 876-893).
- The file layer is SQLite only when `AKASHIC_STORE_BACKEND=sqlite`; otherwise it is the JSON file store (lines 1198-1232).
- On this machine the variable is set only at user level [S:local]. It is not mentioned in `DEPLOY.md` or `AGENTS.md` [S:local].

**SQLite mirror** (`session_logs/store_state.db`, 111.5 MB) [S:local]:
- It is a generic copy of Redis's data types, not a lesson schema: tables `kv`, `hash`, `list`, `set_members`, `zset`, `expiry`.
- Row counts: 82,831 / 26,764 / 2,812 / 32,914 / 85,889 / 0.

**JSON twin** (`store_state.json`) [S:local]:
- It holds 218 lessons. It was last written 2026-10-28 by some process still on the JSON file store.
- 195 of the 258 lessons missing from SQLite are in it.
- [I] Likely cause: seat processes that do not inherit the user-level variable write to Redis and the JSON file, never to SQLite. The missing lessons skew toward the sol seat (95) and the codex variants (codex 41, codex_root 31, codex_root_019fab2d 8).
- [I] The husks come from the chapter writer: it checks `exists()` against Redis but writes the narrative fields to both layers, so it creates a husk wherever the lesson is missing.

**The 28 Redis husks** [S:local]:
- They are named for 2026-07-28 to 07-31, the window of the July split-brain incident [S `check_dual_authority.py:4-6`].
- Their content is in none of: Redis, SQLite, the JSON twin, or the six newest snapshot databases.
- 3 are named in `session_logs/reconcile-displaced-*.json`.
- The 208 MB Redis dumps inside the snapshots were not checked (game running).

**Event ledger** [S:local]:
- `session_logs/ledger/events_raw.jsonl` holds 2,122 `learning` events since 2026-06-27.
- Their detail carries only tried / result / category / success. The ledger cannot rebuild a lesson.

## What a lesson carries (of 1,658 with content) [S:local]

**Text fields:**

| Field | Filled | Median length |
|---|---|---|
| `what_tried` | 1,657 | 221 |
| `actual` | 1,627 | 432 |
| `recommendation` | 1,633 | 455 |
| `expected` | 107 | |
| `root_cause` | 55 | |
| `anti_pattern` | 56 | |

1,119 recommendations are written in the "Use when ..." trigger format.

**Classification fields:**
- `category`: 91 distinct values; 859 are `uncategorized`, 155 `correction`, 76 `architecture`.
- `domain`: 887 system, 104 vfx, 695 absent (read as system).
- `success`: yes 1,526, partial 82, no 50.
- `confidence`: mixed vocabulary — medium 1,343, high 277, and 38 numeric strings.
- `agent_id`: 59 distinct values, not tied to callsigns. Codex alone appears under 6 or more ids.

**Other fields:**
- `timestamp`: naive ISO with no timezone on all records. Two test fixtures leaked into prod: lessons named `newest` (dated 2026-12-01) and `older` (dated 2026-01-01).
- `source`: points at itself on 1,627 lessons, a file path on 31.
- `metrics` filled on 32; `files_affected` filled on 56 (133 paths).
- Narrative fields on 1,474; `related_to` on 395; `benched` 56; `graduated` 3; `forge_rejected` 4; `chunk_fingerprint` 31; `detail_json` 6.

**Age:** under 7 days 31, 7-30 days 130, 30-90 days 878, 90-180 days 618.

**Supersession:** no lesson carries a superseded or supersedes field. Lessons only have bench and graduate states. `core/codex/lifecycle.py` handles narrative nodes, not lessons [S].

**Dedup key:** `experiment_name`, a free-text slug.
- 36 start with `research:web:`, 5 contain spaces or capitals, the longest is 102 characters [S:local].
- Re-recording the same name overwrites all 16 base fields (blanking any not passed) and keeps the extra fields [S].
- Ids carry no instance or world namespace, so two installs collide [S `world_seed.py:155-162`].

**Memory decisions** [S:local]:
- Fields: id, title, status (all "accepted"), decision, consequences, created_at, superseded, curated (1,053 true), context (716), supersedes (664).
- No record has an author field.

## Votes [S:local]

Counters live at `recall:use:<source>` as JSON strings: 1,642 keys covering 1,640 lessons, plus 2 ghosts (`l` and `pull_test`; one carries credit).

| Counter | Total | Lessons |
|---|---|---|
| surfaced | 33,145 | |
| engaged | 1,101 | 609 |
| useful | 509 | 327 |
| helped | 201 | 145 |
| noise | 39 | 34 |

- 341 lessons have an explicit vote. Credited in two or more domains: 1 lesson.
- Judgments run at 1.65% of surfacings.

## How recall ranks [S]

All lesson recall is word matching. The 82 `embed:` vectors serve theme discovery and the clusterer (`embedder.py:16`), not lessons.

- **`recall`** matches stemmed, stopword-stripped words. It requires at least ceil(n/4) of the terms to hit (minimum 2), and otherwise returns up to 5 flagged weak matches (`learning_store.py:821-885`).
- **`recall-at`** works from a disk cache with a 120-second lifetime (in `%TEMP%`).
  - Graduated lessons are dropped; benched lessons are dropped except for probe slots.
  - The score blends relevance 0.4, importance 0.2, recency 0.2 and relationship 0.2, then applies a relevance floor, a domain filter, no-repeat and self-echo exclusions, and a usefulness multiplier between 0.5 and 1.5 (`at_action.py:739, 1842-1908`; `ranker.py:32`).
  - It queries with path words, not exact paths (`at_action.py:1774`).
  - The faithfulness gate checks that the lesson id resolves, not that cited files exist.
- **Boot** uses a ladder: task-id match 1.0, constraint 0.8, exact path match (text or `files_affected`) 0.7, category 0.5, then recency times usefulness (`relevance_budget.py:74-121`).

Recall therefore depends on: lesson ids, text, category, domain, success, timestamp, `agent_id`, `files_affected`, the bench and graduate flags, the vote counters, and triggers mined from the outcome log. The last two are state local to one instance. The anchor and staleness checks read cited paths on disk; those are the consumers a citation resolver would serve [S].

## Citations and portability [S:local]

- **505 of 1,686 lessons cite a repo path.** That is 482 distinct paths, and 90 of them (18.7%) no longer exist in this checkout.
- **By lane (lessons):** core 202, scripts 138, tests 93, state 42, `research/in-flight` 30, arsenal 27, `docs/library` 23, `research/reviewed` 18.
  - 48 lessons cite `research/`. That contradicts the split plan's claim that nothing cites research except the eye archive (`repository-split-plan.md:73-74`) [S].
- **Machine-specific paths:** 45 lessons contain a Windows absolute path, 24 the `E:\AI-Setup` repo path, and 14 the user home path.

## Classification signals [S:local]

**Identity in lessons:** 274 lessons name the operator. 1,446 name a seat; that is an upper bound, since seat names are also tool names.

**Secret-shaped strings in lessons:**
- No real token shapes (Anthropic, GitHub, Google, Slack, Discord, AWS, bearer tokens, private keys).
- One `secret=` pattern hit in `public_push_scope_is_the_whole_unpushed_backlog`: 22 characters, entropy 3.73 bits per character. Inconclusive; needs a human look.
- 4 lessons contain the machine name; 2 contain email addresses that are not the operator's.

**Private content:** keyword heuristics cannot classify it. 59 of 98 hits were "family" used in a technical sense. 13 lessons hit emotional terms; they are review candidates only, e.g. `foreign_memory_is_worse_than_no_memory` and `witness_claim_radius_and_interviewer_seed`.

**The memory plane is more personal than the lessons:**
- 1,169 of 1,977 decisions name the operator; 301 hit the private-term heuristic; 103 contain absolute paths.
- 2 contain the operator's email.
- Decision `ADR_0824212136_c1e54879` has two 21-character strings shaped like an Anthropic key prefix. That is far shorter than a real key, but it needs a human look.
- `world_seed` carries `mem:` to twins by default [S `world_seed.py:59-67`].

## Existing export, backup and mirror paths

| Path | What it does | Round-trips? |
|---|---|---|
| `snapshot_knowledge.py` | Type-aware JSON dump of all of db 0, plus store file copies, a SQLite online backup and chronicles; keeps the last 20 | Values yes. TTLs are dropped, stream ids are regenerated, `db=0` is hard-coded, restore wipes everything first, and prod restore needs `AKASHIC_RESTORE_PROD` [S]. Unclassified. 20 exist; the newest (2026-10-14, 126,293 keys, 208 MB) was used as a laptop travel seed [S:local] |
| `seed_world.py` + `world_seed.py` | Redis DUMP/RESTORE of an allowlist of prefixes; writes a manifest with a content hash per lesson | Byte-exact, same machine only. Downward tiers only, refuses target prod, endpoints hard-coded to localhost [S `world.py:137`, `world_seed.py:118-133`]. The binary format is Redis-version-specific [I] |
| `recall --json` / `list --json` | Full stored hashes, no counters | Export only |
| `learnings.jsonl` importer | Runs on every store startup; skips existing ids | **No.** It reads `actual_outcome`/`expected_outcome`, but the export has `actual`/`expected`, so re-import blanks `actual` (filled on 1,627 lessons) and drops the 12 extra fields [S `learning_store.py:313-345, 737-765`] |
| SQLite mirror / JSON twin | Durable copies | Not faithful today (see above) |
| `seed-sanitize-2026-09-01` (untracked, in `research/in-flight`) | Export → 16 redaction rules → scratch db 13 → recall parity check | Measured 59/60 top-10 overlap with 0 residual identity strings. Hard-codes a dead scratchpad path [S] |
| `durable_reconcile.py --plan`, `reheal_durable_tier.py` | Repair tools for exactly this split | Not run (game) |
| `mirror.py` | Code only; publishes to the public GitHub repo | N/A — knowledge data is never in git [S] |

## What a fresh install does today

Latest commits: `1eb3e533` added greenfield self-validation and an OS-aware `find`; `9abdae38` added the split plan.

- Cloning into `akashic-aurora` names the world prod, from the directory name [S `world.py:172-174`].
- Redis is optional, and no lessons ship: `session_logs/`, `*.jsonl` and `backups/` are git-ignored [S].
- Without the environment variable, the durable layer is the JSON file store [S `sqlite_store.py:6-11`].
- The fresh-install self-check (`bootstrap_world --self-check`) would report:
  - Memory tier: UNCHECKED, "no seed manifest yet".
  - Provenance tier: "native or copied by hand" [S `bootstrap_world.py:144,173`].
- Only a same-machine twin can be seeded. The commit message reports prod→beta verified end to end, but the spec still says "NOT YET EXECUTED" (line 263) [S].
- `find` uses es.exe on Windows, fd or locate on Linux, and a bounded walk otherwise [S].
- Prod itself has no seed manifest [S:local].
- The clone drill, the self-check and the snapshot Redis dumps were not run, because League of Legends started mid-task: **UNCHECKED**.

## What this means for export/import [I]

1. An exporter must read from Redis, or run the per-family reconcile first. The SQLite mirror is incomplete.
2. "Read" doors write. Starting the learning store runs the JSONL importer, opening SQLite creates tables, and taking a SQLite snapshot purges expired keys. An exporter needs read-only connections.
3. The clearance predicate (`spec:51-68`) covers only bench and graduate state. It has no rules for privacy, secrets, operator identity or machine paths, and the September sanitizer is the only prior art.
4. Ids need an instance namespace, or a collision policy, before anything can merge across instances.

Everything was read-only: Redis reads only, SQLite opened with `mode=ro`. The probe scripts and their outputs are in the scratchpad: `<scratch>\census_store.py`, `census_store2.py`, `census_store3.py`, and `census_out*.json`.

---

## Census lane: citations (verbatim)

**Citation census: how lessons and memories cite locations, and which citation format would survive the repo split**

Measured 2026-10-29 on Redis db 0 (:16379) and master at 4ca16c8c8.

**Bottom line**
- The plain repo-relative path citations the corpus already holds will survive the split, provided the split moves whole directories as Heimdall's rule 1 says. The lane can be worked out from each path's first one or two segments, and a lookup table can do that when a lesson is read.
- I do not recommend rewriting stored citations to `lane:path`, or using a content hash as the identity. Use a content hash as a witness instead (a fingerprint of the file as it was when the lesson was written).
- The bigger problem today is not the split. 22.1% of path citations already point at paths missing on master.
- One commit caused a third of that. A resolver for it is already half-built: `core/library/legacy_map.py` plus `store/docs/legacy_map.json`.

Grading: [S] = cited source, [S:local] = measured here, [I] = inference. Everything was read-only (Redis SCAN/HGETALL/HGET/GET/EXISTS, git ls-tree/log/show, file reads). LeagueClient was running from the start and League of Legends.exe started partway through, so the heavy passes ran at BelowNormal priority with a single git-log pass.

## 1. What was scanned
- **Lesson hashes:** there are 1,686 `learn:experiment:*` hashes. 1,658 are real lessons. [S:local]
  - 28 are "ghosts" that hold only `narrative_chapter`/`narrative_track` (e.g. `rg_windows_separator_overescape_2026_07_31`, `o1_p7_harness_batch_drill`). [S:local]
  - An exporter that scans the key pattern would ship 28 empty lessons. [I]
- **Status counts keys, not records:** `status` says "learnings: 1930". That equals the count of every `learn:*` key: 1,686 + 90 category sets + 62 anti_pattern + 60 agent lists + 28 repeat + 4 index keys. [S:local, arithmetic; agent_cli.py:8607 prints it, I did not read how it is computed]
- **Agent memory:** "agent memory: 1214" equals the `mem:*` key count. The `mem:decisions` hash actually holds 1,977 decision records, of which 690 are superseded. Its head index has 1,212 entries, while 1,287 records are not superseded; I did not look into that gap. [S:local]
  - Export/import checks must count records, not keys. [I]
- **Fields scanned:** 16,151 text fields across all lesson fields and the decision fields title/context/decision/rationale/alternatives/consequences.
  - That gave 15,420 raw citations, or 12,066 after removing repeats within one record. [S:local]
- **Extractor precision:** a 40-item random sample had 39 true path citations. The one miss was `core/foundation/timeutil.to_epoch`, a path plus a symbol, which was wrongly counted as missing. [S:local]
- **Extractor recall:** not measured. Paths with spaces get cut short, and prose paths with no slash and no known extension are missed. [I]
- **Noise dropped:** 6 drive-letter false positives (B:/, N:/, P:/). [S:local]

## 2. Citation types (counted once per record) [S:local]
| Type | Count | Detail |
|---|---|---|
| Repo-relative path | 4,970 | Plus 37 absolute paths into the repo and 3 worktree paths converted to repo-relative, giving **5,010 path citations** |
| Bare filename | 2,462 | 1,764 match exactly one file on master, 217 match several, 481 match nothing. Most ambiguous: registry.py (18), index.js (15), architecture.md (14) |
| Redis key | 2,194 | learn:experiment 1,418; mem:decision 609; bifrost:* 69; events 23; recall 15; narr 11 |
| Lesson's own key in `source` | 1,627 | |
| URL | 126 | claude.ai 12; loopback 127.0.0.1 on 8787/3080/8941 |
| Python module name | 122 | core 84, arsenal 31, scripts 7 |
| Relative path with no known top-level dir | 118 | |
| Absolute machine path | 255 | See breakdown below |
| Port | 99 | 8787×25, 8788×13, 3080×12, 16379×8 |
| Process name | 79 | es.exe 17, python.exe 16, py.exe 12, claude.exe 8 |
| Worktree path | 13 | Only 3 resolve to a repo path |

Absolute paths, broken down:
- 109 point into E:\AI-Setup. 72 of those are just the repo root.
- 85 are under %USERPROFILE% (AppData 46, .claude 21).
- 46 are other E:\ folders: sibling clones (AI-Setup-Alpha, -Beta, -publish, -cursor), venvs, akashiclabs-site, Spectrum.
- 8 are on the X:\ ramdisk, 2 in the sandbox, 5 elsewhere on C:\.

Where the citations live:
- **`source` field:** it is the lesson's own key in 1,627 of 1,658 lessons, so it carries no location. The 31 real path sources are all `design/vfx-chunks/*.glsl`, and all exist. [S:local]
- **`files_affected`:** non-empty on only 56 lessons (133 items), even though 589 hashes have the field. scene.py says "39 of 1,526". [S:local; S core/coord/scene.py:52]
- **Prose:** about 95% of path citations are in prose, so any resolver must parse prose. [I, from the field counts]
- **Agent memory:** 77% of path citations (3,847 of 5,010) are in decision records. 1,377 of those are in superseded records. [S:local]

## 3. Lane map
Lanes follow docs/library/design/20261029_repository-split-plan.md. "Other" means not named by the plan. Counts are path citations, with records citing in brackets.

| Lane | Citations | Records | Lessons |
|---|---|---|---|
| substrate | 2,055 | 1,106 | 370 |
| other | 1,748 | 1,027 | 307 |
| knowledge | 504 | 385 | 51 |
| runtime state | 252 | 197 | 49 |
| research (in-flight) | 251 | 202 | 30 |
| research root/briefs/drafts | 115 | 93 | 12 |
| creative (arsenal) | 81 | 59 | 27 |
| worktree | 4 | | |

[S:local]

- **Wider view:** counting single-match bare filenames and module names too gives substrate 2,761, other 2,387, knowledge 561, research 315, runtime 272, creative 196, research root 115. [S:local]
- **Arsenal is cited much less than the plan says.** The plan says lessons cite `arsenal/*` "constantly" [S plan §"hard part"]. Measured: arsenal/ is 1.6% of path citations (81), or 196 in the wider view. arsenal/web appears in 31 records; arsenal/keylab is not in the top 30 prefixes. [S:local]
- **What "other" holds:** scripts/ top-level files 577, docs/*.md 429, agent/ 101, fences/ 81, security/ 71, top-level files 67, data/ 62, charters/ 50, design/ 77, .secrets/ 33, .claude/ 24, scripts/hooks 23, scripts/local 22. [S:local]
  - 120 of these citations (84 records) point at creative-cadence content outside arsenal/: design/vfx-*, scripts/vfx*, scripts/piano*. [S:local]
  - By the plan's "what's left IS the substrate", these would land in the substrate repo. [S plan §Execution 4]
- **The plan disagrees with itself on research/.** The table puts research/reviewed in knowledge and research/in-flight in research. Execution step 1 moves all of `research/`. research/briefs and research/drafts are in neither. [S plan]

**Lessons citing more than one lane**
- 824 records cite 2 or more lanes, counting runtime and other (172 lessons, 652 memories). 290 records cite 2 or more of the split lanes (36 lessons). [S:local]
- After the split, following the execution order (other goes to substrate, all of research/ is one repo), 362 records span 2 or more repos (51 lessons, 311 memories). [S:local]
  - Pairs: research+substrate 251, knowledge+substrate 122, knowledge+research 58, arsenal+substrate 21, arsenal+research 15, arsenal+knowledge 3.
  - 638 of 1,893 path-citing records (107 lessons) cite something outside the substrate.
- Lessons citing 3 or more lanes:
  - `search_documented_ideas_indexes_before_raw_transcripts`
  - `the_rill_story_lives_at_the_reduction_and_the_ratification`
  - `a_safety_argument_expires_when_you_build_the_thing_it_assumed_absent`
  - `doc_adopt_infers_research_from_the_path_prefix_then_refuses_it`
  - `the_call_site_is_not_the_wire`
  - `zero_is_not_no_silence_is_not_a_verdict`
  - `fence_write_overwrites_the_slot_so_pieces_are_lost`
  - `gitattributes_pins_eol_because_autocrlf_cannot_be_fixed_in_the_working_tree`

  [S:local]

## 4. Citations that already point at missing paths
- **Scale:** 1,108 of 5,010 path citations (22.1%) are missing on master. That is about 647 distinct paths across 742 records. [S:local]
- **By lane:**

| Lane | Missing | Share |
|---|---|---|
| runtime | 145 of 252 | 57.5% |
| research root | 71 of 115 | |
| knowledge | 185 of 504 | 36.7% |
| other | 554 of 1,748 | 31.7% |
| research | 32 of 251 | |
| substrate | 112 of 2,055 | 5.4% |
| creative | 5 of 81 | |

[S:local]

- **Why they are missing (distinct paths):**

| Reason | Paths | Records |
|---|---|---|
| Never in master history (runtime, branch-only, some extractor errors) | 288 | 315 |
| Deleted in history | 208 | 264 |
| Present on disk but untracked | 130 | 243 |
| Renamed, and git rename detection finds the new path | 19 | 34 |

  - Untracked-but-present examples: `security/acl.json` (58 records), state/*, .secrets/*.
  - 9 of the 19 renames moved files from "other" into substrate (scripts/check_*.py went to scripts/checkers/).

  [S:local]

- **Rot by record month:** June 33.6%, July 24.5%, August 12.2%, September 12.4%, October 8.3%. [S:local]
- **One commit explains a third.** 425cf527a (2026-07-23, "Delete the 643!") deleted 621 files. 365 missing citations (33%) point at 196 of those paths. [S:local; S commit message]
  - The committed `store/docs/legacy_map.json` (103 entries) already resolves 187 of those citations (77 paths), all to atoms that still exist. [S:local]
  - The other 119 paths are research/reviewed 80, research/drafts 17, research/briefs 11, research/ root 10, research/reference 1. They are not in the map because `_deleted_docs` only keeps paths starting with `docs/`. [S core/library/legacy_map.py:48-49]
  - I ran the module's own body-suffix rule, read-only, on those 119. **All 119 matched exactly one atom.** [S:local]
- **Name-based recovery is weak:** only 21 of 517 missing-and-not-on-disk paths have a single-match filename elsewhere. Matching the old slug against atom filenames found 12 of 119. [S:local]

## 5. Most-cited paths (by number of records)
- agent_cli.py 422
- scripts/bifrost_ui.py 70
- core/comm/toolbox.py 61
- security/acl.json 58 (not on master; exists only locally)
- research/reviewed (folder) 55
- AGENTS.md 44
- ai_setup_mcp.py 41
- core/recall/at_action.py 41
- scripts/bifrost_wake.py 35
- core/comm/discord_inbound.py 34
- scripts/bifrost_runner_discord.py 33
- scripts/bifrost_daemon.py 32
- scripts/bifrost_runner_deepseek.py 30
- docs/library (folder) 29
- scripts/deepseek_chat.py 28
- scripts/mirror.py 27
- research/in-flight (folder) 26
- docs/ARCHITECTURE.md 25
- core/comm/bus.py 24
- docs/CONDUCT.md 21
- docs/WISHLIST.md 20
- state/coord/tasks.json 20

[S:local]

Of the top 16, 7 are top-level scripts/ files the plan does not assign. [S:local]

## 6. Which citation format would survive the split
1. **Keep stored citations as plain repo-relative paths.** Resolve the lane when reading, using a versioned table where the longest matching prefix wins.
   - 4,970 of 5,010 path citations are already in that form. [S:local]
   - The lane follows from the first one or two segments for every anchored path, because the plan moves whole directories. [S plan rule 1; I]
   - Every consumer already in the code parses bare paths [S]:
     - recall-at builds its query from path tokens (at_action.py:1788).
     - Domain inference matches "design/vfx" anywhere in the text (domains.py:62-65).
     - `context.target.v1` treats an unprefixed path as the main checkout and uses longest-root matching (target.py:281-311).
   - Rewriting to `arsenal:arsenal/...` would be a canonical-store migration of 5,010 citations in about 1,900 records. It would also freeze today's lane table while 1,748 citations are unassigned and research/ is unresolved. [S:local; I]
2. **A qualified spelling belongs in `context.target.v1` only, never in the store.** If you want one, add it there as a single key, analogous to `work:<name>:<path>`.
   - `REF_KINDS` is closed at eight, and the module says "a resolver may NOT mint new ref kinds". [S target.py:21-24,52]
   - Absolute paths into a separate clone are refused ("a separate clone is a WORLD"). After the split, arsenal/ would be refused without a ratified amendment. [S target.py:306-310]
   - No lane name is a live Redis prefix. But experiment names already embed `research:` (`learn:experiment:research:web:simon_pr_review_coverage_and_integration`), so a `research:` prefix would be ambiguous in prose. [S:local]
3. **Content hash as a witness, not as the identity.** On each new `learn`, stamp a structured `cites` list: {path, the full commit sha at write time, the git blob id for files}.
   - The hottest files change constantly: agent_cli.py 321 commits, docs/physics.md 1,721, state/coord/tasks.json 196. The median cited file has 2 commits; p90 is 9. A hash identity would go stale immediately for exactly the most-cited files. [S:local]
   - 831 path citations are directories, which have no stable hash. [S:local]
   - Once a file is gone, content is the strongest recovery signal: body-suffix matching got 119 of 119, while filename matching got 21 of 517. [S:local]
   - Only 171 of 1,658 lessons carry any sha-like token today. [S:local]
4. **Knowledge lane: cite by `art_` id.** That is already the library's own convention (frontmatter `akashic_id`, `citations: - target: art_...`). [S docs/library atoms]
   - Lessons and memories cite knowledge by path 504 times, but by `art_` id only 84 times (70 records, 7 lessons). [S:local]
   - 72 of 168 docs/library path citations have id-shaped filenames, so they convert mechanically. 4 of the 49 cited ids have no `artifact:*` record. [S:local]
5. **Resolver order, with measured coverage:**
   - Exact path on master: 77.9%.
   - Then the legacy map, after widening the `docs/` filter in legacy_map.py: +365 citations, reaching about 85.2%.
   - Then git rename history: +34 records.
   - Then mark the 130 paths that exist only on this machine (untracked, 243 records) as non-transferable.
   - Report the rest loudly.

   [S:local; I for the ordering]

## 7. Citation facts that matter for classify, export and import
- **Transferable:** repo paths on master, `art_` ids, and lesson/decision ids.
  - Of 509 distinct `learn:experiment:` references in prose, 3 dangle. Of 386 `mem:decision:` references, none dangle. [S:local]
  - So ids are the stable join, and export must keep experiment names and ADR ids exactly as they are. [I]
- **Machine-local:**
  - 146 absolute paths outside the repo.
  - 109 absolute paths into the repo, which can be converted to relative.
  - 99 ports. 16379 here versus 16380 in the sandbox shows they are per-instance; map them through docs/PORTS.md names instead. [I]
  - 79 process names, 13 worktree paths, 252 runtime-state citations.

  [S:local]
- **Sensitive:**
  - Paths into .secrets/ or private/: 41 citations in 36 records (10 lessons).
  - charters/daniel/: 38 citations in 24 records.
  - One memory record, `ADR_0824212136_c1e54879`, matched an API-key-shaped rule twice and a Slack-token-shaped rule once. The shape (an ellipsis after the match, repeated characters) suggests a truncated example, but I did not verify it. Quarantine it before any export. No values were printed. [S:local]
- **Recall gap in one helper:** `_PATHISH` in core/context/relevance_budget.py:43 only recognises .py, .md, .json, .yaml/.yml, .toml and .txt. It misses 51 of 81 creative citations (.js, .glsl, .html, .mjs) and 154 of 252 runtime citations. [S:local]
- **Casing:** 11 of 1,819 distinct cited paths appear in more than one casing, e.g. docs/ARCHITECTURE.md and docs/architecture.md. [S:local]

Files are in <scratch>\:
- cite_census.py, cite_analyze.py, cite_history.py, cite_extra.py, legacy_probe.py
- cite_census.json (the full per-citation data)
- analysis.txt, hist.txt, extra.txt, legacy.txt

---

## Census lane: prior art (verbatim)

The repo already holds most of the parts a classified lesson export/import needs, but nothing classifies a lesson yet. There are five relevant pieces:

- a one-way seeding transport that copies an allowlist and reports what it refused (shipped 2026-10-29),
- a complete map from old file paths to their new document ids,
- a design for attributing records to an operator as a computed view,
- a private-plane leak guard,
- a secret scanner.

Lessons themselves carry no visibility, origin or schema-version field. The 2026-10-27 clearance predicate filters for quality only. It has no privacy or secret term, and the seed code doesn't enforce it. Today's transport is a Redis DUMP/RESTORE copy between twins of this one house, not a portable bundle another Aurora instance could import.

Grading: [S] cited (file or URL), [S:local] measured here today, [I] inference. My own reads were read-only by construction: Redis HGETALL/LRANGE/SCAN/XREVRANGE/EXISTS/TYPE, SQLite opened with mode=ro, one `status --json`. The SQLite write-ahead log still changed during the session. That is probably the harness's recall-at hooks or other seats, but I did not verify it [S:local/I]. LeagueClient.exe was running (the client, not a game), so I kept to bounded reads.

## 1. What a transfer would carry today (measured)

**Real lesson count.**
- `status` reports "learnings 1930", but that counts every `learn:*` key [S: E:\AI-Setup\agent_cli.py:8582].
- The real numbers are 1,686 lesson hashes, of which 1,658 have bodies. The other 28 are ghosts holding only narrative-stamp fields (the 2026-10-03 census also counted 28) [S:local].
- The rest of the 1,930 are 90 category sets, 62 anti_pattern, 60 agent, 28 repeat, plus 4 index keys [S:local].

**Agent memory.**
- 1,214 `mem:` keys (1,212 decision head pointers) [S:local].

**The SQLite mirror is not a complete copy.**
- It holds 1,658 lesson hashes (none of the 28 ghosts) [S:local].
- It holds 1,150 of the 1,214 `mem:` keys. The 64 Redis-only keys are all `mem:decisions:head` pointers [S:local].
- Any export has to say which store it reads from.

**Lesson schema.** These fields are present on real records:
- experiment_name, success, timestamp, confidence, category, agent_id, source, what_tried, recommendation, actual
- narrative_chapter / narrative_track (1,474)
- domain (991), related_to (395)
- under 4%: expected (107), files_affected (56), anti_pattern (56), root_cause (55), metrics (32) [S:local]

There is no visibility, plane, origin, schema_version or supersedes field on any lesson [S:local]. Atoms do have these: 1,418 atom rows, visibility fleet 1,408 / local 10, schema_version stamped on 383 [S:local].

**Path citations live in prose, not in structure.**
- 548 of 1,686 lessons (32.5%) cite a repo path somewhere. Only 56 have files_affected [S:local].
- That is 538 distinct paths, of which 438 resolve on disk today [S:local].
- Instances pointing into the split plan's non-substrate lanes: arsenal 34, knowledge 48, research 46 [S:local]. My regex can catch some prose false positives [I].

**Secret scan.** Nine shaped-credential rules from check_secrets plus a webhook rule and a JWT-shape rule ran over all 1,686 lessons: 0 hits [S:local]. This is a pattern floor, not proof of absence [S: E:\AI-Setup\scripts\checkers\check_secrets.py header].

**Identity and machine strings (counts only).**
- 195 of 1,658 bodied lessons match at least one identity rule.
- The operator's name appears in 161, an absolute repo path in 24, the home path in 14, the machine name in 3, an email shape in 2 [S:local].
- The 2026-09-01 sanitize run touched 136 lessons [S: research\in-flight\seed-sanitize-2026-09-01\pipeline-summary.json]. The workload has grown since [I].

**Authorship.** 59 distinct agent_ids, including split identities such as codex vs codex_root [S:local]. An importer needs an alias map.

**Keys.** Lesson keys are free-form, mutable prose. The census found 704 distinct first tokens and no namespace or date index [S: E:\AI-Setup\research\reviewed\knowledge-plane-census-2026-10-03.md:22-28].

## 2. In-house prior art

**a. The seeding transport (most direct prior art; not in the lane's list)**
Files: core\world_seed.py, scripts\seed_world.py, scripts\bootstrap_world.py, and docs\library\design\20261027_clearance-predicate-and-self-validation-spec.md.

What it gets right:
- Seeding is downward only. A twin's lessons "is a claim", and promoting one upward means re-checking it or filing it as a rumour (grounded:false) [S: world_seed.py:8-15, 118-125]. This is the right semantics for any import from a peer.
- It copies a knowledge allowlist (learn, mem, narr, artifact, knowledge_map, residents, lookback). `recall:` and `events:` are opt-in, each with a stated reason. `bifrost:` is never copied [S: world_seed.py:51-73].
- The report leads with what it refused (the "Dawe test") [S: world_seed.py:36-39].
- Each seeded lesson gets a sha256 over its content-bearing fields, canonicalised, with lifecycle state excluded. The inventory rides in the manifest, not on the lessons [S: world_seed.py:224-300].

Gaps:
- DUMP/RESTORE is Redis-internal. The docs say it is "opaque and non-standard" and "different Redis versions with incompatible RDB formats will refuse to process the serialized value" [S: https://redis.io/docs/latest/commands/dump/].
- Classification is by key prefix only. All of `mem:` rides, and that is the plane where the private-note leak happened [S: core\trust\private_plane.py:9-23].
- The clearance predicate ("NOT benched AND has domain signal") [S: clearance spec:53-64] has no privacy, secret or identity term.
- bootstrap_world says the predicate is "enforced at seed time" [S: bootstrap_world.py:38-41]. But seed_world copies whole prefixes, and neither seed file contains a bench, clearance or predicate check [S:local, grep].
- The inventory is computed after the copy [S: seed_world.py:64 then :74]. A lesson written between the two steps would mismatch [I].
- The world_seed manifest docstring itself says provenance is corpus-level only: "a key copied out of here by hand is indistinguishable from a native one" [S: world_seed.py:157-183].
- The operator's rulings to honour:
  - Q1: a graduated lesson ships paired with the hook or check that enforces it.
  - Q2: no permanent "seeded" stamp on lessons; a manifest join instead.
  - `recall:` counters never seed.
  [S: clearance spec:70-115]

**b. The sanitize pipeline of 2026-09-01 (untracked)**
File: research\in-flight\seed-sanitize-2026-09-01\seed_pipeline.py.
- A working prototype of a stranger-facing export. It exports the corpus, applies regex identity and locality transforms, sets origin=seed and seed_version, loads into scratch db 13, and re-runs six pre-registered recall queries [S: that file].
- Result: 1,294 exported, 66 stubs excluded, 1,228 seed records, 0 residual identity records. Top-10 recall overlap was 59/60 and same-rank 57/60 [S: pipeline-summary.json]. The pre-registered recall-preservation probe is reusable as the acceptance test for any transform [I].
- It keeps its own secret list (4 key shapes) separate from check_secrets' 9 patterns [S:local]. That is the divergence the lesson redaction_pattern_is_a_claim_about_a_format_someone_else_owns warns about [S: that lesson].
- **Hazard:** diff-sample.md (20 lines carrying the pre-transform name) and seed_pipeline.py (literal identity regexes) sit untracked and not gitignored inside research/in-flight/, which is a tracked lane [S:local: git status `??`, check-ignore negative]. The private-plane guard would not catch the name, because "daniil" is in its generic-token drop list [S: private_plane.py:56-58]. A broad `git add` would commit them [I].

**c. Operator epochs**
File: docs\library\design\20260901_operator-epochs-attribution-as-resolved_a3e0c7.md.
- Attribution is a lookup in an epoch registry by record timestamp, and origin=seed always resolves to epoch 0. Quoted speech stays verbatim, and an `epoch:seed` vs `epoch:native` tag supports "what did this house learn" views [S: lines 33-57].
- It cites a corpus-scale replication: attribution does not move recall (59/60) [S: line 56].
- It describes an installer step that does not exist in code yet. Only bootstrap_world mentions seed provenance [S:local, grep].

**d. Identity split and private plane**
- Measured result: changing identity strings left knowledge-map relevance within 0.001 [S: lesson identity_strings_are_not_load_bearing_for_retrieval_measured]. Its rule: split at identity, find which retrieval path surfaces the record type, and pre-register the scores.
- core\trust\private_plane.py derives leak markers from the files actually in private/ rather than a hand-kept list [S:25-33]. It treats "existence metadata is a leak" [S:17-23] and holds that derived records (commit messages, lessons, PR bodies) do not inherit their sources' visibility [S:185-198]. A report that finds nothing is distinguished from a guard that never ran [S:215-226].
- It is only the backstop half. Its docstring lists the unbuilt write-path design: a visibility stamp at mint, CAS that hashes the plane with the body, cross-plane supersession as a migration event, private as an overlay with public tombstones as authoritative subtraction, and backup of both [S:35-42].
- The 2026-08-15 opening position proposes inverting "denylist over an open plane" into an "allowlist over a closed one". Unclassified records refuse, and pseudonymous handles are the only identity that crosses [S: research\in-flight\private-plane-opening-position-2026-08-15.md:58-88].
- No lesson-level visibility exists. core/trust has none, and learning_store's "visibility" means recall-surface visibility [S:local, grep].

**e. Security schema**
- security\acl.json is schema v1 with 14 grants (1 super_admin, 5 admin, 8 member). Only 2 have expires_at, and unknown agents are quarantined [S:local].
- Capabilities include kb.recall and kb.learn. There is no kb.export or kb.import, and no classification-scoped read [S:local]. Import authority would be a new, time-boxed capability [I].

**f. Library schema and typed headers**
File: docs\LIBRARY.md.
- One facet per path (type), and everything else in headers: never re-shelve to re-categorize [S:11-14].
- A capped category roster of 24 [S:84-100].
- Atoms are schema-versioned, absent reads as 1, and readers refuse loudly on newer versions [S:131-134]. Tools resolve forward to the current head of a supersession chain [S:138-140].
- This is the versioning discipline lessons lack.
- Caveat: atom body_sha is 12 hex characters, 48 bits [S:local]. That is fine inside one house but weak as a cross-instance content address [I].

**g. Lifecycle and supersession engine**
- core\codex\lifecycle.py has bi-temporal valid_from / valid_to / recorded_at fields. Regenerate-in-place is idempotent via version_hash, and supersede closes valid_to, adds replaces / is_version_of edges and never deletes [S:8-15, 59-83].
- core\primitives\supersession.py is field-based and adoptable incrementally [S:10-16].
- Lessons use neither. Re-recording a name updates the hash in place [S: E:\AI-Setup\AGENTS.md, learn section].
- The ledger's `learning` events carry tried, result, category and success, but no recommendation (2 events sampled) [S:local]. `events:raw` is a ring capped at 100,000 entries [S: census:230]. There is no full version history to export [S:local].

**h. Markdown as projection (T101)**
- core\library\projection.py: the atom is the truth and the markdown is disposable. YAML frontmatter that Obsidian Bases reads natively, plus akashic_id and akashic_sha, so drift is detectable [S:1-12].
- This is the right model for human-readable exports [I].
- Its own docstring cites docs/super-wiki-experience-design-2026-07.md, which no longer exists [S:local]. The legacy map does resolve it [S:local].

**i. Recall as a network**
- Laws worth borrowing: immutability makes caching correct, and narrow, versioned envelopes [S: docs\library\report\20260712_recall-networking-reconciliation-the-kno_6df124.md].
- The lane brief's glob `research/reviewed/*recall-networking*` matched 0 files [S:local]. Commit 425cf527a (2026-07-23) deleted 621 originals into atoms [S:local].
- The reconciliation's four body path citations are all dead. Its three frontmatter art_id citations all resolve [S:local]. This is a clean natural experiment: id citations survived the move, path citations didn't.

**j. Citation resolver prototype (already exists)**
- store\docs\migration_map.json maps 664 old paths to art_ids. It covers 621/621 paths deleted in 425cf527a, and all 662 targets are live atoms [S:local]. Its only reader is its writer, scripts\enrich_corpus.py [S:local, grep].
- core\library\legacy_map.py covers top-level `docs/` only (103 entries) [S:49, local]. It builds itself by proof: a byte-exact suffix match with a 200-character floor, and UNMATCHED entries are recorded loudly [S:1-21]. lookback reads it.
- On the lesson corpus: 100 distinct dead path citations across 99 lessons. migration_map resolves 22. The other 78 are mostly code moves (core 18, tests 12, scripts 10, agent 8, state 8) that no map covers [S:local].

**k. Secrets**
- The lesson archaeology_republishes_whatever_the_past_leaked says: scan at adopt time, redact by pattern (never by literal in argv), and rewrite unpushed history rather than committing a removal [S: that lesson].
- Current wiring is unchanged on that point:
  - check_secrets runs at pre-push [S: scripts\githooks\pre-push:81].
  - The private-plane guard runs at pre-commit [S: scripts\githooks\pre_commit.py:469-491].
  - The learn door has no secret or identity scan: learning_store has 0 "secret" hits, and cmd_learn only does a near-duplicate scan [S:local].
- Redis lessons therefore never pass any egress gate.
- Pattern lists live in at least three places: check_secrets, discord_bridge.py:117, and seed_pipeline [S:local].
- check_secrets' two design rules are worth keeping: the finder must not become the leak (mask at capture), and every suppression carries its reason [S:12-25].

**l. Backup and recovery**
- scripts\ops\snapshot_knowledge.py takes a whole-house dump: redis_db0.json is 209 MB [S:local].
- The newest snapshot (2026-10-14) is labelled a laptop travel seed. Its manifest has only a timestamp, note and key count: no hashes, no classification [S:local]. Its learnings.jsonl is a stale 6-row file from June [S:local].
- So cross-machine transfer today is an unclassified clone of the private brain [S:local/I].
- core\coord\world_savepoint.py has the right law, "BOTH PLANES OR NEITHER": the memory snapshot is bound to a git sha [S: header]. A bundle should pin the substrate schema version it was cut from [I].

**m. Related lessons (all [S], by id)**
- consent_does_not_transfer_across_subjects_in_a_shared_bundle: enumerate the subjects; IN / GATED / HOME; silence means HOLD.
- redaction_scoped_to_the_tracked_tree_leaves_the_store_reloading_it: redact the source plane first, or generators refill the projections.
- authored_vs_derived_decides_the_plane_not_the_organ
- token_redaction_cannot_clean_a_dossier: clause-level redaction for passages about people.
- a_clone_has_no_secrets_so_every_credentialed_door_is_closed_in_a_twin
- continuity_cutover_freeze_and_hash: freeze, hash, migrate, byte-identical readback.
- absolute_threshold_on_a_raw_relevance_score_is_not_portable: imports shift the score distribution under the fixed recall floor of 0.20.
- imported_peer_procedure_may_name_a_nonlocal_bridge_helper
- an_empty_corpus_is_paid_for_in_tokens_and_it_presents_as_scatter: why seeding matters at all.

**n. A real cross-instance precedent**
- A peer instance (Mnemosyne) ran a declared 11-item "Aurora Transfer" from this house.
- The archaeology found commit dates gave the opposite answer from file mtimes and self-dated manifests. A self-attested created_at inside the artifact was the strongest evidence [S: E:\AI-Setup\research\reviewed\mnemosyne-provenance-archaeology-2026-10-03.md:12-16, "Other borrowings"].
- Lesson: provenance must be carried in the artifact; it can't be inferred from transport timestamps [I].

## 3. Outside prior art: what to borrow, what to avoid

- **W3C PROV-O (Recommendation, 2013-04-30)** [S: https://www.w3.org/TR/prov-o/]
  - Borrow the vocabulary of Entity / Activity / Agent, wasDerivedFrom, wasRevisionOf, wasQuotedFrom, wasAttributedTo, actedOnBehalfOf, generatedAtTime, invalidatedAtTime. It maps directly onto lesson, learn-act and seat, the bi-temporal fields, and the "seat on behalf of the operator" relation [I].
  - Avoid full RDF/JSON-LD as the wire format. Field names are enough [I].

- **STIX 2.1 with TLP 2.0** [S: https://docs.oasis-open.org/cti/stix/v2.1/os/stix-v2.1-os.html §3.6, §7.2, §8; https://www.first.org/tlp/]
  - This is the closest analogue: cross-organisation knowledge sharing with classification.
  - Borrow per-object marking references, and versions where id + modified identify a version and the consumer "SHOULD use the most recent version". Borrow `revoked`, `created_by_ref` and a 0–100 confidence.
  - Borrow TLP's labels: RED (named recipients only), AMBER+STRICT (organisation only), AMBER, GREEN (community), CLEAR (public), effective August 2022. Wider sharing "must obtain explicit permission from the source".
  - Markings are declared per object (my read of §7.2). That matches the house law that derived records don't inherit visibility.
  - Note: a STIX Bundle has "no versioning semantics". Version the records, not the bundle.

- **Content addressing** [S: https://docs.ipfs.tech/concepts/content-addressing/; https://github.com/in-toto/attestation/blob/main/spec/v1/statement.md]
  - Borrow self-describing digests (algorithm named inside the id, as multihash does) and in-toto's split between subject (name + digest) and predicate (the claim). In-toto matches subjects "purely by digest".
  - A lesson's content hash is the subject; classification, provenance and enforcement pairing are predicates [I].

- **RFC 8785 JCS (Informational, 2020)** [S: https://www.rfc-editor.org/rfc/rfc8785]
  - Borrow canonical JSON for hashing across implementations.
  - world_seed's `json.dumps(sort_keys)` is close, but it is not JCS: ASCII escaping by default, Python number formatting, code-point key order. Fine inside one house; a second implementation would disagree [I].

- **BagIt (RFC 8493, 2018)** [S: https://www.rfc-editor.org/rfc/rfc8493]
  - Borrow its packaging: a declaration file, payload, `manifest-sha256`, a tag manifest, bag-info metadata, and the "complete" vs "valid" distinction.
  - That distinction is the same "zero is not no" discipline this house already enforces.

- **git bundle** [S: https://git-scm.com/docs/git-bundle]
  - Borrow incremental bundles with declared prerequisites and a verify step. Example: "generation seed-v2 requires seed-v1".

- **Signing** [S: https://jedisct1.github.io/minisign/; https://docs.sigstore.dev/cosign/signing/signing_with_blobs/]
  - Borrow minisign's Ed25519 with a signed "trusted comment" that can carry generation, source instance and schema to prevent downgrades.
  - Zero-install equivalents exist here: `ssh-keygen -Y` is present, and Python `cryptography` 46.0.7 has Ed25519 [S:local].
  - Avoid keyless Sigstore for this house. It records "your identity … publicly in Rekor", which would publish the operator's identity [S].

- **JSON Lines and SchemaVer** [S: https://jsonlines.org/; https://docs.snowplow.io/docs/api-reference/iglu/common-architecture/schemaver/]
  - Borrow UTF-8, one JSON value per line, `.jsonl`.
  - Borrow MODEL-REVISION-ADDITION versioning: ADDITION is compatible with all history, MODEL is breaking. Combine it with LIBRARY.md's rule that readers refuse loudly on a newer version.

- **CRDT-style merging** [S: https://automerge.org/docs/reference/documents/conflicts/; https://www.w3.org/TR/activitystreams-vocabulary/#dfn-tombstone]
  - Borrow Automerge's deterministic winner with losers kept in a conflicts set ("the other values are not lost").
  - Borrow ActivityStreams Tombstone (formerType, deleted) for retractions, which matches private_plane's "public tombstones are authoritative subtraction".
  - Avoid last-writer-wins on same-name / different-hash imports. That is what `learn` re-record does today [I].

- **Personal knowledge tools** [S: https://obsidian.md/help/properties; https://retorque.re/zotero-better-bibtex/citing/; https://github.com/logseq/logseq/issues/7362]
  - Obsidian: YAML properties (which the projections already use).
  - Better BibTeX: deterministic, pinnable, collision-suffixed citation keys, "conservative about citation key changes". This is the model for stable lesson ids that survive renames.
  - Logseq: block refs work only if `id::` is persisted in the file. Issue 7362 shows references lost when the id lived only in the database. Citation ids must live in the record, not only in the store's index [I].

- **Agent-memory formats** [S: https://github.com/letta-ai/agent-file; https://docs.mem0.ai/platform/features/memory-export]
  - Borrow Letta's rule: "secrets are set to null" on export.
  - Avoid Letta's default of bundling complete message history; transcripts are where personal material lives.
  - Avoid Mem0-style LLM-processed export as the canonical path. It paraphrases, which is exactly how private material escapes [S: private_plane.py:194-198].

- **Secret scanners** [S: https://github.com/trufflesecurity/trufflehog]
  - Borrow the three result states (verified / unverified / unknown) and multi-source scanning.
  - Avoid live verification ("log in to confirm"). It sends the secret to an issuer and breaks "the finder must not become the leak" [I].

## 4. Synthesis: a shape to take into the design round [I]

1. **Unit.** A versioned JSONL bundle in BagIt style.
   - Manifest: source instance id, generation, git sha and schema version (savepoint law), JCS sha256 per record, prerequisites, refusal report (Dawe test).
   - Signed with an Ed25519 trusted comment.
   - Never Redis DUMP, and never `recall:` counters.
2. **Classification.** An allowlist over a closed plane, with TLP-shaped tiers:
   - private (never leaves; AGENTS.md placement gate)
   - house (this instance and its twins; today's world_seed)
   - peer (named Aurora instances, with consent per subject)
   - public (clearance predicate plus secret scan plus identity transform plus the recall-preservation probe)
   - Unclassified stays home.
   - Classification is a separate axis from the provenance stamp Q2 rejected. Whether it can be a field on the lesson is Daniel's call.
3. **Citation resolver.** At export, lift prose paths into structured citations {kind: path / art / lesson / sha, value, lane}. Resolve in this order:
   1. exact path
   2. migration_map
   3. legacy_map
   4. git rename history
   5. otherwise UNRESOLVED, loudly
   - Cite atoms by art_id wherever one exists.
4. **Import.** Arrives as a claim:
   - origin=import, epoch-resolved attribution, grounded:false until re-checked
   - dedup by content hash
   - same id with a different hash becomes a kept conflict, not an overwrite
   - retractions as tombstones
   - a time-boxed kb.import grant
5. **One shared door module** for secret and identity patterns, used by learn, adopt, export and the git hooks, with one pinned example per vendor.

## 5. Open items and hazards for Daniel

- **Q2 conflict.** A per-record classification field may conflict with his Q2 ruling that the lesson stays clean. I am flagging it, not deciding it.
- **mem: notes.** Whether decision notes may ride at all, given that is where the private-note incident happened.
- **Repo hazard.** The untracked, not-ignored sanitize artifacts in research\in-flight\seed-sanitize-2026-09-01\ (§2b).
- **Recorded claim not in code.** The clearance predicate is documented as enforced at seed time but is not implemented (§2a).
- **Misleading count.** The `status` lesson count is misleading (1,930 vs 1,686 hashes / 1,658 bodies), and the mirror is missing 64 decision pointers (§1).

Scratch scripts (all read-only), in <scratch>\:
- ro_get.py
- ro_census.py
- ro_resolve.py
- ro_ident.py

Sources:
- https://www.w3.org/TR/prov-o/
- https://docs.oasis-open.org/cti/stix/v2.1/os/stix-v2.1-os.html
- https://www.first.org/tlp/
- https://docs.ipfs.tech/concepts/content-addressing/
- https://github.com/in-toto/attestation/blob/main/spec/v1/statement.md
- https://www.rfc-editor.org/rfc/rfc8785
- https://www.rfc-editor.org/rfc/rfc8493
- https://git-scm.com/docs/git-bundle
- https://jedisct1.github.io/minisign/
- https://docs.sigstore.dev/cosign/signing/signing_with_blobs/
- https://jsonlines.org/
- https://docs.snowplow.io/docs/api-reference/iglu/common-architecture/schemaver/
- https://snowplow.io/blog/introducing-schemaver-for-semantic-versioning-of-schemas
- https://automerge.org/docs/reference/documents/conflicts/
- https://www.w3.org/TR/activitystreams-vocabulary/#dfn-tombstone
- https://obsidian.md/help/properties
- https://retorque.re/zotero-better-bibtex/citing/
- https://github.com/logseq/logseq/issues/7362
- https://github.com/letta-ai/agent-file
- https://docs.mem0.ai/platform/features/memory-export
- https://github.com/trufflesecurity/trufflehog
- https://redis.io/docs/latest/commands/dump/
