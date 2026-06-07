"""CSV output."""
from pathlib import Path

import pandas as pd

from ml.gen import config as c
from ml.gen.splits import finalize_events

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def write_all(users, events, interactions, state, out_dir=None):
    out = Path(out_dir) if out_dir else DATA_DIR
    out.mkdir(parents=True, exist_ok=True)
    events = finalize_events(events, interactions)

    users.to_csv(out / "users.csv", index=False)
    events.to_csv(out / "events.csv", index=False)
    interactions.to_csv(out / "interactions.csv", index=False)

    follows = pd.DataFrame(state.follow_rows, columns=["follower_id", "following_id", "time_created"])
    follows.to_csv(out / "follows.csv", index=False)
    likes = pd.DataFrame(state.like_rows, columns=["liker_id", "liked_id", "event_id", "time_created"])
    likes.to_csv(out / "likes.csv", index=False)
