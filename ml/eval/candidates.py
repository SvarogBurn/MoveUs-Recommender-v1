"""Per-user relevant set and feasible full-catalog candidate set for the test window."""
import numpy as np
import pandas as pd


def _haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = (np.sin(dlat / 2) ** 2
         + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2) ** 2)
    return R * 2 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def relevant_set(user_id: int, test_df: pd.DataFrame) -> dict:
    """event_id -> graded relevance for a user's positive test-window interactions.

    join_rated -> rating; join_no_rate -> 1 (floor); leave -> excluded.
    """
    rows = test_df[test_df["user_id"] == user_id]
    rel = {}
    for r in rows.itertuples(index=False):
        if r.signal_type == "leave":
            continue
        if r.signal_type == "join_rated":
            rel[int(r.event_id)] = int(r.rating)
        else:  # join_no_rate
            rel[int(r.event_id)] = 1
    return rel


def feasible_candidates(user: pd.Series, events: pd.DataFrame,
                        already_seen: set,
                        decision_time: pd.Timestamp = None,
                        horizon: pd.Timedelta = None) -> np.ndarray:
    """Events that pass the hard feasibility filter for this user.

    Static feasibility: availability (day/time), travel distance, and not
    already attended. Capacity is intentionally NOT a filter: ``participant_count``
    is the final roster size, so using it at decision time would leak the future.

    When ``decision_time`` and ``horizon`` are given, candidates are restricted to
    events starting in ``[decision_time, decision_time + horizon]`` — the set of
    upcoming events competing for the user's attention at that moment.
    """
    days = set(int(x) for x in str(user["availability_days"]).split(","))
    times = set(int(x) for x in str(user["availability_times"]).split(","))
    max_km = max(float(user["max_travel_distance"]), 1.0)

    dist = _haversine_km(float(user["latitude"]), float(user["longitude"]),
                         events["latitude"].values, events["longitude"].values)
    ok = (
        events["day_of_week"].isin(days).values
        & events["time_of_day"].isin(times).values
        & (dist <= max_km)
        & (~events["event_id"].isin(already_seen).values)
    )
    if decision_time is not None and horizon is not None:
        starts = events["start_time"].values
        lo = np.datetime64(decision_time)
        hi = np.datetime64(decision_time + horizon)
        ok = ok & (starts >= lo) & (starts <= hi)
    return events.loc[ok, "event_id"].values.astype(int)
