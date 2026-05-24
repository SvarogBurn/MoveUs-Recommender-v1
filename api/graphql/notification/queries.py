import graphene

from api.graphql.notification.types import (
    BaseNotificationType,
    EventNotificationType,
    UserNotificationType,
)
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
        entries = NotificationService.get_notifications_with_targets(
            info.context.user.id, last_fetch
        )

        result = []
        for entry in entries:
            if entry["target_kind"] == "user":
                result.append(
                    UserNotificationType(
                        id=entry["id"],
                        time=entry["time"],
                        notification_type=entry["notification_type"],
                        user=entry["user"],
                    )
                )
            elif entry["target_kind"] == "event":
                result.append(
                    EventNotificationType(
                        id=entry["id"],
                        time=entry["time"],
                        notification_type=entry["notification_type"],
                        event=entry["event"],
                    )
                )
        return result
