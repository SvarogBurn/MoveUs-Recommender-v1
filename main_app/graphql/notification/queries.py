import graphene

from main_app.graphql.notification.types import BaseNotificationType, UserNotificationType, EventNotificationType
from main_app.graphql.user.types import UserType
from main_app.graphql.event.types import EventType
from main_app.util import require_auth
from main_app.models import Notification, User, Event

class NotificationQuery(graphene.ObjectType):

    my_notifications = graphene.List(
        BaseNotificationType,
        last_fetch = graphene.DateTime(required=True)
        )

    @require_auth
    def resolve_my_notifications(root, info, last_fetch):
        
        result: list[BaseNotificationType] = []

        user_notifications = Notification.objects.filter(
            user_id = info.context.user.id,
            time_added__gt = last_fetch,
            type__in = Notification.USER_NOTIFICATION_TYPES
        )

        event_notifications = Notification.objects.filter(
            user_id = info.context.user.id,
            time_added__gt = last_fetch,
            type__in = Notification.EVENT_NOTIFICATION_TYPES
        )

        result.extend(
            [UserNotificationType(
                id = n.id,
                time = n.time_added,
                notification_type = n.type,
                user = User.objects.get(pk = n.target_id)
            ) for n in user_notifications]
        )

        result.extend(
            [EventNotificationType(
                id = n.id,
                time = n.time_added,
                notification_type = n.type,
                event = Event.objects.get(pk = n.target_id)
            ) for n in event_notifications]
        )

        return result


