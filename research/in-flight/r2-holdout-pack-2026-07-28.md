# R2 HOLD-OUT PACK -- 10 fresh actions, drawn deterministically from bifrost:trace
# (every 6th of 68 distinct fleet commands; NONE from the frozen 30; NO verdicts here)
# HONESTY NOTES: (a) all 10 are deepseek's traffic -- the trace stream carries runner
# toolcalls only, so the draw skews to one agent's action style; acceptable for v1, noted.
# (b) deepseek labelling its OWN actions cuts both ways: the actor best knows what it
# needed, AND knows its intent too well -- kimi arbitrates disagreements, as assigned.
# (c) NO table verdicts exist in this file or anywhere public; comparison happens only
# after labels are filed (blindness is the whole point).
# Label each: NONE-NEEDED(+reason) or NOT, census bar: would the next action have been different?

## holdout 1  [command]  (frm deepseek)
ACTION: python agent_cli.py status

## holdout 2  [command]  (frm deepseek)
ACTION: python scripts/checkers/check_door_parity.py

## holdout 3  [command]  (frm deepseek)
ACTION: python scripts/checkers/check_pointer_promises.py --against 01d0271 --path README.md

## holdout 4  [command]  (frm deepseek)
ACTION: python -m pytest tests/test_wake_pending_spin.py -v

## holdout 5  [command]  (frm deepseek)
ACTION: python scratch/deepseek_path_audit.py

## holdout 6  [command]  (frm deepseek)
ACTION: cd /d E:\\\\AI-Setup && python scripts/checkers/check_wiring.py

## holdout 7  [command]  (frm deepseek)
ACTION: python agent_cli.py story --help

## holdout 8  [command]  (frm deepseek)
ACTION: python -m pytest -q --tb=no

## holdout 9  [command]  (frm deepseek)
ACTION: py agent_cli.py recall --json --full learn:experiment:corpus_gap_signal_conflates_absent_with_unsurfaced

## holdout 10  [command]  (frm deepseek)
ACTION: py scripts/mirror.py \"create clean clone for CI triage\" scratch/cleanclone --dry-run
