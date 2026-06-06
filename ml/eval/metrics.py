"""Ranking metrics with explicit, stated definitions.

Weighted NDCG@k: gain(rel) = 2**rel - 1, discount = log2(rank + 1) (rank 1-indexed).
Recall@k: fraction of relevant items (rel > 0) that appear in the top k.
Ties in `scores` are broken deterministically by original index (stable sort).
"""
import numpy as np


def _topk_order(scores: np.ndarray, k: int) -> np.ndarray:
    # descending by score, stable (ties -> lower index first)
    order = np.argsort(-scores, kind="stable")
    return order[:k]


def ndcg_at_k(scores: np.ndarray, rels: np.ndarray, k: int) -> float:
    scores = np.asarray(scores, dtype=float)
    rels = np.asarray(rels, dtype=float)
    if rels.size == 0 or np.all(rels <= 0):
        return 0.0
    order = _topk_order(scores, k)
    gains = (2.0 ** rels[order]) - 1.0
    discounts = 1.0 / np.log2(np.arange(2, gains.size + 2))
    dcg = float(np.sum(gains * discounts))

    ideal = np.sort(rels)[::-1][:k]
    igains = (2.0 ** ideal) - 1.0
    idiscounts = 1.0 / np.log2(np.arange(2, igains.size + 2))
    idcg = float(np.sum(igains * idiscounts))
    return dcg / idcg if idcg > 0 else 0.0


def recall_at_k(scores: np.ndarray, rels: np.ndarray, k: int) -> float:
    rels = np.asarray(rels, dtype=float)
    total = int(np.sum(rels > 0))
    if total == 0:
        return 0.0
    order = _topk_order(np.asarray(scores, dtype=float), k)
    found = int(np.sum(rels[order] > 0))
    return found / total
