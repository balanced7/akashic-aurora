"""verbs.groups -- one package per CLUSTER of the CLI surface.

A cluster is a ROW of the dispatch table (the verbs a seat reaches for together), not a file type
and not a layer. `coord` holds the read-only scene verbs (`orient`, `shadow`, `ground`, `glance`)
and the read-only pre-flight (`scout`); `awareness` the snapshot; `research` the corpus walkers;
`meters` the instruments. Growth is by adding a cluster, not by growing a file.
"""
