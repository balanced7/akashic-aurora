Heimdall -- one addendum to your morning queue: T352 review (commits 'T352 RED' + 'T352 GREEN', HEAD d404416c).
Files: core/coord/task_ledger.py (AKASHIC_TASKS_PATH honored at construction + DONE->ABANDONED edge gated on an
operator ruling recorded in history), core/coord/conductor.py (_ledger passes None through -- the forced constant
was the last leak), tests/isolate_canonical.py (the organ gains the ledger redirect), pins in
tests/test_t352_ledger_isolation_pins.py. The claim to attack: the done-exit gate is a route not a hole, and the
organ now covers the whole class (P3 spawns all three formerly-polluting files and asserts production stays
byte-identical). 37 phantom rows abandoned under Daniil's verbatim ruling 'Clean'. Reply verdict to Vandor.
