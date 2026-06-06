import numpy as np
from ml.eval.metrics import ndcg_at_k, recall_at_k


def test_ndcg_perfect_ranking():
    # scores already rank the rel=4 item first
    scores = np.array([3.0, 2.0, 1.0])
    rels   = np.array([4,   2,   0])
    assert abs(ndcg_at_k(scores, rels, 10) - 1.0) < 1e-9


def test_ndcg_single_relevant_at_rank_2():
    # index1 (score 2) ranks first with rel 0; index0 (score 1) ranks 2nd with rel 4
    scores = np.array([1.0, 2.0])
    rels   = np.array([4,   0])
    expected = (15.0 / np.log2(3)) / 15.0   # gain(4)=2^4-1=15, discount log2(2+1)
    assert abs(ndcg_at_k(scores, rels, 10) - expected) < 1e-9


def test_ndcg_zero_when_no_relevant():
    assert ndcg_at_k(np.array([1.0, 2.0]), np.array([0, 0]), 10) == 0.0


def test_recall_half():
    scores = np.array([3.0, 2.0, 1.0, 0.0])
    rels   = np.array([1,   0,   1,   0])   # 2 relevant; top-2 contains 1
    assert recall_at_k(scores, rels, 2) == 0.5


def test_recall_all_found():
    scores = np.array([3.0, 2.0, 1.0])
    rels   = np.array([1,   1,   0])
    assert recall_at_k(scores, rels, 10) == 1.0
