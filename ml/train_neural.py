#!/usr/bin/env python3
"""
train_neural.py — Train only NCF + Two-Tower on GPU and evaluate with LOO@99.

Usage:
    python -u train_neural.py

Requires data to already exist in ml/data/ (run generate_data.py then features.py first).
Saves: ml/models/ncf.pt, ml/models/two_tower.pt, ml/results/results_neural.json
"""

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

# ── resolve paths ─────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent
DATA_DIR    = ROOT / "data"
MODELS_DIR  = ROOT / "models"
RESULTS_DIR = ROOT / "results"
MODELS_DIR.mkdir(exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)

SEED   = 42
N_NEG  = 4        # negatives per positive in NCF
K_EVAL = 10

# ── torch ─────────────────────────────────────────────────────────────────────
try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"device: {DEVICE}")
except ImportError:
    print("ERROR: torch not installed. Run: pip install torch")
    sys.exit(1)

USER_DIM  = 97
EVENT_DIM = 57
EMB_DIM   = 64

USER_SIDE_SLICE  = slice(0, 15)   # prefs(13)+demo(2)
EVENT_SIDE_SLICE = slice(36, 57)  # 21-dim event side features


# ── model definitions ──────────────────────────────────────────────────────────

class NCF(nn.Module):
    def __init__(self, n_users, n_events, emb_dim=EMB_DIM, side_dim=15+21):
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
    def __init__(self, in_dim):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, 128), nn.LayerNorm(128), nn.ReLU(),
            nn.Linear(128, 64),     nn.LayerNorm(64),  nn.ReLU(),
            nn.Linear(64, 64),
        )
    def forward(self, x):
        return F.normalize(self.net(x), dim=-1)


class TwoTower(nn.Module):
    def __init__(self):
        super().__init__()
        self.user_tower  = _Tower(USER_DIM)
        self.event_tower = _Tower(EVENT_DIM)
    def forward(self, uv, ev):
        return (self.user_tower(uv) * self.event_tower(ev)).sum(dim=-1)


# ── training ───────────────────────────────────────────────────────────────────

def train_ncf(model, train_df, user_vecs, event_vecs, n_events,
              n_epochs=25, lr=5e-4, batch_size=512):
    rated = train_df[train_df["signal_type"] == "join_rated"]
    uids_obs   = rated["user_id"].values.astype(int)
    eids_obs   = rated["event_id"].values.astype(int)
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
        if (epoch + 1) % 5 == 0:
            print(f"    NCF epoch {epoch+1:3d}/{n_epochs}  loss={avg:.4f}", flush=True)


def train_two_tower(model, imp_uids, imp_eids, imp_weights,
                    user_vecs, event_vecs, n_events,
                    n_epochs=25, lr=1e-3, batch_size=1024):
    pos_mask  = imp_weights > 0
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

    for epoch in range(n_epochs):
        perm = torch.randperm(n_pos)
        pu = pos_uids[perm]; pe = pos_eids[perm]; pw = pos_wts[perm]
        epoch_loss = 0.0; nb = 0
        for i in range(0, n_pos, batch_size):
            u_b  = pu[i:i+batch_size].to(DEVICE)
            ep_b = pe[i:i+batch_size].to(DEVICE)
            w_b  = pw[i:i+batch_size].to(DEVICE)
            bsz  = len(u_b)
            en_b = torch.LongTensor(rng_np.integers(0, n_events, bsz)).to(DEVICE)
            pos_sc = model(uv[u_b.cpu()].to(DEVICE), ev[ep_b.cpu()].to(DEVICE))
            neg_sc = model(uv[u_b.cpu()].to(DEVICE), ev[en_b.cpu()].to(DEVICE))
            loss   = (w_b * F.softplus(neg_sc - pos_sc)).mean()
            opt.zero_grad(); loss.backward(); opt.step()
            epoch_loss += loss.item(); nb += 1
        sched.step()
        avg = epoch_loss / max(nb, 1)
        if (epoch + 1) % 5 == 0:
            print(f"    TwoTower epoch {epoch+1:3d}/{n_epochs}  loss={avg:.4f}", flush=True)


# ── inference ──────────────────────────────────────────────────────────────────

@torch.no_grad()
def ncf_predict(model, uids, eids, user_vecs, event_vecs, bs=2048):
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


@torch.no_grad()
def tt_predict(model, uids, eids, user_vecs, event_vecs, bs=4096):
    model.eval(); model.to(DEVICE)
    uv = torch.FloatTensor(user_vecs)
    ev = torch.FloatTensor(event_vecs)
    out = []
    for i in range(0, len(uids), bs):
        u_b = torch.LongTensor(uids[i:i+bs]).to(DEVICE)
        e_b = torch.LongTensor(eids[i:i+bs]).to(DEVICE)
        out.append(model(uv[u_b.cpu()].to(DEVICE), ev[e_b.cpu()].to(DEVICE)).cpu().numpy())
    return np.concatenate(out)


# ── evaluation ─────────────────────────────────────────────────────────────────

def evaluate_loo(test_df, seen_train, all_event_ids, score_fn, n_neg=99, k=K_EVAL):
    rng = np.random.default_rng(SEED)
    ndcgs, hits, mrrs = [], [], []
    for row in test_df.itertuples(index=False):
        uid     = int(row.user_id)
        pos_eid = int(row.event_id)
        exclude    = seen_train.get(uid, set()) | {pos_eid}
        candidates = all_event_ids[~np.isin(all_event_ids, list(exclude))]
        negs  = rng.choice(candidates, n_neg, replace=False) if len(candidates) >= n_neg else candidates
        items = np.concatenate([[pos_eid], negs])
        u_arr = np.full(len(items), uid, dtype=int)
        scores = score_fn(u_arr, items)
        rank = int(np.sum(scores[1:] >= scores[0]) + 1)
        ndcgs.append(1.0 / np.log2(rank + 1) if rank <= k else 0.0)
        hits.append(1.0 if rank <= k else 0.0)
        mrrs.append(1.0 / rank)
    return {
        "NDCG@10":    round(float(np.mean(ndcgs)), 4),
        "HitRate@10": round(float(np.mean(hits)),  4),
        "MRR":        round(float(np.mean(mrrs)),  4),
        "n_users":    len(ndcgs),
    }


# ── data loading ───────────────────────────────────────────────────────────────

def load_data():
    print("Loading data...", flush=True)
    train_df = pd.read_csv(DATA_DIR / "train.csv", parse_dates=["timestamp"])
    test_df  = pd.read_csv(DATA_DIR / "test.csv",  parse_dates=["timestamp"])
    cold_df  = pd.read_csv(DATA_DIR / "cold_start_users.csv", parse_dates=["timestamp"])

    user_vecs  = np.load(DATA_DIR / "user_vectors.npy")
    event_vecs = np.load(DATA_DIR / "event_vectors.npy")

    imp_uids    = np.load(DATA_DIR / "train_implicit_uids.npy")
    imp_eids    = np.load(DATA_DIR / "train_implicit_eids.npy")
    imp_weights = np.load(DATA_DIR / "train_implicit_weights.npy")

    n_users = int(user_vecs.shape[0])
    n_events = int(event_vecs.shape[0])

    seen_train: dict = {}
    for row in train_df.itertuples(index=False):
        seen_train.setdefault(int(row.user_id), set()).add(int(row.event_id))

    all_event_ids = np.arange(n_events)

    print(f"  {n_users} users | {n_events} events | "
          f"train={len(train_df)} test={len(test_df)} cold={len(cold_df)}", flush=True)
    assert user_vecs.shape[1]  == USER_DIM,  f"Expected {USER_DIM}-dim user vec, got {user_vecs.shape[1]}"
    assert event_vecs.shape[1] == EVENT_DIM, f"Expected {EVENT_DIM}-dim event vec, got {event_vecs.shape[1]}"

    return {
        "train_df": train_df, "test_df": test_df, "cold_df": cold_df,
        "user_vecs": user_vecs, "event_vecs": event_vecs,
        "imp_uids": imp_uids, "imp_eids": imp_eids, "imp_weights": imp_weights,
        "n_users": n_users, "n_events": n_events,
        "seen_train": seen_train, "all_event_ids": all_event_ids,
    }


# ── main ───────────────────────────────────────────────────────────────────────

def main():
    d = load_data()
    N = d["n_users"]; M = d["n_events"]
    results = {}

    # ── NCF ───────────────────────────────────────────────────────────────────
    print("\n[NCF]", flush=True)
    t0  = time.time()
    ncf = NCF(N, M)
    train_ncf(ncf, d["train_df"], d["user_vecs"], d["event_vecs"], M)
    torch.save(ncf.state_dict(), MODELS_DIR / "ncf.pt")
    print(f"  trained in {time.time()-t0:.1f}s  ->  saved ncf.pt", flush=True)

    def _ncf(u, e): return ncf_predict(ncf, u, e, d["user_vecs"], d["event_vecs"])

    print("  evaluating (test)...", flush=True)
    r_te = evaluate_loo(d["test_df"], d["seen_train"], d["all_event_ids"], _ncf)

    cold_rated = d["cold_df"][d["cold_df"]["signal_type"] == "join_rated"]
    cold_loo   = (cold_rated.sort_values(["user_id","timestamp"])
                  .groupby("user_id").last().reset_index())
    print("  evaluating (cold)...", flush=True)
    r_cl = evaluate_loo(cold_loo, {}, d["all_event_ids"], _ncf)

    results["NCF"] = {"test": r_te, "cold": r_cl}
    print(f"  NCF  NDCG@10={r_te['NDCG@10']:.4f}  HR@10={r_te['HitRate@10']:.4f}"
          f"  MRR={r_te['MRR']:.4f}  cold={r_cl['NDCG@10']:.4f}", flush=True)

    # ── Two-Tower ─────────────────────────────────────────────────────────────
    print("\n[Two-Tower]", flush=True)
    t0 = time.time()
    tt = TwoTower()
    train_two_tower(tt, d["imp_uids"], d["imp_eids"], d["imp_weights"],
                    d["user_vecs"], d["event_vecs"], M)
    torch.save(tt.state_dict(), MODELS_DIR / "two_tower.pt")
    print(f"  trained in {time.time()-t0:.1f}s  ->  saved two_tower.pt", flush=True)

    def _tt(u, e): return tt_predict(tt, u, e, d["user_vecs"], d["event_vecs"])

    print("  evaluating (test)...", flush=True)
    r_te = evaluate_loo(d["test_df"], d["seen_train"], d["all_event_ids"], _tt)
    print("  evaluating (cold)...", flush=True)
    r_cl = evaluate_loo(cold_loo, {}, d["all_event_ids"], _tt)

    results["Two-Tower"] = {"test": r_te, "cold": r_cl}
    print(f"  TT   NDCG@10={r_te['NDCG@10']:.4f}  HR@10={r_te['HitRate@10']:.4f}"
          f"  MRR={r_te['MRR']:.4f}  cold={r_cl['NDCG@10']:.4f}", flush=True)

    # ── Save ──────────────────────────────────────────────────────────────────
    out_path = RESULTS_DIR / "results_neural.json"
    with open(out_path, "w") as fh:
        json.dump(results, fh, indent=2)
    print(f"\nSaved results to {out_path}", flush=True)

    print("\n" + "="*50)
    print(f"{'Model':<14} {'NDCG@10':>8} {'HR@10':>8} {'MRR':>8} {'ColdNDCG':>10}")
    print("="*50)
    for name, res in results.items():
        t = res["test"]; c = res.get("cold", {})
        cold_s = f"{c['NDCG@10']:>10.4f}" if c else f"{'n/a':>10}"
        print(f"{name:<14} {t['NDCG@10']:>8.4f} {t['HitRate@10']:>8.4f}"
              f" {t['MRR']:>8.4f} {cold_s}")
    print("="*50)


if __name__ == "__main__":
    main()
