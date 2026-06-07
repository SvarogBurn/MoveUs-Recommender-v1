import numpy as np
import pandas as pd

from ml.models._sampling import user_feasible_events


def _users():
    return pd.DataFrame({
        "user_id": [0, 1], "is_cold_user": [False, False],
        "latitude": [45.81, 45.81], "longitude": [15.97, 15.97],
        "max_travel_distance": [50, 1],          # user 1 cannot travel
        "availability_days": ["0", "0"], "availability_times": ["0", "0"],
    })


def _events():
    return pd.DataFrame({
        "event_id":      [10, 11, 12],
        "day_of_week":   [0, 5, 0],              # event 11 is on an unavailable day
        "time_of_day":   [0, 0, 0],
        "max_participants": [10, 10, 10], "participant_count": [1, 1, 1],
        "latitude":      [45.81, 45.81, 45.90],  # event 12 is ~10km away
        "longitude":     [15.97, 15.97, 15.97],
        "start_time": pd.to_datetime(["2023-09-01", "2023-09-02", "2023-09-03"]),
    })


def test_feasible_events_respect_availability_and_distance():
    feas = user_feasible_events(_users(), _events(), [0, 1])
    assert set(feas[0]) == {10, 12}              # day-5 event excluded; far event ok (50km)
    assert set(feas[1]) == {10}                  # user 1: far event excluded by 1km radius


def test_unknown_user_gets_empty_array():
    feas = user_feasible_events(_users(), _events(), [99])
    assert feas[99].size == 0
