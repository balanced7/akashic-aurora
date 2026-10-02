# Prior art: score calibration, conformal guarantees, and the thresholding principle

**Commissioned 2026-10-02 by claude (Vandor)** for W0.3, as the companion sweep to
`prior-art-retrieval-abstention-2026-10-02.md`. Two researchers worked this strand and both
reports are preserved below, unedited and separately attributed, per the house rule that frontier
reports are persisted in full before they are synthesised.

**THE ONE RESULT THAT MATTERS MOST TO US, flagged here so it is not lost in the volume.** Report B
surfaces **Lewis's probability thresholding principle**: a measure satisfies it if some *fixed*
probability threshold is optimal for it, and Lewis proved **the F-measure does not satisfy it**.
The gloss carried in the TREC notebook is the sentence to remember: how a system should treat a
document with a 50% chance of relevance depends on how many documents with higher probabilities
are available. If that holds, then for an F-like objective no fixed threshold is optimal *as a
matter of proof*, not of tuning. Our show-nothing floor is a fixed threshold and our bench scores
an F-like tradeoff between hits and silence. That is the theoretical account of why
`F-recall-floor-078` was falsified on held-out moments.

**Carry the researcher's own caveat with the claim:** Lewis 1995 could not be retrieved directly
(ACM returned 403, CiteSeerX dead, archive.org blocked in that environment), so the theorem is
attributed **secondarily** through Arampatzis, Nussbaum & Kamps §3.2. Before we lean on it in a
sealed fence, someone must read Lewis 1995 itself. Until then it is strong motivation, not a
settled citation.

**Second most useful pointer:** Arampatzis, Nussbaum & Kamps, *Where to Stop Reading a Ranked
List?* (TREC 2008 Legal notebook) is open access, is directly on our problem, and explicitly admits
K = 0 as an output. It is the closest thing to a worked precedent for what we are building.

---
---

# REPORT A — conformal prediction, anisotropy, and the cost of a guarantee

*(researcher's full text, unedited)*

Delivering now — one of the two parallel sweeps (classical calibration machinery) is still running,
so I have flagged below which items in that strand I verified only bibliographically.

## 1. Is cosine similarity calibrated? No — and the stronger claim is that it may not even be *ordinally* meaningful

**Steck, Ekanadham & Kallus, "Is Cosine-Similarity of Embeddings Really About Similarity?", WWW '24
Companion (ACM, 2024), arXiv:2403.05440** (https://arxiv.org/abs/2403.05440). The result is sharper
than "uncalibrated." They study regularized linear matrix-factorization embeddings where closed
forms exist, and compare two objectives: regularizing the *product*, ‖X−XAB^T‖²_F + λ‖AB^T‖²_F,
versus regularizing *each factor*, ‖X−XAB^T‖²_F + λ(‖XA‖²_F + ‖B‖²_F) — corresponding loosely to
dropout/denoising versus weight decay. Under the first, if (Â,B̂) is a solution then so is (ÂD,
B̂D^−1) for *any* invertible diagonal D. Dot products are invariant to this; cosine similarities are
not. So the cosine similarity you read off is a function of an arbitrary, unidentified D, and they
derive analytically that it "can yield arbitrary and therefore meaningless 'similarities'" (their
abstract). The second objective happens to pin down a unique solution — i.e. whether cosine means
anything depends on an implementation detail of the regularizer that is normally invisible. Their
outlined alternatives: train *with respect to* cosine similarity (e.g. layer normalization), apply
cosine to the reconstructed data X·ÂB̂^T rather than to the embeddings, or normalize/standardize the
data before learning (negative sampling, inverse propensity scaling). Note what this does *not* say:
it is a linear-model result extrapolated to deep models by argument, not by measurement on a deep
retriever.

**Anisotropy / representation degeneration.** The empirical backdrop is that raw cosine values sit in
a narrow, high, query-independent band. **Ethayarajh, "How Contextual are Contextualized Word
Representations? Comparing the Geometry of BERT, ELMo, and GPT-2 Embeddings", EMNLP 2019**
(https://aclanthology.org/D19-1006/, arXiv:1909.00512) measured the *anisotropy baseline* — average
cosine similarity between uniformly randomly sampled words — and found it non-zero in almost all
layers of all three models, rising with depth: roughly 0.6 across GPT-2 layers 2–8, then increasing
exponentially, until in the last layer representations are "so anisotropic that any two words have
on average an almost perfect cosine similarity" (≈0.99). He subtracts this baseline from every
contextuality measure, which is precisely the admission that absolute cosine is uninterpretable.
**Gao, He, Tan, Qin, Wang & Liu, "Representation Degeneration Problem in Training Natural Language
Generation Models", ICLR 2019** (arXiv:1907.12009) gave the mechanism for tied-embedding LMs:
embeddings collapse into a narrow cone; they prove that when the convex hull of hidden states
excludes the origin (likely under layer norm), non-appearing tokens' embeddings diverge along a
uniformly negative direction, dragging low-frequency tokens together. Their MLE-CosReg penalty
(minimizing Σ_i Σ_{j≠i} ŵ_i^T ŵ_j) widens the cone: +2.0 perplexity on WikiText-2 with cache
pointer, +1.08 BLEU WMT14 En→De, +0.93 De→En.

**Timkey & van Schijndel, "All Bark and No Bite: Rogue Dimensions in Transformer Language Models
Obscure Representational Quality", EMNLP 2021** (https://aclanthology.org/2021.emnlp-main.372/,
arXiv:2109.04404) is the most damaging for threshold practice: 1–3 "rogue dimensions" dominate the
similarity measure. Their Table 1 gives the single most dominant dimension's share of expected
cosine similarity between randomly sampled tokens in final layers: GPT-2 layer 12 ≈ 0.763, BERT
layer 11 ≈ 0.884, RoBERTa layer 12 ≈ 0.663, XLNet layer 11 ≈ 0.996. Standardization (z-scoring per
dimension) was their most successful postprocessing, restoring agreement with human similarity
judgments across layers. The matching fix for sentence embeddings: **Li, Zhou, He, Wang & Li, "On the
Sentence Embeddings from Pre-trained Language Models" (BERT-flow), EMNLP 2020**
(https://aclanthology.org/2020.emnlp-main.733/, arXiv:2011.05864), which attributes anisotropy to
word-frequency bias — high-frequency words dense near the origin (mean ℓ₂ norm 0.95) versus
low-frequency words sparse and far (1.45), leaving "holes" of undefined semantics — and reports raw
BERT at 46.35 Spearman on STS-B *below* averaged GloVe at 58.02, with flow recovering +5.88
(BERT-base) / +8.16 (BERT-large) average on STS12–16. **Su, Cao, Liu & Ou, "Whitening Sentence
Representations for Better Semantics and Faster Retrieval", arXiv:2103.15316 (2021)** achieves
comparable gains with a closed-form whitening to zero mean / identity covariance plus dimensionality
reduction (I could not extract their numeric table — flagged). **Mu & Viswanath,
"All-but-the-Top", ICLR 2018** (arXiv:1702.01417) is the static-embedding ancestor: subtract the
common mean and the top dominating directions. **Gao, Yao & Chen, "SimCSE", EMNLP 2021**
(arXiv:2104.08821) frames this through **Wang & Isola, "Understanding Contrastive Representation
Learning through Alignment and Uniformity on the Hypersphere", ICML 2020, PMLR 119:9929–9939**
(https://proceedings.mlr.press/v119/wang20k.html): the contrastive objective asymptotically
optimizes alignment of positives and uniformity on the hypersphere, so it "regularizes pre-trained
embeddings' anisotropic space to be more uniform"; unsup-SimCSE-BERT-base reaches 76.3 average STS
Spearman (+4.2 over prior SOTA), supervised 81.6 (+2.2). A recent corroboration with a *predictive*
geometric statistic: **Parupudi, "Anisotropy Decides Cosine vs. Rank Metrics for Text Embeddings",
arXiv:2606.29571 (June 2026)** — across 19 encoders (22M–7B) × 7 datasets × 19 parameter-free
metrics, "rogue-dimension dominance" predicts whether cosine loses, at rank correlation 0.86 /
linear 0.95; on well-spread spaces cosine is essentially optimal (~0.001 Spearman to be gained), on
crowded spaces rank/L₁ metrics beat it by ~0.055 Spearman. Caveat: this is a single-author preprint,
unreviewed.

The upshot for retrieval: isotropy work says absolute cosine is dominated by nuisance geometry;
Steck et al. say even the ordering can be regularization-dependent. Neither licenses reading a
cosine as a probability.

## 2. Score→probability machinery, and what IR measured

The classical ladder: **Platt (1999), "Probabilistic Outputs for Support Vector Machines and
Comparisons to Regularized Likelihood Methods"** — fit p(y=1|f) = 1/(1+exp(Af+B)) by maximum
likelihood on the uncalibrated score f; **Zadrozny & Elkan**, histogram binning (ICML 2001) and
isotonic regression via pair-adjacent-violators, "Transforming classifier scores into accurate
multiclass probability estimates", KDD 2002, pp. 694–699, DOI 10.1145/775047.775151. I verified both
bibliographically but could **not** extract their own wording or experimental numbers (Platt's PDF
mirrors failed TLS/404; the Elkan PDF would not parse) — so for the structural facts I lean on
scikit-learn's calibration documentation (https://scikit-learn.org/stable/modules/calibration.html),
which states the bias point explicitly: fitting the calibrator on the classifier's own training
outputs "would thus result in a biased calibrator that maps to probabilities closer to 0 and 1 than
it should", hence cross-validated/disjoint calibration data; and that isotonic, being
non-parametric, needs substantially more data (~1000+ samples) and overfits below that (citing Menon
et al. 2012, and Niculescu-Mizil & Caruana, ICML 2005).

**Guo, Pleiss, Sun & Weinberger, "On Calibration of Modern Neural Networks", ICML 2017**
(arXiv:1706.04599): modern networks are systematically *overconfident* where LeNet-era networks were
not; depth, width, weight decay and batch normalization each worsen it; and temperature scaling —
one scalar on the logits, fit by NLL on validation — is "surprisingly effective", usually best. (I
could not pull their ECE table from the abs page — flagged.)

**ECE is itself contested.** **Nixon, Dusenberry, Zhang, Jerfel & Tran, "Measuring Calibration in
Deep Learning" (arXiv:1904.01685)**: ECE uses only the max prediction, is highly sensitive to bin
count, and is biased by binning; their headline is that "conclusions on the rank ordering of
recalibration methods is drastically impacted by the choice of calibration measure".
**Vaicenavicius, Widmann, Andersson, Lindsten, Roll & Schön, "Evaluating model calibration in
classification", AISTATS 2019 (arXiv:1902.06977)**: binned estimators are inconsistent — they do not
converge to true calibration error. **Kumar, Liang & Ma, "Verified Uncertainty Calibration", NeurIPS
2019 (arXiv:1909.10155)** is the sharpest: Platt/temperature scaling are "less calibrated than
reported", and "current techniques cannot estimate how miscalibrated they are"; sample complexity is
O(B/ε²) for histogram binning versus O(1/ε²) for scaling, and their scaling-binning calibrator gets
O(1/ε²+B) with 35% lower calibration error than histogram binning on CIFAR-10/ImageNet. Also
load-bearing: calibration alone is vacuous without sharpness — **Gneiting, Balabdaoui & Raftery,
"Probabilistic forecasts, calibration and sharpness", JRSS-B 69(2):243–268 (2007)** set the paradigm
of "maximizing the sharpness of the predictive distributions subject to calibration"; a constant
base-rate predictor is perfectly calibrated and useless.

**In ranking, scores are not calibrated by construction.** **Yan, Qin, Wang, Bendersky & Najork,
"Scale Calibration of Deep Ranking Models", KDD 2022, pp. 4300–4309, DOI 10.1145/3534678.3539072**
(ACM blocked my fetch; content below is from the follow-up's description — flagged). **Bai,
Jagerman, Qin, Yan, Kar, Lin, Wang, Bendersky & Najork, "Regression Compatible Listwise Objectives
for Calibrated Ranking with Binary Relevance", arXiv:2211.01494** state the problem directly:
ranking losses "are invariant to rank-preserving score transformations, and tend to learn scores
that are not scale-calibrated to regression targets", and may diverge indefinitely under continued
training. Their measurement is the single most vivid number I found: on MSLR-Web30K, SoftmaxCE
attains NDCG@10 0.4578 at **LogLoss 23.77**, and on Istella NDCG@10 0.6839 at **LogLoss 60.59** —
i.e. a competitive ranker whose scores are catastrophically invalid as probabilities. Their
regression-compatible ListCE reaches 0.4680 / LogLoss 0.6031 and 0.6900 / 0.0634. They also identify
the *conflict* in the naive multi-objective fix (Yan et al.'s weighted sum): SigmoidCE drives s_i →
log P_i − log(1−P_i) while SoftmaxCE drives s_i → log P_i − log ΣP_j + c, so "[the objectives] are
inherently conflicting". Deployed on YouTube Search: SearchCTR +0.66%, SearchAbandonedRate −0.31%.

**Neural rankers specifically are not reliably calibrated.** **Penha & Hauff, "On the Calibration and
Uncertainty of Neural Learning to Rank Models for Conversational Search", EACL 2021**
(https://aclanthology.org/2021.eacl-main.12/) report that "BERT-based rankers are not robustly
calibrated", that stochastic (MC-dropout / ensemble) variants calibrate better, and that uncertainty
is useful for risk-aware re-ranking and for predicting unanswerable contexts. **Cohen, Mitra, Lesota,
Rekabsaz & Eickhoff, "Not All Relevance Scores are Equal: Efficient Uncertainty and Calibration
Modeling for Deep Retrieval Models", SIGIR 2021, pp. 654–664, DOI 10.1145/3404835.3462951** —
verified bibliographically only; ACM returned 403 and I **could not** confirm its measurements.

**Does calibration transfer across queries? The direct evidence says no.** **Rossi, Lin, Liu, Yang,
Lee, Magnani & Liao (Walmart Global Tech), "Relevance Filtering for Embedding-based Retrieval", CIKM
'24** (arXiv:2408.04887) state the premise flatly — "the cosine similarity scores are usually not
interpretable and should not be compared across different queries", because the space is optimized
for *within-query* relative comparison — and their fix is architectural: a "Cosine Adapter" that
learns a **query-dependent** monotone mapping (linear / sqrt / quadratic / power) from raw cosine
into a calibrated relevance score, after which a single *global* threshold becomes legitimate.
Measured on MS MARCO at K=1000: PR AUC 0.139 (power mapping) vs 0.041 (raw cosine), P@R95 0.0066 vs
0.0028, filtering 84.90% of candidates at 95% recall; on Walmart product data PR AUC 0.8619, P@R95
0.6225; online A/B at Walmart, precision +5.34% (top-5) and +4.00% (top-10) with engagement neutral
(orders +0.03%, p=0.86). That is close to a direct experimental refutation of the global-raw-cosine
threshold. Converging evidence: **Sheikholeslami, Hosseini, Bechard, Daruru & Rajeswar, "Optimizing
What Matters: AUC-Driven Learning for Robust Neural Retrieval", arXiv:2510.00137 (Sept 2025)** argue
InfoNCE "is fundamentally oblivious to score separation quality" and yields scores unsuitable for
threshold-based RAG decisions; they propose a Mann-Whitney/AUC loss and report gains in both AUC and
standard retrieval metrics. The older IR line that *did* model per-query score distributions:
**Manmatha, Rath & Feng, "Modeling score distributions for combining the outputs of search engines",
SIGIR 2001, pp. 267–275, DOI 10.1145/383952.384005** (Gaussian relevant / exponential non-relevant
mixture fitted **per query**, then mapped to posterior relevance) — verified bibliographically; I
could **not** retrieve the full text or the Arampatzis–Robertson critiques and truncated-score-
distribution follow-ups, so treat my characterization of that thread as unverified.

## 3. Conformal prediction: a real guarantee, of the wrong shape

The foundation is **Vovk, Gammerman & Shafer, *Algorithmic Learning in a Random World* (Springer
2005; 2nd ed. 2022)** — a conformal predictor wraps any black-box score and attains validity from
exchangeability alone. (Springer blocked direct access; the characterization is from secondary
sources — flagged. Likewise **Angelopoulos, Barber & Bates, *Theoretical Foundations of Conformal
Prediction*, CUP 2025 / arXiv:2411.11824**, body text not extracted.)

**Angelopoulos & Bates, "A Gentle Introduction to Conformal Prediction and Distribution-Free
Uncertainty Quantification", arXiv:2107.07511** gives the split-conformal statement exactly: with q̂
the ⌈(n+1)(1−α)⌉/n empirical quantile of calibration scores,

  1 − α ≤ P(Y_test ∈ C(X_test)) ≤ 1 − α + 1/(n+1),

assuming calibration and test points i.i.d. (exchangeable). Both caveats you asked about are in
their own words. On marginality: they "call this property marginal coverage, since the probability is
marginal (averaged) over the randomness in the calibration and test points." On conditionality, §3.1
says plainly that conditional coverage "is impossible to achieve" in general and that conformal
procedures are not guaranteed to satisfy it. Translated to retrieval: a conformal retrieval wrapper
promises that *across your query distribution* 90% of queries' sets contain the gold answer. It
promises **nothing** about *this* query. (I could not verify the widely-cited *Foundations and Trends
in ML* 16(4) journal version — the arXiv record carries no journal-ref.)

The impossibility is a theorem, not a gap. **Vovk, "Conditional validity of inductive conformal
predictors", ACML 2012, PMLR 25:475–490 / Machine Learning 92:349–376 (arXiv:1209.2673)** separates
training-conditional validity (achievable via Hoeffding) from object-conditional validity, and his
Prop. 4 shows the latter forces prediction sets of infinite measure (full label set, in
classification) with probability ≥ 1−ε at non-atomic test objects: precise object-conditional
validity "cannot be achieved in a useful way unless the test object has a positive probability." His
remedy is the **Mondrian** taxonomy (Vovk, Lindsay, Nouretdinov & Gammerman, "Mondrian Confidence
Machine", 2003, https://alrw.net/old/04.pdf) — group- or label-conditional validity, i.e. you get
conditional coverage only over a *pre-declared partition*. The quantitative version is **Foygel
Barber, Candès, Ramdas & Tibshirani, "The limits of distribution-free conditional predictive
inference", Information and Inference 10(2):455–482 (arXiv:1903.04684)**: Prop. 1, any procedure with
exact conditional coverage has infinite expected set length at almost every x; Thm 2, even
*approximate* (1−α,δ) conditional coverage over all δ-mass subgroups buys nothing beyond marginal
coverage at an inflated level; Thms 4–5 tie feasibility to the VC complexity of the subgroup class.
**Gibbs, Cherian & Candès, "Conformal Prediction with Conditional Guarantees" (arXiv:2305.12616)**
recovers exact finite-sample coverage over *finite-dimensional* shift classes while conceding exact
conditional coverage is universally impossible in finite samples (JRSS-B status unverified).

Shift: **Tibshirani, Barber, Candès & Ramdas, "Conformal Prediction Under Covariate Shift", NeurIPS
2019 (arXiv:1904.06019)** needs the likelihood ratio dP_test/dP_train known or well-estimated;
**Barber, Candès, Ramdas & Tibshirani, "Conformal prediction beyond exchangeability", Annals of
Statistics 51(2):816–845, 2023 (arXiv:2202.13415)** bounds the coverage gap by a weighted sum of
total-variation distances — degradation is continuous, but the bound is not computable in
deployment. For retrieval this is the binding constraint: **Thakur, Reimers, Rücklé, Srivastava &
Gurevych, "BEIR", NeurIPS 2021 Datasets & Benchmarks (arXiv:2104.08663)** found BM25 a "robust
baseline" that dense retrievers "often underperform" out of domain — i.e. the query/corpus
distribution genuinely shifts, which is exactly the exchangeability assumption failing. (I could not
extract their per-dataset win counts — flagged.)

The right primitive for *cutoffs* is risk control rather than coverage. **Angelopoulos, Bates, Fisch,
Lei & Schuster, "Conformal Risk Control", ICLR 2024 (arXiv:2208.02814)** controls
E[ℓ(C_λ̂(X_test), Y_test)] ≤ α for any monotone, right-continuous, bounded loss, "tight up to an
O(1/n) factor" (I could not extract the exact α + B/(n+1) constant). **Angelopoulos, Bates, Candès,
Jordan & Lei, "Learn then Test" (arXiv:2110.01052)** drops monotonicity, giving
P(R(T_λ̂) ≤ α) ≥ 1−δ by recasting risk control as multiple testing over a λ-grid with
Hoeffding–Bentkus p-values and FWER control — the better fit for abstention, since "did we correctly
abstain" is not a coverage event. Applied to ranking: **Angelopoulos, Krauth, Bates, Wang & Jordan,
"Recommendation Systems with Distribution-Free Reliability Guarantees" (arXiv:2207.01609)** wraps any
pretrained ranker with finite-sample **FDR** control, emitting variable-size recommendation sets
whose cardinality adapts to the ranker's confidence, evaluated on Yahoo LTR and MS MARCO — this is
the closest existing analogue of "conformal retrieval cutoff."

RAG applications. **Kang, Gürel, Yu, Song & Li, "C-RAG: Certified Generation Risks for
Retrieval-Augmented Language Models", ICML 2024, PMLR 235:22963–23000 (arXiv:2402.03181)** certify a
*conformal generation risk* bound P[R ≤ α̂_λ] ≥ 1−δ (not coverage), and prove (Thm 1)
P[α̂_rag < α̂_llm] ≥ 1−p_t−p_r under a non-trivial-retriever condition, with Thms 2–3 extending to
Hellinger-bounded test shift; empirical–theoretical gaps narrow to ~1e−3 on
AESLC/CommonGen/DART/E2E. **Li, Park, Lee & Bastani, "TRAQ: Trustworthy Retrieval Augmented Question
Answering via Conformal Prediction", NAACL 2024, pp. 3799–3821, DOI 10.18653/v1/2024.naacl-long.210
(arXiv:2307.04642)** claim the first end-to-end statistical correctness guarantee for RAG by
conformalizing retriever and generator separately then aggregating, using Bayesian optimization to
shrink sets — "reducing prediction set size by 16.2% on average" over an ablation. (Their abstract
does not say "Bonferroni"; the two-stage split necessarily divides the error budget, but I could not
verify their exact correction wording — flagged.) **Gui, Jin & Ren, "Conformal Alignment", NeurIPS
2024 (arXiv:2405.10301)** — note: Ren, not Candès — gives an FDR-style selection guarantee that a
prescribed fraction of *selected* units meet an alignment criterion, on QA and radiology reports.
**Abbasi Yadkori et al., "Mitigating LLM Hallucinations via Conformal Abstention"
(arXiv:2405.01563)** conformally calibrates an abstention threshold on self-consistency scores with
guarantees on the hallucination rate, and abstains far less conservatively than log-prob baselines.
**Kumar, Lu, Gupta, Palepu, Bellamy, Raskar & Beam (arXiv:2305.18404)** find LLM conformal
uncertainty "tightly correlated with prediction accuracy" on multi-choice QA and explicitly probe
exchangeability on out-of-subject questions (numeric tables not extracted).

**Selective prediction** is the older, non-conformal route. **Chow, "On optimum recognition error and
reject tradeoff", IEEE Trans. Information Theory 16(1):41–46, 1970, DOI 10.1109/tit.1970.1054406**:
reject when the max posterior falls below a threshold set by the error/reject cost ratio —
Bayes-optimal *given the true posterior*. (The paper itself was not fetchable; the standard reading
that Chow's rule degenerates to a heuristic under an uncalibrated score is the field's consensus, not
Chow's wording — flagged.) **El-Yaniv & Wiener, JMLR 11:1605–1641 (2010)** formalize the
risk–coverage trade-off. **Geifman & El-Yaniv, "Selective Classification for Deep Neural Networks",
NeurIPS 2017 (arXiv:1705.08500)** give SGR, which binary-searches a confidence threshold with a
guarantee (Thm 3.2) built on the Gascuel–Caraux (1992) numerical generalization bound; measured: 2%
top-5 ImageNet error guaranteed at 99.9% confidence with ~60% coverage; CIFAR-10 at δ=0.001, 1% risk
at 78.56% coverage; CIFAR-100, 5% risk at 44.50% coverage, 10% at 59.52%, 20% at 77.78%. **That table
is the price of abstention in numbers: on CIFAR-100, a 4× risk reduction costs roughly a third of all
queries.** **Geifman & El-Yaniv, "SelectiveNet", ICML 2019 (arXiv:1901.09192)** trains
prediction/selection/auxiliary heads jointly against a target coverage; crucially, target coverage
there is an *objective*, not a guarantee, and their post-hoc Hoeffding band ε = √(ln(2/δ)/2n)
guarantees coverage only, leaving risk uncontrolled.

**What conformal prediction costs, in the literature's own words.** (i) A labelled, exchangeable
calibration set with a hard floor: the ⌈(n+1)(1−α)⌉/n quantile exists only when n ≥ 1/α − 1, else the
threshold is +∞ and the set is vacuous — stated exactly by **Ding, Angelopoulos, Bates, Jordan &
Tibshirani, "Class-Conditional Conformal Prediction with Many Classes", NeurIPS 2023
(arXiv:2306.09335)**: for any class with too few calibration points "we will have q̂_y = ∞." (ii)
Realized coverage fluctuates: conditional on the calibration set it is Beta(n+1−l, l) with
l = ⌊(n+1)α⌋, so at α=0.1 and n=1000 coverage "is typically between .88 and .92" (Angelopoulos &
Bates §3.2). (iii) Marginality produces measured per-group undercoverage: Ding et al. report an
ImageNet model at 89.8% *marginal* coverage whose "water jug" class is covered only 50.8% of the
time; **Kasa & Taylor (arXiv:2307.01088)** find that under distribution shift "performance greatly
degrades … violating safety guarantees" and that in long-tailed settings guarantees are "frequently
violated on many classes." (iv) Validity ≠ usefulness: **Intrator, Kelner, Cohen, Goldenberg, Rivlin
& Freedman, "Streamlining Conformal Information Retrieval via Score Refinement", FEVER @ ACL 2024
(arXiv:2410.02914, https://aclanthology.org/2024.fever-1.22/)** report that existing conformal
retrieval "produce large-sized sets, incurring high computational costs", with baselines on BEIR at
α=0.1 of **417.77 documents on FIQA** and 231.17 on SCIFACT, rising to 846.0 and 760.75 at α=0.05;
their monotone transform T(s_(r),r) = (s_(r)/s_max)·1/log(1+r^λ) cuts these to 56.72/14.07 and
190.5/29.59. A valid 90%-coverage retrieval set of 417 documents is the cleanest demonstration
available that a correct guarantee can be operationally worthless. (v) Explicit critique:
**Mehrtens, Bucher & Brinker, "Pitfalls of Conformal Predictions for Medical Image Classification"
(arXiv:2506.18162)** list unreliability under shift, failure to give reliable per-subset estimates,
limited value with small label spaces, and — directly relevant to using conformal sets as a retrieval
filter — that using the sets to filter predictions for better accuracy is inappropriate and
undermines the guarantee. Related ancestry for recall-constrained set prediction: **Fisch, Jaakkola &
Barzilay, "Conformal Prediction Sets with Limited False Positives", ICML 2022** and "Efficient
Conformal Prediction via Cascaded Inference with Expanded Admission" (arXiv:2007.03114).

## 4. Is an absolute threshold defensible once calibrated? Yes — and only then

The decision-theoretic statement is classical. **Robertson, "The probability ranking principle in
IR", Journal of Documentation 33(4):294–304, 1977, DOI 10.1108/eb026647** (citation verified via
Crossref; I could **not** fetch the original text — flagged). The cleanest accessible formulation is
Manning, Raghavan & Schütze, *Introduction to Information Retrieval*, §11.2. Under 1/0 loss "you lose
a point for either returning a nonrelevant document or failing to return a relevant document", and
the risk-minimizing decision is to "return documents that are more likely relevant than nonrelevant:
d is relevant iff P(R=1|d,q) > P(R=0|d,q)"
(https://nlp.stanford.edu/IR-book/html/htmledition/the-10-loss-case-1.html) — i.e. threshold at 0.5.
With asymmetric costs (C₁ = cost of not retrieving a relevant document, C₀ = cost of retrieving a
nonrelevant one), retrieve d next iff C₀·P(R=0|d) − C₁·P(R=1|d) ≤ C₀·P(R=0|d′) − C₁·P(R=1|d′) for
all unretrieved d′ (https://nlp.stanford.edu/IR-book/html/htmledition/the-prp-with-retrieval-costs-1.html),
which rearranges to the familiar "retrieve iff P(relevant) exceeds a cost ratio". The book's own
caveat is the whole argument in one line: the optimality proof (attributed there to Ripley 1996)
"requires that all probabilities are known correctly. This is never the case in practice."

That is precisely the asymmetry you were probing. The PRP's threshold is a statement about a
**posterior probability**, and it is *only* a theorem about posteriors. Chow's reject rule (1970) is
the classification analogue — reject iff the max posterior falls below a cost-derived threshold — and
inherits the same precondition. **Lewis, "Evaluating and optimizing autonomous text classification
systems", SIGIR '95, pp. 246–254, DOI 10.1145/215206.215366** is the standard reference for carrying
this into thresholding *estimated* probabilities against a utility measure (citation verified; I
could **not** retrieve the full text, so I am flagging my characterization of its specific
F-measure/expected-utility results as unverified rather than asserting numbers). Applying the same
rule to a raw cosine is a category error twice over: the quantity is not a probability (Guo et al.;
Bai et al.'s LogLoss 23.77 and 60.59), and under Steck et al. its scale is set by an unidentified
regularization artifact. Conversely, once you have a *query-conditioned* calibrated mapping, the
absolute threshold is restored to legitimacy — which is exactly what the Walmart CIKM '24 result
demonstrates operationally, and it is also why their adapter had to be query-dependent rather than a
single global sigmoid.

**Honest gaps, for your file:** the classical-calibration sub-sweep (Platt's and Zadrozny–Elkan's own
wording and experiments; Yan et al. KDD 2022's primary text; Lewis 1995's measurements; the
Arampatzis–Robertson score-distribution critique line and the SIGIR 2009 truncated-score-distribution
cutoff work) did not come back in time and remains verified only bibliographically. Also unverified:
Guo et al.'s ECE figures, Su et al.'s whitening table, BEIR's per-dataset win counts, Cohen et al.
SIGIR 2021's measurements, Chow (1970)'s own text, and the *Foundations and Trends* journal version
of Angelopoulos & Bates. The Parupudi (2026) anisotropy-vs-rank-metrics paper is an unreviewed
single-author preprint.

---
---

# REPORT B — the classical calibration machinery, and the thresholding principle

*(researcher's full text, unedited. This is the sub-sweep Report A flagged as still running.)*

## A. Classical calibration machinery

**Platt (1999).** John C. Platt, "Probabilistic Outputs for Support Vector Machines and Comparisons
to Regularized Likelihood Methods," in *Advances in Large Margin Classifiers* (MIT Press, 1999; many
authors cite it as 2000) —
https://www.semanticscholar.org/paper/42e5ed832d4310ce4378c44d05570439df28a393. The exact machinery,
verified via Lin, Lin & Weng, *A Note on Platt's Probabilistic Outputs for Support Vector Machines*
(https://www.csie.ntu.edu.tw/~cjlin/papers/plattprob.pdf): a **two-parameter sigmoid on the raw SVM
decision value**, `Pr(y=1|x) ≈ P_{A,B}(f) = 1/(1 + exp(Af + B))` with `f = f(x)`. A and B are fit by
minimizing the regularized cross-entropy `F(z) = −Σ_i [t_i log p_i + (1−t_i) log(1−p_i)]` where the
targets are *smoothed*, not 0/1: `t_i = (N₊+1)/(N₊+2)` for positives and `1/(N₋+2)` for negatives.
That smoothing is Platt's built-in regularizer. Lin et al. prove the objective is convex, show
Platt's Levenberg–Marquardt pseudocode "may not converge," and replace it with Newton's method plus
backtracking. **FLAG:** I could not retrieve Platt's original text, so I cannot quote his
held-out/CV remark directly. The practice is verified secondarily in Niculescu-Mizil & Caruana,
*Predicting Good Probabilities With Supervised Learning*, ICML 2005
(https://www.cs.cornell.edu/~alexn/papers/calibration.icml05.crc.rev3.pdf), which states they follow
Platt in using 3-fold CV and fitting the sigmoid on the **union of the validation folds**
(out-of-sample) to avoid overfitting the sigmoid.

**Zadrozny & Elkan (2001, ICML).** *Obtaining calibrated probability estimates from decision trees
and naive Bayesian classifiers* — https://cseweb.ucsd.edu/~elkan/calibrated.pdf. Ten methods, four
measures, one dataset (KDD'98 charity). Methods: **histogram binning** for naive Bayes;
**m-estimate smoothing** and **curtailment** (stop descending the tree at any node with < k
examples, k=100) for C4.5. Measured, test set: MSE — bagged curtailment 0.09515, curtailment
0.09535, binned NB 0.09528, base rate 0.09602, raw NB 0.10111, C4.5-with-pruning 0.10113,
C4.4/Laplace 0.10090. Log-loss — bagged curtailment 0.28300, binned NB 0.28365, NB 0.30400.
**Profit** — smoothed curtailment $14,741, binned NB $14,642, curtailment $14,190, raw NB $9,531,
all-base-rate $12,252, all-zero $0; they note $14,741 beats the KDD'98 contest winner (contest median
$10,720). They explicitly **reject AUC** as a calibration measure because it "fails to distinguish
between scores that rank examples correctly" and genuinely calibrated ones.

**Zadrozny & Elkan (2002, KDD),** pp. 694–699, DOI 10.1145/775047.775151 (copy:
http://www.cs.columbia.edu/~djhsu/coms4771-f25/handouts/zadrozny2002kdd.pdf). They propose
**isotonic regression via pair-adjacent violators (PAV)**, O(n), as "an intermediary approach between
sigmoid fitting and binning," and name binning's defects: the bin count must be chosen by
cross-validation (unreliable on small/unbalanced data), bin size is fixed, boundaries are arbitrary.
PAV is characterized as binning where boundaries and widths are chosen by how well the classifier
ranks. Measured: KDD-98 MSE 0.10111 (NB) → 0.09533 (sigmoid) → 0.09528 (PAV), profit $9,531 →
$14,120 → $14,447. TIC: NB 0.13551 → 0.10905 → 0.10818; SVM 0.11889 → 0.11122 (sigmoid) → 0.11200
(PAV). Adult: NB MSE 0.25198 → 0.21515 → 0.20452 and error rate 0.17321 → 0.15190 → 0.14831; SVM MSE
0.28684 → 0.20962 → 0.20924 but error rate *rose* 0.14968 → 0.15113, because the uncalibrated SVM's
threshold was already optimal and calibration slightly reduced refinement. Multiclass: decompose via
a code matrix, calibrate each binary problem with PAV, recombine (normalization / least-squares /
coupling); Pendigits MSE 0.0326 → 0.0241 and error 0.1672 → 0.1498 with PAV + normalization, which
they recommend as simplest.

**Guo, Pleiss, Sun & Weinberger (ICML 2017),** PMLR 70:1321–1330 — https://arxiv.org/abs/1706.04599.
`ECE = Σ_m (|B_m|/n)·|acc(B_m) − conf(B_m)|`. Modern nets "unlike those from a decade ago, are poorly
calibrated" and systematically **overconfident**; drivers are capacity (depth and width),
**BatchNorm**, **reduced weight decay**, and NLL overfitting while 0/1 error still improves.
**Temperature scaling** — one scalar T>0 applied to logits, `softmax(z/T)`, fit by NLL on a
validation set, leaving argmax and hence accuracy untouched — is the most effective method. Table 1
numbers: CIFAR-100 ResNet-110 uncalibrated **16.53%** → temperature scaling **1.26%**, histogram
binning 2.66%, isotonic 4.99%, vector scaling 1.32%; ImageNet DenseNet-161 **6.28% → 1.99%**.
**FLAG:** I did not extract exact LeNet Figure-1 numbers; the LeNet-vs-ResNet contrast is qualitative
in their Figure 1.

**ECE criticisms.** Nixon et al., *Measuring Calibration in Deep Learning* (arXiv:1904.01685; **FLAG**
— arXiv listing shows no peer-reviewed venue) give four flaws: ECE scores only the max-probability
class, ignoring non-predicted classes; fixed-width bins concentrate nearly all mass in "typically one
or two" bins; over- and under-confident predictions **cancel inside a bin**, giving near-zero error
on a miscalibrated model; and L1 vs L2 changes the conclusion. They propose SCE, **ACE** (equal-mass
adaptive bins) and **TACE** (thresholded). Their strongest evidence: across 32 metric variants, eight
recalibration methods get completely different orderings — temperature scaling ranks anywhere from
1st to 7th. Kumar, Liang & Ma, *Verified Uncertainty Calibration*, NeurIPS 2019 (arXiv:1909.10155)
make the sharpest claim: **Proposition 3.3**, for any binning the binned calibration error is ≤ the
true calibration error; **Example 3.2**, binned error can be 0 while true error exceeds 0.49.
Empirically, ImageNet VGG16 with 15 bins (Guo et al.'s setting) reports ≈0.02 while the actual error
is "at least twice as high." Their **scaling-binning** calibrator (fit a parametric function by MSE,
uniform-mass bins, then output the *average function value* per bin rather than the average label)
needs O(1/ε² + B) samples vs O(B/ε²) for histogram binning (Thm 4.1); the debiased estimator needs
O(√B/ε²) vs O(B/ε²) for plugin (Thms 5.3–5.4). Measured: 35% lower calibration error than histogram
binning on CIFAR-10 and **5× lower on ImageNet** at B=100 with ≤1000 recalibration points.
Vaicenavicius et al., AISTATS 2019, PMLR 89:3459–3467
(https://proceedings.mlr.press/v89/vaicenavicius19a.html): the fixed-partition estimator "is prone to
underestimating the true expected miscalibration ... as the size of the data set grows to infinity,"
and comparing two models by their realized ECE values is "unjustified and not necessarily
meaningful" because the two biases `E[η̂]−η` differ and the estimators have different distributions;
they propose consistency resampling to produce p-values against the null of perfect calibration.
Roelofs, Cain, Shlens & Mozer, AISTATS 2022, PMLR 151:4036–4054
(https://proceedings.mlr.press/v151/roelofs22a.html) measure the bias directly on synthesized outputs
across evaluation-set sizes, find **equal-mass bins have lower bias than equal-width**, and recommend
the debiased estimator and **ECE_sweep** (equal-mass, largest bin count preserving monotonicity of
the calibration function). **FLAG:** no numeric bias magnitudes in the abstract. Gruber & Buettner,
NeurIPS 2022 (arXiv:2203.07835): "estimators are usually biased and inconsistent"; they bound
calibration errors by proper scores. **FLAG:** v4 (2024) corrects their Theorem 3.1 / Proposition 3.2.

## B. Ranking and retrieval

**Yan, Qin, Wang, Bendersky & Najork, *Scale Calibration of Deep Ranking Models*, KDD 2022,** DOI
10.1145/3534678.3539072, PDF
https://storage.googleapis.com/gweb-research2023-media/pubtools/6647.pdf. **FLAG: Pasumarthi is not
an author** (the brief's author list is slightly off). The problem exactly as stated: popular pairwise
and listwise losses are **translation-invariant**, rankers have "the freedom to add a constant to item
scores without changing their relative order," so scores are not scale-calibrated; calibrated pCTR is
a *required* input to cost-per-click auction pricing; and the free global translation causes
**numeric training instability** under continuous training. Three during-training fixes (no
post-processing): MultiObj, MultiTask, **Calibrated Softmax**. Their ECE (Eq. 13) is explicitly
**per-query** — bin within each query's candidate list (M=10 equal-count bins), then average over
queries. Table 1 (logistic task), Web30K: Softmax NDCG@10 0.5002 / LogLoss 2.6648 / ECE 0.5432,
unstable; Softmax-Platt 0.5002 / 0.6175 / 0.1491, **still unstable**; Pointwise Logistic 0.4566 /
0.5864 / 0.1136, stable; MultiObj 0.4971 / 0.6013 / 0.1264; Calibrated Softmax 0.5014 / 0.6265 /
0.1601. Istella: Softmax 0.6978 / 2.5206 / 0.5962; Calibrated Softmax 0.6980 / 0.0645 / 0.0229. On
the regression task the uncalibrated softmax **collapses**: Web30K MSE 6.73×10⁴ and ECE 123.3;
Istella MSE 1.68×10⁷ and ECE 955.4. Google **Sponsored Search** (Table 3, relative to the
pointwise-logistic production baseline, 5 months continuous training): Softmax pCTR **−99.6%**, AUC
−1.8%, uncalibrated and unstable; Softmax-Platt pCTR 0.0%, AUC −1.8%, still unstable; **MultiObj pCTR
0.0%, AUC +0.9%**, calibrated and stable, deployed. They note "a 0.5% improvement in AUC has very
significant effect on core business metrics."

**Bai, Jagerman, Qin, Yan, Kar, Lin, Wang, Bendersky & Najork, *Regression Compatible Listwise
Objectives for Calibrated Ranking with Binary Relevance*, CIKM 2023** (arXiv:2211.01494, DOI
10.1145/3583780.3614712). The tension claim verbatim-adjacent: combining regression and ranking
multi-objectively gives calibration, but "the two objectives are not necessarily compatible, which
makes the trade-off less ideal for either of them." Their **RCR** approach proves the ranking and
regression components "mutually aligned." Table 1: Web30K SoftmaxCE 0.4578 / LogLoss **23.77** / ECE
0.5503; SoftmaxCE-Platt 0.4578 / 0.6103 / 0.1333; SigmoidCE 0.4626 / 0.5996 / 0.1216; MultiObj
0.4665 / 0.6239 / 0.1509; **RCR 0.4680 / 0.6031 / 0.1275**. Istella SoftmaxCE LogLoss 60.59, ECE
0.9556. YouTube Search offline (relative to SigmoidCE): MultiObj AUCPR **−0.37%**, LogLoss +0.13%,
NDCG@1 +0.30% — disqualifying, because the regression degradation hurts downstream stages; RCR AUCPR
**+0.22%**, LogLoss +0.03%, NDCG@1 +0.27%. Online A/B over millions of users: SearchCTR **+0.66%**,
SearchAbandonedRate **−0.31%**; fully deployed.

**Penha & Hauff, EACL 2021** (arXiv:2101.04356). They frame it as the PRP's two preconditions:
**[C1]** calibrated probabilities of relevance, **[C2]** certain (point) predictions. ECE with C=10.
In-domain (Table 1): ECE 0.003 / 0.006 / 0.002 on MANtIS / MSDialog / UDC-DSTC8 with R10@1 0.615 /
0.652 / 0.834 — so BERT rankers *are* well calibrated with no distribution shift. Under shift, "the
ECE is **4.6 times higher for cross-domain and 7.9 times higher for cross-NS**," i.e. they "do not
have robust calibrated predictions." Critically, Figure 2 shows calibration degrades as the ratio of
non-relevant to relevant candidates grows — the realistic retrieval regime. Stochastic rankers:
ensemble S-BERT_E averages **14% lower ECE**, MC-dropout S-BERT_D **10% lower**. Risk-aware RA-BERT
gains up to **+16.39% / +17.18% R10@1** in cross-NS settings. On correlation: effectiveness and
calibration do **not** move together — UDC-DSTC8 is both most effective and best calibrated
in-domain, yet has the worst cross-NS ECE (0.050, 0.045). **FLAG:** the paper's text says the
in-domain average is "0.036 ECE" while the table's underlined values average 0.0037 — apparent typo
in the paper.

**Cohen, Mitra, Lesota, Rekabsaz & Eickhoff, *Not All Relevance Scores are Equal*, SIGIR 2021**
(arXiv:2105.04651, DOI 10.1145/3404835.3462951). Last-layer-only MC dropout as an efficient
approximate-Bayesian ranker, 150 inference samples, "negligible computational overhead." Parity
first: MS MARCO MRR 0.305→0.301, TREC DL 0.912→0.916, Robust04 BERT-L4 −2.6%. **CVaR risk-aware
reranking**: TREC DL nDCG@200 0.582→0.606 (BERT-L4), 0.565→0.584 (Conv-KNRM); Robust04 nDCG@20
0.382→0.404 — 3–5% over deterministic baselines. **ERCE** (expected *ranking* calibration error,
adaptive 10 equal-mass bins): TREC DL 0.703→0.465 (BERT-L2), 0.700→0.507 (BERT-L4), 0.519→0.452
(Conv-KNRM); Robust04 0.493→0.396, 0.477→0.395, but Conv-KNRM 0.256→0.264 (slightly worse) —
summarized as "~30% more calibrated." Downstream: adding ⟨μ, σ, skew, entropy⟩ to the Choppy cutoff
predictor gives ≈**9%** higher cutoff accuracy on TREC DL 2019. They also measure that uncertainty
grows monotonically as relevance scores fall and the score distribution approaches normal for
low-scoring documents. **FLAG:** I did not verify Cohen, Mitra, Hofmann & Croft, *Cross Domain
Regularization for Neural Ranking Models using Adversarial Learning* (SIGIR 2018) this session.

**Yu, Cohen, Lamba, Tetreault & Jaimes, *Explain then Rank: Scale Calibration of Neural Rankers Using
NLEs from LLMs*, Findings of ACL 2025,** pp. 22716–22730 —
https://aclanthology.org/2025.findings-acl.1167.pdf. Adds an **IR-specific ECE criticism**: with
highly skewed relevance labels (TREC 58/22/14/6), "MSE and ECE are biased — opting for scores near
the most frequent label results in lower errors while having no real world usability." They propose
**CB-ECE**, the mean of per-class ECE. Results on TREC: NLE(literal) nDCG 0.815 / CB-ECE 0.996 vs
full-calibration baselines; up to **+11.4% nDCG and +63.3% nDCG@10** over the no-calibration and
full-calibration BERT baselines; better-calibrated scores also improved post-hoc QPP (WIG, NQC
correlation with nDCG@10).

**Score distributions and cross-query transfer.** The lineage: Swets, *Science* 141(3577):245–250
(1963) and *American Documentation* 20:72–89 (1969) for the original two-distribution model;
Bookstein, *IP&M* 13(6):377–383 (1977) critiquing it; **Manmatha, Rath & Feng, SIGIR 2001, pp.
267–275** (DOI 10.1145/383952.384005), the canonical **exponential for non-relevant, normal
(Gaussian) for relevant** mixture, fit on TREC-3 and TREC-4 for both INQUERY (probabilistic) and
SMART (vector space) and for English and Chinese, used to map scores to posteriors for engine fusion;
**Arampatzis & van Hameren, SIGIR 2001, pp. 285–293** (DOI 10.1145/383952.384009),
score-distributional (s-d) threshold optimization; Zhang & Callan, SIGIR 2001, pp. 294–302, MLE for
filtering thresholds. The most useful open document is **Arampatzis, Nussbaum & Kamps, "Where to Stop
Reading a Ranked List?", TREC 2008 Legal notebook** —
https://pure.uva.nl/ws/files/4347595/61720_297474.pdf. It gives the s-d machinery explicitly:
`R = n·G_n`, `R₊(s) = R(1−F(s|1))`, `N₊(s) = (n−R)(1−F(s|0))`, and `K = argmax_k M(R₊, N₊, R₋, N₋)`;
scores convert to probabilities of relevance "straightforwardly by using Bayes' rule" once you have
both densities and the generality. **This is also where the cross-query answer lives**: "While for
some measures there exists an optimal fixed probability threshold, for others it does not. D. Lewis
formulates this in terms of whether or not a measure satisfies the **probability thresholding
principle**, and proves that the F measure does not satisfy it ... Consequently, for such measures,
what we should be looking for is **a different score or rank threshold for each ranking**."
Robertson's critique is quoted there too: his **recall-fallout convexity hypothesis** ("For all good
systems, the recall-fallout curve ... is convex," Robertson, *On Score Distributions and Relevance*,
ECIR 2007, LNCS pp. 40–51, DOI 10.1007/978-3-540-71496-5_7; the hypothesis traces to Robertson, *J.
Doc.* 25(1):1–27, 1969) implies that "the normal-exponential mixture **violates such conditions, only
(and always) at both ends of the score range**." Measured: with the improved s-d method F1@K =
**0.1374** vs median 0.0974 across 23 submissions and 0.1264 for a constant threshold set from the
prior year's mean R; and at α=0.05 "all fits but 2 or 3 on the Legal 2007 data" are rejected by χ²
despite looking fine by eye. Also Arampatzis & Robertson, "Modeling score distributions in
information retrieval," *Information Retrieval* 14(1):26–46 (2011), DOI 10.1007/s10791-010-9145-5 —
keywords confirm binary mixture model, gamma distribution, BM25, score calibration. **FLAG:
paywalled, I could not read its body, nor Robertson's ECIR 2007 text (soi.city.ac.uk returned 503);
the convexity quote above is Arampatzis et al. quoting Robertson, not the primary.**

**FLAG — genuine gap:** I found **no** paper that directly measures whether a single global
dense-retriever / embedding-similarity threshold works across queries. The nearest verified evidence
is indirect: Lewis's probability thresholding principle (F needs a per-ranking threshold), the
per-query ECE formulations in Yan et al. 2022 Eq. 13 and Cohen et al.'s ERCE (both chose per-query
normalization deliberately), Penha & Hauff's shift results, and the entire ranked-list-truncation
line (Lien et al.; Bahri et al., "Choppy," cited by Cohen et al.) which exists precisely because the
correct cutoff is query-dependent. Treat "a global similarity threshold does not transfer across
queries" as well-motivated but, in this search, **not directly measured for dense retrievers**.

## C. The decision-theoretic threshold

**Robertson (1977),** "The Probability Ranking Principle in IR," *Journal of Documentation*
33(4):294–304, DOI 10.1108/eb026647. The abstract: the principle "that, for optimal retrieval,
documents should be ranked in order of the probability of relevance or usefulness has been brought
into question by Cooper. It is shown that the principle can be justified under certain assumptions,
but that cases where these assumptions do not hold the principle is not valid. The major problem
appears to lie in the way the principle considers each document independently of the rest." **FLAG:**
I could not reach the primary text, so I cannot certify the famous long canonical sentence ("If a
reference retrieval system's response to each request is a ranking of the documents ... in order of
decreasing probability of relevance ... estimated as accurately as possible on the basis of whatever
data have been made available ...") — verify against Emerald before quoting it. Penha & Hauff's
restatement of the preconditions ([C1] calibration, [C2] certainty) is verified and citable.

**The optimal cutoff "retrieve iff P(relevant) > a cost/utility ratio."** The cleanest **primary**
statement I verified is Zadrozny & Elkan (ICML 2001, https://cseweb.ucsd.edu/~elkan/calibrated.pdf):
with mailing cost $0.68 and estimated donation amount y(x), "the optimal decision-making policy is to
solicit x if and only if P̂(donate|x)·y(x) > $0.68" — i.e. `P̂ > 0.68/y(x)`, a **per-example**
threshold. They then make the argument the brief is after: a monotone score is insufficient, because
knowing a score without the transformation to probability "is not enough, because [0.5] is the
correct threshold for making decisions only if [the transformation] is the identity function."
**FLAG:** I did not verify van Rijsbergen (*Information Retrieval*, 1979, ch. 6) or Robertson 1977's
own cutoff form this session.

**Chow (1970),** "On optimum recognition error and reject tradeoff," *IEEE Trans. Information Theory*
16(1):41–46, DOI 10.1109/TIT.1970.1054406; the abstract says he "describes an optimum rejection rule
and presents a general relation between the error probabilities" and the rejection function. Franc,
Prusa & Voracek, *Optimal strategies for reject option classifiers* (arXiv:2101.12523, JMLR), §2.1:
"the cost-based model of a classification strategy with the reject option was proposed by Chow in his
pioneering work," and the optimal strategy is a Bayes classifier plus a selection function that
**accepts iff the minimal conditional expected risk r*(x) < the reject cost ε**, rejects iff
r*(x) > ε, randomizing at equality. Under 0-1 loss `r*(x) = 1 − max_y p(y|x)`, which recovers the
textbook **"reject iff max posterior < 1 − ε."** **FLAG:** Franc et al. deliberately distinguish the
cost-based model from max-posterior thresholding (which they assign to their "bounded-improvement"
model), so the equivalence is a 0-1-loss special case and should not be asserted in general.

**Lewis (1995),** "Evaluating and optimizing autonomous text classification systems," SIGIR '95, pp.
246–254, DOI 10.1145/215206.215366. OpenAlex abstract: retrieval systems "typically produce a ranking
of documents and let a user decide how far down that ranking to go," whereas autonomous classifiers
"make decisions without human input or supervision," and "optimizing and estimating effectiveness
[is] greatly aided if classifiers [that] explicitly estimate probability of class membership are
used." The load-bearing result for the brief is the **probability thresholding principle**: a measure
satisfies it if some fixed probability threshold is optimal for it, and **Lewis proves F-measure does
not satisfy it** — so, in Arampatzis et al.'s gloss, "how a system should treat documents with, e.g.,
50% chance of being relevant depends on how many documents with higher probabilities are available."
Expected utility (a linear cost function) *does* admit a fixed probability threshold; F does not.
**FLAG: this result is attributed secondarily** — via Arampatzis, Nussbaum & Kamps §3.2, which cites
Lewis 1995 as reference [10]. I could not retrieve Lewis 1995 itself (ACM DL returns 403, CiteSeerX's
copy is dead, web.archive.org is blocked in this environment), so the exact theorem statement and any
measured numbers in it are **unverified**. **FLAG:** Lewis & Gale (1994), "A sequential algorithm for
training text classifiers," SIGIR '94 pp. 3–12 (also arXiv cmp-lg/9407020), is **uncertainty sampling
/ active learning**, not thresholding — the brief conflates it with the 1995 thresholding paper.

## Process notes

WebSearch hit its 200-call session cap after two queries, so almost all of this was gathered via
WebFetch against arXiv, PMLR, ACL Anthology, research.google, UvA DARE, and the OpenAlex REST API
(which itself rate-limited at the end; Semantic Scholar's API 429'd throughout). WebFetch's text
extractor fails on PDFs, so I extracted the fetched PDFs locally with PyMuPDF — that is how the exact
Platt equations, the Zadrozny & Elkan tables, the Guo/Yan/Bai/Cohen/Penha/Yu result tables, and the
Robertson convexity quote were obtained. Three paywalls were not crossed (ACM DL PDFs, SpringerLink,
Emerald) and one CAPTCHA (DuckDuckGo) I did not attempt.
