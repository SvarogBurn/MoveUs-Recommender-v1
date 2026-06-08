import numpy as np

from main.event.models import EventMember
from main.event.services import EventService
from main.feed.recommender import FeedItem, FeedRecommender
from main.user.models import User
from shared.enums import EventPhase
from shared.utils.pagination import validate_pagination

try:
    from ml.recommender_service import get_recommender
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

# Noise std-dev added to raw model scores before ranking.
# Small enough that events with clearly different scores keep their order;
# large enough that near-tied events shuffle on every request and that
# joining/leaving an event produces a visibly different ranking.
_SCORE_NOISE_STD = 0.18


class MLFeedRecommender(FeedRecommender):
    """ML-based event recommender using the trained DeepFM model."""

    def __init__(self):
        self.recommender = get_recommender() if ML_AVAILABLE else None

    def recommend(self, user_id: int, start: int, end: int) -> list[FeedItem]:
        validate_pagination(start, end)

        joined_ids = set(
            EventMember.objects
            .filter(user_id=user_id, participates=True)
            .values_list("event_id", flat=True)
        )
        events = list(
            EventService._queryset()
            .filter(phase=EventPhase.SCHEDULED)
            .exclude(pk__in=joined_ids)
            .select_related("location", "activity")
        )
        if not events:
            return []

        if self.recommender and self.recommender.is_ready():
            try:
                user = (
                    User.objects
                    .prefetch_related(
                        "preferences__availabilities",
                        "preferences__preferred_activities",
                    )
                    .get(pk=user_id)
                )
                scores = self.recommender.score_live(user, events)
                # Per-request noise keeps the feed fresh on every reload and
                # makes the effect of joining / leaving an event immediately
                # visible without needing a manual cache invalidation.
                noisy = scores + np.random.normal(0, _SCORE_NOISE_STD, len(scores))
                scored = sorted(zip(events, noisy), key=lambda x: -x[1])
                return [FeedItem(obj=e, rank_key=float(s)) for e, s in scored][start:end]
            except Exception as e:
                print(f"ML recommender error: {e}, falling back to chronological")

        return self._fallback_recommend(events)[start:end]

    def _fallback_recommend(self, events) -> list[FeedItem]:
        return sorted(
            [FeedItem(obj=e, rank_key=e.start_time) for e in events],
            key=lambda x: x.rank_key,
        )
