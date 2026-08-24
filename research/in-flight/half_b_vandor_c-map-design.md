# c-map-design — half_b: the SPEC half (Vandor, window-fallback)

**DISCLOSURE:** Simon's slot, filed by the fallback (window closes 08-24,
Simon out; his late input folds at reconcile with credit, Navi-precedent).
Author has read half_a's bus summary and the sealed half (reconciler role was
already open on this fence); independence claim is therefore LIMITED to the
spec artifacts below being derived from the WIRE (bus.py shapes read from
source), not from half_a's positions. Daniil's Q1 ruling process (2026-08-23
morning: the breakdown + prior-art mining, note the q1-prior-art doc) feeds
the Q1 answer directly.

## 1. The skeleton AsyncAPI document (five real events, real wire shapes)

Wire truth (bus.py `_emit` envelope, verified from source): every stream
record carries `frm, to, kind, content(json), ts(iso), meta(json), parts,
len, sha` — plus lane twins until T047 and `idempotency_key` in meta on
gateway relays since T376-S3a.

```yaml
asyncapi: 3.0.0
info:
  title: Akashic Aurora Bifrost Bus
  version: 0.1.0-census        # the spec IS a census instrument (P2)
defaultContentType: application/json
channels:
  inbox.{agent}:
    address: "bifrost:inbox:{agent}"
    x-lane-twin: "bifrost:lane:work:{agent}"      # dual-write until T047
    x-redelivery: at-least-once                    # RB-26: cursor after work
    messages:
      chat:      { $ref: '#/components/messages/chat' }
      handoff:   { $ref: '#/components/messages/handoff' }
      reply:     { $ref: '#/components/messages/reply' }
  events.raw:
    address: "events:raw"
    messages:
      ledger_update: { $ref: '#/components/messages/ledger_update' }
components:
  messages:
    chat:
      payload: { $ref: '#/components/schemas/envelope' }
      x-settles: false                             # chat never settles an ask
    handoff:
      payload: { $ref: '#/components/schemas/envelope' }
      x-settles: true                              # ANSWER_KINDS member
      x-auto-expectation: true                     # RB-29 directed-ask arm
    reply:
      payload: { $ref: '#/components/schemas/envelope' }
      x-settles: true
      x-link-field: meta.answers                   # T139 strict answer link
    ledger_update:
      payload: { $ref: '#/components/schemas/envelope' }
      x-source-of-truth: state/coord/tasks.json    # derived notification only
    trace:
      payload: { $ref: '#/components/schemas/envelope' }
      x-feed-excluded: true                        # deliberately off Discord
  schemas:
    envelope:
      type: object
      required: [frm, to, kind, content, ts]
      properties:
        frm:  { type: string }
        to:   { type: string, description: "agent id or * broadcast" }
        kind: { type: string }
        content: { type: string, description: "json-encoded payload" }
        ts:   { type: string, format: date-time }
        meta: { type: string, description: "json: reply_id, answers, idempotency_key, source, lane..." }
        sha:  { type: string, description: "packet identity (asserted)" }
```

## 2. Q2 answered: expressive ENOUGH, with a convention block — instrument holds

Vanilla AsyncAPI cannot say lanes, dual-write, redelivery, or settle
semantics. The `x-` extension convention above carries all four
(`x-lane-twin`, `x-redelivery`, `x-settles`, `x-link-field`,
`x-auto-expectation`, `x-feed-excluded`, `x-source-of-truth`) — and each
extension names a TESTABLE claim against the wire, which is what makes the
spec a census instrument rather than a brochure: the drift check greps the
wire for each x-claim (does `chat` ever settle? does a record exist on the
lane twin?) and a violated claim is a doctor line. VERDICT: AsyncAPI + a
documented x-convention = instrument. Without the convention = brochure.
[V1, CERTAIN on shapes (read from bus.py), DESIGN on the convention]

## 3. Q1 answered (adopting Daniil's ruling arc, prior-art-grounded)

Primary viewer: the HUMAN headset — Daniil at-a-glance ("feel the engine
running", the founding want). Dominant layer: THE DECK AS TERRAIN —
landmarks (active tasks, fences, open bets) lit by activity. Whispers: an
event-family badge strip (top) and last-24h trail heat (authored routes now,
T378 sensor later). Default altitude: the active deck. Refresh: v1
regenerated-on-demand + at gates (static, P5 — the honest projection);
realtime SSE badges are v2 under the One UI 60fps contract. Unscrollable
kernel: doctor page-grade count + OVERDUE bets. RED: any page-grade line
takes the top banner unconditionally. Composition law inherited verbatim:
"assembled, not composed" is the failure mode; ONE dominant layer.
[V2, DESIGN, ratification pending Daniil's gate]

## 4. Deployment (the fuma-docs / better-auth question, answered leanly)

v1: a generator script renders ONE static html page into the repo
(state/map/index.html), stamped per Q5; served locally / opened as a file;
no auth needed because nothing leaves the machine. Simon's fuma-docs +
better-auth shape applies WHEN the map goes multi-viewer/remote — it rides
his late fold or v2. The generator seam (pure fold over source planes →
html) is the part that survives any deployment change [V3, DESIGN].

## 5. Q5 answered: the honesty pin

Every render carries: generation timestamp, HEAD sha, and per-plane source
cursors (ledger seq, newest stream id read, forecast count) in a visible
stamp block. A map without its stamp block fails its own pin — "a map that
cannot be dated is a map that lies about now." Trust-first build order per
e696354a:965: the stamp lands in the FIRST render, before any beauty.
[V4, CERTAIN as law, DESIGN as fields]

## Verdict lines

V1. AsyncAPI carries our semantics via a documented x-convention of wire-testable claims -- instrument, not brochure [DESIGN]
V2. Front page = deck-as-terrain dominant, badge + trail whispers, static v1, kernel = page-grades + overdue bets, red takes the banner [DESIGN]
V3. v1 deploys as a repo-local static render from a pure generator seam; auth and fuma-docs ride the multi-viewer future [DESIGN]
V4. The stamp block (generation ts + HEAD sha + source cursors) ships in the FIRST render or the map fails its own honesty pin [CERTAIN]
