#!/usr/bin/env python3
"""
Feature engineering pipeline for MoveUs recommender — v3.

User vector  : 97 dims  (prefs×13 + demo×2 + history×4
                          + act_affinity×31 + participation_groups×4 + implicit_join_norm×1
                          + pref_act_questionnaire×31 + avail_day×7 + avail_time×4)
Event vector : 57 dims  (unchanged from v2)
Pairwise     : 20 features

Changes from v2:
  - Removed Big Five personality × sport cluster cross-products (were 5 pairwise features)
  - Removed EFA step and personality dims from user vector (65→55 dims)
  - distance_km → distance_sigmoid (steep sigmoid at user's max_travel_distance)
  - Added no_show_rate, co_attendee_affinity, liked_attendee_count
  - avg_organizer_rating now standalone (was part of a cross-product)

Inputs  (ml/data/): users.csv, events.csv, train.csv, test.csv,
                    cold_start_users.csv, train_implicit.csv
Outputs (ml/data/):
  X_train.npy / y_train.npy
  X_test.npy  / y_test.npy
  X_cold.npy  / y_cold.npy
  user_vectors.npy   shape (N_USERS, 55)
  event_vectors.npy  shape (N_EVENTS, 57)
  scaler_pairwise.pkl
  feature_names.json
  train/test/cold _user_ids.npy, _event_ids.npy, _ratings.npy
  train_implicit_uids.npy, train_implicit_eids.npy, train_implicit_weights.npy

Run:  python ml/features.py
"""

import json
import pickle
import warnings
from pathlib import Path
from typing import NamedTuple

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent / "data"

N_ACTIVITIES = 31
N_CLUSTERS   = 8

ACTIVITY_CLUSTER: dict[int, int] = {
    0: 1, 1: 1, 2: 0, 3: 2, 4: 6, 5: 5, 6: 2, 7: 0, 8: 0, 9: 1,
    10: 4, 11: 3, 12: 0, 13: 6, 14: 5, 15: 0, 16: 2, 17: 0, 18: 7,
    19: 4, 20: 5, 21: 0, 22: 7, 23: 3, 24: 3, 25: 3, 26: 7, 27: 7,
    28: 0, 29: 1, 30: 5,
}

PREF_FIELDS = [
    "preferred_session_duration", "organizing_openness", "leadership_inclination",
    "max_travel_distance", "weekly_activity_target", "pushes_through_discomfort",
    "preferred_group_size", "acquaintance_preference", "enjoys_meeting_new_people",
    "activity_vs_social", "motivated_by_competition", "planning_horizon",
    "feels_like_burden",
]

PREF_NULL_DEFAULTS: dict[str, float] = {
    "preferred_session_duration": 60.0,
    "organizing_openness":        1.0,
    "leadership_inclination":     3.0,
    "max_travel_distance":        15.0,
    "weekly_activity_target":     2.0,
    "pushes_through_discomfort":  3.0,
    "preferred_group_size":       5.0,
    "acquaintance_preference":    2.0,
    "enjoys_meeting_new_people":  3.0,
    "activity_vs_social":         3.0,
    "motivated_by_competition":   3.0,
    "planning_horizon":           3.0,
    "feels_like_burden":          2.0,
}

PAIRWISE_FEATURE_NAMES = [
    # Contextual (7)
    "activity_in_preferred",
    "skill_delta",
    "distance_sigmoid",
    "duration_delta_min",
    "group_size_delta",
    "day_match",
    "time_of_day_match",
    # Social signals (2)
    "organizer_is_followed",
    "mutual_follows_attending",
    # History — explicit (3)
    "user_join_rate_this_activity",
    "user_avg_rating_this_cluster",
    "user_activity_frequency",
    # Group composition (3)
    "group_size_match",
    "participation_group_category_match",
    "skill_diversity",
    # Quality (1)
    "avg_organizer_rating",
    # Implicit / people signals (4)
    "implicit_join_rate_this_activity",
    "no_show_rate",
    "co_attendee_affinity",
    "liked_attendee_count",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def haversine_km(lat1: np.ndarray, lon1: np.ndarray,
                 lat2: np.ndarray, lon2: np.ndarray) -> np.ndarray:
    R = 6_371.0
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = (np.sin(dlat / 2) ** 2
         + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2))
         * np.sin(dlon / 2) ** 2)
    return R * 2 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def sigmoid_distance(dist_km: np.ndarray, max_travel_km: np.ndarray,
                     steepness: float = 8.0) -> np.ndarray:
    """~1.0 near home, ~0.0 beyond max_travel. Inflection at max_travel_km."""
    return 1.0 / (1.0 + np.exp(
        steepness * (dist_km - max_travel_km) / np.maximum(max_travel_km, 1.0)
    ))


def _impute_prefs(users_df: pd.DataFrame) -> pd.DataFrame:
    df = users_df.copy()
    for col, default in PREF_NULL_DEFAULTS.items():
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(default)
    return df


# ── History aggregates ────────────────────────────────────────────────────────

def _build_history(
    train_df: pd.DataFrame, n_users: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    rated = train_df[train_df["signal_type"] == "join_rated"]
    total_joins = np.zeros(n_users, float)
    avg_rating  = np.zeros(n_users, float)

    agg = rated.groupby("user_id").agg(cnt=("rating", "count"), mean_r=("rating", "mean")).reset_index()
    for row in agg.itertuples(index=False):
        uid = int(row.user_id)
        if uid < n_users:
            total_joins[uid] = row.cnt
            avg_rating[uid]  = row.mean_r

    cutoff   = train_df["timestamp"].max() - pd.Timedelta(days=30)
    recent   = (rated[rated["timestamp"] >= cutoff]
                .groupby("user_id").size().reset_index(name="rc"))
    join_30d = np.zeros(n_users, float)
    for row in recent.itertuples(index=False):
        uid = int(row.user_id)
        if uid < n_users:
            join_30d[uid] = row.rc / 30.0

    days_span = max((train_df["timestamp"].max() - train_df["timestamp"].min()).days, 1)
    act_freq  = total_joins / days_span
    return total_joins, avg_rating, join_30d, act_freq


def _build_implicit_history(
    train_implicit_df: pd.DataFrame, n_users: int
) -> tuple[np.ndarray, np.ndarray]:
    implicit_joins = np.zeros(n_users, float)
    agg = train_implicit_df.groupby("user_id").size().reset_index(name="cnt")
    for row in agg.itertuples(index=False):
        uid = int(row.user_id)
        if uid < n_users:
            implicit_joins[uid] = row.cnt
    max_val = max(implicit_joins.max(), 1.0)
    return implicit_joins, implicit_joins / max_val


def _build_act_affinity(
    train_df: pd.DataFrame, events_df: pd.DataFrame, n_users: int
) -> np.ndarray:
    rated = train_df[train_df["signal_type"] == "join_rated"]
    merged = rated.merge(events_df[["event_id", "activity_id"]], on="event_id")
    mat = np.zeros((n_users, N_ACTIVITIES), float)
    agg = merged.groupby(["user_id", "activity_id"])["rating"].mean().reset_index()
    for row in agg.itertuples(index=False):
        uid = int(row.user_id)
        if uid < n_users:
            mat[uid, row.activity_id] = row.rating
    return mat


def _build_cluster_affinity(
    train_df: pd.DataFrame, events_df: pd.DataFrame, n_users: int
) -> np.ndarray:
    rated = train_df[train_df["signal_type"] == "join_rated"]
    merged = rated.merge(events_df[["event_id", "sport_cluster"]], on="event_id")
    mat = np.zeros((n_users, N_CLUSTERS), float)
    agg = merged.groupby(["user_id", "sport_cluster"])["rating"].mean().reset_index()
    for row in agg.itertuples(index=False):
        uid = int(row.user_id)
        if uid < n_users:
            mat[uid, row.sport_cluster] = row.rating
    return mat


def _build_act_join_rate(
    train_df: pd.DataFrame, events_df: pd.DataFrame, n_users: int
) -> np.ndarray:
    rated = train_df[train_df["signal_type"] == "join_rated"]
    merged = rated.merge(events_df[["event_id", "activity_id"]], on="event_id")
    n_per_act = events_df.groupby("activity_id").size().to_dict()
    mat = np.zeros((n_users, N_ACTIVITIES), float)
    agg = merged.groupby(["user_id", "activity_id"]).size().reset_index(name="cnt")
    for row in agg.itertuples(index=False):
        uid = int(row.user_id)
        if uid < n_users:
            mat[uid, row.activity_id] = row.cnt / max(n_per_act.get(row.activity_id, 1), 1)
    return mat


def _build_implicit_act_join_rate(
    train_implicit_df: pd.DataFrame, events_df: pd.DataFrame, n_users: int
) -> np.ndarray:
    merged = train_implicit_df.merge(events_df[["event_id", "activity_id"]], on="event_id")
    n_per_act = events_df.groupby("activity_id").size().to_dict()
    mat = np.zeros((n_users, N_ACTIVITIES), float)
    agg = merged.groupby(["user_id", "activity_id"]).size().reset_index(name="cnt")
    for row in agg.itertuples(index=False):
        uid = int(row.user_id)
        if uid < n_users:
            mat[uid, row.activity_id] = row.cnt / max(n_per_act.get(row.activity_id, 1), 1)
    return mat


def _build_no_show_rate(train_df: pd.DataFrame, n_users: int) -> np.ndarray:
    """Fraction of interactions that were 'leave' signals per user."""
    total  = np.zeros(n_users, float)
    leaves = np.zeros(n_users, float)
    for uid in train_df["user_id"].values:
        u = int(uid)
        if u < n_users:
            total[u] += 1
    for uid in train_df[train_df["signal_type"] == "leave"]["user_id"].values:
        u = int(uid)
        if u < n_users:
            leaves[u] += 1
    return np.where(total > 0, leaves / total, 0.0)


def _build_coattendee_data(
    train_df: pd.DataFrame,
) -> tuple[dict[int, set[int]], dict[int, set[int]]]:
    """
    Returns:
      event_attendees[eid]      = set of uids who attended (positive signal only)
      coattendees_by_user[uid]  = set of uids who co-attended any event with uid
    """
    positive = train_df[train_df["signal_type"] != "leave"]

    event_attendees: dict[int, set[int]] = {}
    for uid, eid in zip(positive["user_id"].values, positive["event_id"].values):
        event_attendees.setdefault(int(eid), set()).add(int(uid))

    coattendees_by_user: dict[int, set[int]] = {}
    for eid, attendees in event_attendees.items():
        for uid in attendees:
            coattendees_by_user.setdefault(uid, set()).update(attendees - {uid})

    return event_attendees, coattendees_by_user


def _build_pref_matrices(users_df: pd.DataFrame) -> tuple[
    np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray
]:
    n = len(users_df)
    pref_act_mat        = np.zeros((n, N_ACTIVITIES), float)
    pref_skill_mat      = np.full((n, N_ACTIVITIES), -1, int)
    avail_day_mat       = np.zeros((n, 7), float)
    avail_time_mat      = np.zeros((n, 4), float)
    participation_mat   = np.zeros((n, 4), float)
    default_skill       = np.clip(users_df["pushes_through_discomfort"].values.astype(int) // 2, 0, 3)

    for _, u in users_df.iterrows():
        uid  = int(u["user_id"])
        acts = list(map(int, str(u["preferred_activities"]).split(",")))
        skls = list(map(int, str(u["preferred_skills"]).split(",")))
        for a, s in zip(acts, skls):
            pref_act_mat[uid, a]   = 1.0
            pref_skill_mat[uid, a] = s
        for d in map(int, str(u["availability_days"]).split(",")):
            avail_day_mat[uid, d] = 1.0
        for t in map(int, str(u["availability_times"]).split(",")):
            avail_time_mat[uid, t] = 1.0
        pg_str = str(u.get("participation_groups", "2"))
        for g in map(int, pg_str.split(",")):
            if 0 <= g < 4:
                participation_mat[uid, g] = 1.0

    return (pref_act_mat, pref_skill_mat, default_skill,
            avail_day_mat, avail_time_mat, participation_mat)


# ── FeatureMatrices container ─────────────────────────────────────────────────

class FeatureMatrices(NamedTuple):
    users_df:            pd.DataFrame
    events_df:           pd.DataFrame
    pref_act_mat:        np.ndarray
    pref_skill_mat:      np.ndarray
    default_skill:       np.ndarray
    avail_day_mat:       np.ndarray
    avail_time_mat:      np.ndarray
    participation_mat:   np.ndarray
    act_join_rate:       np.ndarray
    implicit_join_rate:  np.ndarray
    cluster_affinity:    np.ndarray
    act_frequency:       np.ndarray
    implicit_join_norm:  np.ndarray
    no_show_rate:        np.ndarray        # (n_users,)
    event_attendees:     dict              # eid → set[uid]
    coattendees_by_user: dict              # uid → set[uid]
    scaler:              StandardScaler


# ── Pairwise features (20) ────────────────────────────────────────────────────

def build_pairwise(
    interactions: pd.DataFrame,
    fm: "FeatureMatrices",
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Build (N, 20) pairwise feature matrix for all signal types.
    Returns (X_raw, y, w).
    """
    df = interactions.copy()
    if len(df) == 0:
        empty = np.empty((0, len(PAIRWISE_FEATURE_NAMES)))
        return empty, np.empty(0, dtype=int), np.empty(0, dtype=float)

    y_pseudo = np.where(
        df["signal_type"] == "join_rated",
        df["rating"].fillna(0).astype(int),
        np.where(df["signal_type"] == "join_no_rate", 2, 0),
    ).astype(int)
    w_pseudo = df["signal_weight"].abs().values.astype(float)

    uids = df["user_id"].values.astype(int)
    eids = df["event_id"].values.astype(int)

    ev = fm.events_df.sort_values("event_id")
    e_act     = ev["activity_id"].values.astype(int)
    e_cluster = ev["sport_cluster"].values.astype(int)
    e_skill   = ev["skill_level"].values.astype(int)
    e_maxpart = ev["max_participants"].values.astype(float)
    e_dur     = ev["duration_hours"].values.astype(float)
    e_day     = ev["day_of_week"].values.astype(int)
    e_time    = ev["time_of_day"].values.astype(int)
    e_lat     = ev["latitude"].values
    e_lng     = ev["longitude"].values
    e_partcnt = ev["participant_count"].values.astype(float)
    e_skdiv   = ev["skill_diversity"].values.astype(float)
    e_soc_cat = ev["social_density_cat"].values.astype(int)
    e_org_rat = ev["avg_organizer_rating"].values.astype(float)

    us = fm.users_df.sort_values("user_id")
    u_lat       = us["latitude"].values
    u_lng       = us["longitude"].values
    u_pref_dur  = us["preferred_session_duration"].values.astype(float)
    u_pref_gs   = us["preferred_group_size"].values.astype(float)
    u_max_travel = us["max_travel_distance"].values.astype(float)

    # ── Contextual ──────────────────────────────────────────────────────────
    f_act_pref = fm.pref_act_mat[uids, e_act[eids]]

    u_skill_for_act = np.where(
        fm.pref_act_mat[uids, e_act[eids]] > 0,
        fm.pref_skill_mat[uids, e_act[eids]],
        fm.default_skill[uids],
    )
    f_skill_delta = e_skill[eids].astype(float) - u_skill_for_act.astype(float)

    raw_dist    = haversine_km(u_lat[uids], u_lng[uids], e_lat[eids], e_lng[eids])
    f_dist      = sigmoid_distance(raw_dist, u_max_travel[uids])
    f_dur_delta = np.abs(e_dur[eids] * 60.0 - u_pref_dur[uids])
    f_gs_delta  = np.abs(e_maxpart[eids] - u_pref_gs[uids])
    f_day_match  = fm.avail_day_mat[uids,  e_day[eids]]
    f_time_match = fm.avail_time_mat[uids, e_time[eids]]

    # ── Social signals ───────────────────────────────────────────────────────
    n = len(df)
    if "organizer_is_followed" in df.columns:
        f_org_followed = df["organizer_is_followed"].values.astype(float)
    else:
        f_org_followed = np.zeros(n, float)
    f_mutual_follows = np.zeros(n, float)

    # ── History — explicit ───────────────────────────────────────────────────
    clust = e_cluster[eids]
    f_join_rate_act  = fm.act_join_rate[uids, e_act[eids]]
    f_avg_rat_clust  = fm.cluster_affinity[uids, clust]
    f_act_freq       = fm.act_frequency[uids]

    # ── Group composition ────────────────────────────────────────────────────
    f_gs_match = np.abs(u_pref_gs[uids] - e_partcnt[eids]) / np.maximum(e_maxpart[eids], 1.0)

    SOC_CAT_TO_PG = {0: {0, 1}, 1: {2}, 2: {3}}
    f_pg_match = np.array([
        1.0 if any(fm.participation_mat[uids[i], g] > 0
                   for g in SOC_CAT_TO_PG.get(int(e_soc_cat[eids[i]]), set()))
        else 0.0
        for i in range(n)
    ], dtype=float)

    f_skill_div = e_skdiv[eids]

    # ── Quality ───────────────────────────────────────────────────────────────
    f_org_rating = e_org_rat[eids]

    # ── Implicit / people signals ─────────────────────────────────────────────
    f_imp_join_act = fm.implicit_join_rate[uids, e_act[eids]]
    f_no_show      = fm.no_show_rate[uids]

    f_co_attendee = np.array([
        len(fm.event_attendees.get(int(eids[i]), set())
            & fm.coattendees_by_user.get(int(uids[i]), set()))
        / max(len(fm.event_attendees.get(int(eids[i]), set())), 1)
        for i in range(n)
    ], dtype=float)

    # liked_attendee_count: synthetic data has no like events, default to 0
    f_liked = np.zeros(n, float)

    X = np.column_stack([
        f_act_pref, f_skill_delta, f_dist, f_dur_delta, f_gs_delta,
        f_day_match, f_time_match,
        f_org_followed, f_mutual_follows,
        f_join_rate_act, f_avg_rat_clust, f_act_freq,
        f_gs_match, f_pg_match, f_skill_div,
        f_org_rating,
        f_imp_join_act, f_no_show, f_co_attendee, f_liked,
    ])
    return X, y_pseudo, w_pseudo


def build_pairwise_for_pairs(
    uids: np.ndarray,
    eids: np.ndarray,
    fm: "FeatureMatrices",
) -> np.ndarray:
    """
    Compute 20-dim pairwise feature matrix for arbitrary (uid, eid) pairs.
    Output is SCALED (uses fm.scaler).
    """
    ev = fm.events_df.set_index("event_id")
    us = fm.users_df.set_index("user_id")

    n = len(uids)

    def _ev(col): return ev.loc[eids, col].values
    def _us(col): return us.loc[uids, col].values

    e_act      = _ev("activity_id").astype(int)
    e_cluster  = _ev("sport_cluster").astype(int)
    e_skill    = _ev("skill_level").astype(float)
    e_maxpart  = _ev("max_participants").astype(float)
    e_dur      = _ev("duration_hours").astype(float)
    e_day      = _ev("day_of_week").astype(int)
    e_time     = _ev("time_of_day").astype(int)
    e_lat      = _ev("latitude").astype(float)
    e_lng      = _ev("longitude").astype(float)
    e_partcnt  = _ev("participant_count").astype(float)
    e_skdiv    = _ev("skill_diversity").astype(float)
    e_soc_cat  = _ev("social_density_cat").astype(int)
    e_org_rat  = _ev("avg_organizer_rating").astype(float)

    u_lat        = _us("latitude").astype(float)
    u_lng        = _us("longitude").astype(float)
    u_pref_dur   = _us("preferred_session_duration").astype(float)
    u_pref_gs    = _us("preferred_group_size").astype(float)
    u_max_travel = _us("max_travel_distance").astype(float)

    f_act_pref = fm.pref_act_mat[uids, e_act]
    u_skill_for_act = np.where(
        fm.pref_act_mat[uids, e_act] > 0,
        fm.pref_skill_mat[uids, e_act],
        fm.default_skill[uids],
    )
    f_skill_delta = e_skill - u_skill_for_act.astype(float)
    raw_dist      = haversine_km(u_lat, u_lng, e_lat, e_lng)
    f_dist        = sigmoid_distance(raw_dist, u_max_travel)
    f_dur_delta   = np.abs(e_dur * 60.0 - u_pref_dur)
    f_gs_delta    = np.abs(e_maxpart - u_pref_gs)
    f_day_match   = fm.avail_day_mat[uids, e_day]
    f_time_match  = fm.avail_time_mat[uids, e_time]

    f_org_followed   = np.zeros(n, float)
    f_mutual_follows = np.zeros(n, float)

    clust = e_cluster
    f_join_rate_act = fm.act_join_rate[uids, e_act]
    f_avg_rat_clust = fm.cluster_affinity[uids, clust]
    f_act_freq      = fm.act_frequency[uids]

    f_gs_match = np.abs(u_pref_gs - e_partcnt) / np.maximum(e_maxpart, 1.0)

    SOC_CAT_TO_PG = {0: {0, 1}, 1: {2}, 2: {3}}
    f_pg_match = np.array([
        1.0 if any(fm.participation_mat[uids[i], g] > 0
                   for g in SOC_CAT_TO_PG.get(int(e_soc_cat[i]), set()))
        else 0.0
        for i in range(n)
    ], dtype=float)

    f_skill_div  = e_skdiv
    f_org_rating = e_org_rat
    f_imp_join   = fm.implicit_join_rate[uids, e_act]
    f_no_show    = fm.no_show_rate[uids]

    f_co_attendee = np.array([
        len(fm.event_attendees.get(int(eids[i]), set())
            & fm.coattendees_by_user.get(int(uids[i]), set()))
        / max(len(fm.event_attendees.get(int(eids[i]), set())), 1)
        for i in range(n)
    ], dtype=float)

    f_liked = np.zeros(n, float)

    X_raw = np.column_stack([
        f_act_pref, f_skill_delta, f_dist, f_dur_delta, f_gs_delta,
        f_day_match, f_time_match,
        f_org_followed, f_mutual_follows,
        f_join_rate_act, f_avg_rat_clust, f_act_freq,
        f_gs_match, f_pg_match, f_skill_div,
        f_org_rating,
        f_imp_join, f_no_show, f_co_attendee, f_liked,
    ])
    return fm.scaler.transform(X_raw)


# ── User feature vectors (97 dims) ────────────────────────────────────────────

def build_user_vectors(
    users_df: pd.DataFrame,
    total_joins: np.ndarray,
    avg_rating: np.ndarray,
    join_30d: np.ndarray,
    act_freq: np.ndarray,
    act_affinity: np.ndarray,
    participation_mat: np.ndarray,
    implicit_join_norm: np.ndarray,
    pref_act_mat: np.ndarray,    # (n_users, 31) — questionnaire preferred activities
    avail_day_mat: np.ndarray,   # (n_users, 7)  — questionnaire day availability
    avail_time_mat: np.ndarray,  # (n_users, 4)  — questionnaire time availability
) -> tuple[np.ndarray, list[str]]:
    names: list[str] = []
    names += PREF_FIELDS
    pref_mat = users_df[PREF_FIELDS].values.astype(float)
    dem_mat = users_df[["age", "gender"]].values.astype(float)
    names += ["age", "gender"]
    names += ["total_joins", "avg_rating", "join_rate_last_30d", "user_activity_frequency"]
    names += [f"act_affinity_{a}" for a in range(N_ACTIVITIES)]
    names += ["pg_solo", "pg_pair", "pg_small_group", "pg_large_group"]
    names += ["implicit_join_norm"]
    names += [f"pref_act_{a}" for a in range(N_ACTIVITIES)]
    names += [f"avail_day_{d}" for d in range(7)]
    names += [f"avail_time_{t}" for t in range(4)]

    vecs = np.hstack([
        pref_mat,
        dem_mat,
        total_joins.reshape(-1, 1),
        avg_rating.reshape(-1, 1),
        join_30d.reshape(-1, 1),
        act_freq.reshape(-1, 1),
        act_affinity,
        participation_mat,
        implicit_join_norm.reshape(-1, 1),
        pref_act_mat,
        avail_day_mat,
        avail_time_mat,
    ])
    assert vecs.shape[1] == 97, f"Expected 97 user dims, got {vecs.shape[1]}"
    return vecs, names


# ── Event feature vectors (57 dims, unchanged) ────────────────────────────────

def build_event_vectors(events_df: pd.DataFrame) -> tuple[np.ndarray, list[str]]:
    n = len(events_df)
    names: list[str] = []

    act_oh = np.zeros((n, N_ACTIVITIES), float)
    for i, a in enumerate(events_df["activity_id"].values):
        act_oh[i, int(a)] = 1.0
    names += [f"act_{a}" for a in range(N_ACTIVITIES)]

    scalar_cols = ["skill_level", "max_participants", "duration_hours",
                   "fill_rate", "participant_count"]
    names += scalar_cols

    efa_cols = [f"f{j+1}" for j in range(8)]
    names += efa_cols

    clust_oh = np.zeros((n, N_CLUSTERS), float)
    for i, c in enumerate(events_df["sport_cluster"].values):
        clust_oh[i, int(c)] = 1.0
    names += [f"cluster_{c}" for c in range(N_CLUSTERS)]

    names += ["day_of_week", "time_of_day"]
    names += ["skill_diversity", "social_density_cat", "avg_organizer_rating"]

    vecs = np.hstack([
        act_oh,
        events_df[scalar_cols].values.astype(float),
        events_df[efa_cols].values.astype(float),
        clust_oh,
        events_df[["day_of_week", "time_of_day"]].values.astype(float),
        events_df[["skill_diversity", "social_density_cat", "avg_organizer_rating"]].values.astype(float),
    ])
    assert vecs.shape[1] == 57, f"Expected 57 event dims, got {vecs.shape[1]}"
    return vecs, names


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("[1/7] Loading CSVs ...")
    users_df     = pd.read_csv(DATA_DIR / "users.csv")
    events_df    = pd.read_csv(DATA_DIR / "events.csv")
    train_df     = pd.read_csv(DATA_DIR / "train.csv",             parse_dates=["timestamp"])
    test_df      = pd.read_csv(DATA_DIR / "test.csv",              parse_dates=["timestamp"])
    cold_df      = pd.read_csv(DATA_DIR / "cold_start_users.csv",  parse_dates=["timestamp"])
    train_imp_df = pd.read_csv(DATA_DIR / "train_implicit.csv",    parse_dates=["timestamp"])
    n_users = len(users_df)
    print(f"      {n_users} users | {len(events_df)} events | "
          f"{len(train_df)} train | {len(test_df)} test | "
          f"{len(cold_df)} cold | {len(train_imp_df)} implicit-train")

    users_df = _impute_prefs(users_df)

    print("[2/7] Aggregating history ...")
    total_joins, avg_rating, join_30d, act_freq = _build_history(train_df, n_users)
    act_affinity     = _build_act_affinity(train_df, events_df, n_users)
    cluster_affinity = _build_cluster_affinity(train_df, events_df, n_users)
    act_join_rate    = _build_act_join_rate(train_df, events_df, n_users)
    impl_raw, impl_norm = _build_implicit_history(train_imp_df, n_users)
    impl_act_rate    = _build_implicit_act_join_rate(train_imp_df, events_df, n_users)
    no_show_rate     = _build_no_show_rate(train_df, n_users)
    warm_count = int((total_joins > 0).sum())
    print(f"      Warm users (>=1 rated train interaction): {warm_count}/{n_users}")

    print("[3/7] Building co-attendee data ...")
    event_attendees, coattendees_by_user = _build_coattendee_data(train_df)
    print(f"      {len(event_attendees)} events with attendee sets; "
          f"{len(coattendees_by_user)} users with co-attendee sets")

    print("[4/7] Building preference and participation matrices ...")
    (pref_act_mat, pref_skill_mat, default_skill,
     avail_day_mat, avail_time_mat, participation_mat) = _build_pref_matrices(users_df)

    print("[5/7] Building user and event feature matrices ...")
    user_vecs, u_names = build_user_vectors(
        users_df, total_joins, avg_rating, join_30d, act_freq,
        act_affinity, participation_mat, impl_norm,
        pref_act_mat, avail_day_mat, avail_time_mat,
    )
    event_vecs, e_names = build_event_vectors(events_df)
    np.save(DATA_DIR / "user_vectors.npy",  user_vecs)
    np.save(DATA_DIR / "event_vectors.npy", event_vecs)
    print(f"      user_vectors.npy   {user_vecs.shape}")
    print(f"      event_vectors.npy  {event_vecs.shape}")

    print("[6/7] Building pairwise feature matrices ...")
    scaler = StandardScaler()

    def _build(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        fm_tmp = FeatureMatrices(
            users_df=users_df, events_df=events_df,
            pref_act_mat=pref_act_mat, pref_skill_mat=pref_skill_mat,
            default_skill=default_skill, avail_day_mat=avail_day_mat,
            avail_time_mat=avail_time_mat, participation_mat=participation_mat,
            act_join_rate=act_join_rate, implicit_join_rate=impl_act_rate,
            cluster_affinity=cluster_affinity, act_frequency=act_freq,
            implicit_join_norm=impl_norm,
            no_show_rate=no_show_rate,
            event_attendees=event_attendees,
            coattendees_by_user=coattendees_by_user,
            scaler=scaler,
        )
        return build_pairwise(df, fm_tmp)

    cold_rated = cold_df[cold_df["signal_type"] == "join_rated"]
    X_train_raw, y_train, w_train = _build(train_df)
    X_test_raw,  y_test,  w_test  = _build(test_df)
    X_cold_raw,  y_cold,  w_cold  = _build(cold_rated)

    X_train_s = scaler.fit_transform(X_train_raw)
    X_test_s  = scaler.transform(X_test_raw)
    X_cold_s  = scaler.transform(X_cold_raw)

    with open(DATA_DIR / "scaler_pairwise.pkl", "wb") as fh:
        pickle.dump(scaler, fh)

    np.save(DATA_DIR / "X_train.npy", X_train_s); np.save(DATA_DIR / "y_train.npy", y_train)
    np.save(DATA_DIR / "X_test.npy",  X_test_s);  np.save(DATA_DIR / "y_test.npy",  y_test)
    np.save(DATA_DIR / "X_cold.npy",  X_cold_s);  np.save(DATA_DIR / "y_cold.npy",  y_cold)
    np.save(DATA_DIR / "train_sample_weights.npy", w_train)
    np.save(DATA_DIR / "train_global_ts_order.npy",
            np.argsort(train_df["timestamp"].values))
    np.save(DATA_DIR / "train_all_user_ids.npy",
            train_df["user_id"].values.astype(int))

    for split, df in [("train", train_df), ("test", test_df), ("cold", cold_rated)]:
        rated = df[df["signal_type"] == "join_rated"]
        np.save(DATA_DIR / f"{split}_user_ids.npy",  rated["user_id"].values.astype(int))
        np.save(DATA_DIR / f"{split}_event_ids.npy", rated["event_id"].values.astype(int))
        np.save(DATA_DIR / f"{split}_ratings.npy",   rated["rating"].values.astype(int))

    np.save(DATA_DIR / "train_implicit_uids.npy",
            train_imp_df["user_id"].values.astype(int))
    np.save(DATA_DIR / "train_implicit_eids.npy",
            train_imp_df["event_id"].values.astype(int))
    np.save(DATA_DIR / "train_implicit_weights.npy",
            train_imp_df["signal_weight"].values.astype(float))

    for split, df, X in [("train", train_df, X_train_s),
                          ("test",  test_df,  X_test_s),
                          ("cold",  cold_rated, X_cold_s)]:
        rated = df[df["signal_type"] == "join_rated"].reset_index(drop=True)
        rated_mask = (df["signal_type"] == "join_rated").values
        rated_idx  = np.where(rated_mask)[0]
        feat = pd.DataFrame(X[rated_idx], columns=PAIRWISE_FEATURE_NAMES)
        meta = rated[["user_id", "event_id", "rating", "label"]].reset_index(drop=True)
        pd.concat([meta, feat], axis=1).to_csv(
            DATA_DIR / f"{split}_features.csv", index=False
        )

    with open(DATA_DIR / "feature_names.json", "w") as fh:
        json.dump({"pairwise": PAIRWISE_FEATURE_NAMES,
                   "user":     u_names,
                   "event":    e_names}, fh, indent=2)

    print(f"\n  Shapes: X_train {X_train_s.shape}  X_test {X_test_s.shape}  "
          f"X_cold {X_cold_s.shape}")

    print("[7/7] Saving FeatureMatrices for LOO evaluation ...")
    fm_final = FeatureMatrices(
        users_df=users_df, events_df=events_df,
        pref_act_mat=pref_act_mat, pref_skill_mat=pref_skill_mat,
        default_skill=default_skill, avail_day_mat=avail_day_mat,
        avail_time_mat=avail_time_mat, participation_mat=participation_mat,
        act_join_rate=act_join_rate, implicit_join_rate=impl_act_rate,
        cluster_affinity=cluster_affinity, act_frequency=act_freq,
        implicit_join_norm=impl_norm,
        no_show_rate=no_show_rate,
        event_attendees=event_attendees,
        coattendees_by_user=coattendees_by_user,
        scaler=scaler,
    )
    with open(DATA_DIR / "feature_matrices.pkl", "wb") as fh:
        pickle.dump(fm_final, fh)

    print(f"\nDone. All files written to {DATA_DIR.resolve()}")


if __name__ == "__main__":
    main()
