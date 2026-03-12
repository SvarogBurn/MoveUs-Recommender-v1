from main.notifications.models import Notification
from shared.enums import MemberRole, NotificationEnum


class NotificationService:
    @staticmethod
    def send(to: int, target: int, type: NotificationEnum) -> None:
        Notification.objects.create(user_id=to, type=type, target_id=target)

    @staticmethod
    def send_event_finished(event_id: int) -> None:
        from main.events.models import EventMember

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
