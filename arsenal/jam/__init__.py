"""arsenal.jam: the jam space on Daniel's piano page (cards, runs, the tempo map).

Build spec: research/in-flight/piano-jam-2026-09-14/jam-spec.md. The contracts here were frozen in phase J0 and change
only through the conductor, with a note to every running phase (jam-spec 13.1 rule 3):

  schemas.py    validators for the card, the resolved def, the run, its event lines and the ack (section 4)
  tempomap.py   bar <-> epoch <-> pass <-> slot, the landing rule and the hand-off time (sections 9.1, 9.3, 9.4);
                its twin is arsenal/web/piano/tempomap.js, and both run tests/fixtures/jam/tempomap_cases.json

Later phases add cards.py, resolve.py, runs.py, align.py and cli.py (J3) and seed/deck-v1.json (J6).
"""

CARD_API = "arsenal.jam.card/v0"
DEF_API = "arsenal.jam.def/v0"
RUN_API = "arsenal.jam.run/v0"
DECK_API = "arsenal.jam.deck/v0"
SEED_API = "arsenal.jam.seed/v0"
SEED_MOMENTS_API = "arsenal.jam.seed.moments/v0"
REPORT_API = "arsenal.jam.report/v0"      # v2 (section 4.5), named now so v1 leaves room for it
RIFF_API = "arsenal.practice.riff/v0"     # practice riff's output (section 11.6)
TEMPOMAP_CASES_API = "arsenal.jam.tempomap.cases/v0"

API = {
    "card": CARD_API,
    "def": DEF_API,
    "run": RUN_API,
    "deck": DECK_API,
    "seed": SEED_API,
    "seed_moments": SEED_MOMENTS_API,
    "report": REPORT_API,
    "riff": RIFF_API,
    "tempomap_cases": TEMPOMAP_CASES_API,
}
