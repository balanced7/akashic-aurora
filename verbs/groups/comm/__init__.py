"""verbs.groups.comm -- the verbs that inspect ONE message on the bus.

`bus read <id>` is the exception path behind every clipped preview: given a message id (from a
WOKE BY line, a sync, a promoted record), it prints the whole packet and where it came from.
Read-only by construction -- there is no cursor here to advance.
"""
