# Knowledge primitives (shape axis) — full frontier research record (2026-07-03)

provenance: three frontier research agents (A: historical universal vocabularies,
B: cross-domain pattern systems, C: computational analogy + library learning), launched
overnight at user request; claims verified per-agent (VERIFIED/PARTIAL/UNVERIFIED marked);
synthesized by claude. Idea note: 'idea: knowledge primitives (shape axis) + tests-as-schema'
(ADR_0703000542_6378). Feeds the sharpening-loop S4 slice.

---

## PART A — Historical universal vocabularies (agent A, complete)

### A1. Llull's Ars Magna + Leibniz's characteristica universalis
1. Llull (c.1274-1305): rotating wheels over letters = fundamental attributes, mechanically
   generating concept combinations -- the first small-alphabet-of-primitives machine.
   VERIFIED: historyofinformation.com/detail.php?id=1973 ; publicdomainreview.org/essay/let-us-calculate-leibniz-llull-and-the-computational-imagination/
2. Llull's primitives INVENTED a priori (his theological absolutes) -- archetype of the
   invented-inventory approach. PARTIAL: medium.com/@suu-b/ramon-llulls-ars
3. Leibniz (De Arte Combinatoria, 1666): "alphabet of human thought" + calculemus -- and
   in the same breath criticized Llull's categories as ARBITRARY. VERIFIED:
   en.wikipedia.org/wiki/De_Arte_Combinatoria
4. Fate: the computational IDEA survived (Boole/Frege/computing); no concrete primitive
   alphabet ever existed. The framework outlives every attempt to fill it. VERIFIED:
   writings.stephenwolfram.com/2013/05/dropping-in-on-gottfried-leibniz/

### A2. Wilkins (1668) + Borges' demolition
5. Wilkins: 40 genera, words encode their own taxonomy (de=element, deb=fire, deba=flame);
   entirely invented top-down. VERIFIED: en.wikipedia.org/wiki/An_Essay_Towards_a_Real_Character,_and_a_Philosophical_Language
6. Borges ("Analytical Language of John Wilkins"): "there is no classification of the
   Universe that is not arbitrary and full of conjectures." VERIFIED (fetched).
7. Mechanical failure mode: brittle AT THE BOUNDARY -- every new entity forces a placement
   decision the scheme can't adjudicate; world changes strand the fixed genera.
   VERIFIED: borges.pitt.edu/i/wilkins-john

### A3. Ranganathan's faceted classification -- the one that partly survived
8. Colon Classification (1924-33): subjects SYNTHESIZED from orthogonal facets
   (PMEST: Personality, Matter, Energy, Space, Time), not enumerated. VERIFIED:
   historyofinformation.com/detail.php?id=4384 ; en.wikipedia.org/wiki/Faceted_classification
9. Key contrast: primitives as ORTHOGONAL AXES, not a fixed tree -- accommodates subjects
   unforeseen at design time (the exact killer of enumerative schemes). VERIFIED.
10. Faceting survived AS A TECHNIQUE (every e-commerce filter sidebar); PMEST's specific
    labels did not. The compositional MECHANISM transferred; the inventory was discarded.
    VERIFIED: berkeley.pressbooks.pub/tdo4p/chapter/faceted-classification/

### A4. Otlet's Mundaneum + UDC
11. Mundaneum: ~15-16M index cards by the 1930s; anticipated networked knowledge access.
    VERIFIED: en.wikipedia.org/wiki/Paul_Otlet ; en.wikipedia.org/wiki/Mundaneum
12. UDC (1904) still used in ~130 countries / 50 languages; the Mundaneum lost funding
    (1934), partly destroyed (1940+). VERIFIED: en.wikipedia.org/wiki/Universal_Decimal_Classification
13. Lesson: the practical, extensible, community-maintained notation with a MODEST JOB
    outlived the utopian world-brain. VERIFIED: udcc.org history

### A5. Wierzbicka's NSM -- the strongest MINED inventory
14. ~65 semantic primes, posited ONLY if matching word/morpheme found across world
    languages -- discovered, not stipulated. VERIFIED (fetched): en.wikipedia.org/wiki/Natural_semantic_metalanguage
15. Inventory quintupled: 14 (1972) -> 60 (2002) -> 65 (current). Even rigorously mined
    inventories drift -- "the true primitives" are not a fixed natural kind. VERIFIED.
16. Strongest criticism (Riemer 2006): reductive method may be circular; paraphrases
    tunable to look successful. PARTIAL (paywalled): link.springer.com/article/10.1007/s10988-006-0001-4
17. Takeaway: mining beats inventing AND mined sets stay open/contested. Mining raises
    the floor; it does not deliver a closed set.

### A6. AI knowledge-primitive era
18. Schank Conceptual Dependency (~1969): ~11 primitive ACTs (ATRANS, PTRANS, PROPEL,
    MTRANS, MBUILD...) as language-independent canonical form. VERIFIED:
    aclanthology.org/T75-2008.pdf ; en.wikipedia.org/wiki/Conceptual_dependency_theory
19. CD failure modes: (a) knowledge-acquisition bottleneck (hand-authored mappings per
    domain); (b) primitive inadequacy -- ~12 physical-action atoms forced awkward encodings
    of abstract/mental/social meaning. PARTIAL: mbrenndoerfer.com/writing/conceptual-dependency
20. Minsky frames (1974): structure over atoms -- stereotyped situations with default
    slots; DNA survives in schemas/slot-filling/structured extraction. VERIFIED: MIT PDF.
21. Sowa Conceptual Graphs (1976/84): graph+logic formalism survived (ancestor of RDF);
    the specific primitive sets did not. NOTATION generalized; inventories didn't.
    VERIFIED: jfsowa.com/cg/cg_hbook.pdf

### A7. Cyc -- the definitive cautionary tale
22. Bet (1984): hand-encode common sense until a "knowledge pump" primes autonomous
    learning (predicted 1995-2000). VERIFIED (fetched): yuxi.ml/essays/posts/cyc/
23. Numbers: ~$200M, ~2000 person-years, ~30M assertions, ~41 years (1984-2025); by 2002
    ~$60M/600 person-years; cost per assertion $5 -> $0.7 but never self-sustaining.
    VERIFIED (fetched).
24. Why: pump never primed (manual-entry bottleneck at 1000x CD scale); combinatorial
    brittleness (>1,100 specialized inference engines); proprietary insularity, no
    public benchmarks, "no evidence...competitive advantage." VERIFIED: yuxi.ml ;
    cs.nyu.edu/~davise/papers/CYCEval.pdf ; garymarcus.substack.com/p/doug-lenat-1950-2023
25. Lenat's final paper (2023, w/ Marcus, arXiv 2308.04445): the future is HYBRID --
    curated knowledge + inference FUSED with statistical learning. The lifelong champion
    of invented ontology ended by endorsing the fusion. VERIFIED.

### A8. Upper ontologies vs domain ontologies
26. SUMO/DOLCE/BFO: in 430 Linked Open Data datasets, ZERO reused DOLCE or SUMO.
    Causes: complexity, rigidity, mutual incompatibility, unintended inferences.
    VERIFIED: semantic-web-journal.net/system/files/swj2307.pdf
27. schema.org won via demand-side gravity (4 search engines, immediate rich-results
    payoff) -- network effect over metaphysical correctness. VERIFIED: queue.acm.org/detail.cfm?id=2857276
28. Gene Ontology success checklist: community, clear goals, LIMITED SCOPE, simple
    structure, continuous curation, early real use. VERIFIED: GO papers.
29. "Ontology fatigue" is now explicit: bounded scope + real users + maintenance is the
    discriminator, not coverage. VERIFIED.

### A9. THE FIVE TRANSFERABLE DESIGN LAWS (agent A synthesis)
LAW 1: MINE from usage, never invent a priori -- and expect even mined sets to stay OPEN
  (NSM drifted 14->60->65; version the inventory, never close it).
LAW 2: Compose from ORTHOGONAL AXES, never enumerate a fixed tree (faceting survived;
  enumeration died at the boundary; CD's fixed atoms forced awkward encodings).
LAW 3: SCOPE DISCIPLINE predicts survival (GO/UDC bounded+maintained won; Cyc/SUMO
  totalizing died). Build primitives for a bounded demonstrable job; let it earn expansion.
LAW 4: The FRAMEWORK/NOTATION generalizes; the specific primitive set rarely does
  (Leibniz's idea vs alphabet; faceting vs PMEST; Sowa's formalism vs vocabularies).
  Invest in composition machinery; hold the inventory loosely.
LAW 5: ADOPTION follows incentive + network effects, not correctness (schema.org vs
  DOLCE) -- make primitives cheaper to use than to bypass; visible win on first use.
META: grand unifications fail with remarkable consistency; modest composable bounded
  maintained tools survive. Even Lenat concluded hybrid.

---

## PART C — Computational analogy + library learning (agent C, complete)

### C1. Structure-mapping + MAC/FAC (the retrieval architecture)
1. SMT (Gentner 1983): analogy = alignment of RELATIONAL structure (higher-order
   relations like cause/enable), not attributes; SME still maintained (2025 paper,
   Companion architecture). journals.sagepub.com/doi/10.1177/09637214251395678
2. MAC/FAC two-stage: cheap CONTENT VECTORS (flat encoding whose dot product estimates
   full structural-match score) filter; expensive SME verifies top few. Built to
   reconcile: structure dominates judgment, SURFACE dominates retrieval, structural
   remindings still happen. groups.psych.northwestern.edu/gentner/papers/ForbusGentnerLaw94.2b.pdf
3. The problem a shape index solves, quantified: Gick&Holyoak radiation problem --
   ~20-30pct spontaneous transfer -> ~75-80pct WITH A HINT (knowledge present but INERT;
   retrieval is surface-cued). Gentner/Rattermann/Forbus 1993: retrievability tracks
   surface; judged soundness tracks structure -- memory indexes by the wrong key.
   pubmed.ncbi.nlm.nih.gov/8243045 ; 2025 replication: bpspsychub.onlinelibrary.wiley.com/doi/10.1111/bjop.12747
4. Design implication: structure-correlated cheap vector at recall + structural verifier
   for precision. Modern equivalent: embed the SCHEMA RENDERING (relations only,
   entities anonymized to roles), not raw text.

### C2. Copycat / Mitchell
5-6. Copycat survives as an EVALUATION AGENDA (ARC/ConceptARC: humans 91pct vs GPT-4
   ~33pct, arxiv 2311.09247); no mainstream successor system; its claim (retrieval+mapping
   must be structure-sensitive) keeps being vindicated by ARN results below.

### C3. DreamCoder lineage (mined abstraction libraries, MDL-gated)
7. DreamCoder (PLDI 2021, fetched): wake (solve) / abstraction sleep (refactor solutions
   via version-space algebra + e-graphs; candidates = shared subexpressions) / compression
   objective = MINIMIZE -logP[Library] + sum_tasks description-length under it (add
   abstractions greedily while probability improves) / dream sleep (train recognizer on
   50/50 replays + fantasies). arxiv.org/abs/2006.08381
8. Numbers: text-editing 3.7pct -> 79.6pct after library learning; library depth vs
   tasks solved r=0.79; re-derives map/fold/zip from 1959 Lisp primitives; 93pct of a
   physics-law dataset after 8 cycles (vector-algebra abstractions first).
9. Stitch (POPL 2023): corpus-guided top-down abstraction synthesis -- 3-4 ORDERS OF
   MAGNITUDE faster than DreamCoder refactoring, equal/better compression; the practical
   mining engine today. arxiv.org/abs/2211.16605
10. LILO (ICLR 2024, fetched): LLM search + Stitch + AutoDoc. REGEX 77.1 vs DreamCoder
    43.9; LOGO 49.0 vs 28.5. CRITICAL: compression WITHOUT DOCUMENTATION HURTS (-30.6pts
    REGEX, -11.1 LOGO undocumented; AutoDoc recovers) -- a mined abstraction is only
    useful once NAMED + DOCUMENTED for the downstream reasoner. arxiv.org/abs/2310.19791
11. Successors: ReGAL (ICML 2024, LLM refactoring of Python corpora, +11.5-26.1pct abs
    for 13B model, arxiv 2401.16467); SkillOps (2026-05, skill libraries as
    technical-debt management, numbers UNVERIFIED, arxiv 2605.13716).

### C4. Agent skill libraries
12. Voyager: skills indexed by embedding of LLM-written DESCRIPTION; ablation: no
    library -> no zero-shot transfer. arxiv.org/pdf/2305.16291
13. Agent Workflow Memory (ICML 2025): induces reusable workflows from OWN successful
    trajectories -- +24.6pct rel Mind2Web, +51.1pct rel WebArena. Closest published
    analogue to mining lessons from solved problems, no DSL required. arxiv.org/abs/2409.07429
14. SkillWeaver (2025): +31.8pct rel WebArena; mined skills TRANSFER to weaker agents
    up to +54.3pct -- libraries are portable artifacts. arxiv.org/abs/2504.07079

### C5. LLM analogical reasoning (2024-26)
15. ARN benchmark: LLMs drop ~35 abs pts on FAR analogies (no surface overlap); GPT-4
    zero-shot BELOW RANDOM on far analogies -- LLM surface bias mirrors the human one.
    aclanthology.org/2024.tacl-1.59/
16. Robustness debate unresolved (Lewis&Mitchell collapse on counterfactual alphabets vs
    Webb/Holyoak counter-evidence); practical takeaway: don't trust implicit structural
    mapping -- MAKE STRUCTURE EXPLICIT.
17. Explicit structure works: YARN (decompose->abstract->map beats end-to-end, arxiv
    2603.29997); analogical prompting +4-10pct (ICLR 2024); probing: small models ENCODE
    relational structure far better than they express (MAP 0.93 probed vs 0.18 prompted)
    -- extraction pipelines can harvest it (arxiv 2604.03877); AutoSchemaKG ~92pct
    human-schema alignment at web scale.

### C6. Structural indexing of text corpora (the direct precedent)
18. Hope/Chan/Kittur/Shahaf KDD 2017 "Accelerating Innovation Through Analogy Mining"
    (fetched): index 9K product descriptions by learned PURPOSE + MECHANISM vectors
    (deliberately weak structural representation) instead of topic. Top-1pct precision
    0.739 vs 0.630 TF-IDF; ideation experiment: 38pct good ideas vs 22pct random vs 21pct
    surface-similar (surface-similar was WORST -- fixation). arxiv.org/abs/1706.05585
19. Also: structural-dependency embeddings beat BoW for biomedical analogy retrieval;
    "Structural Memory of LLM Agents" (chunks/triples/facts/summaries -- MIXED most
    robust, iterative retrieval best, arxiv 2412.15266); CBR survey names structural
    retrieval the underused third leg (arxiv 2504.06943). NO published system does
    MAC/FAC-grade structural indexing over a free-text lesson store -- pieces exist,
    ASSEMBLY IS OPEN.

### C7. Agent C's recipe for a 150-1000-item corpus (all components published)
1. Two-field schema per lesson, LLM-extracted (purpose/trigger + mechanism/move),
   entities anonymized to roles = the cheap MAC vector; embed schema separately from text.
2. MAC/FAC retrieval: cosine over schema embeddings top-10..20, LLM as FAC verifier
   (explicit mapping table required).
3. Mine the abstraction layer: cluster schema renderings; adopt a named schema ONLY if
   it shortens total description (Stitch/DreamCoder MDL criterion).
4. AUTODOC IS LOAD-BEARING: every mined schema gets name + one-line docstring + 2
   canonical examples (LILO: undocumented = -30pts).
5. Maintain like software: dedup, deprecate unused, track hit-rate per schema (SkillOps).
6. Measure the DreamCoder way: held-out lessons -- schema-index vs raw-embedding retrieval
   precision@k + downstream task success. At this corpus size, full FAC verification of
   top-20 per query = a few hundred LLM calls total.

---

## PART B — Cross-domain pattern systems (agent B, complete; sub-agent verified)

### B1. General Systems Theory
1-8. Bertalanffy 1950: "general system laws... isomorphic laws in different fields";
   delivered a SHORT real list (exponential, logistic, allometric, minimum-action,
   relaxation-oscillation); durable science = open-system/equifinality, NOT the
   isomorphism catalog. Bertalanffy himself called reason #1 for isomorphisms "trivial"
   (limited stock of simple differential equations). Standard critique: unfalsifiable,
   "calling two things systems grants no shared structure". Faded as a theory; its
   WORDS won (open system, feedback, homeostasis) precisely because useful without the
   parent theory. VERIFIED: isnature.org Bertalanffy 1950 PDF ; bactra.org/notebooks/systems-theory.html

### B2. Cybernetics
9-14. Invented from a DESIGN PROBLEM (WWII anti-aircraft predictor), not mined. Durable
   payload = small stable set (~6-8): feedback, homeostasis, control, information, black
   box, requisite variety (Ashby 1956), circular causality, self-organization -- diffused
   into every field. Failure mode: cannibalized by its own spin-offs; ideas won, banner
   didn't. VERIFIED: en.wikipedia.org/wiki/Cybernetics ; en.wikipedia.org/wiki/W._Ross_Ashby

### B3. TRIZ
15-19. MINED: ~200K patents reviewed, ~40K inventive ones analyzed (1946-69) -> 40
   Inventive Principles + 39x39 Contradiction Matrix + 76 Standard Solutions + ARIZ.
   The core 40 stable for DECADES; practitioners keep the 40, quietly drop matrix/ARIZ.
   Transfer: Samsung/Intel/Boeing/Ford (self-reported; Intel ROI claim $212.5M/21mo).
   Critique: dated mechanical-engineering corpus, abstract-needs-expert-interpretation,
   thin controlled validation (critique specifics PARTIAL/UNVERIFIED). VERIFIED:
   en.wikipedia.org/wiki/TRIZ ; en.wikipedia.org/wiki/Genrich_Altshuller

### B4. Senge systems archetypes
20-22. ~9 archetypes (Limits to Growth, Shifting the Burden, Tragedy of Commons...);
   curated from system-dynamics practice, NOT data-mined; pedagogical/diagnostic
   utility, weak empirical base. VERIFIED: en.wikipedia.org/wiki/System_archetype

### B5. Alexander pattern language + GoF
23-29. Alexander 1977: exactly 253 patterns; seeded the first wiki + software patterns.
   GoF 1994: 23 patterns (5/7/11) -- the power was SHARED VOCABULARY. THE DEEP CRITIQUE:
   Norvig -- 16 of 23 patterns "simplified or eliminated" by better language features
   (Lisp/Dylan); Hannemann+Kiczales: 17/23 improved in AspectJ -- many patterns are
   WORKAROUNDS FOR MISSING SUBSTRATE CAPABILITY, not domain insights. Alexander's own
   OOPSLA-96 lament: adopters took the NOTATION, dropped the generative INTENT.
   VERIFIED: en.wikipedia.org/wiki/Design_Patterns ; patternlanguage.com/archive/ieee.html

### B6. Bond graphs -- THE formally successful case
30-34. Paynter 1959-61, Karnopp+Rosenberg tooling 1968. Core = MEASURABLE physical
   isomorphism: power = effort x flow, dimensionally REAL in every domain (voltage/current,
   force/velocity, pressure/flow...). ~9 elements, stable ~60 years, actively tooled,
   formalized in HOL (arxiv 2111.12274). FAILURE MODE MARKS THE BOUNDARY: thermal domain
   breaks power-conjugacy -> "pseudo bond graphs"; domains with no power product
   (information, economics) fall out entirely. Lesson: formalism succeeds only where a
   real measurable conjugate-variable isomorphism exists. VERIFIED: en.wikipedia.org/wiki/Bond_graph

### B7. Ologs / category-theory KR
35-40. Spivak+Kent 2012: types/aspects/commutative-diagram facts; functorial data
   migration -> CQL (Conexus); silk-music cross-domain demo (2011). Verdict:
   research/pilot, not mainstream -- steep abstraction barrier, tiny community, thin
   tooling. VERIFIED: journals.plos.org 0024274 ; github.com/CategoricalData/CQL

### B8. Conceptual blending + image schemas
41-44. Blending = a MECHANISM not a catalog; failure mode = unfalsifiable/post-hoc
   (Gibbs). Image schemas (CONTAINMENT, SOURCE-PATH-GOAL, FORCE family...): NO agreed
   inventory or count (~20-40 by author); ISL formalization research-stage. VERIFIED:
   en.wikipedia.org/wiki/Conceptual_blending ; en.wikipedia.org/wiki/Image_schema

### B9. Agent B's summary (see agent report for the 10-row table)
Mined + small + operationally grounded survives (TRIZ 40, cybernetics ~8, bond graphs 9);
invented + large + verbal decays (Wilkins 40 genera, Alexander 253 in software hands,
GST's program). Bond graphs prove grounding beats resemblance.

### B10. Agent B's three lessons for our corpus
1. TRANSFER TRACKS MEASURABLE ISOMORPHISM: every primitive needs an operational
   DETECTOR (what signature makes it apply / NOT apply) -- a primitive an agent cannot
   test over-fires and retrieves noise.
2. SMALL STABLE CORE, tens not hundreds: 150 lessons support a few dozen load-bearing
   primitives; "mining 200 gives you synonyms and dust." Freeze a named canon; hang
   elaborations off it.
3. TWO DECAY MODES TO GUARD: (a) Norvig test -- is this shape a real reasoning structure
   or a workaround for missing substrate capability? If the latter, FIX THE SUBSTRATE
   (for us: graduate it into a hook/guardrail, not an index entry). (b) Alexander drift --
   notation without intent; every primitive carries when-NOT-to-apply + provenance links
   back to the lessons it was mined from.

---

## SYNTHESIS (frontier, 2026-07-03) — the S4 design, grounded in all three agents

CONVERGED LAWS (independently reached by history, pattern systems, and computation):
1. MINE, never invent (A: NSM vs all invented inventories; B: TRIZ/bond-graph
   isomorphism discovered; C: DreamCoder/AWM mine from solved corpora) -- and version
   the inventory open (NSM drifted 14->65).
2. SMALL STABLE CORE (B: cybernetics ~8 survived; TRIZ's 40 stable; A: framework
   outlives inventory) -- target tens for a 150-1000 lesson corpus.
3. OPERATIONAL GROUNDING per primitive (B: bond graphs vs GST) -- our detector is the
   FUNNEL: a primitive that does not measurably improve retrieval value gets deprecated.
4. MDL AS THE ADOPTION GATE (C: DreamCoder/Stitch -- adopt iff total description
   shortens) = codex C3's objective, now with a working precedent.
5. NAMING IS LOAD-BEARING (C: LILO -30pts undocumented; B: GoF's power = shared
   vocabulary) -- AutoDoc mandatory; primitives join the LEXICON (ubiquitous language).
6. RETRIEVAL = MAC/FAC (C): cheap structure-correlated embedding of the SCHEMA RENDER
   (trigger/purpose + mechanism/move, roles anonymized -- Hope 2017's purpose/mechanism
   precedent: 0.739 vs 0.630, 38pct vs 21pct ideas) + LLM structural verify on top-k.
7. DECAY GUARDS (B): when-NOT-to-apply clause + provenance edges + the Norvig test
   (substrate workarounds graduate into hooks, not index entries).
8. SCOPE + ECONOMICS (A): bounded job, cheaper to use than bypass, visible win on
   first use; kill criterion stated before starting.

S4 RECIPE (rides the sharpening loop; slices, each gated):
- S4a SCHEMA RENDERS: during S2 consolidation, each lesson also gets a shape render
  (trigger-shape + move-shape, entities->roles) + its Tests field (GPT-chat adoption).
  No new substrate: renders are regenerable projections over atoms.
- S4b SHAPE CHANNEL IN RECALL (MAC): separate embedding index over schema renders;
  recall-at gains a structural candidate stream merged with the keyword/topic stream;
  FAC = existing FAITH/render gate + optional LLM verify. GATE: held-out precision@k
  vs raw-embedding baseline (DreamCoder-style measurement); funnel altitude tag
  "shape" so value rate is measurable per channel.
- S4c PRIMITIVE MINING: clusters of schema renders recurring ACROSS topic boundaries =
  candidates; adopt iff MDL improves (Stitch criterion); each adopted primitive gets
  name + docstring + 2 canonical examples + when-NOT-to-apply + provenance edges +
  LEXICON entry. Core capped at ~tens.
- S4d NORVIG PASS: any mined primitive that is really a substrate gap -> build the
  hook/guardrail instead and graduate the constituent lessons.
- KILL CRITERION: if the shape channel does not beat baseline retrieval on held-out
  lessons within its first evaluation cycle, S4b ships nothing and S4c never starts.
SEQUENCE: S1 (value-rate triage) -> S2 (consolidation + Tests fields + schema renders)
-> S4b -> S4c/d. S3 (bench-as-oracle) rides Wave B independently.
