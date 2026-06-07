"""Build positive and feasible-negative dense pair-feature matrices from train.

Negatives are drawn from each user's feasible-but-unattended events (the same
distribution as the evaluation candidate pool), not uniformly from the whole
catalogue, so the model learns to discriminate *within* the feasible set.
"""
import numpy as np

from ml.models._sampling import user_feasible_events, sample_negatives


def build_pos_neg_rows(ctx, neg_per_pos: int = 2, seed: int = 0):
    """Return (pos_rows, neg_rows) as lists of (user_id, event_id)."""
    train = ctx.train
    pos_rows = [(int(r.user_id), int(r.event_id))
                for r in train.itertuples(index=False)
                if r.signal_type in ("join_rated", "join_no_rate")
                and not (r.signal_type == "join_rated" and int(r.rating) < 3)]
    if not pos_rows:
        return [], []

    attended = {}
    for u, e in pos_rows:
        attended.setdefault(u, set()).add(e)
    pos_users = [u for u, _ in pos_rows]
    feasible = user_feasible_events(ctx.users, ctx.events, pos_users)
    all_events = ctx.events["event_id"].astype(int).values
    neg_rows = sample_negatives(feasible, attended, pos_users,
                                neg_per_pos, all_events, seed=seed)
    return pos_rows, neg_rows


def build_pos_neg_pairs(ctx, fc, neg_per_pos: int = 2, seed: int = 0):
    pos_rows, neg_rows = build_pos_neg_rows(ctx, neg_per_pos=neg_per_pos, seed=seed)
    Xp = (np.array([fc.pair_dense(u, np.array([e]))[0] for (u, e) in pos_rows])
          if pos_rows else np.zeros((1, fc.dense_dim)))
    Xn = (np.array([fc.pair_dense(u, np.array([e]))[0] for (u, e) in neg_rows])
          if neg_rows else np.zeros((1, fc.dense_dim)))
    return Xp, Xn
