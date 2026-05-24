import datetime
from abc import ABC, abstractmethod
from typing import NamedTuple

from main.event.models import Event
from main.event.services import EventService
from main.social.models import Post
from shared.enums import EventPhase


class FeedItem(NamedTuple):
    obj: Post | Event
    rank_key: datetime.datetime


class FeedRecommender(ABC):
    @abstractmethod
    def recommend(self, user_id: int, start: int, end: int) -> list[FeedItem]:
        ...


class ChronologicalFeedRecommender(FeedRecommender):
    def recommend(self, user_id: int, start: int, end: int) -> list[FeedItem]:
        # Over-fetch from each source so the merged window of [start:end]
        # is not biased toward whichever source dominates the head.
        limit = end
        posts = (
            Post.objects.select_related("author")
            .order_by("-time_posted")[:limit]
        )
        events = (
            EventService._queryset()
            .filter(phase=EventPhase.SCHEDULED)
            .order_by("start_time")[:limit]
        )

        items = [FeedItem(obj=p, rank_key=p.time_posted) for p in posts]
        items += [FeedItem(obj=e, rank_key=e.start_time) for e in events]
        items.sort(key=lambda item: item.rank_key, reverse=True)
        return items[start:end]
