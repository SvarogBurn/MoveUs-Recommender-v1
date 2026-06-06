"""Build positive and sampled-negative dense pair-feature matrices from train."""
import numpy as np


def build_pos_neg_pairs(ctx, fc, neg_per_pos: int = 2, seed: int = 0):
    rng = np.random.default_rng(seed)
    train = ctx.train
    pos_rows = [(int(r.user_id), int(r.event_id))
                for r in train.itertuples(index=False)
                if r.signal_type in ("join_rated", "join_no_rate")
                and not (r.signal_type == "join_rated" and int(r.rating) < 3)]
    all_events = ctx.events["event_id"].astype(int).values
    seen = {}
    for u, e in pos_rows:
        seen.setdefault(u, set()).add(e)
    neg_rows = []
    for u, _ in pos_rows:
        for _ in range(neg_per_pos):
            e = int(rng.choice(all_events))
            if e not in seen.get(u, set()):
                neg_rows.append((u, e))
    Xp = np.array([fc.pair_dense(u, np.array([e]))[0] for (u, e) in pos_rows]) if pos_rows else np.zeros((1, fc.dense_dim))
    Xn = np.array([fc.pair_dense(u, np.array([e]))[0] for (u, e) in neg_rows]) if neg_rows else np.zeros((1, fc.dense_dim))
    return Xp, Xn
