status: template
# TASK: [SWEEP] What changed at <sources> since <last-swept date>, relevant to <SQn>?
feeds: SQn (<the standing question, verbatim from research/watchlist.md>)
seeds:
- <the source URLs from the watchlist rows being swept>
notes: DELTA sweep, not a survey -- report only what is NEW since <last-swept date>
  (releases, papers, benchmark rows, capability changes). Use websearch.py to find
  changes the seed pages don't surface (e.g. "<source> <capability> 2026"). For each
  delta: one finding + why it matters to <SQn> + a "hypothesis:" line if it suggests
  something we should test, or "no action" if it's context only. Empty deltas are a
  VALID result ("nothing new" = one line, high confidence) -- never pad. "Done" = the
  reviewer can update watchlist.md last-swept and adjudicate each hypothesis in <5 min.
