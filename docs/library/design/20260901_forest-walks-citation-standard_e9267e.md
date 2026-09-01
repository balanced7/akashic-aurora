---
akashic_id: art_20260901_forest-walks-citation-standard_e9267e
akashic_sha: 8dbc4023234d
schema_version: 1
status: current
type: design
arc: unofficial-college
date: 2026-09-01
title: forest-walks-citation-standard
gist: "Daniil's charter: every claim immaculately cited, every link live-verified before ship; three laws, source tiers T1-T3, anchor bibliography, census-to-v2-mint process"
visibility: fleet
body_type: markdown
seats: [claude]
category: [security, conducting, governance]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-09-01T01:02:49"
updated: "2026-09-01T01:02:49"
---
<!-- GENERATED PROJECTION of art_20260901_forest-walks-citation-standard_e9267e -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# forest-walks-citation-standard

# Forest Walks Citation Standard

*Daniil's charter, verbatim (2026-09-01): "I want every source immaculately cited from trusted authoritative sources. we can cite whitepapers, technical presentations, those youtube videos where people do deep architecture dives, anandtech, phoronix, semiaccurate, mooreslawisdead, gamersnexus, and others, scientific papers, conferences, whitepapers." Status: design position; becomes contract at ratification.*

## The three laws

1. **Every factual claim in a published walk carries a citation** to the most authoritative source available for that claim class. Uncited claims get softened to explicit reasoning ("derivable from X"), ranged, or cut. A walk must survive its own audit.
2. **Every citation is verified live before it ships** — fetched, read, and confirmed to actually support the claim, with the supporting line quoted in the claim ledger. A hallucinated citation is the cardinal sin of AI-era publications and the one failure this lab can least afford; our differentiator IS receipts. Dead sources (AnandTech ceased 2024) cite archive.org captures.
3. **Sources are tiered, and the tier must match the claim.** Industry channels are citable *in their lane*; a microarchitectural number never rests solely on a rumor-tier source.

## The tiers

- **T1 — primary**: vendor documentation (AMD Software Optimization Guides, Intel Optimization Reference Manual / SDM, Arm ARM), peer-reviewed papers (ISCA, MICRO, HPCA, CGO, JILP), first-party conference talks (Hot Chips, ISSCC), standards documents.
- **T2 — expert measurement & analysis**: Agner Fog's microarchitecture manuals and instruction tables; Chips and Cheese (microbenchmarked deep dives); uops.info; WikiChip; the AnandTech archive (gold for its era); Phoronix (Linux/perf benchmarks); Dougall Johnson's Apple-core documentation; GamersNexus *for testing methodology, thermals, and hardware investigations*.
- **T3 — industry & narrative**: SemiAccurate, Moore's Law Is Dead, GamersNexus-as-industry-commentary, Asianometry. Citable for industry events, timelines, product context — labeled as analysis/rumor where applicable; never the sole support for a microarchitectural fact.
- **YouTube deep dives**: citable when the speaker is the authority — vendor engineers at Hot Chips, recorded university courses (e.g., Onur Mutlu's architecture lectures), conference recordings, primary interviews (Keller et al.). Cite speaker + venue + timestamp.

## Anchor bibliography (known load-bearing citations for Walks 01-03)

Jimenez & Lin, "Dynamic Branch Prediction with Perceptrons" (HPCA 2001) · Seznec & Michaud, TAGE (JILP 2006) · Yeh & Patt, two-level adaptive prediction (1991) · McFarling, gshare (DEC WRL TN-36, 1993) · Rohou, Swamy & Seznec, "Branch Prediction and the Performance of Interpreters — Don't Trust Folklore" (CGO 2015) · Kanev et al., "Profiling a Warehouse-Scale Computer" (ISCA 2015) · Minsky & Papert, Perceptrons (1969) · Shannon (1948) · Little (1961) · Marpe et al., CABAC (IEEE TCSVT 2003) · Kocher et al., Spectre (2019) · AMD SOG (Zen 4 doc 56665; Zen 5 successor) · Intel Optimization Reference Manual · Agner Fog, microarchitecture.pdf · AMD V-Cache materials (Hot Chips/ISSCC) · AnandTech M1 deep dive (archive) · Chips and Cheese: Zen 4, Zen 5, Golden Cove, Lion Cove analyses.

## The process (per walk)

1. **Claim census**: extract every factual claim (number, mechanism, historical event) into a ledger — claim id, walk, claim text, claim class, proposed source + tier.
2. **Source assignment**: best-tier source per claim; conflicts get both sources and a range ("mispredict penalty ~15-20 cycles; AMD SOG says X, measured analyses say Y").
3. **Live verification**: every URL fetched and read by a browsing-capable lane; supporting quote recorded in the ledger. No fetch, no cite.
4. **v2 minting**: walks re-filed with inline citation markers + a References section AND the Forest Walks series naming (one ceremony fixes both); v1 atoms superseded; the site re-projects automatically.
5. **The gate** (Sunshine preregisters): minimum citation coverage per claim class before a walk ships public; softened/cut claims logged.

## On-site form

Numbered references section per walk; superscript markers in text; archive links alongside live links where rot is a risk. Presentation (footnotes vs margin sidenotes) is Rill's lane in the design round.
