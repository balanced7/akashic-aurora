"""core/provenance -- what the house BELIEVES happened, reconciled against what the disk shows.

The Aurora planes (git, the ledger, notes, promoted lessons) are what `delta` (T052) reads. They
are authoritative for work that LANDED. This package covers the gap underneath them: files that
moved on disk that no plane recorded, which is where work is lost rather than reviewed.

One module today: :mod:`core.provenance.delta`, the disk plane of the delta door.
"""
