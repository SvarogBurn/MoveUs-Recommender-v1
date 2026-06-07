import numpy as np
import pandas as pd
from ml.gen import config as c
from ml.gen.users import generate_users
from ml.gen.events import generate_events


def test_events_have_end_after_start(small, rng):
    users = generate_users(rng)
    ev = generate_events(rng, users)
    assert len(ev) == c.N_EVENTS
    delta_h = (pd.to_datetime(ev["end_time"]) - pd.to_datetime(ev["start_time"])).dt.total_seconds() / 3600
    assert np.allclose(delta_h.values, ev["duration_hours"].values, atol=1e-6)
    assert (delta_h > 0).all()


def test_no_prebaked_attendance_columns(small, rng):
    users = generate_users(rng)
    ev = generate_events(rng, users)
    for col in ["fill_rate", "participant_count", "social_density_cat",
                "avg_organizer_rating", "f1", "f8"]:
        assert col not in ev.columns


def test_organizers_are_host_eligible(small, rng):
    users = generate_users(rng)
    ev = generate_events(rng, users)
    elig = set(users.loc[users["host_eligible"], "user_id"].tolist())
    assert set(ev["organizer_id"].tolist()).issubset(elig)
