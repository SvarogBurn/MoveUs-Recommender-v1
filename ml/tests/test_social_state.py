from datetime import datetime, timedelta
from ml.gen.social_state import SocialState


def test_booked_interval_conflict():
    s = SocialState(n_users=10)
    t0 = datetime(2023, 1, 1, 10)
    s.book(user=1, start=t0, end=t0 + timedelta(hours=2))
    assert s.is_busy(1, t0 + timedelta(hours=1), t0 + timedelta(hours=3))   # overlaps
    assert not s.is_busy(1, t0 + timedelta(hours=2), t0 + timedelta(hours=3))  # back-to-back ok
    assert not s.is_busy(2, t0, t0 + timedelta(hours=1))                    # other user free


def test_follow_seed_and_time_gate():
    s = SocialState(n_users=10)
    t_seed = datetime(2023, 1, 1)
    s.add_follow(0, 1, time_created=t_seed)
    # known as of a later time, not before
    assert s.follows(0, 1, as_of=t_seed + timedelta(days=1))
    assert not s.follows(0, 1, as_of=t_seed - timedelta(days=1))


def test_history_snapshot_is_prior_only():
    s = SocialState(n_users=10)
    s.record_rating(user=0, activity=5, cluster=1, rating=4)
    snap1 = s.history_snapshot(user=0, activity=5, cluster=1)
    assert snap1["total_joins"] == 1
    assert snap1["avg_rating"] == 4.0
    # snapshot reflects state BEFORE the next record
    s.record_rating(user=0, activity=5, cluster=1, rating=0)
    snap2 = s.history_snapshot(user=0, activity=5, cluster=1)
    assert snap2["total_joins"] == 2
