---
akashic_id: art_20260723_charter-per-zone-generated-readme-md-gen_474b95
akashic_sha: 6112badaccd9
status: current
type: brief
date: 2026-07-23
title: "CHARTER — per-zone generated README.md (gen_library extension, your organ)"
gist: "# CHARTER — per-zone generated README.md (gen_library extension, your organ) **Daniel's steer (verbatim, this morning):** \"all the .md's are"
tenant: solo
visibility: fleet
seats: []
category: [library, conducting, optics]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260723_zone-paragraphs-the-one-paragraph-purpos_52c17b
    rel: cites
created: "2026-07-23T09:04:44"
updated: "2026-07-23T21:42:08"
---
<!-- GENERATED PROJECTION of art_20260723_charter-per-zone-generated-readme-md-gen_474b95 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# CHARTER — per-zone generated README.md (gen_library extension, your organ)

# CHARTER — per-zone generated README.md (gen_library extension, your organ)

**Daniel's steer (verbatim, this morning):** "all the .md's are sure to be come confusing,
there are so many of them, the file name does not have timestamps or intuitively explain
what is inside, we dont't know the category of them or the context... how would we
elegantly eliminate the documentation and .md sprawl without losing the value or utility
of the files? ... I want our stuff to be structured, right now it looks too chaotic,
random and unlinked to me"

**Intent.** The library law is ratified and SHELVES.md exists — but the BROWSING face
(GitHub folder views) still shows bare file lists. GitHub auto-renders README.md per
directory: project the library INTO the face. You own gen_library.py (D2) — this is its
natural v2.

**Done-looks-like:** `py scripts/gen_library.py` (same one command) additionally emits a
README.md into each zone: docs/, research/, research/reviewed/, research/drafts/,
research/briefs/, chronicles/, charters/, design/, fences/, docs/_archive/. Each README:
1. Opens with the zone's one-paragraph purpose (claude supplies the texts — consume them
   from research/briefs/claude-zone-paragraphs-2026-07-23.md when it lands, or stub until).
2. Then a generated table, NEWEST FIRST: file (relative link) · Type · Arc · Date ·
   Status dot · first-heading-or-description one-liner from the header block.
3. CURRENT files in the main table; superseded/fossil collapse into a <details> section
   at the bottom (value kept, face decluttered).
4. Footer: generated-by line + never-hand-edit + pointer to docs/LIBRARY.md.
Idempotent, byte-stable when nothing changed (clean diffs). Unparseable-header files
land in an "unclassified" tail section — visible, never hidden.

**Real constraints:** zero renames, zero moves (cited-path law); READMEs are additive.
Commit by name via mirror. Rule-8 mojibake guard applies to what you generate. Pins:
RED-first, your lane namespace.

**Fence:** claude sighted-pass on the rendered result (GitHub-flavored markdown quirks
are a [T] surface — tables with long paths need testing, not assuming).

One question, calibrated: SHELVES.md groups by TYPE fleet-wide; zone READMEs group by
FOLDER. Same generator, two projections — do you see a third projection worth emitting
for free while you are in there (per-ARC index?), or is two enough for v1? Your call;
building only what earns its diff is also an answer.

— claude
