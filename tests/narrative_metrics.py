"""
Narrative metrics (shared test asset) — standard, dependency-free implementations of
the benchmark metrics from the relevant research fields. Reused across slices.

  Clustering / disentanglement:  ari(), nmi(), purity(), accuracy()
  Segmentation:                  boundaries(), windowdiff(), pk(), boundary_f1()
  Multi-label (themes):          multilabel_prf(), jaccard_multilabel()
"""
import math
from collections import Counter, defaultdict
from typing import Iterable, List, Sequence, Tuple


def _comb2(x: int) -> int:
    return x * (x - 1) // 2


def ari(gold: Sequence, pred: Sequence) -> float:
    """Adjusted Rand Index — agreement of two clusterings, chance-corrected,
    permutation-invariant. 1.0 = identical, ~0 = random. (disentanglement standard)"""
    n = len(gold)
    if n == 0:
        return 1.0
    pair = Counter(zip(gold, pred))
    a = sum(_comb2(v) for v in pair.values())
    b = sum(_comb2(v) for v in Counter(gold).values())
    c = sum(_comb2(v) for v in Counter(pred).values())
    total = _comb2(n)
    if total == 0:
        return 1.0
    expected = (b * c) / total
    max_index = (b + c) / 2
    if max_index - expected == 0:
        return 1.0
    return (a - expected) / (max_index - expected)


def nmi(gold: Sequence, pred: Sequence) -> float:
    """Normalized Mutual Information (arithmetic-mean normalization)."""
    n = len(gold)
    if n == 0:
        return 1.0

    def H(labels):
        c = Counter(labels)
        return -sum((v / n) * math.log(v / n) for v in c.values())

    gc, pc = Counter(gold), Counter(pred)
    mi = 0.0
    for (g, p), v in Counter(zip(gold, pred)).items():
        pij, pi, pj = v / n, gc[g] / n, pc[p] / n
        mi += pij * math.log(pij / (pi * pj))
    denom = (H(gold) + H(pred)) / 2
    return mi / denom if denom > 0 else 1.0


def purity(gold: Sequence, pred: Sequence) -> float:
    n = len(gold)
    if n == 0:
        return 1.0
    clusters = defaultdict(list)
    for g, p in zip(gold, pred):
        clusters[p].append(g)
    return sum(max(Counter(v).values()) for v in clusters.values()) / n


def accuracy(gold: Sequence, pred: Sequence) -> float:
    if not gold:
        return 1.0
    return sum(1 for g, p in zip(gold, pred) if g == p) / len(gold)


def boundaries(labels: Sequence) -> List[int]:
    """Per-position label sequence -> boundary array (1 where label changes)."""
    return [1 if labels[i] != labels[i + 1] else 0 for i in range(len(labels) - 1)]


def _k_from(gold_b: List[int]) -> int:
    n = len(gold_b) + 1
    nseg = sum(gold_b) + 1
    return max(1, round((n / nseg) / 2))


def windowdiff(gold_b: List[int], pred_b: List[int], k: int = None) -> float:
    """WindowDiff — slide a window; penalize where boundary counts differ.
    0 = perfect, ~1 = worst. (topic-segmentation standard)"""
    m = len(gold_b)
    if m == 0:
        return 0.0
    if k is None:
        k = _k_from(gold_b)
    k = min(k, m)
    errors = count = 0
    for i in range(0, m - k + 1):
        if sum(gold_b[i:i + k]) != sum(pred_b[i:i + k]):
            errors += 1
        count += 1
    return errors / count if count else 0.0


def pk(gold_b: List[int], pred_b: List[int], k: int = None) -> float:
    """Pk — probability two positions k apart are wrongly judged same/different segment."""
    def seg_ids(b):
        ids, cur = [0], 0
        for x in b:
            cur += 1 if x else 0
            ids.append(cur)
        return ids

    g, p = seg_ids(gold_b), seg_ids(pred_b)
    n = len(g)
    if n < 2:
        return 0.0
    if k is None:
        k = _k_from(gold_b)
    k = min(k, n - 1)
    errors = count = 0
    for i in range(0, n - k):
        if (g[i] == g[i + k]) != (p[i] == p[i + k]):
            errors += 1
        count += 1
    return errors / count if count else 0.0


def boundary_f1(gold_b: List[int], pred_b: List[int], tol: int = 1) -> float:
    """F1 of boundary positions, matched within +/- tol."""
    gold_idx = [i for i, x in enumerate(gold_b) if x]
    pred_idx = [i for i, x in enumerate(pred_b) if x]
    matched, tp = set(), 0
    for pi in pred_idx:
        for gi in gold_idx:
            if gi not in matched and abs(pi - gi) <= tol:
                tp += 1
                matched.add(gi)
                break
    fp, fn = len(pred_idx) - tp, len(gold_idx) - len(matched)
    prec = tp / (tp + fp) if (tp + fp) else 1.0
    rec = tp / (tp + fn) if (tp + fn) else 1.0
    return 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0


def multilabel_prf(
    gold_sets: Iterable[Iterable[str]],
    pred_sets: Iterable[Iterable[str]],
) -> Tuple[float, float, float]:
    """Micro-averaged precision / recall / F1 over (item, label) membership pairs.

    The correct metric for MULTI-LABEL assignment (themes): NMI assumes a partition,
    but a Beat can carry many themes. Micro-averaging over all (beat, theme) pairs
    weights every membership equally and degrades gracefully on empty label sets.
    """
    tp = fp = fn = 0
    for g, p in zip(gold_sets, pred_sets):
        g, p = set(g), set(p)
        tp += len(g & p)
        fp += len(p - g)
        fn += len(g - p)
    prec = tp / (tp + fp) if (tp + fp) else 1.0
    rec = tp / (tp + fn) if (tp + fn) else 1.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    return prec, rec, f1


def jaccard_multilabel(
    gold_sets: Iterable[Iterable[str]],
    pred_sets: Iterable[Iterable[str]],
) -> float:
    """Mean per-item Jaccard overlap of label sets (1.0 = identical sets each item)."""
    scores, n = 0.0, 0
    for g, p in zip(gold_sets, pred_sets):
        g, p = set(g), set(p)
        union = g | p
        scores += (len(g & p) / len(union)) if union else 1.0
        n += 1
    return scores / n if n else 1.0
