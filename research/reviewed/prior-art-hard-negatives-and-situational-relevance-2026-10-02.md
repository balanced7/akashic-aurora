# Prior art: confidently-wrong retrieval on near-duplicates, and situational relevance

**Commissioned 2026-10-02 by claude (Vandor)** for W0.3, the third sweep of the night. The question
put to the researcher described our sibling swap without naming our codebase: two situations sharing
almost all vocabulary but differing in MECHANISM, where the correct document for situation A ranks
first for B and fourth for A under lexical scoring with IDF damping.

**PRESERVED VERBATIM**, unedited, per the house rule. The researcher's own §7 of flagged and
unverified items is part of the evidence and is kept intact, including their citation corrections.

---

## THE FOUR THINGS THIS CHANGES FOR US, so they are not lost in the volume

**1. Our floor experiment was run in 2000, on our exact document type, with our exact result.**
Rhodes' Margin Notes study (MIT PhD thesis, ch. 5.3) had readers rate auto-generated annotations on
their own papers:

| | all annotations | top 20% by relevance score |
|---|---|---|
| general relevance | 3.3 | **3.9** |
| usefulness | **2.7** | **2.7** |

Thresholding on the retriever's own relevance score raised judged RELEVANCE and left judged
USEFULNESS completely flat. That is `F-recall-floor-078`, falsified 26 years earlier by someone who
was pushing retrieved documents at a person doing a task. His conclusion, in his words, is that
relevance was a necessary but not sufficient condition for usefulness.

**2. He named our abstain class and measured its cause.** Rhodes coined **"too relevant to be
useful"** for items rated highly relevant and useless. Of those items, **100% were already known to
the rater and 68% were written by them.** Our corpus has exactly that structure: agents author
lessons and then meet them. Navi's N4 is literally "knowledge authored by the actor, in the store,
needed at the path", and the seeded M2 is "the knowledge was authored by the same actor in the same
hour". We have been treating self-authored recall as the strongest case for the surface. Rhodes
measured it as the dominant source of relevant-but-useless. Both readings can be true at once, and
which one holds is now a measurable question rather than an assumption.

His long-term log study is the other number to sit with: **186,480 suggestions displayed, 197
followed, 0.1%**, over 740 calendar days. He flags it himself as anecdotal and not statistically
significant. Our own funnel is 24,344 surfaced and 532 ever judged, 2.2%. Same regime.

**3. The lens for the sibling swap is a 1993 dissociation, not a retrieval paper.** Gentner,
Rattermann & Forbus separate **retrievability from inferential soundness**: surface similarity
governs what gets retrieved from memory, structural similarity governs what is sound to use, and the
two are measurably dissociated. MAC/FAC (Forbus, Gentner & Law 1995) is retrieve-then-rerank
twenty-five years early, with a cheap non-structural matcher feeding a structural one. The
case-based-reasoning version is Smyth & Keane 1998: retrieve by **adaptability** rather than
similarity, because the most similar case is not the most useful one. Our N3/N6 pair is this exactly
-- same surface, different mechanism -- and it says the fix is a second stage that scores mechanism,
not a better first-stage score.

**4. Our document type has its own literature and we did not know.** Weber, Aha, Muñoz-Avila &
Breslow, "Active Delivery for Lessons Learned Systems" (EWCBR 2000), and Weber & Aha, "Intelligent
delivery of military lessons learned" (*Decision Support Systems* 2003). The architecture is a
**monitor embedded in the authoring tool** that watches the user update domain objects and alerts
them to the ramifications of past experiences: the lesson is pushed into the task rather than
searched for. That is our recall-at-action hook, with a 2000-2003 precedent we have never read.
Also directly on our abstention measure: ProCIS (Samarinas & Zamani, SIGIR 2024) introduces
**npDCG**, a metric built to score engaging at an opportune MOMENT rather than merely retrieving the
right thing. We re-invented that as the bench's abstention row.

**AND ONE WARNING AIMED STRAIGHT AT TONIGHT'S FIX.** Mozannar, Bansal, Fourney & Horvitz (AAAI
2024), from 535 programmers: **using suggestion acceptance as the reward signal for deciding when to
display leads to suggestions of reduced quality.** Our `usefulness_factor` ranks on acceptance
(`useful` votes). Tonight's commit fixed it to estimate over judgments instead of impressions, which
removes the anti-popularity defect but does NOT address this one. Worth a pin before we lean harder
on vote-derived ranking.

---
---

# Confidently-wrong retrieval on near-duplicate documents: what the literature says

*(researcher's full text, unedited)*

**How this was verified.** Primary full texts I extracted and read myself: Saracevic 2007 Part II
(JASIST), Rhodes' 2000 MIT PhD thesis, plus paper-level extraction of RocketQA, ANCE, Zhan et al.,
NevIR, HANS, Reproducing NevIR, Rank1, Drowning in Documents, FollowIR, and the cross-encoder
mechanism paper. Teammates read primary PDFs for the relevance-theory, BM25-pathology and
proactive-IR strands. Everything not verified from a paper or a reliable record is flagged in §7.
The session's WebSearch quota (200 calls) was exhausted partway, so late verification ran through
arXiv, Crossref, OpenAlex, ERIC and publisher records.

Your failure shape — **document correct-for-A ranks 1st for B and 4th for A, under lexical scoring
with IDF damping** — sits at the intersection of five literatures that mostly don't cite each other.
The honest summary is that **every one of them has characterised your failure, and none of them has
solved it.**

---

## 1. Hard negatives: the problem is named, and the canonical definition is your failure verbatim

**The characterisation.** DPR (Karpukhin, Oğuz, Min, Lewis, Wu, Edunov, Chen, Yih; EMNLP 2020)
defines its "BM25" negative class as the top BM25 passages that match most question tokens but do
not contain the answer. That is precisely your situation-B document: maximal vocabulary overlap,
wrong on the decisive detail. The field's name for your bad-ranking document is *hard negative*, and
the name for a system that cannot separate it from the right one is a dual-encoder without
hard-negative training.

DPR's ablation (NQ dev, top-20 / top-100 accuracy):

| Negatives | Top-20 | Top-100 |
|---|---|---|
| Gold, 7, no in-batch | 63.1 | 78.3 |
| Gold, 31, in-batch | 70.8 | 82.1 |
| Gold + 1 BM25 negative | **77.3** | 84.4 |
| Gold + 2 BM25 negatives | 76.4 | 84.0 |

One hard negative buys +6.5 points; the second buys nothing. DPR also reports the inverse failure in
its own error analysis: it fails on rare salient phrases where BM25 succeeds.

**Why mining them matters, formally.** ANCE (Xiong, Xiong, Li, Tang, Liu, Bennett, Ahmed, Overwijk;
ICLR 2021) gives the variance-reduction argument: convergence rate depends on gradient variance, the
optimal sampling distribution is proportional to per-instance gradient norm, and for standard
ranking losses a near-zero loss implies a near-zero gradient — so easy negatives contribute almost
nothing. With batch size far below corpus size and few informative negatives in the corpus, the
probability that a random mini-batch contains an informative negative is near zero. Measured: MS
MARCO passage dev MRR@10 — BM25 0.240, DPR 0.311, ANCE 0.330; MS MARCO doc Recall@1k 0.387 → 0.648;
NQ top-20/100 59.1/73.7 → 81.9/87.5; TriviaQA 66.9/76.7 → 80.3/85.3. Latency 11.6 ms versus 1.42 s
for a BERT reranking cascade. Their own case analysis says ANCE's residual errors are documents that
are topically related but not exactly relevant — i.e. the hard-negative problem survives
hard-negative training.

**And here is the part that should interest you most: harder is not monotonically better.**

RocketQA (Qu, Ding, Liu, Liu, Ren, Zhao, Dong, Wu, Wang; NAACL 2021) manually examined top-retrieved
MS MARCO passages that carried no positive label and found **70% of them were actually positive**.
Their ablation (MRR@10, MS MARCO dev):

| Training negatives | MRR@10 |
|---|---|
| In-batch | 32.39 |
| Cross-batch | 33.32 |
| **Hard negatives, no denoising** | **26.03** |
| Hard negatives, cross-encoder-denoised | 36.38 |
| + data augmentation | 37.02 |

Naive hard negatives are **6.4 points worse than random in-batch negatives**. The fix is a
cross-encoder used as a filter — a second, more expensive model whose job is exactly to tell the
near-duplicates apart.

Cai, Guo, Fan, Ai, Zhang & Cheng (CIKM 2022, "Hard Negatives or False Negatives") replicate this as
a general IR finding: sampling top-ranked results from a *stronger* retriever makes the learned
ranker *worse*, and they trace the root cause to pooling bias in dataset construction rather than to
hard negatives per se. Their fix is a Coupled Estimation Technique that learns a relevance model and
a selection model jointly.

Zhan, Mao, Liu, Guo, Zhang & Ma (SIGIR 2021, STAR/ADORE) add the theory: random sampling minimises
total pairwise errors with an unbounded per-query loss (0.2% of queries contribute 60% of the total
error), while hard-negative sampling minimises top-K errors with loss bounded by K. But *static*
hard negatives have three named risks — the quality bound is loose; gradient descent actively pushes
the fixed negatives down the ranking, so they go stale; and a zero-loss model can still have MRR
approaching 1/|C|. Measured: MS MARCO doc dev MRR@100 — random 0.330, static BM25 negatives **0.316**
(worse), STAR 0.390, ADORE+STAR 0.405. Static sampling makes training MRR fluctuate wildly and
periodically dip below random.

Follow-ons that sharpen the prescription: **SimANS** (Zhou et al., EMNLP 2022) samples *ambiguous*
negatives ranked near the positive rather than the hardest, on the empirical grounds that the
hardest are disproportionately false negatives. **NV-Retriever** (Moreira, Osmulski, Xu, Ak,
Schifferer, Oldridge; 2024) formalises this as positive-aware thresholds — TopK-MarginPos (positive
score minus 0.05) and TopK-PercPos (95% of the positive score) — moving average nDCG@10 from 0.5407
to 0.5856 at small scale and 51.44 to 60.55 at large scale.

**Contrastive-learning theory names the mechanism.** Robinson, Chuang, Sra & Jegelka (ICLR 2021)
give a controllable-hardness importance-sampling family; Kalantidis et al. (NeurIPS 2020, MoCHi)
synthesise hard negatives by mixing. The most explanatory result is Wang & Liu (CVPR 2021): the
contrastive loss is hardness-aware, temperature controls the penalty on hard negatives, and there is
a **uniformity–tolerance dilemma** — pushing uniformity hard makes the representation intolerant of
semantically similar items and destroys local semantic structure. That is the trade-off you are
actually choosing between: a space that separates near-duplicates and a space that keeps them
together.

**Two structural results worth knowing.** Radovanović, Nanopoulos & Ivanović (JMLR 2010) show
*hubness*: in high-dimensional vector spaces a few points become nearest neighbours of
disproportionately many queries, as an intrinsic property of the geometry. That is the vector-space
version of "one document wins for everything" — though I found no lexical-retrieval analogue. And
Weller, Boratko, Naim & Lee (2025, "On the Theoretical Limitations of Embedding-Based Retrieval",
plus the LIMIT dataset) prove the number of top-k document subsets any single-vector embedding can
return is bounded by its dimension, and show state-of-the-art models failing on trivially simple
queries as a consequence.

**Survey:** Wischounig, Abdallah & Jatowt, "Negative Sampling Techniques in Information Retrieval: A
Survey" (Findings of EACL 2026) — 35 papers, taxonomy of random / statically-or-dynamically-mined /
synthetic.

**One label-side caveat on all of the above.** Arabzadeh, Vtyurina, Yan & Clarke ("Shallow pooling
for sparse labels") had crowd workers compare a modern neural ranker's top result against the
judged-relevant MS MARCO passage; the workers preferred the unjudged neural result often enough that
a hypothetically perfect MRR ranker would be *beaten* by a real system. Your "ranks fourth where it
is right" may partly be a judgment artefact rather than a ranking artefact — worth checking before
you treat the gold label as ground truth.

---

## 2. Topical vs situational relevance: the theory says your retriever is structurally incapable, and has said so since 1973

This literature predicts your failure from first principles, and names it.

**Saracevic's manifestations.** The five-way enumeration originates at Saracevic 1996 (CoLIS 2, p.
214) and reaches canonical form in Saracevic 2007, "Relevance: A review of the literature and a
framework for thinking on the notion in information science. Part II: Nature and manifestations of
relevance," *JASIST* **58(13):1915–1933** (note: widely miscited as 58(3), including on his own
publications page). The list, with his criterion of inference for each:

| Manifestation | Relation between | Criterion |
|---|---|---|
| System / algorithmic | a query and the objects in the system's file, as retrieved or failed-to-be-retrieved by a given algorithm | comparative algorithmic effectiveness |
| Topical / subject | the topic expressed in the query and the topic the objects cover | **aboutness** |
| Cognitive / pertinence | the user's state of knowledge and the objects | correspondence, informativeness, **novelty**, quality |
| **Situational / utility** | **the situation, task, or problem at hand** and the objects | usefulness in decision making, appropriateness to resolving the problem, uncertainty reduction |
| Affective | the user's intents, goals, emotions, motivations and the information | satisfaction, success, accomplishment |

Your system computes column 2 (topical). Your actual requirement is column 4 (situational).
Saracevic's own vocabulary for this gap, at p. 1930, is **weak versus strong relevance**: bare
topical correspondence is weak relevance, relevance derived beyond topicality is strong relevance,
and he states flatly that systems construct weak relevance while people construct strong. He adds
(p. 1929) that it has so far not proved possible to substantively integrate subjective relevance
into information objects and retrieval algorithms.

**The decisive precursor.** Wilson, "Situational Relevance," *Information Storage and Retrieval*
9(8):457–471 (1973): situationally relevant items are those that answer, or logically help answer,
*questions of concern*, and significant situational relevance is explained in terms of **changes of
view** relative to those concerns. He builds it on Cooper's logical relevance (Cooper 1971, *ISR*
7(1):19–37, where a sentence is relevant iff it belongs to some minimal premiss set entailing the
request), on *evidential* relevance from inductive logic, and on a personal stock of knowledge plus
a set of personal concerns. Wilson's direct/indirect split matters for you: an item inside a concern
set is directly situationally relevant; one relevant but outside it is only indirectly so.

**The clean statement of your exact failure.** Cosijn & Ingwersen, "Dimensions of Relevance,"
*Information Processing & Management* 36(4):533–550 (2000), p. 539, give the canonical
false-positive case: a paper may be topically relevant while repeating earlier results. They also
state the structural claim directly (p. 541): neither the system nor its algorithms are relevant to
the *context* from which the user directs the query, because intention always derives from context
and the algorithm has no access to it. They add socio-cognitive relevance as a further layer and
argue, against Saracevic, that motivational relevance is an attribute (intention) rather than a
manifestation and that affective relevance is an influence on the others rather than a category.

**The nested-set reading, which is the optimistic one.** Soergel (1994), as reported by Saracevic
(Part II p. 1930): an object is topically relevant if it can help answer the question; *pertinent*
if topically relevant **and** appropriate for the user; and has *utility* if pertinent **and** gives
new information. On this view topicality is necessary but never sufficient — and every pertinence or
utility failure is, by construction, a topical false positive. That is a precise description of what
you observed.

**The pessimistic reading.** Harter, "Psychological relevance and information science," *JASIS*
43(9):602–615 (1992), opens with an outright rejection of topical relevance, substitutes relevance
tied to dynamically changing cognitive state, and at p. 613 charges that topical relevance concerns
itself only with a restricted form of language and that the user is ignored. Green, "Topical
relevance relationships. I. Why topic matching fails," *JASIS* 46(9):646–653 (1995), argues from
recall failures, citation analysis and knowledge synthesis that topical relevance relationships are
*not* limited to matching — and in certain circumstances are quite likely not to be matching
relationships at all. Hersh (*JASIS* 45(3):201–206, 1994, p. 201) argues topical relevance cannot
measure a system's impact on its users and that a situational definition is required instead.

**What users actually use beyond topic, measured.** Schamber, Eisenberg & Nilan, "A re-examination
of relevance: toward a dynamic, situational definition," *IP&M* 26(6):755–776 (1990), p. 774,
conclude relevance is multidimensional and user-perception-dependent; dynamic, depending on judgment
at a point in time; and complex but systematic and measurable — *conditional* on being approached
conceptually and operationally from the user's perspective. That conditional is almost always
dropped in citation. Xu & Chen, *JASIST* 57(7):961–973 (2006), build a five-factor model from Grice
— topicality, novelty, reliability, understandability, scope — and find topicality and novelty
essential, understandability and reliability significant, **scope not significant**. Barry (*JASIS*
45(3):149–159, 1994) yields 23 categories in seven groups; Barry & Schamber (*IP&M* 34(2–3):219–236,
1998) find ten criteria common across two radically different populations, evidencing a finite
criteria set. Saracevic's Part III consolidation over 16 clues studies gives seven groups — content,
object, validity, **use/situational match**, cognitive match, affective match, belief match — with
the verdict that content criteria (including topicality) rate highest in importance but interact
with the others and are never the sole criteria.

**Evaluation implications, and the formal statement of what your retriever assumes.** Saracevic Part
III, p. 2133, enumerates the five postulates behind all Cranfield-derived evaluation: relevance is
**topical** (the query–object relation rests *solely* on a topicality match), **binary**,
**independent**, **stable** (judgments do not change as cognitive or situational factors change),
and **consistent**. His verdict in the summary is that **none of the five holds** — immediately
followed by the observation that using them anyway produced major improvements in IR technique.
Supporting numbers: Janes (*JASIS* 45(3):160–171, 1994) had 48 non-users re-judge documents
previously judged by their actual owners, with user/non-user agreement of 57% and 72%; Gull's 1956
first-ever IR evaluation collapsed at 30.9% agreement after reconciliation; assessor overlap across
populations hovers around 30% (lowest reported 3.5%, Haynes et al. 1990); Sormunen found 25% of
TREC-relevant documents judged not relevant on re-assessment and 36% only marginally relevant.

**Modern re-derivation.** Mao, Liu, Zhou, Nie, Song, Zhang, Ma, Sun & Luo, "When does Relevance Mean
Usefulness and User Satisfaction in Web Search?" (SIGIR 2016, pp. 463–472): external-assessor
relevance labels and searcher-reported usefulness come apart; a usefulness-based measure correlates
better with satisfaction; assessors *can* annotate usefulness **when given more search-context
information**. That last clause is the only operational optimism in the whole strand.

**The methodology for evaluating the thing you actually care about.** Borlund & Ingwersen, *Journal
of Documentation* 53(3):225–250 (1997), and Borlund, *Information Research* 8(3) paper 152 (2003): a
**simulated work task situation** is a short cover story describing a situation that leads a person
to need the system; it has two functions, triggering an individually interpreted information need,
and serving as the platform against which *situational* relevance is judged. Her objection to
Cranfield is that it treats the need as static and fully reflected by the query. Her measures are
**Relative Relevance** (cosine agreement between two sets of assessments — e.g. algorithmic versus
situational) and **Ranked Half-Life**. Borlund (*JASIST* 54(10):913–925, 2003) reports that many
researchers regard situational relevance as the most realistic type of user relevance. Borlund 2016
(*JDoc* 72(3):394–413) is a meta-evaluation finding the instrument is used inconsistently and that
realism of the situation description is essential.

---

## 3. Lexical over-match: BM25/TF-IDF have a documented pathology here, and IDF has a specific one

**The forward problem (vocabulary mismatch), for calibration.** Furnas, Landauer, Gomez & Dumais,
*CACM* 30(11):964–971 (1987): across five domains, two people favoured the same term with
probability **below 0.20**; single-keyword access produces **80–90% failure rates**; rich aliasing
improves success by factors of three to five. Zhao & Callan quantify the query-dependent version:
term necessity P(t|R) averages 0.38–0.43 on description queries and 0.54–0.59 on title queries, i.e.
**a query term mismatches 40–50% of its own relevant documents** (SIGIR 2012). Oracle necessity
weights gain 30–80% MAP; predicted ones 10–25%.

**The inverse problem, stated by the same authors.** Zhao & Callan (SIGIR 2012) say explicitly that
the retrieval model penalises relevant documents lacking the term *while simultaneously favouring
false positives that happen to contain it* — and because false positives vastly outnumber relevant
documents, they bury the true results throughout the ranked list. That is your failure in one
sentence, from the term-mismatch literature itself.

**IDF's specific pathology.** Robertson, "Understanding inverse document frequency," *Journal of
Documentation* 60(5):503–520 (2004): under the Robertson–Spärck Jones forms, a term occurring in
more than half the collection receives a **negative weight** — he calls this an odd prediction for a
query term, that its presence should count against retrieval — and traces it to a fixed
relevance-probability assumption unreasonable for frequent terms. He also concludes the
information-theoretic justifications for IDF are problematic on event-space grounds, and notes that
a Shannon-style account gives no reason to score only query terms.

Fang, Tao & Zhai (SIGIR 2004) turn this into a measured defect. They formalise six retrieval
constraints and show **no** standard formula satisfies all of them unconditionally. For Okapi/BM25:
if df(w) > N/2 the IDF is negative, and then the formula violates the term-frequency,
length-normalisation and TF-length constraints — **matching an additional occurrence of a query term
can decrease the document's score**. They predict this will hurt verbose queries specifically, and
confirm it across seven collections, with Wilcoxon signed-rank p < 0.013 in all verbose conditions.
Lucene's BM25Similarity guards against it by construction, using log(1 + (docCount − docFreq +
0.5)/(docFreq + 0.5)) rather than the classical RSJ form.

Note also that the damping is deliberate. Robertson & Zaragoza (*FnTIR* 3(4), 2009, §3.4.2) state
that any single term's contribution cannot exceed a saturation point however often it occurs, and
call that a valuable property. If your discriminative token is *repeated* in the right document,
saturation is designed to throw that signal away.

**The root cause: term independence.** Robertson & Zaragoza concede term independence is a much more
arguable step than the rest of the derivation, taken for tractability; and in §3.8 they state the
probabilistic relevance framework largely ignores positional information, for two reasons — no sound
formal model exists without a parameter explosion, and position has empirically shown surprisingly
little average effect. **A bag of independent terms cannot represent a configuration.** Metzler &
Croft (SIGIR 2005) give the causal statement: independent query terms match many irrelevant
documents, whereas matching against specific patterns of *dependent* terms filters many of those
out. Measured MAP gains over full independence: AP +5.2%, WSJ +7.1%, WT10g +6.6–9.8%, **GOV2 +13.2–13.7%
MAP and +18.1–20.7% P@10**.

**The NLP analogue, with the sharpest numbers in this whole report.** McCoy, Pavlick & Linzen,
"Right for the Wrong Reasons" (ACL 2019), define the **lexical overlap heuristic** — assume the
premise entails any hypothesis built from its words — and build HANS to break it. MNLI-trained
models, with chance at 50%:

| Model | Overlap → entailment | Overlap → **non**-entailment | MNLI test |
|---|---|---|---|
| DA | 99% | **1%** | 72% |
| ESIM | 98% | **1%** | 77% |
| SPINN | 96% | **2%** | 67% |
| BERT | 95% | **16%** | 84% |

Humans: 76% (crowd), 97% (linguists). MNLI's training distribution rewards the heuristic roughly 8:1
(2,158 supporting versus 261 contradicting examples for lexical overlap). This is the measured form
of "confidently right when overlap happens to align, confidently wrong when it doesn't." Rajaee,
Yaghoobzadeh & Pilehvar (EMNLP 2022) add a *reverse* bias on low-overlap pairs, and find existing
debiasing methods ineffective against it.

**The retrieval benchmarks built on your exact pair structure.** NevIR (Weller, Lawrie & Van Durme,
EACL 2024) takes 2,556 document pairs from CondaQA that differ only in a negation — 112–117 words
each, average length difference about 4 words — with one query relevant to each member. Paired
accuracy, random = 25%: **TF-IDF 2.0%**, SPLADEv2 8.0–8.7%, DPR 6.8%, bi-encoders up to 11.1%,
ColBERTv2 13.0% / v1 19.7%, cross-encoders 22.4% (RocketQAv2) rising through monoT5 base 34.9% to
monoT5-3B 50.6%; humans 100%. **Important caveat the authors state themselves:** they exclude BM25
because it behaves like TF-IDF here given the small collection and intra-pair lexical similarity,
and annotators were instructed not to use words appearing in only one paragraph — so the
construction *guarantees* lexical failure rather than measuring it in the wild.

ExcluIR (Zhang, Zhang, Wu, Pei, Ren, de Rijke, Chen & Ren, 2024) is the cleaner measurement for
your purposes: 3,452 manually annotated exclusionary queries, random reciprocal rank = 50%. **BM25
scores 53.48%, docT5query 53.85%** — barely above random. And the number that matters most: **BM25's
Recall@100 is 95.77% for positive documents and 94.74% for negatives.** Lexical retrieval reliably
surfaces *both* twins and cannot order them. QUEST (Malaviya, Shaw, Chang, Lee & Toutanova, ACL
2023) reports the same for implicit set operations, with negation and conjunction hardest.

**The direction where lexical wins.** Sciavolino, Zhong, Lee & Chen (EMNLP 2021) show BM25 at 72.0%
top-20 on EntityQuestions against DPR's 49.7%, with per-relation gaps up to 65.8 points — because
there the decisive token is a rare entity string. Formal, Piwowarski & Clinchant (ECIR 2022) tie
BM25's relative advantage specifically to the mean IDF of important terms rising on the target
collection (7.3 → 10.9). **So the decisive-token case splits by frequency: when the discriminating
token is rare, lexical scoring is the method that works; when it is common or absent, lexical
scoring is the method that cannot work.** Your description — IDF-damped, discriminative detail not a
rare token — puts you squarely in the second regime.

**Near-duplicate corpora specifically.** Broder (1997) defines resemblance over w-shingles and
clustered 30M+ AltaVista documents into 3.6M clusters; Charikar (2002) gives the cosine LSH
(simhash). Both are *purely syntactic* set-overlap measures — maximal, by construction, for a pair
differing in one decisive token. Bernstein & Zobel (CIKM 2005) measured the consequence: **16.6% of
all relevant documents in TREC 2004 Terabyte runs are content-equivalent**, and applying a novelty
principle drops MAP by 20% on average, with many content-equivalent pairs carrying *inconsistent*
relevance judgments. Fröbe, Bittner, Potthast & Hagen (ECIR 2020) reproduce and extend: **23.39% of
GOV2 is retrieval-equivalent**; their worst case is TREC Web 2012 topic 194 ("designer dog breeds")
where **40 of 47 relevant documents are content-equivalent**, all derived from one Wikipedia
article; worst-case rank penalties range from 8 to 53 positions. Fröbe, Bevendorff, Reimer, Potthast
& Hagen (SIGIR 2020) add the training-side effect: near-duplicates receive the same relevance label
with probability above 97%, and learning-to-rank models trained without deduplication lose **30%
nDCG@20** on average.

**The learned-sparse response, and its limit.** doc2query (Nogueira, Yang, Lin & Cho, 2019)
decomposes its own gain: expanding with *new* words only moves MRR@10 from 18.4 to 18.8, with
*copied* words only to 19.7, and with both to 21.5 — i.e. **term re-weighting is worth roughly three
times what closing the vocabulary gap is worth.** docTTTTTquery reaches 0.277 and SPLADE 0.322 on MS
MARCO dev while claiming to inherit exact matching and inverted-index efficiency. But **SPLADEv2
scores 8.0–8.7% on NevIR, below the 25% random baseline and indistinguishable from plain
bi-encoders.** Learned sparse expansion buys recall against the vocabulary gap and buys essentially
nothing against two near-identical documents differing in a decisive detail.

---

## 4. Rerankers: the standard fix, measurably better, measurably insufficient

**The lineage.** monoBERT (Nogueira & Cho, 2019, "Passage Re-ranking with BERT") took MS MARCO
passage dev MRR@10 to 36.53 (eval 35.87), a 27% relative gain over the prior state of the art,
against a BM25 baseline around 0.184–0.187. monoT5 recasts it as sequence-to-sequence true/false
generation (Nogueira, Jiang, Pradeep & Lin, EMNLP Findings 2020), reaching 0.3980 at 3B;
Expando-Mono-Duo (Pradeep, Nogueira & Lin, 2021) adds a pairwise duoT5 third stage. Rosa,
Bonifacio, Jeronymo, Abonizio, Fadaee, Lotufo & Nogueira ("In Defense of Cross-Encoders for
Zero-Shot Retrieval", 2022) attribute the generalisation specifically to parameter count **and early
query–document interaction**, with their largest cross-encoder beating a state-of-the-art bi-encoder
by more than 4 average BEIR points — and report that bi-encoders as first stage give no gain over
BM25 out of domain.

Listwise and LLM rerankers: RankGPT (Sun, Yan, Ma, Wang, Ren, Chen, Yin & Ren, EMNLP 2023) uses
permutation generation with a sliding window, and distils a 440M model that beats a 3B supervised
model on BEIR. RankZephyr (Pradeep, Sharifymoghaddam & Lin, 2023) matches or exceeds GPT-4 on TREC
DL and on the post-cutoff NovelEval set. Pairwise Ranking Prompting (Qin, Jagerman, Hui, Zhuang, Wu,
Yan, Shen, Liu, Liu, Metzler, Wang & Bendersky, NAACL 2024) argues pointwise and listwise prompts
are formulations off-the-shelf LLMs do not fully understand, and shows Flan-UL2 (20B) performing
comparably to the best GPT-4-based approach while beating InstructGPT-175B by over 10% on all
metrics and ChatGPT by 4.2% nDCG@10 across seven BEIR tasks. **The PRP argument is directly relevant
to you: reducing the task to "which of these two is better" is what makes LLM rankers reliable.**

**The measured answer on near-duplicate discrimination specifically.** NevIR is the controlled
instrument, and the arc across architectures is the headline result of this entire report (paired
accuracy, random = 25%, human = 100%):

| Architecture | Score |
|---|---|
| TF-IDF | 2.0% |
| Learned sparse (SPLADEv2) | 8.0–8.7% |
| Bi-encoders (DPR → multi-qa-mpnet) | 6.8–11.1% |
| Late interaction (ColBERT v2 / v1) | 13.0 / 19.7% |
| Cross-encoders (RocketQAv2 → monoT5-3B) | 22.4 → **50.6%** |

Van den Elsen, Barkhof, Nijdam, Lupart & Aliannejadi ("Reproducing NevIR", SIGIR 2025) extend it to
current models:

| Model | NevIR paired accuracy |
|---|---|
| gte-Qwen2-7B-instruct | 19.0% |
| **Promptriever-mistral-7b** | **19.7%** (below chance) |
| OpenAI text-embedding-3-large | 22.6% |
| GritLM-7B | 39.0% |
| bge-reranker-v2-m3 | 43.5% |
| jina-reranker-v2-base-multilingual | 65.2% |
| GPT-4o-mini (listwise) | 64.1% |
| GPT-4o (listwise) | 70.1% |
| o3-mini (listwise) | **77.3%** |

Their conclusion: only cross-encoders and listwise LLM rerankers reach reasonable performance,
listwise LLM rerankers gain about 20 points over the previous best category, and all still fall
short of humans. Rank1 (Weller, Ricci, Yang, Yates, Lawrie & Van Durme, 2025) confirms with a
reasoning-distilled reranker: NevIR 65.1% (7B) / 67.5% (14B) / 70.1% (32B) against RankLlama-7B's
31.6% and monoT5-3B's 34.9%; on BRIGHT, nDCG@10 27.5/28.7/29.4 against RankLlama-7B 13.9 and
monoT5-3B 16.8 — with an ablation showing the non-reasoning variant at 17.5 versus 27.5, so roughly
**two-thirds of the gain is attributable to test-time reasoning rather than to the model**.

**Three findings that complicate the "just add a reranker" conclusion.**

*(a) Rerankers have their own confidently-wrong mode, and it gets worse with more candidates.*
Jacob, Lindgren, Zaharia, Carbin, Khattab & Drozdov, "Drowning in Documents" (ReNeuIR @ SIGIR 2025):
in **53.3% of academic and 44.4% of enterprise experiments**, scaling the number of scored
candidates produced Recall@10 **worse than first-stage retrieval alone**. They name the pathology
**phantom hits** — rerankers assigning high scores to documents with no lexical or semantic overlap
with the query, in their qualitative analysis ranking documents about dishwashing and exercise
thousands of positions above true positives. Cross-encoders were robust in only 23.3%/22.2% of
experiments; GPT-4o-mini listwise reranking was the one approach that improved monotonically with
candidate count.

*(b) The mechanism may be inherited rather than replaced.* Lu, Chen & Eickhoff, "Pathway to
Relevance: How Cross-Encoders Implement a Semantic Variant of BM25" (EMNLP 2025), locate 13
attention heads computing a soft term frequency (attention/semantic-similarity correlation 0.500
versus 0.132 elsewhere), document-length effects in the same heads, and a low-rank embedding
direction correlating −71.36% with IDF. A linear model over these components predicts cross-encoder
scores with median Pearson 0.8401 / Spearman 0.7619 and 88.4% nDCG@10 alignment, against BM25's
0.4570. The authors are careful that this is an incomplete account — but it is the natural
mechanistic hypothesis for why cross-encoders only *partly* fix your problem: they are running a
semantic BM25, with the same damping, over better representations.

*(c) Scores are not calibrated, so "confident" means nothing.* Cohen, Mitra, Lesota, Rekabsaz &
Eickhoff, "Not All Relevance Scores Are Equal" (SIGIR 2021), argue ranking systems emit point scores
with no uncertainty estimate and give an approximate-Bayesian treatment that improves risk-aware
reranking and calibration, naming cutoff prediction as the downstream application. Bahri, Zheng,
Tay, Metzler & Tomkins ("Surprise", SIGIR 2023) take the same premise — relevance scores are often
poorly calibrated — and fit a Generalized Pareto Distribution from extreme value theory to produce
interpretable calibrated scores.

**The instruction/condition-following strand, which is where "mechanism differs" has been studied
directly.** FollowIR (Weller, Chang, MacAvaney, Lo, Cohan, Van Durme, Lawrie & Soldaini, 2024)
repurposes TREC assessor narratives as instructions and introduces p-MRR, a pairwise metric that is
positive when newly non-relevant documents correctly *drop* in rank. Results: no-instruction IR
models average **−3.9** (only monoT5-3B positive at +2.5); instruction-trained IR models generally
negative, GritLM-7B at about 0.0; API models mixed (Gecko +2.3); instruction-tuned LMs all positive,
FollowIR-7B best at **+12.2**. Their diagnostic ablation is the one you should note: for models that
perform poorly, replacing the full instruction with extracted keywords changes performance by **±1
point** — they are using the instruction as a bag of keywords, not as a condition.

Promptriever (Weller, Van Durme, Lawrie, Paranjape, Zhang & Hessel, 2024) shows a bi-encoder *can*
be trained to follow instructions (+14.3 p-MRR / +3.1 nDCG on FollowIR, +12.9 Robustness@10 on
InstructIR, +1.4 BEIR) — but scores **19.7% on NevIR, below chance**. Instruction-following and
near-duplicate discrimination are not the same capability. InstructIR (Oh, Lee, Ye, Shin, Jang, Jun
& Seo, 2024) reports the opposite-signed finding: instruction-tuned retrievers such as INSTRUCTOR
can **underperform** their non-instruction-tuned counterparts, which they attribute to overfitting
on existing instruction-aware retrieval datasets. InfoSearch (Zhou, Zheng, Chen, Zheng, Su, Zhang,
Meng & Shen, ICLR 2025) tests six document-level attributes with SICR and WISE metrics and finds
most models fall short of compliance despite gains from fine-tuning and scale.

**Why standard benchmarks hid this.** BRIGHT (Su, Yen, Xia, Shi, Muennighoff, Wang, Liu, Shi,
Siegel, Tang, Sun, Yoon, Arik, Chen & Yu, 2024) states the premise explicitly: existing retrieval
benchmarks consist of queries where keyword or semantic matching is usually sufficient.
SFR-Embedding-Mistral scores 59.0 nDCG@10 on MTEB and **18.3 on BRIGHT**; explicit reasoning about
the query buys up to 12.2 points.

**And the downstream cost of your specific failure, measured.** Cuconasu, Trappolini, Siciliano,
Filice, Campagnano, Maarek, Tonellotto & Silvestri, "The Power of Noise" (SIGIR 2024): the
retriever's **highest-scoring but non-answer-bearing** documents *negatively* affect the LLM, while
adding *random* documents improved accuracy by up to 35%. A near-miss is worse than noise. **This is
contested:** Mazuryk, Dolmans, Gehringer, Klaric, Ju & Aliannejadi, "The Powerless Noise" (SIGIR
2026 reproducibility), confirm the effect under the original restrictive setup with
earlier-generation LLMs but find it highly sensitive to prompt formulation and decoding limits, and
conclude the random-document benefit cannot be robustly confirmed as general. They do not, on the
evidence I read, overturn the harm from near-miss documents.

---

## 5. When the query is an action: the literature is old, the measurements are brutal, and nobody solved *when to fire*

**The lineage.** Hart & Graham, "Query-free information retrieval," *IEEE Expert* 12(5):32–37 (1997),
name the concept (system: Fixit). Lieberman's Letizia (IJCAI 1995) and Let's Browse (IUI 1998) treat
browsing as the query. Rhodes & Starner introduce the Remembrance Agent (PAAM 1996); Rhodes' MIT PhD
thesis *Just-In-Time Information Retrieval* (2000) is the full account; Rhodes & Maes, *IBM Systems
Journal* 39(3–4):685–704 (2000) is the canonical citation; Rhodes, *IEEE Transactions on Computers*
52(8):1011–1014 (2003) covers Jimminy, the wearable version driven by physical context. Budzik &
Hammond's Watson (IUI 2000, pp. 44–51; Budzik, Hammond & Birnbaum, *Knowledge-Based Systems* 2001,
pp. 37–53) watches everyday applications. Czerwinski, Dumais, Robertson, Dziadosz, Tiernan & van
Dantzich (CHI 1999, pp. 560–567) study visualised implicit queries.

**The measurement you should read before building anything.** I extracted Rhodes' thesis directly.
Two results matter.

*Long-term log study (ch. 5.4.2):* six self-selecting users, three Media Lab and three internet,
logs spanning three to seven months — **740 calendar days** total (312 with active use), **186,480
suggestions displayed, 197 followed: 0.1%**. Roughly two suggestions looked at per week. Only 49 of
the 197 were rated, averaging 3.1/5. The thesis itself states the sample is small, not statistically
significant, and should be taken as anecdotal — cite it as a direction, not a number.

*The Margin Notes relevance-versus-usefulness study (ch. 5.3), which is the exact experiment your
situation calls for:* readers rated automatically-generated INSPEC annotations on their own papers.

| | All annotations | Top 20% by relevance score |
|---|---|---|
| General relevance | 3.3 ± 0.3 | **3.9 ± 0.7** |
| Section relevance | 3.4 ± 0.3 | **4.0 ± 0.7** |
| Usefulness | **2.7 ± 0.3** | **2.7 ± 0.7** |

**Thresholding on the retriever's own relevance score raised judged relevance substantially and left
judged usefulness completely flat.** Rhodes' conclusion is that relevance was a necessary but not
sufficient condition for usefulness. Reasons given for non-usefulness: not relevant enough 42%,
already knew the citation 29%, low quality 12%, it was the rater's own paper 10%, don't need more
references 7%. Of the 14% of items rated low on usefulness but high on general relevance, **100%
were already known to the rater and 68% were written by them** — his gloss is that one might say
these documents were **"too relevant to be useful"** (Rhodes 2000, p. 99).

He then names your failure mode exactly. A second category of highly-relevant-but-useless items were
those so similar that no new information was presented — in one case the suggestion was the very
paper being annotated. Margin Notes attempts to detect and suppress documents almost identical to
the current environment, but, he writes, the detection cannot be perfect because documents can still
differ from the current environment in only trivial ways. He also notes that no suggestion may be
useful simply because the user does not need new information in the current environment — the
when-to-fire problem, stated in 2000. One of his low-quality examples is a mechanism mismatch: a
citation about formalisms for a field whose paper explicitly discounted formal approaches.

Corpus sensitivity: on a Media Lab email corpus rather than INSPEC, the same system scored relevance
2.6/2.8 and **usefulness 1.7**.

**Developer-tool recommenders that fire on activity.** Hipikat (Čubranić & Murphy, ICSE 2003, pp.
408–418; Čubranić, Murphy, Singer & Booth, *TSE* 2005, pp. 446–465); ROSE/eROSE (Zimmermann,
Weissgerber, Diehl & Zeller, ICSE 2004, pp. 563–572; *TSE* 31:429–445, 2005), the "programmers who
changed this also changed" recommender; Mylar/Mylyn (Kersten & Murphy, "Using task context to
improve programmer productivity," FSE 2006, pp. 1–11) with its degree-of-interest model; Strathcona
(Holmes & Murphy, ICSE 2005). Robillard, Walker & Zimmermann's IEEE Software 2010 overview and the
2014 *Recommendation Systems in Software Engineering* book are the field's own retrospectives.

**Where "when to fire" has actually been measured.** Horvitz's expected-cost-of-interruption line:
Horvitz & Apacible, "Learning and Reasoning About Interruption" (ICMI 2003, pp. 20–27); BusyBody
(Horvitz, Koch & Apacible, CSCW 2004, pp. 507–510); notification deferral policies (Horvitz,
Apacible & Subramani, UM 2005). The modern, directly-measured instance is Mozannar, Bansal, Fourney
& Horvitz, "When to Show a Suggestion? Integrating Human Feedback in AI-Assisted Programming" (AAAI
2024): a utility-theoretic framework, CDHF, that cascades acceptance-likelihood models to
**selectively hide** suggestions, evaluated retrospectively on data from **535 programmers**,
cutting both latency and verification time. Their stated pitfall is the one to carry away: **using
suggestion acceptance as the reward signal for deciding when to display leads to suggestions of
reduced quality.** Their companion CHI 2024 paper (CUPS, 21 programmers) quantifies the
per-suggestion verification cost that makes a false fire expensive.

**The field's formalisation of timing.** Samarinas & Zamani, "ProCIS: A Benchmark for Proactive
Retrieval in Conversations" (SIGIR 2024): 2.8M conversations with depth-k pooled judgments,
annotations linking documents to the *parts* of the conversation they relate to, and a new metric,
**normalized proactive discounted cumulative gain (npDCG)**, built to evaluate engaging at an
opportune moment rather than merely retrieving the right thing. That is the closest thing to a
solution to "when to fire": not an algorithm, but a metric that penalises firing at the wrong time.

**IR's own abstention machinery, which is the under-used answer.** Deciding how many results to
return — including zero — is a named task with a 15-year literature: Arampatzis, Kamps & Robertson,
"Where to stop reading a ranked list? Threshold optimization using truncated score distributions"
(SIGIR 2009), using score distributions alone; Bahri, Tay, Zheng, Metzler & Tomkins, "Choppy: Cut
Transformer for Ranked List Truncation" (SIGIR 2020), assumption-free and optimising any
user-defined metric from relevance scores only; Wu, Zhang, Guo, Fan, Lan & Cheng, "AttnCut" (AAAI
2021); Ma, Ai, Wu, Shao, Liu, Zhang & Ma, "LeCut"/"JOTR" for legal search (SIGIR 2022), jointly
optimising truncation and reranking; Bahri et al., "Surprise" (SIGIR 2023), explicitly motivated by
poor score calibration; and Meng, Arabzadeh, Askari, Aliannejadi & de Rijke (SIGIR 2024) applying
ranked-list truncation in LLM-reranking pipelines. Upstream of this sits query performance
prediction — Cronen-Townsend, Zhou & Croft's clarity score (SIGIR 2002) and successors — which
estimates *whether a retrieval will succeed* without relevance judgments. Note that QPP's own
evaluation is contested: Faggioli, Zendel, Culpepper, Ferro & Scholer (ECIR 2021; *IRJ* 2022, sMARE)
argue the standard evaluation framework is deficient.

**The RAG version of the same question.** Mallen, Asai, Zhong, Das, Khashabi & Hajishirzi, "When Not
to Trust Language Models" (ACL 2023), introduce PopQA (14k questions) and an adaptive scheme that
retrieves non-parametric memory **only when necessary** — keyed on entity popularity — improving
performance while reducing inference cost. SELF-RAG, FLARE and Adaptive-RAG extend the
when-to-retrieve decision.

**The two domain-closest precedents, both pre-2005.** First, the lessons-learned literature, which
is literally your document type: Weber, Aha & Becerra-Fernandez, "Intelligent lessons learned
systems," *Expert Systems with Applications* (2001); Weber, Aha, Muñoz-Avila & Breslow, "Active
Delivery for Lessons Learned Systems" (EWCBR 2000); Weber, Aha, Branting, Lucas & Becerra-Fernandez
(FLAIRS 2000), whose architecture is a **monitor** embedded in a plan-authoring system that watches
the user update domain objects and alerts them to the ramifications of past experiences — i.e. the
lesson is pushed into the task, not searched for; and Weber & Aha, "Intelligent delivery of military
lessons learned," *Decision Support Systems* (2003).

Second, and most structurally illuminating, **analogical retrieval in cognitive science**. Gentner,
Rattermann & Forbus, "The Roles of Similarity in Transfer: Separating Retrievability From
Inferential Soundness" (*Cognitive Psychology*, 1993) is the canonical dissociation: surface
similarity drives what gets *retrieved* from memory, structural similarity drives what is *sound* to
use. Forbus, Gentner & Law's MAC/FAC (*Cognitive Science*, 1995) is the architectural answer and is,
essentially, retrieve-then-rerank twenty-five years early: a computationally cheap **non-structural**
matcher over content vectors, then the Structure-Mapping Engine computing a detailed structural
match — explicitly built to explain why structural commonalities dominate similarity judgments
*despite* surface similarity governing retrieval. The case-based reasoning version is Smyth &
Keane, "Adaptation-guided retrieval: questioning the similarity assumption in reasoning"
(*Artificial Intelligence* 102, 1998): retrieve by *adaptability* rather than by similarity, because
the most similar case is not the most useful one. If you want a single framing for your problem that
predates every retrieval paper above: surface overlap is a retrievability signal, mechanism is a
soundness signal, and the two are measurably dissociated.

---

## 6. Where the literature genuinely disagrees

1. **Does topicality have primacy?** Saracevic names two schools explicitly (Part II, p. 1930).
   Soergel 1994's nested set makes pertinence and utility *follow from* topicality. Green 1995,
   Harter 1992, Hersh 1994 and Swanson & Smalheiser's literature-based discovery work hold that
   relevance exists where no topical relation does. Saracevic refuses to adjudicate and splits the
   difference as weak/strong relevance.

2. **Is situational relevance operationalisable?** Swanson (1986, p. 395) called describing
   subjective relevance for IR purposes essentially intractable, and Saracevic judged the
   pessimistic side pragmatically ahead. Against that, Borlund's simulated work task situations plus
   Relative Relevance, and Cosijn & Ingwersen's claim that the manifestations can realistically be
   applied and compared; and Saracevic's own Part III bottom line that relevance *is* measurable.
   Mao et al. (2016) add the empirical middle ground: assessors can judge usefulness **if given
   situational context**.

3. **Does assessor disagreement invalidate evaluation?** Voorhees 2000 (p. 714) found relative
   system performance stable despite marked judgment differences. Voorhees 2001 contradicted her own
   earlier result for *highly* relevant documents, with assessor agreement on the single best page
   at 34%. Harter 1996 holds the whole edifice unsound.

4. **Does term position/configuration matter?** Robertson & Zaragoza argue a human could often judge
   relevance from scrambled words and that the fraction of queries requiring position is small.
   Metzler & Croft's dependence-model gains are *largest on the largest collection* (GOV2, +13.2%
   MAP), which is exactly where the independence assumption should hurt most. These cannot both be
   right about your regime.

5. **Is BM25 actually a strong out-of-domain baseline?** BEIR reports DPR at −47.7% average versus
   BM25; Lin (SIGIR Forum 2018) documents weak-baseline inflation in the neural literature. But
   Kamalloo, Thakur, Lassance, Ma, Yang & Lin (2023) show BEIR's BM25 number depends on an unaudited
   multi-field Elasticsearch indexing choice (multi-field 0.429, flat 0.424, wordpiece 0.404), and
   **BEIR's own authors concede a strong lexical bias in the benchmark**, since lexical models
   dominated the pooling that produced its labels. Both camps are partly arguing about the measuring
   instrument.

6. **Is harder better in hard-negative mining?** ANCE and the general contrastive literature say
   yes; RocketQA (26.03 vs 32.39), Cai et al. (explicitly "opposite results"), Zhan et al. (static
   negatives *below* random on MS MARCO doc) and SimANS say the hardest negatives are
   disproportionately false negatives and that the optimum is strictly interior. NV-Retriever's
   95%-of-positive threshold is the current operational answer.

7. **Does instruction-conditioning help?** FollowIR and Promptriever report large gains; InstructIR
   reports instruction-tuned retrievers *underperforming* their base models from overfitting on
   instruction-retrieval data. And Promptriever's own 19.7% on NevIR — below the 25% chance line —
   shows the two capabilities are separable.

8. **Do near-miss documents hurt downstream?** Cuconasu et al. (SIGIR 2024) say yes, and that random
   documents help by up to 35%. Mazuryk et al. (SIGIR 2026) reproduce the effect only under the
   original narrow configuration and decline to confirm it generally.

9. **Hjørland versus the cognitive view.** Hjørland (*JASIST* 61(2):217–237, 2010) argues the
   subject-knowledge/epistemological view Saracevic called most fundamental in 1975 was then almost
   entirely neglected in favour of views resting on less fruitful assumptions, and relocates
   relevance in domain analysis and a social paradigm — rejecting *both* poles of the system/user
   dichotomy. Nicolaisen (*Information Research* 22(1), 2017) formally refutes the Hjørland &
   Christensen relevance equation, showing that applying logical probability theory to it implies
   either nothing is relevant or everything is (his lottery case: all 1,000 tickets come out
   relevant).

---

## 7. Flagged: unverified or weakly sourced

- **Items taken from a teammate's reading rather than mine:** Henzinger, Chang, Milch & Brin's
  "Query-free news search" (WWW 2003) precision of 84–91% and an abstention filter worth roughly +20
  precision points at a recall cost; Zamani et al.'s MIMICS figure that 82.8% of 414,362 Bing
  clarification panes received zero engagement; Czerwinski et al.'s CHI 1999 null results; Mozannar
  et al.'s 15.21 s mean verification cost and 25.3–52.9% suppression rate; a Chen et al. CHI 2025
  finding of identical productivity with preference falling from 90% to 47% on firing cadence alone.
  Citations verified; the numbers are second-hand to me.
- **Bernstein & Zobel 2005's own numbers** are quoted via the Fröbe et al. reproductions, not from
  the original PDF.
- **Gentner, Rattermann & Forbus 1993**: existence, venue and citation count verified via OpenAlex;
  the specific retrieval-versus-soundness percentages were not obtained. The MAC/FAC architectural
  claim is verified.
- **Smyth & Keane 1998** (*Artificial Intelligence*, 175 citations): bibliographic record verified;
  full text and abstract not obtained (ScienceDirect 403). Treat the "similarity ≠ adaptability"
  framing as well-attested by title and secondary use, not quoted.
- **Cooper 1971** and **Schamber, Eisenberg & Nilan 1990**: abstracts not obtainable (Elsevier).
  Content via Saracevic's full text and Borlund's page-cited attribution.
- **Hjørland 2010**: no open-access copy exists; abstract-level only. His sentence-level critique of
  Saracevic's framework is *not* verified.
- **HANS per-cell table** and **Sciavolino et al. numbers**: single-source extractions from ar5iv
  HTML, not line-verified against the published PDFs.
- **Lv & Zhai**, "When documents are very long, BM25 fails!" (SIGIR 2011) and "Lower-bounding term
  frequency normalization" (CIKM 2011) — the canonical BM25 TF-normalisation pathology papers —
  could not be retrieved. This is the main gap in §3.
- **Letizia** (Lieberman, IJCAI 1995) is not in Crossref; cited from secondary attestation.
- **No paper establishes "BM25 degrades on short documents."** BM25's documented length pathologies
  run in the long direction. The nearest verified claim is Metzler & Croft's: short documents starve
  the machinery that would otherwise model term *configuration*.
- **Citation corrections worth propagating:** Saracevic 2007 Part II is *JASIST* **58(13)**:1915–1933,
  not 58(3) — his own publications page is wrong. Harter 1992 is *JASIS* **43(9)**:602–615;
  Saracevic's own reference list misprints it as 53(4). Hjørland & Christensen is **2002, *JASIST*
  53(11)**:960–965, not 55(11)/2004 (55(11) is Vakkari & Sormunen 2004).
