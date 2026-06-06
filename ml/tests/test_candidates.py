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


def test_feasible_filters_full_and_unavailable():
    cand = feasible_candidates(_user(), _events(), already_seen=set())
    # event 3 is full -> excluded; event 2 is on an available day/time but different activity is allowed
    assert 3 not in cand
    assert 0 in cand and 1 in cand
