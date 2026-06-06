#!/usr/bin/env python3
"""
Seminar Implementation: Recommender System for MoveUs

Active Models:
  ✓ Baseline  : Random, Popularity+Feasibility
  ✓ Ranker    : LightGBM LambdaMART
  ✓ Hybrid    : Factorization Machines (FM)
  ✓ CF warm   : BPR Matrix Factorization
  ✓ GNN       : LightGCN
  ✓ Neural    : DeepFM

Metrics:
  Primary   : Weighted NDCG@10
  Secondary : Recall@10
  Auxiliary : MRR

Evaluation slices: overall, cold users, warm users, new events

Data: Synthetic 10K users × 3.3K events × 300K interactions over 24 months
"""

import json
import pickle
import time
import warnings
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.naive_bayes import GaussianNB
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

try:
    import xgboost as xgb
    XGB_OK = True
except ImportError:
    XGB_OK = False
    print("[warn] xgboost not found — pip install xgboost")

try:
    import shap
    SHAP_OK = True
except ImportError:
    SHAP_OK = False

try:
    import lightgbm as lgb
    LGB_OK = True
except ImportError:
    LGB_OK = False
    print("[warn] lightgbm not found — pip install lightgbm")

try:
    from surprise import SVD as _SVD, KNNBasic as _KNN
    from surprise import Dataset as _DS, Reader as _Reader
    SURPRISE_OK = True
except ImportError:
    SURPRISE_OK = False
    print("[warn] scikit-surprise not found — pip install scikit-surprise")

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from torch.utils.data import DataLoader, TensorDataset
    TORCH_OK = True
    DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
except ImportError:
    TORCH_OK = False
    print("[warn] torch not found — pip install torch")

try:
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    MPL_OK = True
except ImportError:
    MPL_OK = False

DATA_DIR    = Path(__file__).parent / "data"
MODELS_DIR  = Path(__file__).parent / "models"
RESULTS_DIR = Path(__file__).parent / "results"
MODELS_DIR.mkdir(exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)

SEED    = 42
K_EVAL  = 10
N_NEG   = 4        # BPR negatives per positive (neural training)
EMB_DIM = 64

USER_TOWER_DIM  = 97   # v3: 97-dim (added pref_act_q×31 + avail_day×7 + avail_time×4)
EVENT_TOWER_DIM = 57

# Side slices for NCF
# user_vecs[:, 0:15]  prefs(13) + demo(2) — first 15 dims unchanged
# event_vecs[:, 36:57] sportEFA(8)+cluster(8)+temporal(2)+group(3) = 21 dims
USER_SIDE_SLICE  = slice(0, 15)
EVENT_SIDE_SLICE = slice(36, 57)
NCF_SIDE_DIM     = 15 + 21   # 36

np.random.seed(SEED)


# ══════════════════════════════════════════════════════════════════════════════
# Data loading
# ══════════════════════════════════════════════════════════════════════════════

def load_data() -> dict:
    d: dict = {}

    for split in ("train", "test", "cold"):
        d[f"X_{split}"]       = np.load(DATA_DIR / f"X_{split}.npy")
        d[f"y_{split}"]       = np.load(DATA_DIR / f"y_{split}.npy")        # ratings 0-4
        d[f"{split}_uids"]    = np.load(DATA_DIR / f"{split}_user_ids.npy").astype(int)
        d[f"{split}_eids"]    = np.load(DATA_DIR / f"{split}_event_ids.npy").astype(int)
        d[f"{split}_ratings"] = np.load(DATA_DIR / f"{split}_ratings.npy").astype(int)

    d["user_vecs"]  = np.load(DATA_DIR / "user_vectors.npy")
    d["event_vecs"] = np.load(DATA_DIR / "event_vectors.npy")

    d["train_df"]  = pd.read_csv(DATA_DIR / "train.csv",             parse_dates=["timestamp"])
    d["test_df"]   = pd.read_csv(DATA_DIR / "test.csv",              parse_dates=["timestamp"])
    d["cold_df"]   = pd.read_csv(DATA_DIR / "cold_start_users.csv",  parse_dates=["timestamp"])
    d["train_imp_df"] = pd.read_csv(DATA_DIR / "train_implicit.csv", parse_dates=["timestamp"])
    d["events_df"] = pd.read_csv(DATA_DIR / "events.csv")

    d["train_imp_uids"]    = np.load(DATA_DIR / "train_implicit_uids.npy").astype(int)
    d["train_imp_eids"]    = np.load(DATA_DIR / "train_implicit_eids.npy").astype(int)
    d["train_imp_weights"] = np.load(DATA_DIR / "train_implicit_weights.npy").astype(float)

    # All-signal-type arrays for model training (X_train has all signal types)
    d["train_weights"]         = np.load(DATA_DIR / "train_sample_weights.npy").astype(float)
    d["train_global_ts_order"] = np.load(DATA_DIR / "train_global_ts_order.npy").astype(int)
    d["train_all_uids"]        = np.load(DATA_DIR / "train_all_user_ids.npy").astype(int)

    with open(DATA_DIR / "feature_names.json") as fh:
        d["feature_names"] = json.load(fh)["pairwise"]

    # FeatureMatrices was pickled from features.__main__; register it here so pickle can find it
    import sys as _sys, importlib as _il
    _sys.path.insert(0, str(Path(__file__).parent))
    _feat = _il.import_module("features")
    import __main__ as _main
    _main.FeatureMatrices = _feat.FeatureMatrices
    with open(DATA_DIR / "feature_matrices.pkl", "rb") as fh:
        d["fm"] = pickle.load(fh)

    d["event_popularity"] = d["train_df"]["event_id"].value_counts().to_dict()
    d["user_n_train"]     = d["train_df"].groupby("user_id").size().to_dict()
    d["n_users"]  = len(d["user_vecs"])
    d["n_events"] = len(d["event_vecs"])

    # All event IDs for negative sampling
    d["all_event_ids"] = np.arange(d["n_events"])

    # Map: user_id → set of event_ids they interacted with (train only)
    seen: dict[int, set] = defaultdict(set)
    for row in d["train_df"].itertuples(index=False):
        seen[int(row.user_id)].add(int(row.event_id))
    d["seen_train"] = dict(seen)

    return d


# ══════════════════════════════════════════════════════════════════════════════
# Evaluation framework — LOO@99 (primary) + full AUC (secondary)
# ══════════════════════════════════════════════════════════════════════════════

def bootstrap_ci(
    values: list, n_boot: int = 1000, alpha: float = 0.95
) -> tuple[float, float]:
    """Bootstrap 95% CI by resampling users with replacement."""
    rng  = np.random.default_rng(SEED + 1)
    arr  = np.array(values)
    means = np.array([rng.choice(arr, len(arr), replace=True).mean()
                      for _ in range(n_boot)])
    lo = float(np.percentile(means, (1 - alpha) / 2 * 100))
    hi = float(np.percentile(means, (1 + alpha) / 2 * 100))
    return round(lo, 4), round(hi, 4)


def evaluate_loo(
    test_df: pd.DataFrame,
    seen_train: dict,
    all_event_ids: np.ndarray,
    score_fn,                  # callable(uids: ndarray, eids: ndarray) -> scores: ndarray
    n_neg: int = 99,
    k: int = K_EVAL,
    tag: str = "",
) -> dict:
    """
    Leave-One-Out evaluation with random negative sampling (standard RecSys protocol).
    For each user in test_df, the ONE interaction is the positive; n_neg random
    unseen events are sampled as negatives; rank the positive among 1+n_neg items.
    """
    rng_loo = np.random.default_rng(SEED)
    ndcgs, hits, mrrs = [], [], []

    # One positive per user (last interaction, guaranteed by generate_data LOO split)
    for row in test_df.itertuples(index=False):
        uid     = int(row.user_id)
        pos_eid = int(row.event_id)

        exclude    = seen_train.get(uid, set()) | {pos_eid}
        candidates = all_event_ids[~np.isin(all_event_ids, list(exclude))]

        if len(candidates) >= n_neg:
            negs = rng_loo.choice(candidates, n_neg, replace=False)
        else:
            negs = candidates

        items = np.concatenate([[pos_eid], negs])
        u_arr = np.full(len(items), uid, dtype=int)
        scores = score_fn(u_arr, items)

        # Rank of positive (index 0) among all items — pessimistic tie-breaking
        rank = int(np.sum(scores[1:] >= scores[0]) + 1)

        ndcgs.append(1.0 / np.log2(rank + 1) if rank <= k else 0.0)
        hits.append(1.0 if rank <= k else 0.0)
        mrrs.append(1.0 / rank)

    ci = bootstrap_ci(ndcgs)
    return {
        "NDCG@10":     round(float(np.mean(ndcgs)), 4),
        "NDCG@10_CI":  ci,
        "HitRate@10":  round(float(np.mean(hits)),  4),
        "MRR":         round(float(np.mean(mrrs)),  4),
        "n_users":     len(ndcgs),
        "tag":         tag,
    }


def evaluate_full(
    uids: np.ndarray, ratings: np.ndarray,
    scores: np.ndarray, tag: str = ""
) -> dict:
    """Full-set AUC-ROC using binary label (rating>=3=positive)."""
    labels = (ratings >= 3).astype(int)
    auc = roc_auc_score(labels, scores) if len(np.unique(labels)) == 2 else 0.5
    return {"AUC-ROC": round(float(auc), 4), "tag": tag}


def ndcg_vs_k(
    test_df: pd.DataFrame,
    seen_train: dict,
    all_event_ids: np.ndarray,
    score_fn,
    ks: range,
    n_neg: int = 99,
) -> list[float]:
    """NDCG@k for each k, reusing same negative samples (fixed seed)."""
    rng_loo = np.random.default_rng(SEED)
    all_scores_by_user: list[tuple[int, np.ndarray]] = []

    for row in test_df.itertuples(index=False):
        uid     = int(row.user_id)
        pos_eid = int(row.event_id)
        exclude    = seen_train.get(uid, set()) | {pos_eid}
        candidates = all_event_ids[~np.isin(all_event_ids, list(exclude))]
        if len(candidates) >= n_neg:
            negs = rng_loo.choice(candidates, n_neg, replace=False)
        else:
            negs = candidates
        items = np.concatenate([[pos_eid], negs])
        u_arr = np.full(len(items), uid, dtype=int)
        scores = score_fn(u_arr, items)
        rank = int(np.sum(scores[1:] >= scores[0]) + 1)
        all_scores_by_user.append(rank)

    ranks = np.array(all_scores_by_user)
    out = []
    for k in ks:
        ndcg_k = np.mean([1.0 / np.log2(r + 1) if r <= k else 0.0 for r in ranks])
        out.append(round(float(ndcg_k), 4))
    return out


# ══════════════════════════════════════════════════════════════════════════════
# Additional metrics — Precision@K, Novelty, Coverage
# ══════════════════════════════════════════════════════════════════════════════

def precision_at_k(
    test_df: pd.DataFrame,
    seen_train: dict,
    all_event_ids: np.ndarray,
    score_fn,
    n_neg: int = 99,
    k: int = K_EVAL,
) -> float:
    """Precision@K in the LOO@99 protocol (=HR@K / K for one relevant item per user)."""
    rng_loo = np.random.default_rng(SEED)
    hits = []
    for row in test_df.itertuples(index=False):
        uid     = int(row.user_id)
        pos_eid = int(row.event_id)
        exclude = seen_train.get(uid, set()) | {pos_eid}
        cands   = all_event_ids[~np.isin(all_event_ids, list(exclude))]
        negs    = rng_loo.choice(cands, min(n_neg, len(cands)), replace=False)
        items   = np.concatenate([[pos_eid], negs])
        u_arr   = np.full(len(items), uid, dtype=int)
        scores  = score_fn(u_arr, items)
        rank    = int(np.sum(scores[1:] >= scores[0]) + 1)
        hits.append(1.0 if rank <= k else 0.0)
    return round(float(np.mean(hits)) / k, 4)


def novelty(
    test_df: pd.DataFrame,
    seen_train: dict,
    all_event_ids: np.ndarray,
    score_fn,
    pop_map: dict,
    n_total_interactions: int,
    n_neg: int = 99,
    k: int = K_EVAL,
) -> float:
    """
    Mean self-information of top-K recommendations.
    Novelty = -Σ log2(pop(e) / n_total) averaged over users and top-K items.
    Higher = recommending less popular (more surprising) items.
    """
    rng_loo = np.random.default_rng(SEED)
    user_novelties = []
    for row in test_df.itertuples(index=False):
        uid   = int(row.user_id)
        exclude = seen_train.get(uid, set())
        cands   = all_event_ids[~np.isin(all_event_ids, list(exclude))]
        sample  = rng_loo.choice(cands, min(n_neg + 1, len(cands)), replace=False)
        u_arr   = np.full(len(sample), uid, dtype=int)
        scores  = score_fn(u_arr, sample)
        top_k   = sample[np.argsort(-scores)[:k]]
        nov_k   = []
        for eid in top_k:
            p = pop_map.get(int(eid), 1) / max(n_total_interactions, 1)
            nov_k.append(-np.log2(p + 1e-12))
        user_novelties.append(float(np.mean(nov_k)))
    return round(float(np.mean(user_novelties)), 4)


def coverage(
    test_df: pd.DataFrame,
    seen_train: dict,
    all_event_ids: np.ndarray,
    score_fn,
    n_neg: int = 99,
    k: int = K_EVAL,
) -> float:
    """
    Fraction of all events that appear in at least one user's top-K list.
    Higher = the system recommends a broader slice of the catalogue.
    """
    rng_loo = np.random.default_rng(SEED)
    recommended: set = set()
    for row in test_df.itertuples(index=False):
        uid     = int(row.user_id)
        exclude = seen_train.get(uid, set())
        cands   = all_event_ids[~np.isin(all_event_ids, list(exclude))]
        sample  = rng_loo.choice(cands, min(n_neg + 1, len(cands)), replace=False)
        u_arr   = np.full(len(sample), uid, dtype=int)
        scores  = score_fn(u_arr, sample)
        top_k   = sample[np.argsort(-scores)[:k]]
        recommended.update(top_k.tolist())
    return round(len(recommended) / max(len(all_event_ids), 1), 4)


# ══════════════════════════════════════════════════════════════════════════════
# Ordinal scoring helpers
# ══════════════════════════════════════════════════════════════════════════════

def expected_rating(model, X: np.ndarray) -> np.ndarray:
    """Score = Σ r·P(r) for r in 0..4 — ordinal expected value."""
    proba   = model.predict_proba(X)
    classes = model.classes_.astype(float)
    return proba @ classes


# ══════════════════════════════════════════════════════════════════════════════
# Tier 0 — Baselines
# ══════════════════════════════════════════════════════════════════════════════

def random_scores(n: int, seed: int = SEED) -> np.ndarray:
    return np.random.default_rng(seed).random(n)


def popularity_scores(event_ids: np.ndarray, pop_map: dict) -> np.ndarray:
    return np.array([float(pop_map.get(e, 0)) for e in event_ids])


# ══════════════════════════════════════════════════════════════════════════════
# Tier 1 — Ordinal ML (cold-start capable)
# ══════════════════════════════════════════════════════════════════════════════

def train_gnb(X_train: np.ndarray, y_train: np.ndarray) -> GaussianNB:
    model = GaussianNB(var_smoothing=1e-9)
    model.fit(X_train, y_train)   # y = rating 0-4
    return model


def train_lr(X_train: np.ndarray, y_train: np.ndarray,
             sample_weight=None) -> LogisticRegression:
    model = LogisticRegression(C=1.0, solver="lbfgs", max_iter=2000,
                               random_state=SEED, multi_class="multinomial")
    model.fit(X_train, y_train, sample_weight=sample_weight)
    return model


# ══════════════════════════════════════════════════════════════════════════════
# Tier 2 — Classical ML
# ══════════════════════════════════════════════════════════════════════════════

def train_rf(X_train: np.ndarray, y_train: np.ndarray) -> RandomForestClassifier:
    model = RandomForestClassifier(n_estimators=200, max_depth=12,
                                   random_state=SEED, n_jobs=-1)
    model.fit(X_train, y_train)
    return model


def train_xgb_ltr(
    X_train: np.ndarray, y_train: np.ndarray,
    train_uids: np.ndarray,
    X_val: np.ndarray,  y_val: np.ndarray,
    val_uids: np.ndarray,
):
    """XGBoost LambdaMART — directly optimises NDCG (rank:ndcg objective)."""
    if not XGB_OK:
        return None

    # Sort by user so queries are contiguous
    sort_tr  = np.argsort(train_uids, kind="stable")
    X_s      = X_train[sort_tr]
    y_s      = y_train[sort_tr]
    uid_s    = train_uids[sort_tr]
    # Filter users with < 2 items (XGBoost LTR requirement)
    cnts  = np.bincount(uid_s, minlength=uid_s.max() + 1)
    valid = np.isin(uid_s, np.where(cnts >= 2)[0])
    X_s   = X_s[valid]; y_s = y_s[valid]; uid_s = uid_s[valid]
    groups_tr = [int(v) for v in np.bincount(uid_s) if v > 0]

    sort_vl = np.argsort(val_uids, kind="stable")
    X_vs    = X_val[sort_vl]; y_vs = y_val[sort_vl]; uid_vs = val_uids[sort_vl]
    cnts_v  = np.bincount(uid_vs, minlength=uid_vs.max() + 1)
    valid_v = np.isin(uid_vs, np.where(cnts_v >= 2)[0])
    X_vs    = X_vs[valid_v]; y_vs = y_vs[valid_v]; uid_vs = uid_vs[valid_v]
    groups_vl = [int(v) for v in np.bincount(uid_vs) if v > 0]

    dtrain = xgb.DMatrix(X_s,  label=y_s.astype(float));  dtrain.set_group(groups_tr)
    dval   = xgb.DMatrix(X_vs, label=y_vs.astype(float)); dval.set_group(groups_vl)

    params = {
        "objective":      "rank:ndcg",
        "eval_metric":    "ndcg@10",
        "eta":            0.05,
        "max_depth":      6,
        "subsample":      0.8,
        "colsample_bytree": 0.8,
        "seed":           SEED,
        "verbosity":      0,
    }
    model = xgb.train(
        params, dtrain,
        num_boost_round=500,
        evals=[(dval, "val")],
        early_stopping_rounds=30,
        verbose_eval=False,
    )
    return model


def xgb_ltr_score(model, X: np.ndarray) -> np.ndarray:
    return model.predict(xgb.DMatrix(X))


# ── LightGBM LTR ──────────────────────────────────────────────────────────────

def train_lgb_ltr(
    X_train: np.ndarray, y_train: np.ndarray,
    train_uids: np.ndarray,
    X_val: np.ndarray,  y_val: np.ndarray,
    val_uids: np.ndarray,
    sample_weight=None,
):
    """LightGBM LambdaRank — faster XGBoost alternative, direct NDCG optimisation."""
    if not LGB_OK:
        return None

    sort_tr  = np.argsort(train_uids, kind="stable")
    X_s      = X_train[sort_tr]; y_s = y_train[sort_tr]; uid_s = train_uids[sort_tr]
    cnts     = np.bincount(uid_s, minlength=uid_s.max() + 1)
    valid    = np.isin(uid_s, np.where(cnts >= 2)[0])
    X_s      = X_s[valid]; y_s = y_s[valid]; uid_s = uid_s[valid]
    w_s      = sample_weight[sort_tr][valid] if sample_weight is not None else None
    groups_tr = list(np.bincount(uid_s)[np.bincount(uid_s) > 0])

    sort_vl  = np.argsort(val_uids, kind="stable")
    X_vs     = X_val[sort_vl]; y_vs = y_val[sort_vl]; uid_vs = val_uids[sort_vl]
    cnts_v   = np.bincount(uid_vs, minlength=uid_vs.max() + 1)
    valid_v  = np.isin(uid_vs, np.where(cnts_v >= 2)[0])
    X_vs     = X_vs[valid_v]; y_vs = y_vs[valid_v]; uid_vs = uid_vs[valid_v]
    groups_vl = list(np.bincount(uid_vs)[np.bincount(uid_vs) > 0])

    if not groups_tr or not groups_vl:
        return None

    ds_tr = lgb.Dataset(X_s, label=y_s.astype(float),
                        group=groups_tr, weight=w_s, free_raw_data=False)
    ds_vl = lgb.Dataset(X_vs, label=y_vs.astype(float),
                        group=groups_vl, reference=ds_tr, free_raw_data=False)

    params = {
        "objective":       "lambdarank",
        "metric":          "ndcg",
        "ndcg_at":         [10],
        "learning_rate":   0.05,
        "num_leaves":      63,
        "max_depth":       -1,
        "min_data_in_leaf": 20,
        "feature_fraction": 0.8,
        "bagging_fraction": 0.8,
        "bagging_freq":    5,
        "verbose":         -1,
        "seed":            SEED,
    }
    callbacks = [lgb.early_stopping(30, verbose=False), lgb.log_evaluation(-1)]
    model = lgb.train(
        params, ds_tr,
        num_boost_round=500,
        valid_sets=[ds_vl],
        callbacks=callbacks,
    )
    return model


def lgb_ltr_score(model, X: np.ndarray) -> np.ndarray:
    return model.predict(X)


# ── EASE (Embarrassingly Shallow Autoencoder for Recommendations) ─────────────

class EASE:
    """
    Closed-form linear collaborative filter (Steck, RecSys 2019).
    W = I - P · diag(1/diag(P))  where P = (XᵀX + λI)⁻¹
    No neural network or iterative training required.
    """

    def __init__(self, lam: float = 500.0):
        self.lam = lam
        self._W: np.ndarray | None = None
        self._n_items: int = 0

    def fit(self, n_users: int, n_items: int,
            uids: np.ndarray, eids: np.ndarray,
            weights: np.ndarray | None = None) -> "EASE":
        self._n_items = n_items
        # Build sparse user-item matrix
        X = np.zeros((n_users, n_items), dtype=float)
        w = weights if weights is not None else np.ones(len(uids), float)
        for u, e, wt in zip(uids, eids, w):
            X[int(u), int(e)] += float(wt)

        G    = X.T @ X
        diag = np.arange(n_items)
        G[diag, diag] += self.lam
        P    = np.linalg.inv(G)
        W    = np.eye(n_items) - P * (1.0 / np.diag(P))
        W[diag, diag] = 0.0      # no self-loops
        self._W = W
        self._X = X
        return self

    def predict(self, uids: np.ndarray, eids: np.ndarray) -> np.ndarray:
        scores = (self._X @ self._W)        # (n_users, n_items)
        return scores[uids, eids]


# ── SVD & k-NN CF ─────────────────────────────────────────────────────────────

def _to_surprise(df: pd.DataFrame):
    rated = df[df["signal_type"] == "join_rated"]
    reader  = _Reader(rating_scale=(0, 4))
    data    = _DS.load_from_df(rated[["user_id", "event_id", "rating"]], reader)
    return data.build_full_trainset()


def train_svd(trainset):
    model = _SVD(n_factors=50, n_epochs=30, lr_all=0.005, reg_all=0.02, random_state=SEED)
    model.fit(trainset)
    return model


def train_knn(trainset):
    model = _KNN(k=40, sim_options={"name": "pearson_baseline", "user_based": True, "min_support": 3})
    model.fit(trainset)
    return model


def surprise_predict(model, uids: np.ndarray, eids: np.ndarray) -> np.ndarray:
    return np.array([model.predict(int(u), int(e)).est for u, e in zip(uids, eids)])


def hybrid_scores(svd_sc: np.ndarray, gnb_sc: np.ndarray,
                  uids: np.ndarray, user_n_train: dict) -> np.ndarray:
    alphas = np.array([min(1.0, user_n_train.get(int(u), 0) / 20.0) for u in uids])
    return alphas * svd_sc + (1.0 - alphas) * gnb_sc


# ══════════════════════════════════════════════════════════════════════════════
# Tier 2b — BPR-MF (standalone implicit model — Cold Start report Model 2)
# ══════════════════════════════════════════════════════════════════════════════

if TORCH_OK:
    class BPRMF(nn.Module):
        def __init__(self, n_users: int, n_events: int, emb_dim: int = EMB_DIM):
            super().__init__()
            self.user_emb  = nn.Embedding(n_users,  emb_dim)
            self.event_emb = nn.Embedding(n_events, emb_dim)
            nn.init.normal_(self.user_emb.weight,  std=0.01)
            nn.init.normal_(self.event_emb.weight, std=0.01)

        def forward(self, u_ids, e_ids):
            return (self.user_emb(u_ids) * self.event_emb(e_ids)).sum(dim=-1)


def train_bpr_mf(
    model: "BPRMF",
    imp_uids: np.ndarray,
    imp_eids: np.ndarray,
    imp_weights: np.ndarray,
    n_events: int,
    n_epochs: int = 20,
    lr: float = 0.01,
    batch_size: int = 2048,
) -> list[float]:
    """
    Train BPR-MF on implicit signals.
    Positive examples: join_rated (weight=3/2) + join_no_rate (weight=1).
    Weighted softplus BPR loss: weight * softplus(neg - pos).
    """
    pos_mask  = imp_weights > 0
    pos_uids  = torch.LongTensor(imp_uids[pos_mask])
    pos_eids  = torch.LongTensor(imp_eids[pos_mask])
    pos_wts   = torch.FloatTensor(imp_weights[pos_mask])

    opt   = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-5)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=n_epochs)
    model.to(DEVICE); model.train()

    n_pos  = len(pos_uids)
    rng_np = np.random.default_rng(SEED)
    curves: list[float] = []

    for epoch in range(n_epochs):
        perm = torch.randperm(n_pos)
        pu = pos_uids[perm]; pe = pos_eids[perm]; pw = pos_wts[perm]
        epoch_loss = 0.0; n_batches = 0

        for i in range(0, n_pos, batch_size):
            u_b  = pu[i:i+batch_size].to(DEVICE)
            ep_b = pe[i:i+batch_size].to(DEVICE)
            w_b  = pw[i:i+batch_size].to(DEVICE)
            bsz  = len(u_b)
            en_b = torch.LongTensor(rng_np.integers(0, n_events, bsz)).to(DEVICE)

            pos_sc = model(u_b, ep_b)
            neg_sc = model(u_b, en_b)
            loss   = (w_b * F.softplus(neg_sc - pos_sc)).mean()

            opt.zero_grad(); loss.backward(); opt.step()
            epoch_loss += loss.item(); n_batches += 1

        sched.step()
        avg = epoch_loss / max(n_batches, 1)
        curves.append(avg)
        if (epoch + 1) % 5 == 0:
            print(f"    BPR-MF epoch {epoch+1:3d}/{n_epochs}  loss={avg:.4f}")

    return curves


@torch.no_grad()
def bpr_mf_predict(
    model: "BPRMF", uids: np.ndarray, eids: np.ndarray,
    batch_size: int = 4096,
) -> np.ndarray:
    model.eval(); model.to(DEVICE)
    out = []
    for i in range(0, len(uids), batch_size):
        u_b = torch.LongTensor(uids[i:i+batch_size]).to(DEVICE)
        e_b = torch.LongTensor(eids[i:i+batch_size]).to(DEVICE)
        out.append(model(u_b, e_b).cpu().numpy())
    return np.concatenate(out)


# ══════════════════════════════════════════════════════════════════════════════
# Tier 3 — Neural models
# ══════════════════════════════════════════════════════════════════════════════

if TORCH_OK:
    class NCF(nn.Module):
        def __init__(self, n_users: int, n_events: int,
                     emb_dim: int = EMB_DIM, side_dim: int = NCF_SIDE_DIM):
            super().__init__()
            self.gmf_u = nn.Embedding(n_users,  emb_dim)
            self.gmf_e = nn.Embedding(n_events, emb_dim)
            self.mlp_u = nn.Embedding(n_users,  emb_dim)
            self.mlp_e = nn.Embedding(n_events, emb_dim)
            self.side_proj = nn.Linear(side_dim, emb_dim)
            self.mlp = nn.Sequential(
                nn.Linear(3*emb_dim, 128), nn.ReLU(), nn.Dropout(0.2),
                nn.Linear(128, 64),        nn.ReLU(), nn.Dropout(0.2),
            )
            self.out = nn.Linear(emb_dim + 64, 1)
            for m in self.modules():
                if isinstance(m, nn.Embedding):
                    nn.init.normal_(m.weight, std=0.01)
                elif isinstance(m, nn.Linear):
                    nn.init.xavier_uniform_(m.weight)

        def forward(self, u_ids, e_ids, side):
            gmf     = self.gmf_u(u_ids) * self.gmf_e(e_ids)
            side_e  = self.side_proj(side)
            mlp_out = self.mlp(torch.cat([self.mlp_u(u_ids), self.mlp_e(e_ids), side_e], dim=-1))
            return torch.sigmoid(self.out(torch.cat([gmf, mlp_out], dim=-1))).squeeze(-1)

    class _Tower(nn.Module):
        def __init__(self, in_dim: int):
            super().__init__()
            self.net = nn.Sequential(
                nn.Linear(in_dim, 128), nn.LayerNorm(128), nn.ReLU(),
                nn.Linear(128, 64),     nn.LayerNorm(64),  nn.ReLU(),
                nn.Linear(64, EMB_DIM),
            )
        def forward(self, x):
            return F.normalize(self.net(x), dim=-1)

    class TwoTower(nn.Module):
        def __init__(self):
            super().__init__()
            self.user_tower  = _Tower(USER_TOWER_DIM)
            self.event_tower = _Tower(EVENT_TOWER_DIM)
        def forward(self, u_feats, e_feats):
            return (self.user_tower(u_feats) * self.event_tower(e_feats)).sum(dim=-1)


def train_ncf(
    model: "NCF", train_df: pd.DataFrame,
    user_vecs: np.ndarray, event_vecs: np.ndarray,
    n_events: int, n_epochs: int = 25, lr: float = 5e-4, batch_size: int = 512,
) -> list[float]:
    rated = train_df[train_df["signal_type"] == "join_rated"]
    uids_obs   = rated["user_id"].values.astype(int)
    eids_obs   = rated["event_id"].values.astype(int)
    # Use actual rating normalised to [0,1] as target (soft supervision)
    labels_obs = (rated["rating"].values / 4.0).astype(np.float32)
    wts_obs    = rated["signal_weight"].values.astype(np.float32)

    pos_mask = labels_obs >= 0.5
    n_pos    = int(pos_mask.sum())
    rng_np   = np.random.default_rng(SEED)
    extra_u  = uids_obs[pos_mask][rng_np.integers(0, n_pos, n_pos * N_NEG)]
    extra_e  = rng_np.integers(0, n_events, n_pos * N_NEG).astype(int)
    extra_l  = np.zeros(n_pos * N_NEG, np.float32)
    extra_w  = np.ones(n_pos * N_NEG, np.float32)

    all_u = torch.LongTensor(np.concatenate([uids_obs, extra_u]))
    all_e = torch.LongTensor(np.concatenate([eids_obs, extra_e]))
    all_l = torch.FloatTensor(np.concatenate([labels_obs, extra_l]))
    all_w = torch.FloatTensor(np.concatenate([wts_obs,    extra_w]))

    u_side = torch.FloatTensor(user_vecs[:,  USER_SIDE_SLICE])
    e_side = torch.FloatTensor(event_vecs[:, EVENT_SIDE_SLICE])

    opt   = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-5)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=n_epochs)
    model.to(DEVICE); model.train()

    curves: list[float] = []
    n_total = len(all_u)

    for epoch in range(n_epochs):
        perm = torch.randperm(n_total)
        au = all_u[perm]; ae = all_e[perm]; al = all_l[perm]; aw = all_w[perm]
        epoch_loss = 0.0; nb = 0

        for i in range(0, n_total, batch_size):
            u_b = au[i:i+batch_size].to(DEVICE)
            e_b = ae[i:i+batch_size].to(DEVICE)
            l_b = al[i:i+batch_size].to(DEVICE)
            w_b = aw[i:i+batch_size].to(DEVICE)
            side = torch.cat([u_side[u_b.cpu()], e_side[e_b.cpu()]], dim=-1).to(DEVICE)
            sc   = model(u_b, e_b, side)
            loss = (w_b * F.binary_cross_entropy(sc, l_b, reduction="none")).mean()
            opt.zero_grad(); loss.backward(); opt.step()
            epoch_loss += loss.item(); nb += 1

        sched.step()
        avg = epoch_loss / max(nb, 1)
        curves.append(avg)
        if (epoch + 1) % 5 == 0:
            print(f"    NCF epoch {epoch+1:3d}/{n_epochs}  loss={avg:.4f}")

    return curves


@torch.no_grad()
def ncf_predict(model: "NCF", uids, eids, user_vecs, event_vecs, bs=2048):
    model.eval(); model.to(DEVICE)
    u_side = torch.FloatTensor(user_vecs[:,  USER_SIDE_SLICE])
    e_side = torch.FloatTensor(event_vecs[:, EVENT_SIDE_SLICE])
    out = []
    for i in range(0, len(uids), bs):
        u_b = torch.LongTensor(uids[i:i+bs]).to(DEVICE)
        e_b = torch.LongTensor(eids[i:i+bs]).to(DEVICE)
        side = torch.cat([u_side[u_b.cpu()], e_side[e_b.cpu()]], dim=-1).to(DEVICE)
        out.append(model(u_b, e_b, side).cpu().numpy())
    return np.concatenate(out)


def train_two_tower(
    model: "TwoTower", train_df: pd.DataFrame,
    user_vecs: np.ndarray, event_vecs: np.ndarray,
    imp_uids: np.ndarray, imp_eids: np.ndarray, imp_weights: np.ndarray,
    n_events: int, n_epochs: int = 25, lr: float = 1e-3, batch_size: int = 1024,
) -> list[float]:
    """
    Weighted BPR training on ALL implicit signals (join_rated + join_no_rate).
    Signal weight controls how strongly each pair is treated as positive.
    """
    pos_mask = imp_weights > 0
    pos_uids  = torch.LongTensor(imp_uids[pos_mask])
    pos_eids  = torch.LongTensor(imp_eids[pos_mask])
    pos_wts   = torch.FloatTensor(imp_weights[pos_mask])

    uv = torch.FloatTensor(user_vecs)
    ev = torch.FloatTensor(event_vecs)

    opt   = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-5)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=n_epochs)
    model.to(DEVICE); model.train()

    n_pos  = len(pos_uids)
    rng_np = np.random.default_rng(SEED)
    curves: list[float] = []

    for epoch in range(n_epochs):
        perm = torch.randperm(n_pos)
        pu = pos_uids[perm]; pe = pos_eids[perm]; pw = pos_wts[perm]
        epoch_loss = 0.0; nb = 0

        for i in range(0, n_pos, batch_size):
            u_b  = pu[i:i+batch_size]; ep_b = pe[i:i+batch_size]
            w_b  = pw[i:i+batch_size].to(DEVICE)
            bsz  = len(u_b)
            en_b = torch.randint(0, n_events, (bsz, N_NEG))

            uv_b  = uv[u_b].to(DEVICE)
            epv_b = ev[ep_b].to(DEVICE)
            pos_sc = model(uv_b, epv_b)

            neg_sc = torch.stack([model(uv_b, ev[en_b[:, k]].to(DEVICE))
                                   for k in range(N_NEG)], dim=1).mean(dim=1)

            loss = (w_b * F.softplus(neg_sc - pos_sc)).mean()
            opt.zero_grad(); loss.backward(); opt.step()
            epoch_loss += loss.item(); nb += 1

        sched.step()
        avg = epoch_loss / max(nb, 1)
        curves.append(avg)
        if (epoch + 1) % 5 == 0:
            print(f"    TwoTower epoch {epoch+1:3d}/{n_epochs}  loss={avg:.4f}")

    return curves


@torch.no_grad()
def tt_predict(model: "TwoTower", uids, eids, user_vecs, event_vecs, bs=2048):
    model.eval(); model.to(DEVICE)
    uv = torch.FloatTensor(user_vecs)
    ev = torch.FloatTensor(event_vecs)
    out = []
    for i in range(0, len(uids), bs):
        u_b = torch.LongTensor(uids[i:i+bs])
        e_b = torch.LongTensor(eids[i:i+bs])
        out.append(model(uv[u_b].to(DEVICE), ev[e_b].to(DEVICE)).cpu().numpy())
    return np.concatenate(out)


# ══════════════════════════════════════════════════════════════════════════════
# Accumulation curve experiment
# ══════════════════════════════════════════════════════════════════════════════

def run_accumulation_curve(d: dict) -> pd.DataFrame:
    """
    Train fast models on 5/10/25/50/100% of temporal training data.
    Evaluate each with LOO@99. Shows which models need more data to converge.
    Two-Tower is trained at 3 fractions (10/50/100) with 10 epochs to limit runtime.
    """
    fracs  = [0.05, 0.10, 0.25, 0.50, 1.00]
    tt_fracs = {0.10, 0.50, 1.00}
    results: list[dict] = []

    # Sort training data by global timestamp (not per-user timestamp) for
    # proper temporal slicing — reveals how performance grows with real time,
    # not just with user interaction count.
    global_ts_order = d["train_global_ts_order"]
    train_df_ts     = d["train_df"].iloc[global_ts_order].reset_index(drop=True)
    X_full          = d["X_train"][global_ts_order]
    y_full          = d["y_train"][global_ts_order]
    w_full          = d["train_weights"][global_ts_order]
    uids_full       = d["train_all_uids"][global_ts_order]

    imp_uids_full    = d["train_imp_uids"]
    imp_eids_full    = d["train_imp_eids"]
    imp_wts_full     = d["train_imp_weights"]

    all_eid  = d["all_event_ids"]
    seen_tr  = d["seen_train"]
    test_df  = d["test_df"]
    n_ev     = d["n_events"]
    uv       = d["user_vecs"]
    ev       = d["event_vecs"]
    fm       = d["fm"]

    print("\n[Accumulation curve experiment]")

    for frac in fracs:
        n_use = max(int(len(X_full) * frac), 20)
        # Temporal slice: first n_use rows in global timestamp order
        sub_train = train_df_ts.iloc[:n_use].reset_index(drop=True)
        sub_X     = X_full[:n_use]
        sub_y     = y_full[:n_use]
        sub_w     = w_full[:n_use]
        sub_uids  = uids_full[:n_use]

        n_imp_use = max(int(len(imp_uids_full) * frac), 20)
        sub_imp_u = imp_uids_full[:n_imp_use]
        sub_imp_e = imp_eids_full[:n_imp_use]
        sub_imp_w = imp_wts_full[:n_imp_use]

        n_rated_use = int((sub_train["signal_type"] == "join_rated").sum())
        print(f"  frac={frac*100:.0f}%  ({n_use} total rows, {n_rated_use} rated, {n_imp_use} implicit)")

        def _loo(score_fn) -> float:
            r = evaluate_loo(test_df, seen_tr, all_eid, score_fn, tag=f"accum_{frac}")
            return r["NDCG@10"]

        # GNB
        gnb_s = train_gnb(sub_X, sub_y)
        def _gnb_fn(u, e, _m=gnb_s):
            from features import build_pairwise_for_pairs as bpfp
            return expected_rating(_m, bpfp(u, e, fm))
        results.append({"model": "GNB", "fraction": frac, "NDCG@10": _loo(_gnb_fn)})

        # XGBoost-LTR (use all-signal uids so LTR has enough users with ≥2 items)
        if XGB_OK and len(np.unique(sub_uids)) >= 5:
            xgb_s = train_xgb_ltr(sub_X, sub_y, sub_uids, sub_X, sub_y, sub_uids)
            if xgb_s is not None:
                def _xgb_fn(u, e, _m=xgb_s):
                    from features import build_pairwise_for_pairs as bpfp
                    return xgb_ltr_score(_m, bpfp(u, e, fm))
                results.append({"model": "XGBoost-LTR", "fraction": frac, "NDCG@10": _loo(_xgb_fn)})

        # BPR-MF
        if TORCH_OK:
            bpr_s = BPRMF(d["n_users"], n_ev)
            train_bpr_mf(bpr_s, sub_imp_u, sub_imp_e, sub_imp_w, n_ev,
                         n_epochs=10, batch_size=2048)
            def _bpr_fn(u, e, _m=bpr_s): return bpr_mf_predict(_m, u, e)
            results.append({"model": "BPR-MF", "fraction": frac, "NDCG@10": _loo(_bpr_fn)})

        # Two-Tower (only at selected fractions, 10 epochs)
        if TORCH_OK and frac in tt_fracs:
            tt_s = TwoTower()
            train_two_tower(tt_s, sub_train, uv, ev, sub_imp_u, sub_imp_e, sub_imp_w,
                            n_ev, n_epochs=10, batch_size=1024)
            def _tt_fn(u, e, _m=tt_s): return tt_predict(_m, u, e, uv, ev)
            results.append({"model": "Two-Tower", "fraction": frac, "NDCG@10": _loo(_tt_fn)})

    df_out = pd.DataFrame(results)
    df_out.to_csv(RESULTS_DIR / "accumulation_curve.csv", index=False)

    if MPL_OK:
        fig, ax = plt.subplots(figsize=(9, 5))
        for model_name, grp in df_out.groupby("model"):
            ax.plot(grp["fraction"] * 100, grp["NDCG@10"], marker="o", label=model_name)
        ax.set_xlabel("Training data (%)"); ax.set_ylabel("NDCG@10 (LOO@99)")
        ax.set_title("Data accumulation curve — NDCG@10 vs training fraction")
        ax.legend(); ax.grid(alpha=0.3); fig.tight_layout()
        fig.savefig(RESULTS_DIR / "accumulation_curve.png", dpi=150)
        plt.close(fig)

    print("  Saved accumulation_curve.csv + .png")
    return df_out


# ══════════════════════════════════════════════════════════════════════════════
# Ablation study
# ══════════════════════════════════════════════════════════════════════════════

# Feature group → column indices in the 20-dim pairwise feature vector (v3)
ABLATION_GROUPS: dict[str, list[int]] = {
    "contextual":         [2, 3, 5, 6],              # distance_sigmoid, duration_delta, day, time
    "history_explicit":   [9, 10, 11],               # join_rate_act, avg_rating_cluster, act_freq
    "group_composition":  [12, 13, 14],              # gs_match, pg_match, skill_div
    "quality_social":     [7, 8, 15],                # org_followed, mutual_follows, org_rating
    "implicit_signals":   [16, 17, 18, 19],          # implicit_join_rate, no_show, co_attendee, liked
}


def run_ablation_study(
    xgb_model, tt_model: "TwoTower",
    d: dict,
) -> pd.DataFrame:
    """
    Zero-out each feature group in turn; evaluate NDCG@10 LOO@99 for XGBoost-LTR
    and Two-Tower. Measures marginal contribution of each group.
    Two-Tower uses user/event vectors where the corresponding pairwise features
    are embedded differently — for simplicity we ablate the XGBoost test matrix
    and mark Two-Tower ablation as 'implicit' (via pairwise score wrapper).
    """
    from features import build_pairwise_for_pairs as bpfp
    fm = d["fm"]

    all_eid = d["all_event_ids"]
    seen_tr = d["seen_train"]
    test_df = d["test_df"]

    results: list[dict] = []

    # Baseline scores
    def _xgb_base(u, e): return xgb_ltr_score(xgb_model, bpfp(u, e, fm))
    def _tt_base(u, e):   return tt_predict(tt_model, u, e, d["user_vecs"], d["event_vecs"])

    base_xgb = evaluate_loo(test_df, seen_tr, all_eid, _xgb_base, tag="baseline")["NDCG@10"]
    base_tt  = evaluate_loo(test_df, seen_tr, all_eid, _tt_base,  tag="baseline")["NDCG@10"]

    results.append({"model": "XGBoost-LTR", "ablated": "none (baseline)", "NDCG@10": base_xgb, "NDCG_drop": 0.0})
    results.append({"model": "Two-Tower",   "ablated": "none (baseline)", "NDCG@10": base_tt,  "NDCG_drop": 0.0})

    print("\n[Ablation study]")
    print(f"  Baselines: XGBoost={base_xgb:.4f}  Two-Tower={base_tt:.4f}")

    for group_name, feat_idxs in ABLATION_GROUPS.items():
        # XGBoost ablation: zero-out columns in pairwise features
        def _xgb_abl(u, e, _idxs=feat_idxs):
            X = bpfp(u, e, fm).copy()
            X[:, _idxs] = 0.0
            return xgb_ltr_score(xgb_model, X)

        ndcg_xgb = evaluate_loo(test_df, seen_tr, all_eid, _xgb_abl, tag=group_name)["NDCG@10"]
        drop_xgb = round(base_xgb - ndcg_xgb, 4)
        results.append({"model": "XGBoost-LTR", "ablated": group_name,
                         "NDCG@10": ndcg_xgb, "NDCG_drop": drop_xgb})
        print(f"    XGBoost ablate {group_name:22s}  NDCG={ndcg_xgb:.4f}  drop={drop_xgb:+.4f}")

        # Two-Tower ablation: zero-out matching user/event vector dims
        # Map pairwise group → user/event vector feature indices (v3, 97-dim user)
        # user layout: prefs(0:13), demo(13:15), history(15:19), act_affinity(19:50),
        #              participation_groups(50:54), implicit_join_norm(54),
        #              pref_act_questionnaire(55:86), avail_day(86:93), avail_time(93:97)
        TT_ABLATION_MAP: dict[str, dict[str, list[int]]] = {
            "contextual":        {"user": list(range(86, 97))},    # avail_day + avail_time
            "history_explicit":  {"user": list(range(15, 19))},    # total_joins, avg_rating, join_30d, act_freq
            "group_composition": {"user": list(range(50, 54)),     # participation groups
                                  "event": list(range(54, 57))},   # skill_div, soc_dens, org_rat
            "quality_social":    {"user": list(range(55, 86))},    # pref_act_questionnaire
            "implicit_signals":  {"user": [54]},                   # implicit_join_norm
        }
        abl_map = TT_ABLATION_MAP.get(group_name, {})

        def _tt_abl(u, e, _umap=abl_map.get("user", []), _emap=abl_map.get("event", [])):
            uv = d["user_vecs"].copy()
            ev = d["event_vecs"].copy()
            if _umap: uv[:, _umap] = 0.0
            if _emap: ev[:, _emap] = 0.0
            return tt_predict(tt_model, u, e, uv, ev)

        ndcg_tt  = evaluate_loo(test_df, seen_tr, all_eid, _tt_abl,  tag=group_name)["NDCG@10"]
        drop_tt  = round(base_tt - ndcg_tt, 4)
        results.append({"model": "Two-Tower", "ablated": group_name,
                         "NDCG@10": ndcg_tt, "NDCG_drop": drop_tt})
        print(f"    TwoTower  ablate {group_name:22s}  NDCG={ndcg_tt:.4f}  drop={drop_tt:+.4f}")

    df_out = pd.DataFrame(results)
    df_out.to_csv(RESULTS_DIR / "ablation_results.csv", index=False)

    if MPL_OK:
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        for ax, mname in zip(axes, ["XGBoost-LTR", "Two-Tower"]):
            sub = df_out[(df_out["model"] == mname) & (df_out["ablated"] != "none (baseline)")]
            colors = ["red" if d > 0 else "green" for d in sub["NDCG_drop"]]
            ax.barh(sub["ablated"], sub["NDCG_drop"], color=colors)
            ax.axvline(0, color="black", linewidth=0.8)
            ax.set_xlabel("NDCG@10 drop (positive = hurts)"); ax.set_title(f"Ablation — {mname}")
            ax.grid(alpha=0.3, axis="x")
        fig.tight_layout()
        fig.savefig(RESULTS_DIR / "ablation_results.png", dpi=150)
        plt.close(fig)

    return df_out


# ══════════════════════════════════════════════════════════════════════════════
# Multi-objective reranking score
# ══════════════════════════════════════════════════════════════════════════════

def multi_objective_score(
    gnb_model, xgb_model,
    uids: np.ndarray, eids: np.ndarray,
    fm,
    event_vecs: np.ndarray,
) -> np.ndarray:
    """
    Combines three signals:
      0.50 × P(join)         ≈ XGBoost-LTR score (normalised 0-1)
      0.30 × P(rating ≥ 3)   ≈ GNB ordinal P(r≥3)
      0.20 × group_cohesion  ≈ social_density normalised
    Motivated by: Morrish 2023 (repeated group participation) & Zhang 2016 (social effects).
    """
    from features import build_pairwise_for_pairs as bpfp
    X = bpfp(uids, eids, fm)

    xgb_sc = xgb_ltr_score(xgb_model, X)
    xgb_sc = (xgb_sc - xgb_sc.min()) / (xgb_sc.max() - xgb_sc.min() + 1e-9)

    gnb_proba = gnb_model.predict_proba(X)
    classes   = gnb_model.classes_.astype(float)
    # P(r >= 3) = sum of probabilities for classes >= 3
    p_good = np.array([
        gnb_proba[i, classes >= 3].sum()
        for i in range(len(gnb_proba))
    ])

    # Group cohesion: social_density_cat normalised to [0,1]
    ev_idx        = eids   # event_vecs is indexed by event_id
    soc_density   = event_vecs[ev_idx, 55]   # social_density_cat dim
    soc_norm      = soc_density / 2.0         # 0=solo→0, 1=small→0.5, 2=large→1.0

    return 0.50 * xgb_sc + 0.30 * p_good + 0.20 * soc_norm


# ══════════════════════════════════════════════════════════════════════════════
# Visualisations
# ══════════════════════════════════════════════════════════════════════════════

def save_ndcg_curve(curves: dict[str, list], ks: range):
    df = pd.DataFrame({"K": list(ks)})
    for name, vals in curves.items():
        df[name] = vals
    df.to_csv(RESULTS_DIR / "ndcg_vs_k.csv", index=False)

    if MPL_OK:
        fig, ax = plt.subplots(figsize=(10, 6))
        for name, vals in curves.items():
            ax.plot(list(ks), vals, marker="o", markersize=3, label=name)
        ax.set_xlabel("K"); ax.set_ylabel("NDCG@K (LOO@99)")
        ax.set_title("NDCG@K — LOO@99 evaluation"); ax.legend(fontsize=8); ax.grid(alpha=0.3)
        fig.tight_layout(); fig.savefig(RESULTS_DIR / "ndcg_vs_k.png", dpi=150); plt.close(fig)


def save_rf_importance(model, feature_names: list):
    df = pd.DataFrame({"feature": feature_names, "importance": model.feature_importances_}
                      ).sort_values("importance", ascending=False)
    df.to_csv(RESULTS_DIR / "feature_importance_rf.csv", index=False)
    if MPL_OK:
        fig, ax = plt.subplots(figsize=(8, 7))
        ax.barh(df["feature"][::-1], df["importance"][::-1])
        ax.set_xlabel("Importance"); ax.set_title("Random Forest — Feature Importances")
        fig.tight_layout(); fig.savefig(RESULTS_DIR / "feature_importance_rf.png", dpi=150)
        plt.close(fig)


def save_shap(xgb_model, X_test: np.ndarray, feature_names: list):
    if not (SHAP_OK and XGB_OK):
        return
    explainer = shap.TreeExplainer(xgb_model)
    sv  = explainer.shap_values(X_test[:2000])
    df  = pd.DataFrame({"feature": feature_names,
                         "mean_abs_shap": np.abs(sv).mean(axis=0)}
                       ).sort_values("mean_abs_shap", ascending=False)
    df.to_csv(RESULTS_DIR / "shap_summary.csv", index=False)
    if MPL_OK:
        fig, ax = plt.subplots(figsize=(8, 7))
        ax.barh(df["feature"][::-1], df["mean_abs_shap"][::-1], color="steelblue")
        ax.set_xlabel("|SHAP| mean"); ax.set_title("XGBoost-LTR — SHAP Feature Importance")
        fig.tight_layout(); fig.savefig(RESULTS_DIR / "shap_summary.png", dpi=150); plt.close(fig)
    print(f"    SHAP top-5: {df['feature'].tolist()[:5]}")


def save_training_curve(curves: list[float], name: str):
    df = pd.DataFrame({"epoch": range(1, len(curves)+1), "loss": curves})
    df.to_csv(RESULTS_DIR / f"{name.lower().replace(' ','_')}_training_curve.csv", index=False)
    if MPL_OK:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.plot(df["epoch"], df["loss"], color="crimson")
        ax.set_xlabel("Epoch"); ax.set_ylabel("Loss"); ax.set_title(f"{name} — Training Curve")
        ax.grid(alpha=0.3); fig.tight_layout()
        fig.savefig(RESULTS_DIR / f"{name.lower().replace(' ','_')}_training_curve.png", dpi=150)
        plt.close(fig)


def print_table(all_results: dict) -> str:
    header = (f"{'Model':<22} {'NDCG@10':>9} {'95%CI':>13} "
              f"{'HR@10':>7} {'MRR':>8} {'AUC-ROC':>9} {'ColdNDCG':>10}")
    sep    = "-" * len(header)
    lines  = [sep, header, sep]
    for name, r in all_results.items():
        t = r["test"]
        ci = t.get("NDCG@10_CI", (0.0, 0.0))
        ci_s   = f"[{ci[0]:.4f},{ci[1]:.4f}]"
        cold_s = (f"{r['cold']['NDCG@10']:>10.4f}" if r.get("cold") else f"{'n/a':>10}")
        auc_s  = (f"{r.get('test_full', {}).get('AUC-ROC', 0.0):>9.4f}")
        lines.append(f"{name:<22} {t['NDCG@10']:>9.4f} {ci_s:>13} "
                     f"{t['HitRate@10']:>7.4f} {t['MRR']:>8.4f} {auc_s}{cold_s}")
    lines.append(sep)
    table = "\n".join(lines)
    print(table)
    (RESULTS_DIR / "results_table.txt").write_text(table)
    return table


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════

def main(neural_only: bool = False):
    print("=" * 65)
    print("MoveUs Recommender v3 — LOO@99 evaluation / LambdaMART / BPR-MF")
    print("=" * 65)
    if neural_only:
        print("  [--neural-only] Skipping tiers 0-2, training NCF + Two-Tower only.")

    print("\n[Loading data]")
    d = load_data()
    Xtr, ytr, wtr = d["X_train"], d["y_train"], d["train_weights"]
    Xte, yte = d["X_test"],  d["y_test"]
    Xcl, ycl = d["X_cold"],  d["y_cold"]
    feat_names = d["feature_names"]
    N = d["n_users"]; M = d["n_events"]
    print(f"  {N} users | {M} events | "
          f"train={len(Xtr)} test={len(Xte)} cold={len(Xcl)}")
    print(f"  device: {DEVICE if TORCH_OK else 'cpu (torch not installed)'}")

    all_results: dict = {}
    ndcg_curves: dict = {}
    KS = range(1, 21)

    from features import build_pairwise_for_pairs as bpfp
    fm = d["fm"]

    def _eval_all(score_fn, name: str, score_fn_cold=None,
                  full_scores_te=None, full_scores_cl=None):
        r: dict = {}
        r["test"] = evaluate_loo(d["test_df"], d["seen_train"], d["all_event_ids"],
                                  score_fn, tag="test")
        if full_scores_te is not None:
            r["test_full"] = evaluate_full(d["test_uids"], d["test_ratings"],
                                           full_scores_te, tag="test")
        if score_fn_cold is not None:
            # Cold LOO: last *rated* interaction per cold user is the positive
            cold_rated = d["cold_df"][d["cold_df"]["signal_type"] == "join_rated"]
            cold_loo_df = (cold_rated.sort_values(["user_id", "timestamp"])
                           .groupby("user_id").last().reset_index())
            r["cold"] = evaluate_loo(
                cold_loo_df, {}, d["all_event_ids"], score_fn_cold, tag="cold"
            )
            if full_scores_cl is not None:
                r["cold_full"] = evaluate_full(d["cold_uids"], d["cold_ratings"],
                                               full_scores_cl, tag="cold")
        all_results[name] = r
        ndcg_curves[name] = ndcg_vs_k(d["test_df"], d["seen_train"],
                                       d["all_event_ids"], score_fn, KS)
        t = r["test"]
        auc = r.get("test_full", {}).get("AUC-ROC", "-")
        cold_s = (f"  cold={r['cold']['NDCG@10']:.4f}" if "cold" in r else "")
        print(f"  {name:<22} NDCG@10={t['NDCG@10']:.4f}  HR@10={t['HitRate@10']:.4f}"
              f"  MRR={t['MRR']:.4f}  AUC={auc}{cold_s}")

    # ── Tier 0 ────────────────────────────────────────────────────────────────
    if not neural_only:
        print("\n[Tier 0: Baselines]")
    _eval_all(lambda u, e: random_scores(len(u), seed=int(u[0])), "Random",
              score_fn_cold=lambda u, e: random_scores(len(u), seed=int(u[0])),
              full_scores_te=random_scores(len(Xte), seed=SEED + 2),
              full_scores_cl=random_scores(len(Xcl), seed=SEED + 3))

    def _pop_fn(u, e): return popularity_scores(e, d["event_popularity"])
    _eval_all(_pop_fn, "Popularity",
              score_fn_cold=_pop_fn,
              full_scores_te=popularity_scores(d["test_eids"], d["event_popularity"]),
              full_scores_cl=popularity_scores(d["cold_eids"], d["event_popularity"]))

    # ── Tier 1 ────────────────────────────────────────────────────────────────
    print("\n[Tier 1: Ordinal ML — cold-start capable]")

    t0 = time.time()
    gnb = train_gnb(Xtr, ytr)   # GNB does not support sample_weight
    pickle.dump(gnb, open(MODELS_DIR / "gnb.pkl", "wb"))
    gnb_te = expected_rating(gnb, Xte)
    gnb_cl = expected_rating(gnb, Xcl)
    def _gnb_fn(u, e): return expected_rating(gnb, bpfp(u, e, fm))
    _eval_all(_gnb_fn, "GaussianNB",
              score_fn_cold=_gnb_fn,
              full_scores_te=gnb_te, full_scores_cl=gnb_cl)
    print(f"    trained in {time.time()-t0:.1f}s")

    t0 = time.time()
    lr_m = train_lr(Xtr, ytr, sample_weight=wtr)
    pickle.dump(lr_m, open(MODELS_DIR / "lr.pkl", "wb"))
    lr_te = expected_rating(lr_m, Xte)
    lr_cl = expected_rating(lr_m, Xcl)
    def _lr_fn(u, e): return expected_rating(lr_m, bpfp(u, e, fm))
    _eval_all(_lr_fn, "LogisticRegression",
              score_fn_cold=_lr_fn,
              full_scores_te=lr_te, full_scores_cl=lr_cl)
    print(f"    trained in {time.time()-t0:.1f}s")

    coef_df = pd.DataFrame({"feature": feat_names, "coef_sum": lr_m.coef_.sum(axis=0)}
                           ).sort_values("coef_sum", ascending=False)
    coef_df.to_csv(RESULTS_DIR / "lr_coefficients.csv", index=False)

    # ── Tier 2 ────────────────────────────────────────────────────────────────
    print("\n[Tier 2: Classical ML]")

    t0 = time.time()
    rf = RandomForestClassifier(n_estimators=200, max_depth=12,
                                random_state=SEED, n_jobs=-1)
    rf.fit(Xtr, ytr, sample_weight=wtr)
    pickle.dump(rf, open(MODELS_DIR / "rf.pkl", "wb"))
    rf_te = expected_rating(rf, Xte)
    rf_cl = expected_rating(rf, Xcl)
    def _rf_fn(u, e): return expected_rating(rf, bpfp(u, e, fm))
    _eval_all(_rf_fn, "RandomForest",
              score_fn_cold=_rf_fn,
              full_scores_te=rf_te, full_scores_cl=rf_cl)
    print(f"    trained in {time.time()-t0:.1f}s")
    save_rf_importance(rf, feat_names)

    xgb_m = None
    if XGB_OK:
        t0 = time.time()
        xgb_m = train_xgb_ltr(Xtr, ytr, d["train_all_uids"],
                               Xte, yte, d["test_uids"])
        if xgb_m is not None:
            pickle.dump(xgb_m, open(MODELS_DIR / "xgb.pkl", "wb"))
            xgb_te = xgb_ltr_score(xgb_m, Xte)
            xgb_cl = xgb_ltr_score(xgb_m, Xcl)
            def _xgb_fn(u, e): return xgb_ltr_score(xgb_m, bpfp(u, e, fm))
            _eval_all(_xgb_fn, "XGBoost-LTR",
                      score_fn_cold=_xgb_fn,
                      full_scores_te=xgb_te, full_scores_cl=xgb_cl)
            print(f"    trained in {time.time()-t0:.1f}s")
            save_shap(xgb_m, Xte, feat_names)
    else:
        print("  XGBoost skipped")

    lgb_m = None
    if LGB_OK:
        t0 = time.time()
        lgb_m = train_lgb_ltr(Xtr, ytr, d["train_all_uids"],
                               Xte, yte, d["test_uids"],
                               sample_weight=wtr)
        if lgb_m is not None:
            lgb_m.save_model(str(MODELS_DIR / "lgb.txt"))
            lgb_te = lgb_ltr_score(lgb_m, Xte)
            lgb_cl = lgb_ltr_score(lgb_m, Xcl)
            def _lgb_fn(u, e): return lgb_ltr_score(lgb_m, bpfp(u, e, fm))
            _eval_all(_lgb_fn, "LightGBM-LTR",
                      score_fn_cold=_lgb_fn,
                      full_scores_te=lgb_te, full_scores_cl=lgb_cl)
            print(f"    trained in {time.time()-t0:.1f}s")
    else:
        print("  LightGBM skipped")

    if SURPRISE_OK:
        t0 = time.time()
        trainset = _to_surprise(d["train_df"])
        svd_m  = train_svd(trainset)
        pickle.dump(svd_m, open(MODELS_DIR / "svd.pkl", "wb"))
        svd_te  = surprise_predict(svd_m, d["test_uids"], d["test_eids"])
        svd_te  = (svd_te - svd_te.min()) / (svd_te.max() - svd_te.min() + 1e-9)
        def _svd_fn(u, e): return (lambda s: (s-s.min())/(s.max()-s.min()+1e-9))(
            surprise_predict(svd_m, u, e))
        _eval_all(_svd_fn, "SVD-MF", full_scores_te=svd_te)
        print(f"    SVD trained in {time.time()-t0:.1f}s")

        knn_m  = train_knn(trainset)
        pickle.dump(knn_m, open(MODELS_DIR / "knn.pkl", "wb"))
        knn_te  = surprise_predict(knn_m, d["test_uids"], d["test_eids"])
        knn_te  = (knn_te - knn_te.min()) / (knn_te.max() - knn_te.min() + 1e-9)
        def _knn_fn(u, e): return (lambda s: (s-s.min())/(s.max()-s.min()+1e-9))(
            surprise_predict(knn_m, u, e))
        _eval_all(_knn_fn, "kNN-CF", full_scores_te=knn_te)

        svd_raw  = surprise_predict(svd_m, d["test_uids"], d["test_eids"])
        svd_norm = (svd_raw - svd_raw.min()) / (svd_raw.max() - svd_raw.min() + 1e-9)
        hyb_te   = hybrid_scores(svd_norm, gnb_te, d["test_uids"], d["user_n_train"])
        def _hyb_fn(u, e): return hybrid_scores(
            (lambda s: (s-s.min())/(s.max()-s.min()+1e-9))(surprise_predict(svd_m, u, e)),
            expected_rating(gnb, bpfp(u, e, fm)),
            u, d["user_n_train"])
        _eval_all(_hyb_fn, "Hybrid(SVD+GNB)", full_scores_te=hyb_te)
    else:
        print("  SVD / k-NN / Hybrid skipped (scikit-surprise not installed)")

    # ── Tier 2b — BPR-MF ─────────────────────────────────────────────────────
    bpr_model = None
    if TORCH_OK:
        print("\n[Tier 2b: BPR-MF — implicit signals]")
        t0 = time.time()
        bpr_model = BPRMF(N, M)
        bpr_curves = train_bpr_mf(bpr_model,
                                   d["train_imp_uids"], d["train_imp_eids"],
                                   d["train_imp_weights"], M, n_epochs=20)
        torch.save(bpr_model.state_dict(), MODELS_DIR / "bpr_mf.pt")
        bpr_te = bpr_mf_predict(bpr_model, d["test_uids"], d["test_eids"])
        bpr_cl = bpr_mf_predict(bpr_model, d["cold_uids"], d["cold_eids"])
        def _bpr_fn(u, e): return bpr_mf_predict(bpr_model, u, e)
        _eval_all(_bpr_fn, "BPR-MF",
                  score_fn_cold=_bpr_fn,
                  full_scores_te=bpr_te, full_scores_cl=bpr_cl)
        print(f"    BPR-MF trained in {time.time()-t0:.1f}s")
        save_training_curve(bpr_curves, "BPR-MF")

    # ── EASE (closed-form CF) ─────────────────────────────────────────────────
    print("\n[EASE: Embarrassingly Shallow Autoencoder]")
    t0 = time.time()
    ease_m = EASE(lam=500.0)
    ease_m.fit(N, M,
               d["train_imp_uids"], d["train_imp_eids"],
               weights=d["train_imp_weights"])
    pickle.dump(ease_m, open(MODELS_DIR / "ease.pkl", "wb"))
    ease_te = ease_m.predict(d["test_uids"], d["test_eids"])
    ease_cl = ease_m.predict(d["cold_uids"], d["cold_eids"])
    def _ease_fn(u, e): return ease_m.predict(u, e)
    _eval_all(_ease_fn, "EASE",
              score_fn_cold=_ease_fn,
              full_scores_te=ease_te, full_scores_cl=ease_cl)
    print(f"    EASE fitted in {time.time()-t0:.1f}s")

    # ── Tier 3 — Neural ───────────────────────────────────────────────────────
    tt_model = None
    if TORCH_OK:
        print(f"\n[Tier 3: Neural Models  (device={DEVICE})]")

        t0 = time.time()
        ncf = NCF(n_users=N, n_events=M)
        ncf_curves = train_ncf(ncf, d["train_df"], d["user_vecs"], d["event_vecs"], M)
        torch.save(ncf.state_dict(), MODELS_DIR / "ncf.pt")
        ncf_te = ncf_predict(ncf, d["test_uids"], d["test_eids"], d["user_vecs"], d["event_vecs"])
        ncf_cl = ncf_predict(ncf, d["cold_uids"], d["cold_eids"], d["user_vecs"], d["event_vecs"])
        def _ncf_fn(u, e): return ncf_predict(ncf, u, e, d["user_vecs"], d["event_vecs"])
        _eval_all(_ncf_fn, "NCF",
                  score_fn_cold=_ncf_fn,
                  full_scores_te=ncf_te, full_scores_cl=ncf_cl)
        print(f"    NCF trained in {time.time()-t0:.1f}s")
        save_training_curve(ncf_curves, "NCF")

        t0 = time.time()
        tt_model = TwoTower()
        tt_curves = train_two_tower(tt_model, d["train_df"],
                                    d["user_vecs"], d["event_vecs"],
                                    d["train_imp_uids"], d["train_imp_eids"],
                                    d["train_imp_weights"], M)
        torch.save(tt_model.state_dict(), MODELS_DIR / "two_tower.pt")
        tt_te = tt_predict(tt_model, d["test_uids"], d["test_eids"], d["user_vecs"], d["event_vecs"])
        tt_cl = tt_predict(tt_model, d["cold_uids"], d["cold_eids"], d["user_vecs"], d["event_vecs"])
        def _tt_fn(u, e): return tt_predict(tt_model, u, e, d["user_vecs"], d["event_vecs"])
        _eval_all(_tt_fn, "Two-Tower",
                  score_fn_cold=_tt_fn,
                  full_scores_te=tt_te, full_scores_cl=tt_cl)
        print(f"    Two-Tower trained in {time.time()-t0:.1f}s")
        save_training_curve(tt_curves, "Two-Tower")
    else:
        print("\n[Tier 3: skipped — torch not installed]")

    # ── Results table ─────────────────────────────────────────────────────────
    print("\n" + "=" * 65)
    print("Results (LOO@99 evaluation):")
    print("=" * 65)
    print_table(all_results)

    save_ndcg_curve(ndcg_curves, KS)
    with open(RESULTS_DIR / "results.json", "w") as fh:
        json.dump(all_results, fh, indent=2)

    # ── Beyond-accuracy metrics (Precision@K, Novelty, Coverage) ─────────────
    print("\n[Beyond-accuracy metrics — Precision@10, Novelty, Coverage]")
    n_train_interactions = len(d["train_df"])
    beyond_rows: list[dict] = []
    # Evaluate the three key models: XGBoost-LTR, GNB, Popularity
    for mname, fn in [("Popularity", _pop_fn),
                      ("GaussianNB", _gnb_fn),
                      *([("XGBoost-LTR", _xgb_fn)] if XGB_OK and xgb_m is not None else []),
                      *([("LightGBM-LTR", _lgb_fn)] if LGB_OK and lgb_m is not None else [])]:
        p_k  = precision_at_k(d["test_df"], d["seen_train"], d["all_event_ids"], fn)
        nov  = novelty(d["test_df"], d["seen_train"], d["all_event_ids"], fn,
                       d["event_popularity"], n_train_interactions)
        cov  = coverage(d["test_df"], d["seen_train"], d["all_event_ids"], fn)
        beyond_rows.append({"model": mname, "Precision@10": p_k,
                             "Novelty": nov, "Coverage@10": cov})
        print(f"  {mname:<22} P@10={p_k:.4f}  Novelty={nov:.2f}  Coverage={cov:.4f}")
    pd.DataFrame(beyond_rows).to_csv(RESULTS_DIR / "beyond_accuracy.csv", index=False)

    # ── Multi-objective score ─────────────────────────────────────────────────
    if XGB_OK and xgb_m is not None:
        print("\n[Multi-objective reranking score — sample]")
        sample_u = d["test_uids"][:100]
        sample_e = d["test_eids"][:100]
        mo_scores = multi_objective_score(gnb, xgb_m, sample_u, sample_e,
                                          fm, d["event_vecs"])
        pd.DataFrame({"user_id": sample_u, "event_id": sample_e,
                      "multi_obj_score": mo_scores}
                     ).to_csv(RESULTS_DIR / "multi_objective_sample.csv", index=False)
        print(f"    mean={mo_scores.mean():.4f}  std={mo_scores.std():.4f}")

    # ── Accumulation curve ────────────────────────────────────────────────────
    print("\n[Accumulation curve — retraining at 5 data fractions]")
    run_accumulation_curve(d)

    # ── Ablation study ────────────────────────────────────────────────────────
    if XGB_OK and xgb_m is not None and tt_model is not None:
        run_ablation_study(xgb_m, tt_model, d)
    else:
        print("\n[Ablation: skipped — XGBoost or Two-Tower not available]")

    print(f"\nAll artefacts:\n  {MODELS_DIR.resolve()}\n  {RESULTS_DIR.resolve()}")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--neural-only", action="store_true",
                    help="Skip tiers 0-2 and train only NCF + Two-Tower")
    args = ap.parse_args()
    main(neural_only=args.neural_only)
