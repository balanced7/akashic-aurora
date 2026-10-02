# Prior art: when a proactive retriever should fire, and what firing wrong costs

**Commissioned 2026-10-02 by claude (Vandor)** for W0.3. This is the RESUMED, fuller delivery from
the same researcher whose interim report is preserved in
`prior-art-hard-negatives-and-situational-relevance-2026-10-02.md`. That file holds the first
delivery; this one holds the sections that are materially new or substantially expanded in the
second. The two overlap on hard negatives, relevance theory and lexical pathology, and where they
overlap the earlier file stands.

**What is new here:** the Watson replication, Rhodes' score/usefulness correlations, his two-sided
gate, the whole when-to-fire section, the measured ignore rates, ProactiveBench, and the
researcher's verification ledger.

---

## THE DESIGN FINDING, and the test we ran against it the same hour

Rhodes' Margin Notes did not have a floor. It had a **floor and a ceiling**: show nothing below
relevance 0.1, and **suppress anything above 0.65**, because a near-duplicate of what you are
already looking at carries no new information. Our gate is one-sided. Our M4 abstain has the highest
top-score of any abstain in the set at 0.766, above most positives, which is exactly the shape a
ceiling is for.

**We tested the two-sided idea immediately and it FAILED on our data.** We also tested a cleaner
version of it, separating the two decisions a single floor conflates:

- should the surface SPEAK at all, a property of the returned LIST
- which items should it SHOW, a property of each ITEM

| rule | recall@1 | recall@5 | abstention |
|---|---|---|---|
| live single floor 0.20 | 20% | 30% | 0/5 |
| single floor 0.78 (already falsified) | 20% | 20% | 5/5 |
| two-gate, speak >= 0.78, show >= 0.00 | 20% | **20%** | 5/5 |
| two-gate, speak >= 0.85, show >= 0.20 | 20% | **20%** | 5/5 |

Separating the gates bought nothing. The reason is in the numbers and it is not fixable by rule
shape: the M4 abstain has a top score of 0.766 while the N12 positive has 0.621. **Any gate on the
top score alone that silences M4 also silences N12.** The loss was never the per-item filter.

A separating rule does exist on the current 16 if you use the rank1-to-rank2 margin as well, since
M4's margin is 0.000 against N12's 0.065. We have NOT built it. Fitting a two-feature band to four
positives and five negatives is the same mistake as the floor at higher complexity, and the floor
has already been scored a miss. The prediction is registered as `F-recall-margin-rule` and waits for
moments nobody has written yet.

**And the strategic finding, which is the one that should set expectations for the whole gate lane.**
Rhodes measured his score against human judgment directly: it correlates with judged RELEVANCE at
r = 0.36, p = 0.0002, which is **13% of the variance**, and its correlation with judged USEFULNESS
was **not significant**. Watson, independently, got similarity-to-utility r = 0.51, so **r-squared
0.26, about a quarter of the variance in utility**. Two systems, built on different corpora a
continent apart, both measured that the retrieval score carries somewhere between an eighth and a
quarter of the information about whether the thing is worth showing. No rule computed from that score
can do much better than the score allows. That is an argument for putting the actor's situation into
the query, which is Wave 1 row A6, rather than for a cleverer gate.

---
---

# Confident retrieval of the wrong document: the literature

*(researcher's full resumed text. Sections 1 through 3 and 6 overlap the earlier file and are kept
there; what follows is the new and expanded material, reproduced unedited.)*

## 0. What the failure mode is called

Your shape — two situations sharing nearly all vocabulary but differing in mechanism, where the
correct document for A wins decisively for B — sits at the intersection of four separately-developed
literatures that rarely cite each other:

1. **Hard/false negatives** in dense-retrieval training (ML side: the pair is a training problem).
2. **Topical vs situational relevance** in information science (theory side: the pair is a
   *relevance-type* problem, and a topic-only system provably cannot represent the difference).
3. **Lexical over-match** / term-independence pathologies in BM25 (mechanism side: the scoring
   function has no place to put the decisive token).
4. **Just-in-time / zero-query IR** (systems side: where the query is a situation, and where
   "relevance ≠ usefulness" was measured in 2000 and never solved).

The single most on-point published instrument is **NevIR** (Weller, Lawrie & Van Durme, EACL 2024):
2,556 document *pairs* that differ only by a negation, with a query for each member. It is literally
your scenario with the decisive detail held to one token.

---

## 4.2 (expanded) The measured ladder on near-duplicate discrimination

Random = 25%, human = 100%.

| Class | Model | Paired accuracy |
|---|---|---|
| Sparse / lexical | TF-IDF | **2.0** |
| | SPLADEv2 | 8.0–8.7 |
| Bi-encoder | DPR | 6.8 |
| | coCondenser / RocketQAv2 | 7.7 / 7.8 |
| | multi-qa-mpnet | 11.1 |
| | gte-Qwen2-7B-instruct | 19.0 |
| | **Promptriever-mistral-7b** | **19.7** (below chance) |
| | OpenAI text-embedding-3-large | 22.6 |
| | GritLM-7B | 39.0 |
| Late interaction | ColBERTv2 / v1 | 13.0 / 19.7 |
| Cross-encoder | RocketQAv2 | 22.4 |
| | monoT5 small / base / large / 3B | 27.7 / 34.9 / 45.8 / **50.6** |
| | RankLlama-7B / bge-reranker-v2-m3 / jina-reranker-v2 | 31.6 / 43.5 / **65.2** |
| Reasoning reranker | Rank1-7B / 14B / 32B | **65.1 / 67.5 / 70.1** |
| Listwise LLM | Qwen2-7B / Mistral-7B-Instruct | 36.9 / 46.3 |
| | GPT-4o-mini / GPT-4o / o3-mini | 64.1 / 70.1 / **77.3** |

Read it as four facts:

1. **The first-stage/reranker gap on near-duplicates is enormous** — from 2–11% to 35–65%, an order
   of magnitude, far larger than the corresponding gap on MS MARCO (roughly 0.18 → 0.40 MRR@10,
   barely a factor of two). This is the one place where cross-encoders are not an incremental
   upgrade.
2. **It is still nowhere near solved.** The best cross-encoder in the original paper, monoT5-3B, is
   at 50.6% against 25% chance and 100% human. Scaling helps monotonically (27.7 → 34.9 → 45.8 →
   50.6 across monoT5 sizes) but does not close it.
3. **Explicit reasoning at inference buys the largest single jump.** Rank1-7B at 65.1% vs
   RankLlama-7B 31.6% and monoT5-3B 34.9%; and on BRIGHT the ablation is stark — Rank1-7B scores
   27.5 nDCG@10 with reasoning, **17.5 without**.
4. **Instruction-following in a bi-encoder does not transfer.** Promptriever — explicitly trained to
   follow instructions, and strong on instruction benchmarks — scores **19.7%, below the 25% random
   baseline**, on near-duplicate negation. Whatever the architecture needs here, instruction-tuning
   a dual encoder does not supply it.

The fine-tuning trade-off is measured too, in the reproduction: multi-qa-mpnet reaches 50.1% NevIR
with MS MARCO MRR@10 collapsing to 0.06, versus 48.9% NevIR at MS MARCO 0.20 under a trade-off
selection criterion; monoT5-base reaches 71.6% NevIR at MS MARCO 0.30. Buying discrimination costs
general ranking unless you select for it deliberately.

---

## 5. When the query is an action or a situation

### 5.1 The lineage

| System | Citation |
|---|---|
| Fixit, coining "query-free information retrieval" | Hart, P. E. & Graham, J., *IEEE Expert* 12(5):32–37, 1997, DOI 10.1109/64.621226 |
| Letizia | Lieberman, H., *Proc. IJCAI-95*, pp. 924–929 |
| Remembrance Agent | Rhodes, B. J. & Starner, T., *Proc. PAAM '96*, pp. 487–495 |
| Wearable RA / Jimminy | Rhodes, *ISWC '97*, pp. 123–128 and *Personal Technologies* 1(4):218–224 |
| WebWatcher | Joachims, T., Freitag, D. & Mitchell, T., *Proc. IJCAI-97* |
| Watson | Budzik, J. & Hammond, K. J., *IUI '00*, pp. 44–51; Budzik, Hammond & Birnbaum, *Knowledge-Based Systems* 14(1–2):37–53, 2001 |
| Margin Notes | Rhodes, *IUI '00*, pp. 219–224 |
| JITIR thesis | Rhodes, B. J., "Just-In-Time Information Retrieval," PhD, MIT Media Lab, May 2000, 150 pp. (supervisor Pattie Maes) |
| JITIR survey | Rhodes & Maes, *IBM Systems Journal* 39(3&4):685–704, 2000 |
| Jimminy, physical context | Rhodes, *IEEE Transactions on Computers* 52(8):1011–1014, 2003 |
| PowerScout | Lieberman, Fry & Weitzman, *CACM* 44(8):69–75, 2001 |

Two corrections to common recollection: the RA's back end in 1996 was **SMART**, not Savant (Savant
arrives by 1999–2000; "wn" appears in none of six primary Rhodes sources). Savant's text scoring is
BM25 with k₁=1.2, k₃=100, b=0.75, over hand-set, by Rhodes' own admission arbitrary, field biases.

### 5.2 The result that matters most for you, and it is 26 years old

Rhodes' thesis Study 2 is a direct measurement of the topical/situational gap inside a just-in-time
retriever. Media Lab researchers' own papers were annotated by Margin Notes against INSPEC (152,860
docs) with thresholding disabled and relevance scores blanked; the authors rated their own
annotations. N = 9 researchers, 112 annotations.

| | All 112 annotations | Top 20% by Savant's own relevance score |
|---|---|---|
| General relevance | 3.3 ± 0.3 | **3.9 ± 0.7** |
| Section relevance | 3.4 ± 0.3 | **4.0 ± 0.7** |
| **Usefulness** | **2.7 ± 0.3** (35% rated 4–5) | **2.7 ± 0.7** (36% rated 4–5) |

**Gating on the relevance score lifts judged relevance by 0.6 points and leaves judged usefulness
exactly flat.** Rhodes' conclusion, verbatim: "relevance was a necessary but not sufficient condition
for usefulness."

The IBM Systems Journal paper adds the correlation: the raw unnormalised score correlates with human
judgments of relevance at **r = 0.36, p = 0.0002 — 13% of the variance**; normalised scores r = 0.13,
not significant; and "correlations between scores and usefulness were not significant." Any threshold
built on that score is firing on a 13%-informative signal.

The failure taxonomy he reports is almost a description of your bug. Reasons a suggestion was not
useful: not relevant enough 42%, already knew about it 29%, low quality 12%, it is my own paper 10%,
don't need more references 7%. Of the 14% rated low-usefulness but *high*-relevance, **100% were
already known to the rater and 68% were written by the rater** — "One might say these documents were
too relevant to be useful." He then names the second category explicitly: documents "so similar that
no new information was presented," for which Margin Notes tries to suppress near-identical items,
"but the detection cannot be perfect **because documents can still differ from the current
environment in only trivial ways.**"

And corpus fit dominates everything: the same papers annotated against a Media Lab email corpus
instead of INSPEC score general relevance 2.6 ± 0.4, section 2.8 ± 0.4, **usefulness 1.7 ± 0.2** with
only 5% reaching 4-or-5; all differences significant at p ≤ 0.05.

### 5.3 Watson reached the same conclusion independently

Budzik, Hammond & Birnbaum (KBS 2001) put it in their abstract: **"contrary to the assumptions of
many system designers, similar documents are not necessarily useful documents in the context of a
particular task."** Their Experiment 2 (6 respondents, 74 auto-fired suggestions, two 5-point
scales):

- **Mean precision 0.25 ± 0.22 useful, against 0.48 ± 0.27 judged merely "similar."** One of six
  subjects found **zero** useful documents.
- Similarity-to-utility correlation **r = 0.51**, so similarity accounts for **r² = 0.26 — about a
  quarter of the variance in utility**. Per-subject correlations range 0.11 to 0.85.

Watson's IUI 2000 study also names the mechanism in the user's words: failures were **"mere-appearance
matches**: they were lexically similar, but generally off-topic." Watson used no IDF at all (its
target repositories did not expose corpus statistics); instead seven document-structure heuristics —
value emphasised words, value words earlier in the document, punish de-emphasised words, ignore
ordering within lists, ignore navigation — with the top 20 terms re-sorted into document order
forming the query.

*Flag: IUI 2000 and KBS 2001 report irreconcilable numbers for the earlier study (10 researchers / 8
of 10 useful / 4 novel vs 6 responded / all useful / 2 novel), and KBS's prose contradicts its own
Table 2 (Subject 3 scores zero useful). Treat the N=6 Table 2 data as authoritative.*

### 5.4 Did anyone solve WHEN to fire?

No. But the question has been posed four distinct ways, and three of them produced measurements.

**(a) Rhodes posed it and reversed himself.** In 1996 he argued *against* thresholded display: "it is
impossible to create a back end which can reliably know when a document is useful for a user… If the
RA only displayed a suggestion when the relevance passed a certain threshold, the users' attention
would be drawn away from their primary task whenever a new suggestion appeared. With the high ratio
of false-positives, this would rapidly become a prohibitive distraction." By 1997, after informal
long-term wear, he reversed: because suggestions are displayed even when nothing relevant is
available, "the wearer has a tendency to distrust the display, and after a few weeks of use… tends to
ignore the display." By 2000 the cull is hard numeric gates in Margin Notes: show nothing below
relevance 0.1, **suppress anything above 0.65** (a near-duplicate carries no new information), skip
sections under 100 words and documents under 200 words. He names the cost himself: "valuable
suggestions might occasionally not be shown. It is also difficult to set these thresholds properly,
and the values may be dependent on the particular task and corpus used."

His theoretical resolution is the **ramping interface**: six stages from no-action through peripheral
indicator, histogram, note, mouse-over, to click — each costing more attention, each allowing
bail-out. Its third stated assumption is the one that makes abstention necessary: "the act of
determining whether a suggestion might be useful is in itself a distraction and produces cognitive
load." And his design rule, which is the claim you are probably looking for: **"the information
retrieval algorithms for JITIRs should tend to favor precision over recall"** — because "more
suggestions, even if all of them were relevant, would be too much of a distraction" — paired with a
requirement that "JITIRs require a combination of ranked-best evaluation and filtering… and to
potentially suppress the display of low-quality suggestions."

**Lieberman states the opposite position just as explicitly.** Letizia, CHI 1997: a
continuously-running agent "can be bolder in its recommendations… since it is likely to get another
chance to do better at some future time," and need only be "better than nothing"; the relevant output
is "a preference ordering of interest among a set of links," not an absolute score. Letizia's firing
rule is a *quota* — recommend a settable percentage of the links currently available — explicitly
rejecting an absolute interestingness threshold. Note also that Letizia, PowerScout and SUITOR report
**no quantitative evaluation of any kind**; this is an absent result, not a weak one.

**(b) Horvitz posed it as expected utility, and priced both errors.** "Principles of Mixed-Initiative
User Interfaces" (CHI 1999) derives the threshold `p*` where the expected utilities of acting and not
acting cross, then adds dialog as a third action, giving **two** thresholds: `p*_{¬A,D}` between
inaction and dialog, and `p*_{D,A}` between dialog and action. Crucially he does **not** take a
precision-first position: "The utility of unwanted action can diminish significantly with increases
in the depth of a user's focus on another task… leads to a higher probability threshold" — but
equally, the cost of *not* acting when the user does have the goal "may decrease as a user becomes
more rushed," which *reduces* the threshold. (CHI 1999 gives no numeric values for any threshold.)

"Learning and Reasoning about Interruption" (Horvitz & Apacible, ICMI 2003, pp. 20–27) operationalises
cost of interruption as willingness-to-pay in dollars, prices six interruption types simultaneously,
and learns it from desktop, calendar, acoustic and vision sensors. Accuracy on current COI: all
events .73/.64 for two subjects vs marginal .53/.37. **Cross-user transfer fails outright: S1→S2 .28,
S2→S1 .32 — worse than the marginal model.** BusyBody (Horvitz, Koch & Apacible, CSCW 2004, pp.
507–510) reports 0.87/0.70/0.85/0.71 accuracy for four users on 2,365/789/1,449/470 training cases.
Bounded deferral (Horvitz, Apacible & Subramani, UM 2005, pp. 433–437) measured 4,803 busy situations
across **113 users**: mean busy duration **43.12 s (SD 51.79)**, with the great majority transitioning
to free within one to two minutes — and for email, "a deferral of 4 minutes would lead to a
diminishment of alerts during busy times from 20 to 4 alerts for participant 1 and from 80 to zero
for participant 2."

**(c) Iqbal & Bailey measured task breakpoints, and found the detectable ones are the useless ones.**
Bailey & Iqbal (TOCHI 14(4), 2008; 24 users, pupillometry at 250 Hz) found boundaries show ~12%
workload increase, mean duration 590 ms — but "**not all boundaries exhibit a detectable decrease in
workload**"; the effect only reaches significance once the *lowest-level* (i.e. most
machine-detectable) boundaries are excluded. Iqbal & Bailey CHI 2005: resumption lag **2.06 s at Best
moments vs 6.69 s at Worst and 5.66 s Random** (F(2,22)=6.866, p<0.005). CHI 2006: a 3-predictor model
of cost of interruption reached adjusted R² = 0.26, and an MLP classified three COI levels at 63.2%
(10-fold CV) in-domain, **53% on different tasks**, with the "most egregious" error (predicting low
COI when it was high) rising from 4.7% to 20.8% out of domain. CHI 2008, deferral to detected
breakpoints: recall 41.5%/41.3% (coarse), down to 15%/1.7% (fine), false-alarm rate 2.8%/2.3%; mean
deferral 88.6 s; frustration improved, and — correcting a common recollection — **resumption time
showed no policy effect**.

**(d) The recent LLM literature made it a trained decision, and the numbers are consistent.**

- **Mallen, Asai, Zhong, Das, Khashabi & Hajishirzi, "When Not to Trust Language Models" (ACL 2023).**
  PopQA, 14,267 questions. Retrieval **flips 10% of correct answers to wrong** (recall@1 on that
  slice is 0.14 vs 0.42 overall), while fixing 17%. Their Adaptive Retrieval — retrieve only when the
  subject entity's popularity falls below a per-relation threshold — reaches **46.5% accuracy, 5.3
  points above any non-adaptive method**, while retrieving for only 40% of questions.
- **FLARE** (Jiang et al., EMNLP 2023): retrieve when a token's probability falls below θ, and mask
  low-confidence tokens out of the query because "low-confidence erroneous tokens can distract
  retrievers." On StrategyQA, **no retrieval (72.9) beats single-time retrieval (68.6)**; FLARE
  reaches 77.3. Their sweep: "triggering retrieval for 40%–80% of sentences usually leads to a good
  performance," with performance *dropping* above 50% on StrategyQA.
- **Adaptive-RAG** (Jeong, Baek, Cho, Hwang & Park, NAACL 2024): a T5-Large router picks
  no-retrieval / single-step / multi-step. It reaches 48.97 average accuracy at 1.03 steps versus
  multi-step's 49.70 at 2.81 steps — **~99% of the accuracy at ~37% of the retrieval calls** — while
  the router itself is only **54.52% accurate**.
- **SKR** (Wang, Li, Sun & Liu, Findings of EMNLP 2023) reports the decisive negative on the obvious
  gate: asking the model whether it can answer unaided is a weak signal — accuracy on
  self-declared-answerable questions was 71–73%, meaning **~30% "unknown unknowns"** — and their
  prompt-based variant performs at or below chance as guidance, while a k-NN variant reaches 55–78%.
- **Labruna, Campos & Azkune (2025)**: popularity thresholding re-run on Llama-2-7B degenerates to
  **retrieving 99.86% of the time**; their trained ⟨RET⟩ token gate retrieves 84% of the time at
  slightly higher accuracy, and forcing context where the gate declines it **costs up to 7 absolute
  points**.
- **Kamath, Jia & Liang, "Selective Question Answering under Domain Shift" (ACL 2020)** is the
  reference point for abstention: a trained calibrator achieves **56.1% coverage at 80% accuracy**
  versus MaxProb's 48.2%, because "abstention policies based solely on the model's softmax
  probabilities fare poorly, since models are overconfident on out-of-domain inputs."

**(e) IR's own abstention machinery, which is older and under-cited.** Deciding *how many* results to
return, including zero, is a named task: **Arampatzis, Kamps & Robertson, "Where to stop reading a
ranked list? Threshold optimization using truncated score distributions" (SIGIR 2009)**; **Bahri,
Tay, Zheng, Metzler & Tomkins, "Choppy: Cut Transformer for Ranked List Truncation" (SIGIR 2020)**;
Wu et al. AttnCut (AAAI 2021); Ma et al. LeCut/JOTR (SIGIR 2022); Bahri et al. Surprise (SIGIR 2023);
and **Meng, Arabzadeh, Askari, Aliannejadi & de Rijke, "Ranked List Truncation for Large Language
Model-based Re-Ranking" (SIGIR 2024)**. Upstream of it sits **query performance prediction** —
Cronen-Townsend, Zhou & Croft (SIGIR 2002, clarity score) onward — whose own evaluation is contested
(Faggioli, Zendel, Culpepper, Ferro & Scholer, ECIR 2021 and *IRJ* 2022 "sMARE"; Zendel, Culpepper &
Scholer, SIGIR 2021).

**(f) The field now has a metric that penalises firing at the wrong moment.** **Samarinas & Zamani,
"ProCIS: A Benchmark for Proactive Retrieval in Conversations" (SIGIR 2024)** — 2.8M conversations,
depth-k pooled judgments, and **normalized proactive discounted cumulative gain (npDCG)**, which
gives no credit before a document becomes relevant and decays after. Their structural finding is the
one to carry: **retrieval quality and timing quality are separable and can be anti-correlated** —
their best reactive model ranks second-worst on npDCG, while a weaker reactive model wins
proactively.

### 5.5 Measured ignore rates, which is what "firing wrong" costs

- Remembrance Agent, long-term logs: 6 self-selecting users, 740 calendar days (312 active),
  **186,480 suggestions displayed, 197 followed = 0.1%**. Only 49 of the 197 were rated, averaging
  3.1/5. *Rhodes himself: "because the sample size is small these log-file results are not
  statistically significant and should be taken as anecdotal."*
- Margin Notes, one month, 12 users: "Of the 4576 suggestions shown during the period in question,
  **only 6% of them were followed** to the full-text." Seven of eight survey respondents named
  suggestion quality as the single most needed improvement; all eight ranked it top two. One tester's
  statement of the asymmetry: "when a search engine returns bad hits he just tries different search
  terms… When Margin Notes produces a bad suggestion he is annoyed that it cluttered his screen
  without merit."
- Bing clarification panes (Zamani, Lueck, Chen, Quispe, Luu & Craswell, MIMICS, CIKM 2020; 400k+
  unique queries): **82.8% of 414,362 production query-clarification pairs received zero clicks.**
- A controlled null: **Czerwinski, Dumais, Robertson, Dziadosz, Tiernan & van Dantzich, "Visualizing
  implicit queries for information management and retrieval" (CHI 1999, pp. 560–567)**, N=35 — no
  significant benefit on retrieval time or errors, organisation time went *up*, and the
  better-matching content-based variant was rated **significantly less satisfying and more
  distracting** than the weaker co-occurrence one.
- Jimminy's only quantitative evaluation is N=1 (the author), 300 note pairs, and it is a **null
  result for physical context**: All-features 56% rated 4-or-5, **note text alone 50% (difference not
  significant)**, Subject 24%, Location 12%, Person 8%, random control 0%. His verdict: "Jimminy is an
  example where physical context… is not especially useful for automatically retrieving information
  from a personal notes archive."
- Frontier LLM agents reproduce the same precision profile. **Lu et al., "Proactive Agent" (2024)**,
  ProactiveBench, 233 real-world test events: every model sits at **97–100% recall and 35–50%
  precision, with false-alarm rates of 50–65%** (GPT-4o: recall 98.11%, precision 48.15%, false alarm
  51.85%). Their framing: "Most of them succeed in assisting when the user needs but fail to stay
  silent when the user does not require any assistance." Offering three candidates instead of one
  drops GPT-4o's false alarm from 51.85% to 36.44%.
- And a caution about optimising the gate: **Mozannar, Bansal, Fourney & Horvitz, "When to Show a
  Suggestion? Integrating Human Feedback in AI-Assisted Programming" (AAAI 2024)** build a
  utility-theoretic display/withhold decision (CDHF) over GitHub Copilot data from 535 programmers,
  and report in their own abstract that **using suggestion acceptance as the reward signal for
  guiding display "can lead to suggestions of reduced quality"** — the gate corrupts the payload.

### 5.6 Two literatures almost nobody connects, and they are the closest fit

**Lessons-learned systems.** Your corpus is literally this field's object. **Weber, Aha &
Becerra-Fernandez, "Intelligent lessons learned systems," Expert Systems with Applications (2001)**;
**Weber, Aha, Muñoz-Avila & Breslow, "Active Delivery for Lessons Learned Systems" (EWCBR 2000,
LNCS)**; **Weber, Aha, Branting, Lucas & Becerra-Fernandez (FLAIRS 2000)**, whose architecture is a
*monitor* embedded in a conversational case-based plan authoring system (HICAP) that, as users
interact and update domain objects, "alerts the user to the ramifications of past experiences"; and
**Weber & Aha, "Intelligent delivery of military lessons learned," Decision Support Systems (2003)**.
The field's founding diagnosis is that lessons repositories fail because lessons must be *delivered
into the task*, not searched for. *(Flag: I verified these citations and the FLAIRS abstract; the 2001
and 2003 papers' bodies were not obtainable.)*

**Analogical retrieval.** The cognitive-science literature named your exact dissociation and built the
two-stage architecture for it before IR did. **Gentner, Rattermann & Forbus, "The Roles of Similarity
in Transfer: Separating Retrievability From Inferential Soundness," Cognitive Psychology (1993)** —
surface similarity drives what gets retrieved; structural similarity drives what is judged sound.
**Forbus, Gentner & Law, "MAC/FAC: A Model of Similarity-Based Retrieval," Cognitive Science (1995)**:
a computationally cheap non-structural matcher (MAC) followed by structural alignment (FAC) —
retrieve-then-rerank, derived from the finding that structural commonalities dominate similarity
judgments *despite* surface similarity dominating retrieval. And in case-based reasoning, **Smyth &
Keane, "Adaptation-guided retrieval: questioning the similarity assumption in reasoning," Artificial
Intelligence 102 (1998)** — retrieving the most *similar* case is not retrieving the most *usable*
one, so retrieval should be indexed by adaptability rather than surface similarity. *(Flag: for
Gentner et al. 1993 and Smyth & Keane 1998 I verified authorship, venue and citation counts via
OpenAlex but could not obtain the full texts; the MAC/FAC two-stage description is from its verified
abstract.)*

---

## 6 (new items only) Where the literature genuinely disagrees

6. **Precision-first vs bolder-is-fine for proactive systems.** Rhodes: favour precision over recall,
   and suppress. Lieberman: be bolder, you get another chance, "better than nothing" suffices.
   Horvitz: price both errors and let the context set the threshold. ProCIS's npDCG penalises firing
   early; Sen's C4 criterion *rewards* it. The two modern timing-aware metrics disagree about the sign
   of the penalty.

---

## 7. Verification ledger

**Read as primary text by the researcher:** Saracevic 2007 Part II (local text extraction of the
Rutgers PDF — the five manifestations, the weak/strong passage, the primacy section, the
Soergel/Hersh/Ingwersen quotations); Rhodes' MIT thesis (local text extraction — Study 2 tables, the
0.1% log result, the "too relevant to be useful" and near-identical-document passages, the
thresholds).

**Verified from paper, abstract or authoritative metadata via direct fetch:** ANCE, RocketQA, Zhan et
al., DPR, Cai et al., SimANS, NV-Retriever, Robinson et al., Wang & Liu, the negative-sampling
survey, Shallow Pooling, LIMIT, hubness, NevIR, Reproducing NevIR, Rank1, FollowIR, Promptriever,
InstructIR, InfoSearch, ExcluIR, QUEST, BRIGHT, RankGPT, RankZephyr, PRP, Rosa et al., Drowning in
Documents, Pathway to Relevance, Cohen et al., the truncation papers, Power of Noise and its
reproducibility rebuttal, HANS, Lucene's IDF formula, Furnas (Crossref abstract), Mallen et al.,
CUPS, When to Show a Suggestion, ProCIS, MIMICS, Hjørland 2010 (abstract), Wilson 1973
(Crossref/ERIC), plus Crossref-verified citations for Hart & Graham, Rhodes & Maes, Rhodes 2003,
Budzik & Hammond, Czerwinski et al. 1999, Hipikat, ROSE, Mylyn, Horvitz & Apacible, BusyBody, bounded
deferral, Henzinger et al., Bernstein & Zobel, Shokouhi & Guo, Metzler & Croft, Smyth & Keane,
MAC/FAC, Gentner et al. 1993, Weber/Aha (all four), and the QPP lineage.

**Relayed from teammates who read the primary text, and NOT independently verified at the number
level:** Zhao & Callan's necessity tables and the over-match quotation; Robertson 2004 and
Fang/Tao/Zhai quotations; Robertson & Zaragoza's §3.8 and scrambling passages; BEIR's per-dataset
table and the Kamalloo re-audit; Fröbe et al.'s duplicate statistics; doc2query's new/copied
ablation; Saracevic Part III's criteria groups, the five postulates and the assessor-overlap figures;
Cosijn & Ingwersen and Borlund quotations; Harter's p. 613 quotation; Watson's Experiment 2 table and
the 2006 Ford/Bigchalk/Motorola field findings; Letizia/PowerScout/WebWatcher quotations; Jimminy's
N=1 table; Margin Notes' 6% of 4,576; the Horvitz/Iqbal-Bailey/Mark et al. numbers; and the
FLARE/Adaptive-RAG/SKR/Labruna/Kamath numbers.

**Could not be verified at all — do not cite without checking:**
- **Cooper 1971** — no abstract or full text obtainable; all content secondary.
- **Hjørland 2010** — no open-access copy exists; abstract-level only. His specific critique of
  Saracevic's manifestations framework is *not* verified at sentence level.
- **Schamber, Eisenberg & Nilan 1990** — abstract elided by Elsevier; the three conclusions come via
  Borlund's 2013 attribution to p. 774.
- **Gentner, Rattermann & Forbus 1993** — existence, venue and 640 citations confirmed; the specific
  percentages for mere-appearance vs true-analogy reminding are **not** verified.
- **Smyth & Keane 1998** — existence and venue confirmed (AIJ, 175 citations); no text obtained,
  including any measured results from their DÉJÀ VU system.
- **Lv & Zhai**, "When documents are very long, BM25 fails!" (SIGIR 2011) and "Lower-bounding term
  frequency normalization" (CIKM 2011) — the canonical BM25 TF-normalisation pathology papers, not
  retrieved.
- **Developer-tool recommenders**: no measured precision/recall was verified for Mylyn, Hipikat,
  ROSE, Strathcona, Prospector or Suade; citations only. In particular, the Murphy-Hill & Murphy
  chapter "Recommendation Delivery: Getting the User Interface Just Right" in *Recommendation Systems
  in Software Engineering* (Springer 2014) — the most on-point source for the triggering question in
  that field — was not obtained.
- **Zero-query canon**: the SWIRL workshop reports that introduced the term; Shokouhi & Guo's actual
  numbers; Benetka/Krumm/Bennett; Teevan's and White's proactive-search papers; and the
  notification-receptivity line (Pielot et al., Mehrotra et al., Okoshi et al. "Attelia") — all
  unverified. That last body is the most relevant missing when-to-fire evidence.
- **"Is the lexical gap the only problem?"** — no paper with that or a close title was found; the
  nearest is Van Gysel, "Remedies against the Vocabulary Gap in Information Retrieval" (arXiv
  1711.06004), unread. The title may be a misremembering.
- **Self-RAG's venue** (the PDF is headed "Preprint"; ICLR 2024 not confirmed in this session).
  **Rowen** is SIGIR-AP 2025, **SeaKR** is ACL 2025, **Labruna et al.** is RANLP 2025 — all three
  corrected from common citation.

**Citation errors found and worth propagating:** Saracevic 2007 Part II is JASIST **58(13)**:1915–1933,
not 58(3) (his own Rutgers page is wrong). Saracevic's own Part II reference list misprints Harter
1992 as *JASIS* 53(4); it is **43(9)**:602–615. Hjørland & Sejer Christensen is **2002, JASIST
53(11)**:960–965, not 55(11)/2004 (JASIST 55(11):963–969 is Vakkari & Sormunen 2004). BusyBody's
author order is **Horvitz, Koch & Apacible**. NevIR's random baseline is **25%**, not 50% — it is a
paired metric over two queries.
