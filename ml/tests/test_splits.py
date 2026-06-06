import numpy as np
from ml.gen import config as c
from ml.gen.timeline import run_timeline
from ml.gen.splits import finalize_events, ensure_min_joins, build_splits


def test_finalize_events_emergent_fields(small):
    rng = np.random.default_rng(3)
    users, events, interactions, state = run_timeline(rng)
    events2 = finalize_events(events, interactions)
    for col in ["participant_count", "fill_rate", "social_density_cat", "avg_organizer_rating"]:
        assert col in events2.columns
    assert (events2["participant_count"] >= 0).all()


def test_every_warm_user_has_one_test_row(small):
    rng = np.random.default_rng(3)
    users, events, interactions, state = run_timeline(rng)
    interactions = ensure_min_joins(interactions, users, events, state)
    train, test, train_imp, cold = build_splits(interactions)
    warm = set(range(c.N_USERS - c.N_COLD_USERS))
    warm_present = warm & set(interactions["user_id"].unique())
    assert set(test["user_id"]) == warm_present
    assert test.groupby("user_id").size().max() == 1
    assert set(cold["user_id"]).issubset(set(range(c.N_USERS - c.N_COLD_USERS, c.N_USERS)))
