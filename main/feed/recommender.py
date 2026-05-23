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
        posts = (
            Post.objects.select_related("author").order_by("-time_posted")[:end]
        )
        events = (
            EventService._queryset()
            .filter(phase=EventPhase.SCHEDULED)
            .order_by("start_time")[:end]
        )

        items = [FeedItem(obj=p, rank_key=p.time_posted) for p in posts]
        items += [FeedItem(obj=e, rank_key=e.start_time) for e in events]
        items.sort(key=lambda item: item.rank_key, reverse=True)
        return items[start:end]
