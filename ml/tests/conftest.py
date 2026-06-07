import numpy as np
import pytest


@pytest.fixture
def rng():
    return np.random.default_rng(42)


@pytest.fixture
def small(monkeypatch):
    """Shrink scale so tests run fast and deterministically."""
    from ml.gen import config as c
    monkeypatch.setattr(c, "N_USERS", 400)
    monkeypatch.setattr(c, "N_EVENTS", 200)
    monkeypatch.setattr(c, "N_COLD_USERS", 40)
    return c
