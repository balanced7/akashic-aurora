# The liveness work, in plain language

Status: current  (2026-07-11)
Class: reference
Audience: anyone -- no distributed-systems vocabulary assumed. The precise version lives
in docs/agent-liveness-tier-2026-07.md; this page trades precision for a kitchen.
Seed: a GPT explainer Daniel commissioned (research/reviewed/gpt-plain-language-
explainer-2026-07-11.md), kept where it was right, extended where simplifying dropped
the decisions that mattered.

## The kitchen

Two cooks (the AI agents) share a kitchen. Orders arrive as tickets on a rail. A cook
takes a ticket, makes the food, hands it to the customer, and moves the rail marker
forward so nobody remakes a served order.

One night a cook was killed mid-shift (a real incident: a badly-wired power strip --
our own launch command). The ticket he had just taken was gone: the rail marker had
already moved past it, but no food had been made, and no one could tell anything was
missing. The customer waited on a meal that no longer existed anywhere. Every dashboard
said the kitchen was fine, because the replacement cook WAS fine -- just idle.

Everything below exists because of that ticket.

## Fix 1: move the marker AFTER the food goes out

The old kitchen moved the rail marker when a ticket was TAKEN. The new kitchen moves it
only after the meal is SERVED. Now, if a cook dies mid-burger, the marker still points
at that ticket -- the next cook re-reads it and cooks it. An order can no longer vanish.
The trade: sometimes work is done twice. Which leads to --

## Fix 2: the "already served" note

Before moving the marker, the cook writes a small note: "table 7 got their burger." If
a ticket ever comes around again (because a cook died at the wrong moment), the next
cook sees the note and skips it. One meal per order, even across deaths.

The honest exception, and we chose it on purpose: there is one tiny instant -- after
handing over the plate, before writing the note -- where a death means the next cook
makes a SECOND burger. We could close that gap only by writing the note BEFORE serving,
but then a death in the other order means a customer gets NOTHING and the kitchen
thinks they were fed. Two burgers occasionally beats zero burgers ever. We didn't just
accept this -- we built a test that kills a cook in exactly that instant and CONFIRMS
the second burger appears. The tolerance is a decision with a receipt, not a surprise.

## Fix 3: numbered kitchen keys

Cooks hold a shift key that expires if they stop checking in. The failure nobody thinks
about: an old cook who froze (not died), whose key expired, and who then WAKES UP and
keeps cooking while his replacement is already on shift -- two cooks, one rail, chaos.

So every key is numbered, and THE RAIL checks the number: marker moves only if your key
number is at least the newest one issued. The woken-up old cook's stale key is refused
at the rail itself, loudly, and he clocks out. (The lock on the door can lie; the rail
cannot.)

## Fix 4: kill a cook at every step, on purpose

We listed the five moments in the ticket-to-marker pipeline where a death could hurt:
just after taking the ticket; mid-cooking; after serving but before the note; after the
note but before the marker; between two tickets. Then we built a harness that MURDERS a
cook at each exact moment, brings in a replacement, and checks: no lost meals, no
double meals (except the one chosen tolerance, which must appear). The night's original
disaster is now the first of those five tests, passing forever.

We also keep a second, dead-simple model of the kitchen on paper -- a checklist version
that says what the rail and the notes SHOULD look like after any sequence of events --
and after every murder-test we compare the real kitchen against the paper one. The
paper kitchen has caught nothing yet; the day it disagrees with the real one, one of
them is lying, and that is exactly the day it earns its keep.

## Why we read before we built

None of these fixes are inventions. Move-the-marker-after-serving is how Kafka (the
world's post office) commits reads. The numbered keys are Kleppmann's fencing tokens.
Murder-testing is how FoundationDB and SQLite are built. The "read the field first"
step found us the key-numbering fix we did not know we needed, and talked us OUT of
heavier machinery (consensus systems, message groups) that our two-cook kitchen doesn't
warrant. Rejections got written down too, so future-us knows the ceiling we declined.

## Why two readers

Both agents read the same sources SEPARATELY and wrote verdicts before comparing. Where
they agreed, confidence. Where they disagreed, the gold: one reader ruled "page the
manager when a meal might be lost" -- the other pointed out the hour-old Fix 1 already
re-cooks lost meals automatically, so paging would just wake the manager for something
the kitchen now heals itself. The disagreement was the system working: the second
reader caught the first one reasoning from a kitchen that no longer existed.

## The point

The kitchen is now boring in the best way: any cook can die at any instant, and either
nothing is lost or the loss is one we chose, tested, and wrote down. And the process
that got us here -- name the problem, find who has studied it for twenty years, read
independently, argue, build one small piece, murder it, ship -- is written down as the
house method (docs/method-baseline-2026-07.md), because the kitchen was never the
point. The method is.
