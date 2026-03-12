import graphene

from api.graphql.event.types import EventType
from api.graphql.notification.types import (
    BaseNotificationType,
    EventNotificationType,
    UserNotificationType,
)
from main.event.models import Event
from main.notification.models import Notification
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

        result: list[BaseNotificationType] = []

        user_notifications_list = list(
            Notification.objects.filter(
                user_id=info.context.user.id,
                time_added__gt=last_fetch,
                type__in=Notification.USER_NOTIFICATION_TYPES,
            )
        )

        event_notifications_list = list(
            Notification.objects.filter(
                user_id=info.context.user.id,
                time_added__gt=last_fetch,
                type__in=Notification.EVENT_NOTIFICATION_TYPES,
            )
        )

        user_ids = [n.target_id for n in user_notifications_list]
        event_ids = [n.target_id for n in event_notifications_list]

        users_by_id = {u.id: u for u in User.objects.filter(id__in=user_ids)}
        events_by_id = {e.id: e for e in Event.objects.filter(id__in=event_ids)}

        result.extend(
            [
                UserNotificationType(
                    id=n.id,
                    time=n.time_added,
                    notification_type=n.type,
                    user=users_by_id[n.target_id],
                )
                for n in user_notifications_list
            ]
        )

        result.extend(
            [
                EventNotificationType(
                    id=n.id,
                    time=n.time_added,
                    notification_type=n.type,
                    event=events_by_id[n.target_id],
                )
                for n in event_notifications_list
            ]
        )

        return sorted(result, key=lambda notification: notification.time, reverse=True)
