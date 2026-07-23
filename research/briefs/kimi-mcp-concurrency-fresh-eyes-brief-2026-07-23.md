# Brief — kimi fresh-eyes on the MCP-concurrency round

Status: current (awaiting kimi's next seating)
Type: brief · Arc: interface / System-5 door · Seats: kimi (fresh-eyes) · Date: 2026-07-23

**Daniel's charter (verbatim, two levels up):** "Can we modify our mcp to allow concurrent
calls? do we need to swap it out I want everyone's thoughts on this. both your ergonomics
and the mcp concurrancy"

**Intent (why you):** the opening claims a confirmed mechanism and a fix design. Your
audit genus — "asserts the guard rather than having it" — is the exact risk in both. We
want the opening to survive a stranger who checks the ledgers, before Daniel rules.

**Read:** research/drafts/mcp-concurrency-and-boot-ergonomics-opening-claude-2026-07-23.md
(the opening) · tests/test_mcp_concurrent_calls.py (the fence) · ai_setup_mcp.py (the door).
deepseek's counter will exist by the time you seat — per the Q6 ruling in your stance
counter file (2026-07-23): the blind applies during counter-phases; if this round's
counter-phase is still open when you write, stay unread on deepseek's counter and say so.

**Asks (in order):**
1. RUN the fence (`py -m pytest tests/test_mcp_concurrent_calls.py -q --timeout=120 -s`).
   Do the receipts reproduce (C1 green; C2/C3 xfail; fast waits behind slow)?
2. Verify the two SDK claims against the installed source, cite lines: (a) task-per-message
   at the session layer; (b) no to_thread in the FastMCP tools dispatch path (1.27.0).
3. Hunt asserted-guards in the O1 design: the "redis-py pools are thread-safe" claim; the
   read/write verb tier assignment (is any READ verb secretly consuming/writing?); the
   thread-local stdout proxy (what escapes it — C-level writes, child processes?).
4. Stranger-test the boot-ergonomics census F1–F9: does each carry a receipt a stranger
   can check? What did living-through-it blind the author to?
5. One page, red first. File to research/reviewed/ (round counters are reports — W58
   precedent pending the G11 ruling; note the tension rather than resolving it).
6. WIDENED (Daniel, 2026-07-23, verbatim): "how many of our concurrent agents and wake and
   all the rest can be solved by us leveraging the multithreaded -ness and concurrency in
   the MCP? Have everyone think on what we can improve by improving our setup and the
   interface with mcp" — read the addendum
   (research/drafts/mcp-leverage-map-addendum-claude-2026-07-23.md) and stranger-test its
   leverage map L2–L6: every "dies/solved" claim either carries a receipt or gets
   downgraded by you to "should". The two you should hit hardest: the L3 lease-binding
   claim and A1's "harness can cancel post-O1".

**Constraints (real ones only):** verify against code and ledgers, not the register; your
disclosure discipline (lead with the lens) as before; wishes for any friction you feel.
