"""Production recommender service — loads best model, serves live predictions.

Usage in Django:
    from ml.recommender_service import get_recommender

    service = get_recommender()
    scores = service.score_live(user_orm_obj, list_of_event_orm_objs)
    ranked = sorted(zip(events, scores), key=lambda x: -x[1])
"""

import pickle
from pathlib import Path
from typing import Optional

import numpy as np
import torch


def _haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat, dlon = np.radians(lat2 - lat1), np.radians(lon2 - lon1)
    a = (np.sin(dlat / 2) ** 2
         + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2))
         * np.sin(dlon / 2) ** 2)
    return R * 2 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def _hour_to_tod(hour: int) -> int:
    """Map start hour to TimeOfTheDay enum value (0=MORNING … 3=NIGHT)."""
    if 6 <= hour < 12:
        return 0  # MORNING
    if 12 <= hour < 17:
        return 1  # AFTERNOON
    if 17 <= hour < 22:
        return 2  # EVENING
    return 3  # NIGHT


class RecommenderService:
    """Singleton service: load best trained model once, serve ranked feeds."""

    _instance: Optional["RecommenderService"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.model = None
        self.model_name = None
        self._load_best_model()

    def _load_best_model(self):
        """Load best trained model from ml/models_store/."""
        models_dir = Path(__file__).parent / "models_store"
        best_model_path = models_dir / "best_model.pkl"
        metadata_path = models_dir / "best_model_metadata.txt"

        if not best_model_path.exists():
            print(f"WARNING: No best model found at {best_model_path}")
            print("Run: python -m ml.models.run_benchmark")
            return

        try:
            with open(best_model_path, "rb") as f:
                self.model = pickle.load(f)
            if metadata_path.exists():
                with open(metadata_path) as f:
                    self.model_name = f.read().strip()
            else:
                self.model_name = "unknown"
            print(f"Loaded recommender: {self.model_name}")
        except Exception as e:
            print(f"ERROR loading model: {e}")
            self.model = None

    def score_live(self, user, events: list) -> np.ndarray:
        """Score a Django User against a list of Django Event objects.

        Expects:
          - user.preferences prefetched with .availabilities and
            .preferred_activities (or None if not set).
          - each event prefetched with .location and .activity.

        All live users are cold-start: interaction history defaults to zero.
        Returns np.ndarray of scores (higher = more relevant), len == len(events).
        """
        if self.model is None or not events:
            return np.zeros(len(events))

        try:
            from ml.models.context import ACTIVITY_CLUSTER

            prefs = getattr(user, "preferences", None)

            user_lat = float(user.latitude or 0.0)
            user_lon = float(user.longitude or 0.0)
            max_travel = float((prefs and prefs.max_travel_distance) or 10.0)
            pref_session = float((prefs and prefs.preferred_session_duration) or 60.0)
            pref_group = float((prefs and prefs.preferred_group_size) or 5.0)
            motivated = float((prefs and prefs.motivated_by_competition) or 1.0)

            avail_days: set[int] = set()
            avail_times: set[int] = set()
            if prefs is not None:
                for av in prefs.availabilities.all():
                    avail_days.add(int(av.day_of_week))
                    avail_times.add(int(av.time_of_day))

            pref_acts: set[int] = set()
            if prefs is not None:
                for pa in prefs.preferred_activities.all():
                    pref_acts.add(int(pa.activity_id))
            pref_clusters = {ACTIVITY_CLUSTER.get(a, 0) for a in pref_acts}

            raw_rows = []
            for event in events:
                act_id = int(event.activity_id)
                clu = ACTIVITY_CLUSTER.get(act_id, 0)

                if act_id in pref_acts:
                    act_match = 1.0
                elif pref_clusters and clu in pref_clusters:
                    act_match = 0.6
                else:
                    act_match = 0.1

                ev_lat = float(event.location.latitude)
                ev_lon = float(event.location.longitude)
                dist = _haversine_km(user_lat, user_lon, ev_lat, ev_lon)
                dist_score = float(np.exp(-dist / max(max_travel, 1.0)))

                ev_day = event.start_time.weekday()
                ev_tod = _hour_to_tod(event.start_time.hour)
                avail = float(ev_day in avail_days and ev_tod in avail_times)

                duration_h = (
                    (event.end_time - event.start_time).total_seconds() / 3600.0
                )
                dur_gap = abs(duration_h * 60.0 - pref_session)
                size_gap = abs(float(event.max_participants or 10) - pref_group)
                skill = float(event.skill_level)

                raw_rows.append([
                    act_match, dist_score, avail, dur_gap, size_gap,
                    skill, motivated,
                    0.0, 0.0, 0.0,       # total_joins, avg_rating, no_show
                    0.0, 0.0, 0.0, 0.0,  # act_aff, act_seen, clu_aff, clu_seen
                    0.0,                 # event_pop (new events = 0)
                ])

            raw = np.array(raw_rows, dtype=float)
            scaled = self.model.fc.scaler.transform(raw)
            X = torch.tensor(scaled, dtype=torch.float32)
            with torch.no_grad():
                scores = self.model.model(X).numpy()
            return scores.astype(float)

        except Exception as e:
            print(f"ERROR in score_live: {e}")
            return np.zeros(len(events))

    def is_ready(self) -> bool:
        return self.model is not None

    def reload(self):
        """Reload the best model from disk (after retrain)."""
        self.model = None
        self.model_name = None
        self._load_best_model()


def get_recommender() -> RecommenderService:
    """Get singleton recommender instance."""
    return RecommenderService()
