import graphene

from api.graphql.event.types import EventType
from api.graphql.misc.types import AttachmentType
from api.graphql.social.types import PostType
from api.graphql.user.types import UserType
from main.event.services import EventService
from main.search.services import SearchService
from shared.enums import SearchCategory
from shared.storage import storage_backend
from shared.utils.decorators import require_auth


class SignedURLQuery(graphene.ObjectType):
    profile_picture_url = graphene.String(
        content_type=graphene.String(required=True)
    )
    event_picture_url = graphene.String(
        event_id=graphene.Int(required=True),
        content_type=graphene.String(required=True),
    )
    new_attachment = graphene.Field(
        AttachmentType, content_type=graphene.String(required=True)
    )

    @require_auth
    def resolve_profile_picture_url(
        root, info: graphene.ResolveInfo, content_type: str
    ) -> str:
        user_id = info.context.user.id
        return storage_backend.generate_profile_picture_url(user_id, content_type)

    @require_auth
    def resolve_event_picture_url(
        root, info: graphene.ResolveInfo, event_id: int, content_type: str
    ) -> str:
        user_id = info.context.user.id
        return EventService.generate_event_picture_url(
            event_id, user_id, content_type
        )

    @require_auth
    def resolve_new_attachment(
        root, info: graphene.ResolveInfo, content_type: str
    ) -> AttachmentType:
        user_id = info.context.user.id
        attachment = storage_backend.generate_attachment_upload_url(
            user_id, content_type
        )
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
        return SearchService.search(search_string, categories)
