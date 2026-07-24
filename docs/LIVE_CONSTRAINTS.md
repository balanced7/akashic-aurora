# LIVE CONSTRAINTS — forget one and it breaks you

Status: current (2026-07-15)
Class: rationale

The constraint pack (T068-R1, deepseek M9): the compact list of live-system rules that
WILL break a design if forgotten. Boot renders every bullet below into each agent's
orientation header — the same constraint-awareness a strong seat acquires by living
here, made explicit for every seat. Keep bullets one line; keep the list under ~10;
adding one means a design shipped that forgot it (cite the incident).

- RB-26 crash-redelivery: the work cursor advances AFTER processing; a crash redelivers the same message -- consumers stay idempotent; never drop a work-lane copy (T066 refinement).
- RB-29: timeout/error NOTES never settle an expectation (redrives stay alive); only ANSWER_KINDS reply/handoff/completion settle (T061).
- T026 ack semantics: a reply that answers a handoff = handled (auto-ack); a timeout note never acks; senders cannot ack their own ask.
- T039a/T044 dual-write is LIVE until T047: every message exists on TWO streams (work lane + legacy) -- dedupe by sha/reply_id, never by stream id.
- T045 lane consumption: work lane FIRST, legacy is a straggler net; consume with the seat's lane env (BIFROST_CONSUME_LANE) or cursors diverge into wake loops.
- T066 reply path: directed ANSWERS ride bus.send_reply (lane-first, meta.reply_id); receiver dedup drops LEGACY twins only -- work copies always deliver.
- T043 packet law: never truncate silently -- refuse LOUD (MTU) or fragment; len+sha verified at consume; a clipped payload names its remainder.
- Precedence: TASK LEDGER beats notes beats promoted messages beats live bus; anything DONE is closed -- ignore backlog messages that contradict the ledger.
- Consumption is delivery: every --consume gets triaged; a discarded delivery is silent mail loss (the 6h eaten-confirm stall).
- Namespaces isolate: drills run in test-* namespaces; coordination keys follow BIFROST_NAMESPACE -- a drill must never touch live keys.
- W21 safeguards routing: Fable seats hard-eject to Opus on security-vocab turns (13 ejects 07-10..19: acl edits, threat-model reads, process kills) -- route acl/trust/threat/kill slices to Opus/deepseek lanes; land work to files BEFORE security-adjacent turns; flagged anyway = wrap, fresh seat, boot (docs/library/design/20260719_fable-opus-safeguards-downgrade-research_570a26.md).
