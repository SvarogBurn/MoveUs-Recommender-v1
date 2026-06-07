import numpy as np
from ml.gen.timeline import run_timeline
from ml.gen.splits import finalize_events


def test_finalize_events_emergent_fields(small):
    rng = np.random.default_rng(3)
    users, events, interactions, state = run_timeline(rng)
    events2 = finalize_events(events, interactions)
    for col in ["participant_count", "fill_rate", "social_density_cat", "avg_organizer_rating"]:
        assert col in events2.columns
    assert (events2["participant_count"] >= 0).all()
