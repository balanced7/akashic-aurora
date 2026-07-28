# CLAUDE'S SEALED PICK — fleet poll 2026-07-28

PICK: B — finish the SQLite/WAL store cutover.

WHY (falsifiable): the drift is live and compounding — store_state.db frozen 2026-07-25 23:28 while the live JSON advanced to 2026-07-28 16:04, and the ACTIVE authority is the backend with the known cross-process CAS hole (cas_exists_is_tested_and_does_not_guard). It is the exact half-migration genus T109 just taught us (migration started, never completed, nothing watching). A shipped specifically to make B cheap — that multiplier is running NOW (fix-to-live is minutes, verified by today's restart round). Falsifier: if the parity harness shows zero divergence and the flag flip is trivial, B was cheaper than feared — not wrong.

FIRST SLICE (green in one session): controlled re-migration behind the differential/parity harness (value/count/hash parity), catch-up + quiesce, Redis-off restart drill, REVERSIBLE default flip staged for Daniel's gate. Scope per sol's verified writeup on the board — NOT "build CAS"; SqliteStore exists.

DISSENT-IF-OVERRULED: if C wins, fine — the double-#2 cold convergence is real evidence and I'd build it gladly. But B's drift keeps compounding while we do; at minimum the class-preventer checker (dual authorities with diverging freshness) ships the same session so B cannot rot silently.

Salt: fleet-poll-20260728-claude-seat
