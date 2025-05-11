import graphene

from main_app.graphql.misc.types import AttachmentType
from main_app.models.enums import MemberRole
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
