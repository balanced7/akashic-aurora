# Prior art: when a retrieval surface should return NOTHING

**Commissioned 2026-10-02 by claude (Vandor)** for W0.3, after `recall-bench` measured abstention
0/5 and after the pre-registered forecast `F-recall-floor-078` was FALSIFIED on held-out moments.
The question put to the researcher was narrow and deliberately not about our codebase: *is an
absolute threshold on a similarity/relevance score known to work, or known to fail?*

**PRESERVED VERBATIM.** This is the researcher's full report, unedited, per the house rule that
frontier reports are persisted before they are synthesised. Our own reading of it, and what we
build from it, belongs in the slice notes and the fence, never in edits to this file. The
researcher's own "could not verify" list is part of the evidence and is kept intact.

**Why it matters to us in one line:** our show-nothing floor IS an absolute threshold on a raw
relevance score, and this report is the reason its falsification was predictable rather than bad
luck.

---

# When to return nothing: what the literature actually establishes

**Headline answer.** There is a strong and old consensus against an absolute threshold on a raw
similarity/relevance score as a *portable* abstention rule. The consensus is not "it never works" —
it is that the number is a property of a particular model + corpus + query distribution, not of
relevance, so it has to be *fitted against labels* and *refitted on any change*, and that
everything which generalises across queries is either a calibrated probability or a
per-query-normalised statistic of the score *list* rather than the score *level*. The strongest
single sentence in the literature is from Bahri et al., writing specifically about embedding/ANN
retrieval: relevance scores are often not well calibrated, and "what distance constitutes relevance
varies from query to query and changes dynamically as more documents are added to the index"
(*Surprise: Result List Truncation via Extreme Value Theory*, Bahri, Zheng, Tay, Metzler &
Tomkins, arXiv:2010.09797, SIGIR 2023 — abstract verified verbatim).

---

## 1. Chow's rule and selective prediction: what the theory demands

**Chow, C.K. (1970), "On optimum recognition error and reject tradeoff," IEEE Trans. Information
Theory 16(1):41–46** (925 citations per OpenAlex) established the reject option: abstain iff the
maximum posterior probability falls below a threshold *t*, with the cost-optimal threshold
*t = (C_r − C_c)/(C_e − C_c)* in the costs of rejection, correct decision and error. Two things
follow, and they are the whole answer to the question as posed:

- **The thresholded quantity must be the true posterior.** Chow's rule is Bayes-optimal only when
  *p(y|x)* is known. The canonical modern survey — **Hendrickx, Perini, Van der Plas, Meert &
  Davis, "Machine learning with a reject option: a survey" (Machine Learning, 2024;
  arXiv:2107.11277)** — states the limitation flatly: obtaining complete knowledge of the class
  distributions is not realistic, and when posteriors are merely *estimated*, Chow's rule "is not
  suitable" and the threshold should instead be learned via a cost-based approach. **Fumera, Roli &
  Giacinto, "Reject option with multiple thresholds," Pattern Recognition 33(12):2099–2101 (2000)**
  is the empirical demonstration: Chow's rule degrades when posterior estimates carry error, and
  class-specific thresholds give a better error–reject tradeoff.
- **Threshold-on-a-black-box-score is formally a *learning* problem, not a tuning knob.** **Franc,
  Průša & Voráček, "Optimal Strategies for Reject Option Classifiers" (JMLR 24, 2023)** prove that
  the cost-based, bounded-improvement (guaranteed selective risk, maximal coverage) and
  bounded-abstention (guaranteed coverage, minimal selective risk) formulations all reduce to the
  same strategy: the Bayes classifier plus a randomised Bayes selection function. They then define
  a **proper uncertainty score** — the scalar summary sufficient to construct that selection
  function — and give two algorithms to *learn it from examples* for an arbitrary black-box
  classifier. That is the precise statement of what a sound reject option requires: not a score,
  but a score that is a proper uncertainty score, which for a black box must be estimated from
  labelled data.

The modern selective-prediction line (El-Yaniv & Wiener, JMLR 11:1605–1641, 2010, *On the
foundations of noise-free selective classification*) measures everything on the **risk–coverage
curve**. Note the technical consequence for the absolute/relative question: the risk–coverage curve
is invariant to any monotone transform of the confidence score, so **only the ordering of the
confidence score carries information; its numeric level carries none**. What converts an ordering
into a threshold with a guarantee is a held-out labelled sample. **Geifman & El-Yaniv, "Selective
Classification for Deep Neural Networks" (NeurIPS 2017, arXiv:1705.08500)** make this explicit:
their SGR procedure picks θ on a labelled set sampled i.i.d. from *P*, using the Gascuel–Caraux
exact binomial tail bound with a δ/k split over candidate thresholds, yielding e.g. a guaranteed 2%
top-5 ImageNet error at ~60% coverage with probability 99.9%. The guarantee is entirely contingent
on the i.i.d. assumption.

Two refinements worth naming. **Kamath, Jia & Liang, "Selective Question Answering under Domain
Shift" (ACL 2020)** found that abstaining on softmax probability alone fares poorly because models
are overconfident out of domain, and trained a separate *calibrator* to predict model error — i.e.
they replaced the score threshold with a learned rejector. **Fisch, Jaakkola & Barzilay, "Calibrated
Selective Classification" (arXiv:2208.12084)** sharpen what ordinary selective classification does
*not* buy you: it can still accept high-confidence wrong predictions and reject low-confidence
correct ones, so they add a *selective calibration* requirement over the accepted set. **Traub et
al., "Overcoming Common Flaws in the Evaluation of Selective Classification Systems" (NeurIPS 2024,
arXiv:2407.01032)** show the standard metric (AURC, built on selective risk) is non-monotone — you
can improve the classifier or the confidence ranking and get a worse score — and propose AUGRC;
metric rankings changed on 5 of 6 datasets. Treat published selective-classification comparisons
with that in mind.

---

## 2. Score normalisation in IR: why raw scores are not cross-query comparable

This is settled, and it is settled in the primary sources rather than in folklore.

**The score-distribution tradition.** Swets (*Science* 141:245–250, 1963; *American Documentation*
20:72–89, 1969) modelled retrieval as signal detection with separate score distributions for
relevant and non-relevant documents — first two equal-variance normals, later unequal-variance
normals or two exponentials. Bookstein (*IPM* 13(6):377–383, 1977) attacked the normal pair and
proposed two Poissons; Baumgarten (SIGIR 1999) used shifted gammas. **Manmatha, Rath & Feng,
"Modeling score distributions for combining the outputs of search engines" (SIGIR 2001, pp.
267–275)** is the pivot: fit, *per query*, an exponential to non-relevant scores and a normal to
relevant scores, recover the components from the unlabelled total by EM, and convert score →
posterior probability of relevance by Bayes' rule, then average those probabilities for metasearch
(validated on TREC-3 and TREC-4 over INQUERY, SMART and an LSI engine). The companion **Manmatha &
Sever, "A Formal Approach to Score Normalization for Meta-search" (HLT 2002)** states the premise
directly — scores from different engines are usually not comparable — and reports that normalising
by equalising the non-relevant exponentials beat the heuristics (TREC-3 top-5 engines: 0.4614 mean
non-interpolated precision vs 0.4579 min-max and 0.4447 ZMUV). **Kanoulas, Pavlu, Dai & Aslam
(ICTIR 2009)** proposed gamma for non-relevant plus a mixture of normals for relevant; **Dai, Pavlu,
Kanoulas & Aslam (ECIR 2012)** documented EM's sensitivity to initialisation and local optima — a
practical warning for anyone fitting these online.

**The validity constraint, which is the deepest point.** **Robertson, "On score distributions and
relevance" (ECIR 2007, LNCS 4425:40–51)** formalises a *Recall–Fallout Convexity Hypothesis*: a
valid pair of distributions must produce a convex ROC, because a concave stretch could be improved
by randomly re-ordering it — so a model implying non-convexity implies a trivially improvable
system. Verdict: two exponentials pass, two Poissons pass, two gammas pass over a wide range, two
normals pass only with equal variances, and **the now-standard normal/exponential mixture always
violates convexity at both ends**. His §5.3 is the key observation for your question: because any
monotone transformation leaves the ranking untouched, observed score distributions may reflect
accidental implementation choices rather than anything about relevance. **Arampatzis & Robertson,
"Modeling score distributions in information retrieval" (Information Retrieval 14(1):26–46, 2011;
with Kamps, ICTIR 2009)** add two in-the-limit hypotheses that reject two exponentials and two
Poissons for the relevant class, leaving two gammas as the likeliest universal model; they fit all
110 runs of the TREC 2004 Robust track (250 topics) and note that scores vary wildly across models,
are incomparable across engines *and across different requests on the same engine* when request
length varies, and that no single threshold serves all purposes because the optimum depends on the
effectiveness measure. **This is a direct disagreement between two papers by overlapping authors**
— Robertson 2007 admits exponential/exponential on convexity grounds; Arampatzis & Robertson 2011
reject it on limit grounds — and it is worth flagging that the field has not converged on a single
valid parametric family.

**Normalisation methods.** Lee (SIGIR 1997, *Analyses of multiple evidence combination*) established
that per-query normalisation substantially improves fusion. **Montague & Aslam, "Relevance score
normalization for metasearch" (CIKM 2001, pp. 427–433)** defined the canonical shift-and-scale
family — Standard (min-max), Sum, ZMUV — and found the choice of normalisation has a significant
effect on performance; in Manmatha & Sever's reproduction the normalisation mattered more than the
combination rule. The engineering endpoint is **Cormack, Clarke & Buettcher, "Reciprocal rank fusion
outperforms Condorcet and individual rank learning methods" (SIGIR 2009)**: throw the scores away
and fuse ranks. Elastic sells RRF on exactly this basis — no tuning required, indicators need not be
commensurable — which is a vendor conceding score incomparability as a design premise.

**BM25 and cosine specifically.** **Robertson & Zaragoza, "The Probabilistic Relevance Framework:
BM25 and Beyond" (FnTIR 3(4):333–389, 2009)**, §2.5: because the derivation freely drops and
transforms rank-preserving components, BM25 is not reversible into an explicit estimate of
probability of relevance, and the model must be considerably modified for any application needing
one — they cite adaptive filtering as exactly that case. BM25 is an unbounded sum of per-term
weights, so the same document–query pair scores differently purely as a function of query length
and IDF. **Robertson, "Threshold setting and performance optimization in adaptive filtering"
(Information Retrieval 5:239–256, 2002)** is the direct operational refutation: he calibrates BM25
per profile as log-odds ≈ α + β·(s_d / s_1%), where s_1% is *that topic's own* mean top-1% score — a
per-topic scale divisor — remarking that the score is typically very far from an actual probability.
Same paper, TREC-9: adaptive runs optimised for one utility measure scored mean utility of −6.32,
−7.29 and −4.40 (worse than retrieving nothing) while T9U-optimised runs on the same data scored
+9.70 to +46.53. **Same scores, different threshold policy, sign flip in utility.**

For embeddings the problem is geometric, not merely affine. **Ethayarajh (EMNLP-IJCNLP 2019,
arXiv:1909.00512)** measured the null baseline: contextual representations are anisotropic,
occupying a narrow cone, with GPT-2's average cosine between *uniformly random* words around 0.6 in
layers 2–8 and so extreme by layer 12 that two random words have near-perfect cosine. Any absolute
cosine threshold is meaningless without a model- and layer-specific null baseline. Related: Gao et
al. (ICLR 2019) on representation degeneration; Li et al. (EMNLP 2020, BERT-flow) on a non-smooth
anisotropic sentence space; Su et al. (2021) whitening. **Steck, Ekanadham & Kallus, "Is
Cosine-Similarity of Embeddings Really About Similarity?" (WWW 2024 Companion, arXiv:2403.05440)**
show analytically that cosine similarity can yield arbitrary similarities — **but note carefully:
this is proven for regularised linear models, and the deep-model implications in that paper are
discussion, not measurement.** It is routinely overstated.

The mechanistic reason the absolute scale is unpinned is, to my reading, best stated by **Yan, Qin,
Wang, Bendersky & Najork, "Scale Calibration of Deep Ranking Models" (KDD 2022)**: popular ranking
losses are **translation-invariant** — you can add a constant to all item scores without changing
the ordering or the loss — so nothing in training constrains the output scale, and advanced ranking
functions are not scale-calibrated. *(My own extension, flagged as inference rather than citation:
InfoNCE/softmax contrastive objectives used to train bi-encoders are likewise invariant to a
per-query shift in logits, so the same argument applies to cosine from contrastively trained
retrievers. I did not find a paper making that specific claim.)*

---

## 3. Query Performance Prediction: the field that replaced level with shape

QPP exists because absolute score level is a poor signal, and almost every established
post-retrieval predictor is either a divergence from a per-query reference or a dispersion
statistic — both of which cancel the query-specific scale.

- **Clarity Score** — Cronen-Townsend, Zhou & Croft (SIGIR 2002): KL divergence between a query
  language model and the collection language model; correlates positively with average precision
  across TREC sets. They also give an algorithm for automatically setting a clarity threshold to
  separate predicted-poor from acceptable queries — i.e. **the one classic "abstain" threshold in
  this literature is on a normalised divergence, set from training data, and collection-specific.**
- **WIG (Weighted Information Gain)** — Zhou & Croft (SIGIR 2007, pp. 543–550): the divergence of
  the mean top-*k* retrieval score **from the score the system assigns the whole corpus**, divided
  by √|q|. Note the two corrections built in: subtract a per-query reference level, divide out query
  length.
- **NQC (Normalized Query Commitment)** — Shtok, Kurland, Carmel, Raiber & Markovits, ICTIR 2009 /
  **ACM TOIS 30(2), 2012**: the standard deviation of top-*k* scores, **normalised by the corpus
  score**, as a surrogate for query drift. *(The standard reading is that low dispersion indicates
  drift and hence a harder query; I verified the authors, venue and the standard-deviation/query-
  drift framing from the abstract but did not read the directional statement verbatim in the primary
  text — flagged.)*
- **σ_max, σ_k, n(σ_x%)** — Pérez-Iglesias & Araujo (SPIRE 2010); Cummins, Jose & O'Riordan (SIGIR
  2011): dispersion measured at an adaptively chosen list depth so the tail does not dominate.
- **SMV** — Tao & Wu (2014): magnitude and variance together. **UEF** — Shtok et al. (2010):
  re-rank against a pseudo-effective reference list.

**Be honest about how well this works.** From the reproducibility study **Meng/Faggioli-lineage work
"Combining Query Performance Predictors: A Reproducibility Study" (arXiv:2503.24251, ECIR 2025)**:
best pre-retrieval Pearson ρ ≈ 0.63 / Kendall τ ≈ 0.39 on TREC 678; ρ ≈ 0.40–0.47 on Robust; ρ ≈
0.29 on ClueWeb09B; best post-retrieval on TREC DL ρ ≈ 0.59 (qppBERT-PL), ρ ≈ 0.62 for a BOLASSO
combination. Combining predictors bought under 2% on the older collections. And **Hauff, Hiemstra &
de Jong, "A case for improved evaluation of query difficulty prediction" (SIGIR 2009)** is the
standing methodological warning: a predictor's measured quality is *not consistent across retrieval
systems*, so published QPP results are largely not comparable and prediction should be evaluated
against a spectrum of systems. QPP is a real signal, but a weak one, and its own benchmark
literature is unstable.

**The directly-on-point recent evidence** is a preprint and should be labelled as such:
**Holdcroft, Abdallah & Jatowt, "The Magnitude Mirage: Rethinking Confidence for
Reasoning-Intensive Retrieval" (arXiv:2609.15578, Sept 2026, not peer reviewed)** evaluate six
zero-cost QPP metrics for RAG abstention over 28 datasets (BEIR, BRIGHT, TEMPO) and 11 retrievers
(BM25, 7 dense bi-encoders, 3 reasoning encoders). At *k*=25, abstention AUROC for **MaxScore (s₁)**
is .583–.754 on BEIR but collapses to **.520–.611 on BRIGHT** and **.536–.649 on TEMPO** — near
random. **Score Gap (s₁−s_k)** recovers to .724–.805, .605–.653 and .638–.709 respectively, gains up
to +0.158 AUROC; end-to-end on BRIGHT, 65.8% → 74.1% answer accuracy at 10% coverage. A second Sept
2026 preprint (arXiv:2609.22056, multi-hop retrieval) reaches the same conclusion with nine
distributional features (top-2 margin, peak-to-mean ratio, normalised entropy, per-hop), reporting
that entropy alone performs poorly while a logistic combination beats any single heuristic, and that
cross-dataset transfer costs only −0.5pp AUC. **Read both as suggestive, not settled.** Also read
the magnitudes honestly: the *better* relative signal is only moderately discriminative (AUROC
~0.6–0.8).

---

## 4. Production practice: what is shipped, and the structural gap nobody has closed

**No major vector database decides "nothing matched" for you**, and the clearest statement of why is
Microsoft's own Azure AI Search documentation: ANN search identifies nearest neighbours and always
returns *k* results even if they are not similar, so nonsensical or off-topic queries still produce
*k* hits. Their recommended mitigations are hybrid search and a minimum score threshold — **with the
explicit caveat that a minimum threshold is only applicable to a pure single-vector query, because
fused (RRF) ranges are small and volatile.**

What the vendors say about the number itself:

- **Weaviate**: `distance`/`certainty` exist, and the value depends on many factors including the
  vectorisation model; experiment with your data.
- **Qdrant**: `score_threshold` is framed as yours to supply if you know the minimal acceptance
  score for your model — plus the metric-direction trap (higher Euclidean = more distant).
- **Milvus** (`radius`/`range_filter`) and **OpenSearch** radial search (`min_score`/`max_distance`)
  illustrate with undefended constants (0.4, 0.95) and no calibration method.
- **Pinecone** has no native minimum; staff have told users to post-filter.
- **Elastic**: the kNN `similarity` parameter applies to the *raw* similarity, **not the document
  `_score`** — the knob lives in a different numeric space from the number users see. Elastic
  separately documents that scores are not even stable within one retriever, since index statistics
  differ across shard copies with deleted documents.
- **Vespa** gives the strongest vendor guidance I found, and it matches the research answer: setting
  `distanceThreshold` is best handled by supervised learning, because it should be calibrated on
  query complexity and on the feature distributions of the returned top-*k*.
- Framework layers are weakest. LangChain's `similarity_search_with_relevance_scores` advertises
  [0,1] while its own `_select_relevance_score_fn` docstring concedes the "correct" function depends
  on the metric and on the scale of your embeddings — a per-integration heuristic, with a long bug
  tail (langchain issues #10864, #11386). LlamaIndex's `SimilarityPostprocessor` ships
  `similarity_cutoff` with no default and no guidance.

**Weaviate autocut is the one shipped relative rule, and its limits matter.** Reading the source
(`entities/autocut/autocut.go`): it min-max normalises the returned distance list by its first and
last elements, subtracts the diagonal, and counts **local maxima** of that deviation; `autocut: N`
cuts at the Nth peak. That is a Kneedle-style maximum-curvature detector (the 2022 design issue
credits the `kneed` library). Three consequences: it is purely relative to the returned list, so the
cut depends on `limit`; it requires `relativeScoreFusion` for hybrid, so it does not work with RRF,
and an absolute threshold on a relativeScoreFusion score is close to meaningless because the top is
mapped to 1 and the bottom to 0; and **it can never return zero results** — if everything is bad but
evenly spaced it still hands back a group. It answers "how many", not "any".

**That gap is the central negative finding of the academic ranked-list-truncation literature.** The
line runs: **Arampatzis & van Hameren (SIGIR 2001)** score-distributional threshold optimisation for
adaptive filtering (with a central-limit argument whose Gaussian only forms for long queries — on
TREC vector-space scores, around k ≈ 250 terms); **Arampatzis, Beney, Koster & van der Weide (TREC-9,
2000)**; **Arampatzis, Kamps & Robertson (SIGIR 2009)**, which I read directly — ranked retrieval has
no clear cut-off point where to stop consulting results; they fit a truncated normal/exponential
mixture by EM with no relevance judgements, optimise F1@K on TREC Legal, and the optimal rank
formulation explicitly "allows for K to become 0, meaning that no document should be retrieved"
(verified verbatim). F1@K: 0.0751 → 0.1069/0.1032 (2007) and 0.0744 → 0.1356/0.1362 (2008), against
an oracle of 0.1848 for 2008. Caveat usually omitted: **the baseline was an older score-distribution
model, not a fixed cutoff.** They also note in passing that unbounded scores are conventionally
mapped to (0,1) by a logistic or "by normalizing with the per-query score range" — primary-source
confirmation that per-query normalisation is the standing practice.

Then: **BiCut** (Lien et al., ICTIR 2019) showed the parametric model is brittle on neural rankings
(0.2227 → 0.1660 on DRMM, because normal/exponential was fitted to tf·idf-era shapes); **Choppy**
(Bahri, Tay, Zheng, Metzler & Tomkins, SIGIR 2020, arXiv:2004.13012) runs a transformer over the
scalar score sequence — Robust04/BM25 F1: Oracle 0.367, Fixed-5/10/50 = 0.158/0.209/0.239, a single
tuned constant (Greedy-k) 0.248, BiCut 0.244, Choppy 0.272; **AttnCut** (Wu, Zhang, Guo, Fan, Lan &
Cheng, AAAI 2021, arXiv:2102.12793) reaches 0.2821 against Oracle 0.3591, motivated by the
observation that the best fixed point varies across datasets and metrics. Honest reading: on neural
rankings the learned methods beat a single well-tuned constant by a couple of points.

And then the result that should temper all of it: **Meng, Arabzadeh, Askari, Aliannejadi & de Rijke,
"Ranked List Truncation for Large Language Model-based Re-Ranking" (SIGIR 2024, arXiv:2404.18185)**
— 8 RLT methods × 3 retrievers × 2 rerankers on TREC-DL 19/20. I verified these from the paper's
HTML: their conclusion is that findings on RLT do not generalise well to the retrieve-then-re-rank
setup; Fixed-*k*(20) consistently achieves the best effectiveness/efficiency trade-off versus
supervised methods (DL-20 SPLADE++→RankLLaMA: Fixed-k(20) nDCG@10 0.778 at 0.60 s vs AttnCut 0.768
at 29.76 s); about 30% of queries do not need re-ranking at all with RepLLaMA as retriever; and
**"both methods fail to predict a re-ranking cut-off of zero."** The field has been optimising "how
many" and the abstain case is structurally outside its hypothesis space.

**The one abstention threshold in common use that is properly calibrated is SQuAD 2.0's.**
Rajpurkar, Jia & Liang (ACL 2018) make the no-answer decision a score threshold tuned separately for
each model on the development set; always-abstain scores 48.9 F1, which is the real floor. Devlin et
al. (NAACL 2019, §4.3) predict a span iff its score beats the null score `s_null` at `[CLS]` by τ,
with τ selected on dev to maximise F1. The engineering realisation is google-research/bert's README:
take `best_f1_thresh` from `null_odds.json` and feed it back as `--null_score_diff_threshold`, with
typical values between −1.0 and −5.0. **Watch the sign convention:** HuggingFace's `run_qa.py`
exposes the same flag with default 0.0, which is Devlin's τ=0, while Google's suggested −1…−5 demands
the span beat null by a margin — same knob, opposite sign, a live source of silent misconfiguration.

**Adaptive-retrieval RAG systems all use tuned, per-dataset thresholds, and that is itself the
finding.** Self-RAG (Asai et al., ICLR 2024) thresholds the normalised `Retrieve`-token probability
at δ=0.2 by default but δ=0 for ASQA. FLARE (Jiang et al., EMNLP 2023) triggers at θ=0.8 for three
datasets but θ=0.4 for StrategyQA, and reports performance degrading above ~50% retrieval there.
Adaptive-RAG (Jeong et al., NAACL 2024) trains a T5-Large router on ~400 silver labels per dataset
for +22.3 EM over never-retrieve but only **+2.3 EM over always-retrieve at 2.17× the steps**, with
"don't retrieve" the hardest class to predict. SKR (Wang et al., EMNLP 2023 Findings) harvests labels
empirically and gains +1.8 to +2.9. CRAG (arXiv:2401.15884, no venue I could confirm) sets its
evaluator thresholds empirically and per dataset — PopQA (0.59, −0.99), PubHealth/ARC (0.5, −0.91),
Biography (0.95, −0.91). **Folklore hygiene: the widely quoted 0.7/0.3 CRAG thresholds come from
third-party LangGraph implementations, not the paper.**

Two corrections to the motivating evidence. "The Power of Noise" (Cuconasu et al., SIGIR 2024) is
robust on the half that matters for abstention — near-miss related-but-answer-free documents cost up
to 0.38 absolute accuracy (−67%), and a single such document up to 0.24. The famous "random noise
helps" half is a single model/config cell, and a SIGIR 2026 replication, "The Powerless Noise"
(arXiv:2607.03615), reproduces it under the original setup and then shows it vanishes and reverses
under modern inference practice — the original 15-token generation cap produced 53.6% truncated
outputs. **Treat "distractors hurt" as robust and "noise helps" as an artifact.** Separately,
"Sufficient Context" (Joren et al., ICLR 2025, arXiv:2411.06037) finds large models fail to abstain
when context is insufficient, and are still correct about 35% of the time with insufficient context
— so a sufficiency signal alone is a poor abstain gate; combined with self-confidence it buys 2–10
points at equal coverage.

**Are reranker scores more absolutely interpretable? Mostly no.** Sentence-Transformers' own docs
contradict themselves (one page claims cross-encoders output 0–1; another says MS MARCO models return
logits; a third notes the raw value can reasonably span −10 to 10 and that sigmoid does not affect
ranking) — and none gives threshold guidance. monoT5 (Nogueira, Jiang, Pradeep & Lin, Findings of
EMNLP 2020) softmaxes the `true`/`false` logits and interprets them as ranking probabilities, but
neither it nor Expando-Mono-Duo claims calibration or discusses thresholds — and monoT5's own finding
that target-token choice changes effectiveness even between semantically close words argues against
reading that softmax as a principled probability. Cohere is admirably precise: scores are normalised
to [0,1] but **query-dependent** and could be higher or lower depending on the query and passages
sent in; a score of 0.91 does not mean twice as relevant; their prescribed method is 30–50 domain
queries each with a borderline-relevant document, averaging those as the reference threshold — i.e.
held-out calibration. BAAI states `bge-reranker-large`'s score is not bounded to a specific range.
Voyage and Jina document no range. BEIR (Thakur et al., NeurIPS 2021 D&B) and Rosa et al.
(arXiv:2212.06121) do show cross-encoders generalise best zero-shot, but that is per-query ranking
quality (nDCG@10), **not score-scale stability** — and I found no study measuring whether
cross-encoder score thresholds transfer across domains.

**Documented fixed-threshold failures.** The cleanest is a vendor's own: Pinecone's model page for
Cohere rerank warns that `cohere-rerank-4-fast` returns different relevance scores than
`cohere-rerank-3.5` and that hard-coded score thresholds must be re-tuned. Voyage advertises the
mirror image as a feature — Rerank 3 scores calibrated to match Rerank 2.5's distributions so
existing thresholds keep working — which concedes that normally you would have to re-tune. On the
retrieval side, a Pinecone community thread documents a 0.7 cosine threshold working for a
SentenceTransformer model and breaking on SPLADE, with Pinecone confirming SPLADE scores are not
normalised.

---

## 5. Calibration and conformal prediction

**Is cosine similarity calibrated? No, and there is a mechanism.** Yan et al. (KDD 2022) locate it in
the loss: ranking objectives are translation-invariant, so training never pins the scale. Penha &
Hauff, "On the Calibration and Uncertainty of Neural Learning to Rank Models for Conversational
Search" (EACL 2021) is the most useful IR-side result, and its framing is exactly the
decision-theoretic point you asked about: the Probability Ranking Principle holds only when **[C1]**
the models are well calibrated and **[C2]** probabilities of relevance are reported with certainty,
and they find BERT-based rankers are *not robustly calibrated*, while stochastic variants calibrate
better and the resulting uncertainty estimates help both risk-aware ranking **and predicting
unanswerable contexts**. That is the defensible version of an absolute threshold: *retrieve iff
P(relevant) exceeds the cost ratio* is sound (Robertson's PRP, 1977; Lewis & Gale's
utility-thresholding line in text classification), but only on the calibrated probability, never on
the raw score — and Robertson & Zaragoza say BM25 does not give you that probability without
modification.

**The machinery for turning a score into a probability** is Platt scaling (Platt 1999 — a sigmoid on
the score, fitted on held-out data), isotonic regression (Zadrozny & Elkan, 2001/2002 — a monotone
step function, also fitted on held-out data), and temperature scaling (Guo, Pleiss, Sun &
Weinberger, ICML 2017, *On Calibration of Modern Neural Networks*, which found modern networks are
poorly calibrated unlike older ones and that temperature scaling, a variant of Platt scaling, is a
surprisingly effective fix). **The structural point to extract: all three are monotone transforms of
the score.** A monotone transform cannot change the ranking, cannot change the risk–coverage curve,
and cannot change which items a *relative* rule selects. What it does is make the *number* mean
something — and it does so only by consuming labelled held-out data from the target distribution.
Calibration is not an alternative to collecting labels; it is a way to spend labels.

**Conformal prediction** gives the only distribution-free guarantee on offer, and the fine print is
what matters. From Angelopoulos & Bates, *A Gentle Introduction to Conformal Prediction and
Distribution-Free Uncertainty Quantification* (arXiv:2107.07511), verified verbatim: the guarantee is
**marginal coverage**, "averaged ... over the randomness in the calibration and test points"; the
theorem assumes the calibration and test points are i.i.d.; coverage conditional on the calibration
set is itself a random quantity; "in the most general case, conditional coverage is impossible to
achieve"; and practically, n = 1000 calibration points gives coverage typically between .88 and .92
for a nominal .90. Translate that into your question: **conformal prediction cannot tell you that
*this* query has no good answer.** It can tell you that, over the query distribution you calibrated
on, a procedure's prediction sets contain the right answer 90% of the time.

Applications to retrieval/RAG exist and are young. **TRAQ (Li, Park, Lee & Bastani, NAACL 2024,
arXiv:2307.04642)** claims the first end-to-end statistical correctness guarantee for RAG,
constructing conformal prediction sets over retrieved passages and generated answers with Bayesian
optimisation to shrink them — reducing set size by 16.2% on average against an ablation. C-RAG (Kang
et al., ICML 2024) does certified generation risk. The costs are consistent across this line and
should be stated plainly: (i) a labelled, exchangeable calibration set; (ii) a guarantee that is
marginal, not per-query; (iii) an output that is a *set*, so the "decision" is deferred rather than
made, and set sizes can be large enough to be uninformative; (iv) no validity under distribution
shift, which for a live corpus is the normal condition — and recall Bahri et al.'s observation that
the relevance-bearing distance shifts as documents are added to the index. Conformal risk control
(Angelopoulos, Bates et al.) extends the framework to arbitrary risk functions including abstention
rates, but inherits all four costs.

---

## Consensus, disagreement, and what I could not verify

**Consensus (strong).** (a) An absolute threshold on a raw BM25 score, dot product or cosine is not a
portable rule: the level is a property of the model, the corpus statistics, the query length and the
training objective's arbitrary scale, not of relevance. Primary support: Robertson 2007 (monotone
invariance), Robertson & Zaragoza 2009 (BM25 not reversible to a probability), Arampatzis &
Robertson 2011 (incomparable across requests; no single threshold for all purposes), Bahri et al.
2020/2023 (per-query, index-time-varying relevance distance), Yan et al. 2022 (translation-invariant
losses), Ethayarajh 2019 (anisotropic null baseline). (b) A threshold *is* sound on a calibrated
posterior probability of relevance, with the cutoff given by the cost ratio — Chow 1970 for
classification, the PRP and its [C1]/[C2] conditions for retrieval. (c) Absent calibration, the only
defensible absolute threshold is one *fitted on labelled held-out data from the same distribution and
refitted on every model, corpus or query-mix change* — the SQuAD 2.0 / BERT null-score discipline,
Cohere's borderline-document sampling, Vespa's supervised-calibration advice, Geifman & El-Yaniv's
i.i.d. binomial bound. (d) Everything that transfers across queries without labels is a *shape*
statistic of the returned list with a per-query normaliser: Clarity's divergence, WIG's subtraction
of the corpus score, NQC's corpus-normalised dispersion, Surprise's per-query extreme-value fit, the
top-1/top-2 margin.

**Where the literature disagrees.** (1) *Does a learned/relative cutoff actually beat one well-tuned
constant?* Choppy and AttnCut say yes by ~2 points on pre-neural rankings; Meng et al. (SIGIR 2024)
say no behind a strong retriever+reranker, where Fixed-k(20) wins on both effectiveness and a 30–50×
latency margin. (2) *Which score-distribution family is valid?* Robertson 2007 and Arampatzis &
Robertson 2011 reach incompatible verdicts on exponential/exponential, and the field's workhorse
normal/exponential is known to violate Robertson's convexity condition. (3) *Is margin/gap reliably
better than magnitude?* The two 2026 preprints say yes with gains of 0.09–0.16 AUROC, but they are
unrefereed and the absolute numbers remain modest (~0.6–0.8). (4) *How broadly does the cosine
critique apply?* Steck et al.'s result is proven for regularised linear models; its routine extension
to deep embeddings is not measured in that paper.

**The gap worth naming.** Virtually the entire ranked-list-truncation and QPP literature optimises
"how many results", not "any results". Only Arampatzis, Kamps & Robertson (SIGIR 2009) explicitly
admits K = 0 as an output, and it does so from a per-query distribution fit plus an explicit utility
measure — not a score threshold. Meng et al. confirm the practical consequence: supervised truncation
methods never predict zero, while ~30% of queries wanted zero.

**Could not verify.** Swets (1963, 1969) and Bookstein (1977) primaries (attributions come from
Robertson 2007 and Arampatzis/Robertson/Kamps 2009, which agree). The TREC-9 KUN filtering paper's
title and numbers (the verifiable title is "Incrementality, half-life, and threshold optimization for
adaptive document filtering"). NQC's directional statement verbatim from the primary text. Montague
& Aslam's and Fernández et al.'s internal numbers (reported as reproduced by Manmatha & Sever). A
*quantified* published measurement of per-query score-scale variance — the qualitative claim is
everywhere in primary sources, the number is nowhere I could reach. Any official OpenAI statement
that absolute cosine values are meaningless (the narrow-high-band claim rests on non-staff forum
posts and one vendor blog measuring ada-002 unrelated-pair similarity averaging ~0.809). The
semantic-cache claim that optimal thresholds differ by embedding model (MPNet 0.83 vs Albert 0.78) —
surfaced only in search snippets, not located in the MeanCache paper. The much-quoted "do not compare
relevance scores from different queries" passage is from *Elasticsearch: The Definitive Guide*, not
current Elastic docs. LeCut (SIGIR 2022) and MtCut (WSDM 2022) internal numbers (ACM returned 403).
CRAG, Astute RAG and RAGTruth have no venue I could confirm. One WebFetch extraction of the
Pérez-Iglesias & Araujo SPIRE 2010 paper returned a dispersion-direction claim *contradicting* NQC's
and a quoted sentence I could not corroborate in the source — **I discarded both as extraction
artifacts and have not relied on that paper's internals.** There is no standalone survey of ranked
list truncation; Meng et al. 2024 is a reproducibility study. Finally, TREC HARD-track set-retrieval
thresholds were not researched; the set-retrieval evidence here is TREC-9/TREC-11 Filtering and TREC
Legal 2007–2008 only.
