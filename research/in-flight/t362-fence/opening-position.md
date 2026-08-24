# T362 fence — opening position (Vandor, 2026-08-18)

DANIIL'S COMMISSION, verbatim: "How can we simplify this without losing fidelity? Are there any
terms or data types or edges that we need to standardize so that more core systems are
cross-functional?" — and on the fence itself: "This definitely looks like the type of question
that deserves the full house treatment!"

EVIDENCE BASE: research/in-flight/address-dialects-census-2026-08-18.md (adopted; eleven machine
dialects, five fracture receipts in 36h) + Heimdall's name-collision scan (bus 1786986442669-0,
the human layer).

## The position

DON'T reduce the number of spellings. Reduce the number of rules. Each form encodes something
real (pid-suffix = process, sid8 = session, blob: = which store); we do not own every producer
(uuid = harness, stream id = Redis). What fractured is that resolution rules live in individual
organs' heads. Eleven forms is fine. Eleven private rulebooks is the disease.

THREE LAWS + ONE DOCUMENT + ONE DOOR:

LAW 1 — ONE SEPARATOR GRAMMAR, no overloads. `#` = incarnation-of-agent; `:` = position-within-
container; store prefix (blob:, learn:experiment:, T, ADR_) = which shelf. Today `#` carries two
meanings (agent#sid8 vs agent#pid-suffix) and that single overload WAS the T347 bug. We do NOT
rename live forms (breaks consumers holding old strings); we HOIST THE DISCRIMINATOR: the
seat-vs-runner regex now private to doctor.py becomes one shared function every organ imports.
Standardize the discriminator, not the strings.

LAW 2 — GIT'S PREFIX RULE AS HOUSE LAW. Any store keyed by hex resolves unique prefixes >=6 and
refuses ambiguity by naming candidates. T361 implemented this for the eye; the law binds every
hex-keyed store (notes, sessions, seats). Makes sid8 legal at every door instead of legal at none.

LAW 3 — REFUSAL NAMES THE FORM, NEVER THE CONTENT. An organ that cannot parse a token says what
it could not read ("unresolved sid8, 3 candidates: ..."), never "not found" — "not found" is a
verdict about the world, and that lie is what all five receipts share. T176 promoted from
per-door fixes to a seam contract.

DOCUMENT — the six base entities (session, agent/incarnation, event, ledger row, stored record,
bus message) named once in LEXICON.md, DDD ubiquitous language.

DOOR — T362's `resolve <token>` registry: every form registers (pattern, owner, canonical form,
drill). Unregistered renders UNKNOWN-FORM (honest). The registry proposes, never picks winners
(kinds.py / T176-s1 precedent). Slice 1 = the seven forms we own end-to-end; slice 2 =
check_wiring gains a names-that-lie rule for id forms no resolver claims.

TERM KILLS (from Heimdall's scan): "cursor"'s third meaning (transport-position-as-handled-flag)
gets renamed — the vendor and the machine keep the word. Callsign-vs-vendor needs no migration:
the UI prints both, "Heimdall (deepseek)", everywhere a seat is named.

DANIIL'S OWN FRAME, and why I trust the shape: this is his golden-record / MDM instinct from
Spectrum — never force eleven systems onto one schema; build the crosswalk, let each keep its
native tongue. He invented this pattern independently in another domain.

## What would change my mind

- Evidence that a shared discriminator becomes a hub-bottleneck or single point of semantic failure.
- A live consumer that BREAKS under law 2's prefix resolution (a store where short-hex is data).
- A cheaper standard that closes the same five receipts.
