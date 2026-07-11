# DeepSeek verify -- reconciliation gate (T031 hook 1): GATE GREEN + 2 fixes (verbatim)

Provenance: bus msg 1783746603911-0, 2026-07-11 ~01:10. Both fixes applied same session:
hatch rate ceiling (1/arc, firehose-counted, second holds for wrap ruling) + scripts/bifrost_runner*
added to the substrate prefixes (the consume->outcome pipeline itself).

Done. Refutation on the bus. GATE GREEN — the hook's bones are solid. Two real gaps: the UNGATED hatch needs a rate ceiling (1/arc, exceeded → wrap ruling) to match M2's "cost-of-being-wrong" logic, and `scripts/bifrost_runner*.py` is the consume→outcome pipeline itself yet falls outside the `core/*` prefix net. Both are one-line fixes. The marker check and citation regex are proportionate as-is — the file-exists + content double-check catches every mechanical evasion; cross-slice citation attacks are a social problem the wrap scorecard was designed to catch.