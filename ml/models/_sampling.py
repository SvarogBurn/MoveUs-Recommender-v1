"""Feasible negative sampling shared by the content/ranking models.

Training negatives must come from the same distribution as the evaluation
candidate pool (events that are actually feasible for the user), otherwise the
model only learns to reject obviously-infeasible events and has nothing left to
discriminate at eval time.
"""
import numpy as np

from ml.eval.candidates import feasible_candidates


def user_feasible_events(users, events, user_ids) -> dict:
    """user_id -> array of statically-feasible event ids (availability + distance).

    No time window here: this is the per-user pool from which negatives are drawn.
    Unknown users map to an empty array.
    """
    users_i = users.set_index("user_id", drop=False)
    out = {}
    for uid in {int(u) for u in user_ids}:
        if uid not in users_i.index:
            out[uid] = np.array([], dtype=int)
            continue
        out[uid] = feasible_candidates(users_i.loc[uid], events, already_seen=set())
    return out


def sample_negatives(feasible_by_user, attended_by_user, users_seq,
                     neg_per_pos, all_events, seed=0):
    """For each user occurrence in ``users_seq`` draw ``neg_per_pos`` negatives.

    Negatives are feasible-but-not-attended events; falls back to the full
    catalogue when a user has no feasible alternatives.
    """
    rng = np.random.default_rng(seed)
    all_events = np.asarray(all_events, dtype=int)
    negs = []
    for u in users_seq:
        feas = feasible_by_user.get(int(u))
        if feas is None or len(feas) == 0:
            pool = all_events
        else:
            attended = attended_by_user.get(int(u), set())
            pool = feas[~np.isin(feas, list(attended))] if attended else feas
            if len(pool) == 0:
                pool = all_events
        for e in rng.choice(pool, size=neg_per_pos):
            negs.append((int(u), int(e)))
    return negs
