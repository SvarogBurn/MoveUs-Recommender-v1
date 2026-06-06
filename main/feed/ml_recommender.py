import sys
from pathlib import Path

import numpy as np

# Add ml module to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "ml"))

from main.feed.recommender import FeedRecommender, FeedItem
from main.event.models import Event
from main.event.services import EventService
from shared.enums import EventPhase
from shared.utils.pagination import validate_pagination

try:
    from ml.recommender_service import get_recommender
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False


class MLFeedRecommender(FeedRecommender):
    """ML-based event recommender using trained model."""
    
    def __init__(self):
        self.recommender = None
        if ML_AVAILABLE:
            self.recommender = get_recommender()
    
    def recommend(self, user_id: int, start: int, end: int) -> list[FeedItem]:
        """Get recommended events for user using ML model.
        
        Falls back to popularity if model unavailable.
        """
        validate_pagination(start, end)
        
        # Get candidate events (upcoming/scheduled only)
        events = EventService._queryset().filter(phase=EventPhase.SCHEDULED)
        if not events.exists():
            return []
        
        event_ids = list(events.values_list("id", flat=True))
        
        # Score with ML model
        if self.recommender and self.recommender.is_ready():
            try:
                scores = self.recommender.score(user_id, event_ids)
                scored_events = list(zip(events, scores))
                scored_events.sort(key=lambda x: -x[1])  # descending by score
                items = [FeedItem(obj=e, rank_key=score) for e, score in scored_events]
            except Exception as e:
                print(f"ML recommender error: {e}, falling back to popularity")
                items = self._fallback_recommend(events)
        else:
            items = self._fallback_recommend(events)
        
        return items[start:end]
    
    def _fallback_recommend(self, events) -> list[FeedItem]:
        """Fallback: rank by event start time (soonest first)."""
        items = [FeedItem(obj=e, rank_key=e.start_time) for e in events]
        items.sort(key=lambda item: item.rank_key)
        return items
