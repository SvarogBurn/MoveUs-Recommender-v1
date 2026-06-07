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


class MLFeedRecommender(FeedRecommender):
    """ML-based event recommender using the trained DeepFM model."""

    def __init__(self):
        self.recommender = get_recommender() if ML_AVAILABLE else None

    def recommend(self, user_id: int, start: int, end: int) -> list[FeedItem]:
        validate_pagination(start, end)

        events = list(
            EventService._queryset()
            .filter(phase=EventPhase.SCHEDULED)
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
                scored = sorted(zip(events, scores), key=lambda x: -x[1])
                return [FeedItem(obj=e, rank_key=float(s)) for e, s in scored][start:end]
            except Exception as e:
                print(f"ML recommender error: {e}, falling back to chronological")

        return self._fallback_recommend(events)[start:end]

    def _fallback_recommend(self, events) -> list[FeedItem]:
        return sorted(
            [FeedItem(obj=e, rank_key=e.start_time) for e in events],
            key=lambda x: x.rank_key,
        )
