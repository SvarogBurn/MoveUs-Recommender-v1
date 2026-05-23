from django.conf import settings
from django.utils.module_loading import import_string

from main.event.models import Event
from main.feed.recommender import FeedRecommender
from main.social.models import Post


def _load_recommender() -> FeedRecommender:
    return import_string(settings.FEED_RECOMMENDER)()


class FeedService:
    _recommender: FeedRecommender = _load_recommender()

    @classmethod
    def get_feed(cls, user_id: int, start: int, end: int) -> list[Post | Event]:
        return [item.obj for item in cls._recommender.recommend(user_id, start, end)]
