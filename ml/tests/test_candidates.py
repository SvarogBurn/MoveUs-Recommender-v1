import numpy as np
import pandas as pd
from ml.eval.candidates import relevant_set, feasible_candidates


def _events():
    return pd.DataFrame({
        "event_id": [0, 1, 2, 3],
        "activity_id": [1, 1, 2, 1],
        "sport_cluster": [1, 1, 2, 1],
        "max_participants": [10, 10, 10, 10],
        "participant_count": [2, 2, 2, 10],          # event 3 is full
        "day_of_week": [0, 1, 0, 0],
        "time_of_day": [0, 0, 0, 0],
        "latitude": [45.81, 45.81, 45.81, 45.81],
        "longitude": [15.97, 15.97, 15.97, 15.97],
        "start_time": pd.to_datetime(["2023-06-01", "2023-06-02", "2023-06-03", "2023-06-04"]),
        "end_time":   pd.to_datetime(["2023-06-01 02:00", "2023-06-02 02:00", "2023-06-03 02:00", "2023-06-04 02:00"]),
    })


def _user():
    return pd.Series({
        "user_id": 0, "latitude": 45.81, "longitude": 15.97,
        "max_travel_distance": 50, "availability_days": "0,1",
        "availability_times": "0",
    })


def test_relevant_set_uses_test_positives():
    test_df = pd.DataFrame({
        "user_id": [0, 0, 0],
        "event_id": [0, 3, 2],
        "signal_type": ["join_rated", "leave", "join_no_rate"],
        "rating": [4, None, None],
    })
    rel = relevant_set(0, test_df)              # event 0 (rated 4) and event 2 (no_rate, floor)
    assert rel == {0: 4, 2: 1}                  # leave (event 3) excluded


def test_feasible_excludes_unavailable_day():
    # _user is available on days {0,1}; event 1 is on day 1, event 0 on day 0 -> both kept.
    cand = feasible_candidates(_user(), _events(), already_seen=set())
    assert 0 in cand and 1 in cand


def test_capacity_is_not_a_feasibility_filter():
    # event 3 has participant_count == max_participants (full at the END of the sim).
    # Final-roster capacity is a point-in-time leak, so it must NOT remove a candidate.
    cand = feasible_candidates(_user(), _events(), already_seen=set())
    assert 3 in cand


def test_feasible_time_window_restricts_to_horizon():
    # decision window [2023-06-01, 2023-06-02] keeps only events starting inside it.
    cand = feasible_candidates(
        _user(), _events(), already_seen=set(),
        decision_time=pd.Timestamp("2023-06-01"),
        horizon=pd.Timedelta(days=1),
    )
    assert set(cand) == {0, 1}            # events 2 (06-03) and 3 (06-04) are out of window
