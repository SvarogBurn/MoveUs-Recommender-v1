import graphene

from django.db.models import Q

from main_app.graphql.event.types import EventType
from main_app.graphql.misc.types import AttachmentType
from main_app.graphql.post.types import PostType
from main_app.graphql.user.types import UserType
from main_app.models.enums import MemberRole
from main_app.models import User, Event, Post
from main_app.util import (
    generate_attachment_upload_url,
    generate_event_picture_url,
    generate_profile_picture_url,
    get_event,
    require_auth,
)


class SignedURLQuery(graphene.ObjectType):
    profile_picture_gcloud_url = graphene.String()
    event_picture_gcloud_url = graphene.String(
        event_id = graphene.Int(required=True)
    )
    new_attachment = graphene.Field(AttachmentType)

    @require_auth
    def resolve_profile_picture_gcloud_url(root, info):
        user_id = info.context.user.id
        return generate_profile_picture_url(user_id)

    @require_auth
    def resolve_event_picture_gcloud_url(root, info, event_id: int):
        user_id = info.context.user.id
        get_event(event_id, user_id, MemberRole.ORGANIZER)
        return generate_event_picture_url(event_id)

    @require_auth
    def resolve_new_attachment(root, info):
        user_id = info.context.user.id
        attachment = generate_attachment_upload_url(user_id)
        return AttachmentType(
            id = attachment[0],
            url = attachment[1]
        )

class SearchUnion(graphene.Union):
    class Meta:
        types = (UserType, EventType, PostType)

class SearchQuery(graphene.ObjectType):
    search_result = graphene.List(
        SearchUnion,
            search_string = graphene.String(required=True)
        )

    def resolve_search_result(self, info, search_string: str):
        userq1 = Q(username__istartswith=search_string)
        userq2 = Q(first_name__istartswith=search_string)

        users = User.objects.filter(
            userq1 | userq2
        )
        events = Event.objects.filter(
            title__istartswith=search_string
        )
        posts = Post.objects.filter(
            title__istartswith=search_string
        )

        return list(users) + list(events) + list(posts)