import datetime

from main.notification.models import Notification
from shared.enums import MemberRole, NotificationKind


class NotificationService:
    @staticmethod
    def send(to: int, target: int, type: NotificationKind) -> None:
        Notification.objects.create(user_id=to, kind=type, target_id=target)

    @staticmethod
    def get_notifications(
        user_id: int, last_fetch: datetime.datetime
    ) -> list[Notification]:
        return list(
            Notification.objects.filter(
                user_id=user_id, time_added__gt=last_fetch
            ).order_by("-time_added")
        )

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
                member_id, event_id, NotificationKind.EVENT_FINISHED
            )
