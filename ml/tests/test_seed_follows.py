import numpy as np
from ml.gen import config as c
from ml.gen.users import generate_users
from ml.gen.social_state import SocialState, seed_follows


def test_seed_covers_small_fraction_including_cold(small, rng):
    users = generate_users(rng)
    s = SocialState(n_users=len(users))
    seed_follows(s, users, rng)
    followers = {f[0] for f in s.follow_rows}
    frac = len(followers) / len(users)
    assert 0.05 < frac < 0.30                      # ~10-15% seeded
    cold_start = c.N_USERS - c.N_COLD_USERS
    cold_followers = {u for u in followers if u >= cold_start}
    assert len(cold_followers) > 0                  # some cold users seeded
