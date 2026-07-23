Status: current
Type: reference · Arc: library-schema / reader-face · Seats: claude · Date: 2026-07-23

# Zone paragraphs — the one-paragraph purpose each generated README opens with

(Consumed by gen_library's zone-README emitter. Tone: plain, a stranger's first read.)

**docs/** — The governing layer: contracts, laws, designs, plans, and maps that are
CURRENT unless their header says otherwise. Start at LIBRARY.md (how filing works),
SHELVES.md (everything by type), ARCHITECTURE.md (the system skeleton).

**research/** — The evidence plane. Nothing here governs; everything here is the record
of how decisions were earned. Three rooms: reviewed/ (reports and reconciliations that
passed a gate), drafts/ (working halves, positions, openings — deliberately unpolished),
briefs/ (charters and asks handed between seats).

**research/reviewed/** — Gate-passed evidence: fence reports, reconciliations, frontier
reports, captured verbatim records. If a decision cites its receipts, they live here.

**research/drafts/** — Working material: blind halves, counter-positions, openings,
want-charters. Unpolished by design — the value is provenance, not prose.

**research/briefs/** — Charters, asks, and briefs passed between seats. Each is
addressed (From/To in the header) and dated; they read as the fleet's correspondence.

**chronicles/** — The narrative spine: session reflections, night plans, morning
packages. Read newest-first and you have the story so far in the seats' own voices.

**charters/** — The black book: per-seat charter records — demonstrated abilities and
the current stretch, one folder per seat.

**design/** — The design plane for every rendered surface: specs, the design corpus,
captured reference indexes (OneUI/HIG assets are gitignored for copyright; their
INDEX.md files are tracked so captures are reproducible).

**fences/** — Fence workspaces (one folder per fenced build): the brief, the blind
halves, the reconciliation, and the machine verdict for that build. These folders are
cited by reports in research/reviewed/ — they are receipts, not scratch.

**docs/_archive/** — The L3 shelf: superseded and fossil documents, kept whole because
paths are citations. Nothing here is current; everything here is why something current
says what it says.
