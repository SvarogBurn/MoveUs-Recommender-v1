import graphene
from django.db.models import Q

from api.graphql.event.types import EventType
from api.graphql.misc.types import AttachmentType
from api.graphql.social.types import PostType
from api.graphql.user.types import UserType
from main.event.models import Event
from main.event.services import EventService
from main.social.models import Post
from main.user.models import User
from shared.enums import MemberRole, SearchCategory
from shared.storage import storage_backend
from shared.utils.decorators import require_auth


class SignedURLQuery(graphene.ObjectType):
    profile_picture_url = graphene.String()
    event_picture_url = graphene.String(event_id=graphene.Int(required=True))
    new_attachment = graphene.Field(AttachmentType)

    @require_auth
    def resolve_profile_picture_url(
        root, info: graphene.ResolveInfo
    ) -> str:
        user_id = info.context.user.id
        return storage_backend.generate_profile_picture_url(user_id)

    @require_auth
    def resolve_event_picture_url(
        root, info: graphene.ResolveInfo, event_id: int
    ) -> str:
        user_id = info.context.user.id
        EventService.get_event(event_id, user_id, MemberRole.ORGANIZER)
        return storage_backend.generate_event_picture_url(event_id)

    @require_auth
    def resolve_new_attachment(
        root, info: graphene.ResolveInfo
    ) -> AttachmentType:
        user_id = info.context.user.id
        attachment = storage_backend.generate_attachment_upload_url(user_id)
        return AttachmentType(id=attachment[0], url=attachment[1])


class SearchUnion(graphene.Union):
    class Meta:
        types = (UserType, EventType, PostType)


class SearchQuery(graphene.ObjectType):
    search = graphene.List(
        SearchUnion,
        search_string=graphene.String(required=True),
        categories=graphene.List(SearchCategory.as_graphene_enum()),
    )

    def resolve_search(
        self, info: graphene.ResolveInfo, search_string: str, categories=None
    ) -> list:
        result_list = []

        if categories == None or SearchCategory.EVENTS in categories:
            events = Event.objects.filter(title__icontains=search_string)
            result_list += list(events)

        if categories == None or SearchCategory.USERS in categories:
            userq1 = Q(username__istartswith=search_string)
            userq2 = Q(first_name__istartswith=search_string)
            users = User.objects.filter(userq1 | userq2)
            result_list += list(users)

        if categories == None or SearchCategory.POSTS in categories:
            posts = Post.objects.filter(content__icontains=search_string)
            result_list += list(posts)

        return result_list
