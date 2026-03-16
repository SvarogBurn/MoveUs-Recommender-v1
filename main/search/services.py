from django.db.models import Q

from main.event.models import Event
from main.social.models import Post
from main.user.models import User
from shared.enums import SearchCategory


class SearchService:
    @staticmethod
    def search(search_string: str, categories: list = None) -> list:
        result_list = []

        if categories is None or SearchCategory.EVENTS in categories:
            events = Event.objects.filter(title__icontains=search_string)
            result_list += list(events)

        if categories is None or SearchCategory.USERS in categories:
            userq1 = Q(username__istartswith=search_string)
            userq2 = Q(first_name__istartswith=search_string)
            users = User.objects.filter(userq1 | userq2)
            result_list += list(users)

        if categories is None or SearchCategory.POSTS in categories:
            posts = Post.objects.filter(content__icontains=search_string)
            result_list += list(posts)

        return result_list
