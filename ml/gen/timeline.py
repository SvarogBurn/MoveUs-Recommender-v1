"""Chronological event-timeline sweep."""
import numpy as np
import pandas as pd

from ml.gen import config as c
from ml.gen.users import generate_users
from ml.gen.events import generate_events
from ml.gen.social_state import SocialState, seed_follows
from ml.gen.calibrate import calibrate_propensity
from ml.gen.enrollment import run_enrollment, resolve_event, build_candidate_index


def run_timeline(rng):
    users = generate_users(rng)
    events = generate_events(rng, users).sort_values("start_time").reset_index(drop=True)
    state = SocialState(n_users=len(users))
    seed_follows(state, users, rng)
    base = calibrate_propensity(users, events)

    # Precompute the activity/cluster -> candidate index and per-user numeric
    # arrays once; reused across every event (hot-path optimisation).
    cand_index = build_candidate_index(users)

    rows = []
    for _, ev in events.iterrows():
        roster = run_enrollment(ev, users, state, base, rng, cand_index=cand_index)
        rows += resolve_event(ev, roster, users, state, rng)

    interactions = pd.DataFrame(rows).sort_values("timestamp").reset_index(drop=True)
    return users, events, interactions, state


def main():
    import argparse
    from ml.gen.io import write_all
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default=None, help="Output directory (default: ml/data)")
    parser.add_argument("--seed", type=int, default=c.SEED)
    args = parser.parse_args()
    rng = np.random.default_rng(args.seed)
    users, events, interactions, state = run_timeline(rng)
    write_all(users, events, interactions, state, out_dir=args.out_dir)


if __name__ == "__main__":
    main()
