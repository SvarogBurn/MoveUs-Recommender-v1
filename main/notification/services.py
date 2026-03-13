import datetime

from main.notification.models import Notification
from shared.enums import MemberRole, NotificationEnum


class NotificationService:
    @staticmethod
    def send(to: int, target: int, type: NotificationEnum) -> None:
        Notification.objects.create(user_id=to, type=type, target_id=target)

    @staticmethod
    def get_notifications(
        user_id: int, last_fetch: datetime.datetime
    ) -> list:
        from api.graphql.notification.types import (
            EventNotificationType,
            UserNotificationType,
        )
        from main.event.models import Event
        from main.user.models import User

        user_notifications_list = list(
            Notification.objects.filter(
                user_id=user_id,
                time_added__gt=last_fetch,
                type__in=Notification.USER_NOTIFICATION_TYPES,
            )
        )
        event_notifications_list = list(
            Notification.objects.filter(
                user_id=user_id,
                time_added__gt=last_fetch,
                type__in=Notification.EVENT_NOTIFICATION_TYPES,
            )
        )

        user_ids = [n.target_id for n in user_notifications_list]
        event_ids = [n.target_id for n in event_notifications_list]

        users_by_id = {u.id: u for u in User.objects.filter(id__in=user_ids)}
        events_by_id = {e.id: e for e in Event.objects.filter(id__in=event_ids)}

        result = []
        result.extend(
            UserNotificationType(
                id=n.id,
                time=n.time_added,
                notification_type=n.type,
                user=users_by_id[n.target_id],
            )
            for n in user_notifications_list
        )
        result.extend(
            EventNotificationType(
                id=n.id,
                time=n.time_added,
                notification_type=n.type,
                event=events_by_id[n.target_id],
            )
            for n in event_notifications_list
        )
        return sorted(result, key=lambda n: n.time, reverse=True)

    @staticmethod
    def send_event_finished(event_id: int) -> None:
        from main.event.models import EventMember

        member_ids = [
            x["user_id"]
            for x in EventMember.objects.filter(event_id=event_id)
            .exclude(role=MemberRole.ORGANIZER)
            .values("user_id")
        ]
        for member_id in member_ids:
            NotificationService.send(
                member_id, event_id, NotificationEnum.EVENT_FINISHED
            )
