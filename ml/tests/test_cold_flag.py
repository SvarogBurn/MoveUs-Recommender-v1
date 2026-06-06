import numpy as np
from ml.gen import config as c
from ml.gen.users import generate_users


def test_is_cold_user_flag(small, rng):
    df = generate_users(rng)
    assert "is_cold_user" in df.columns
    cold = df[df["is_cold_user"]]["user_id"].tolist()
    assert set(cold) == set(range(c.N_USERS - c.N_COLD_USERS, c.N_USERS))
