import graphene

from api.graphql.notification.types import (
    BaseNotificationType,
    EventNotificationType,
    UserNotificationType,
)
from main.event.models import Event
from main.notification.models import Notification
from main.notification.services import NotificationService
from main.user.models import User
from shared.utils.decorators import require_auth


class NotificationQuery(graphene.ObjectType):

    my_notifications = graphene.List(
        BaseNotificationType, last_fetch=graphene.DateTime(required=True)
    )

    @require_auth
    def resolve_my_notifications(
        root, info: graphene.ResolveInfo, last_fetch
    ) -> list[BaseNotificationType]:
        notifications = NotificationService.get_notifications(
            info.context.user.id, last_fetch
        )

        user_notifs = [
            n for n in notifications
            if n.kind in Notification.USER_NOTIFICATION_KINDS
        ]
        event_notifs = [
            n for n in notifications
            if n.kind in Notification.EVENT_NOTIFICATION_KINDS
        ]

        users_by_id = {
            u.id: u
            for u in User.objects.filter(
                id__in=[n.target_id for n in user_notifs]
            )
        }
        events_by_id = {
            e.id: e
            for e in Event.objects.filter(
                id__in=[n.target_id for n in event_notifs]
            )
        }

        result = []
        for n in notifications:
            if n.kind in Notification.USER_NOTIFICATION_KINDS:
                result.append(
                    UserNotificationType(
                        id=n.id,
                        time=n.time_added,
                        notification_type=n.kind,
                        user=users_by_id[n.target_id],
                    )
                )
            elif n.kind in Notification.EVENT_NOTIFICATION_KINDS:
                result.append(
                    EventNotificationType(
                        id=n.id,
                        time=n.time_added,
                        notification_type=n.kind,
                        event=events_by_id[n.target_id],
                    )
                )
        return result
