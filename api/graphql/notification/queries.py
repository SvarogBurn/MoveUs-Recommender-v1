import graphene

from api.graphql.notification.types import BaseNotificationType
from main.notification.services import NotificationService
from shared.utils.decorators import require_auth


class NotificationQuery(graphene.ObjectType):

    my_notifications = graphene.List(
        BaseNotificationType, last_fetch=graphene.DateTime(required=True)
    )

    @require_auth
    def resolve_my_notifications(
        root, info: graphene.ResolveInfo, last_fetch
    ) -> list[BaseNotificationType]:
        return NotificationService.get_notifications(info.context.user.id, last_fetch)
