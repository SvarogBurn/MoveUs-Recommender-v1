import numpy as np
import pandas as pd
from ml.gen.timeline import run_timeline
from ml.gen.splits import finalize_events, ensure_min_joins, build_splits
from ml.gen.io import write_all


def test_write_all_produces_expected_files(small, tmp_path, monkeypatch):
    import ml.gen.io as io
    monkeypatch.setattr(io, "DATA_DIR", tmp_path)
    rng = np.random.default_rng(11)
    users, events, interactions, state = run_timeline(rng)
    write_all(users, events, interactions, state)
    for fn in ["users.csv", "events.csv", "follows.csv", "likes.csv",
               "interactions.csv", "train.csv", "test.csv",
               "train_implicit.csv", "cold_start_users.csv"]:
        assert (tmp_path / fn).exists(), fn
    ev = pd.read_csv(tmp_path / "events.csv")
    assert "end_time" in ev.columns and "participant_count" in ev.columns
    assert "f1" not in ev.columns
    follows = pd.read_csv(tmp_path / "follows.csv")
    assert {"follower_id", "following_id", "time_created"}.issubset(follows.columns)
