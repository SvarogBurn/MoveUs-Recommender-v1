"""Chronological event-timeline sweep."""
import numpy as np
import pandas as pd

from ml.gen import config as c
from ml.gen.users import generate_users
from ml.gen.events import generate_events
from ml.gen.social_state import SocialState, seed_follows
from ml.gen.calibrate import calibrate_propensity
from ml.gen.enrollment import run_enrollment, resolve_event


def run_timeline(rng):
    users = generate_users(rng)
    events = generate_events(rng, users).sort_values("start_time").reset_index(drop=True)
    state = SocialState(n_users=len(users))
    seed_follows(state, users, rng)
    base = calibrate_propensity(users, events)

    rows = []
    for _, ev in events.iterrows():
        roster = run_enrollment(ev, users, state, base, rng)
        rows += resolve_event(ev, roster, users, state, rng)

    interactions = pd.DataFrame(rows).sort_values("timestamp").reset_index(drop=True)
    return users, events, interactions, state


def main():
    from ml.gen.io import write_all
    rng = np.random.default_rng(c.SEED)
    users, events, interactions, state = run_timeline(rng)
    write_all(users, events, interactions, state)
