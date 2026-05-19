import datetime

from main.notification.models import Notification
from shared.enums import NotificationKind


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
    def get_notifications_with_targets(
        user_id: int, last_fetch: datetime.datetime
    ) -> list[dict]:
        from main.event.models import Event
        from main.user.models import User

        notifications = NotificationService.get_notifications(user_id, last_fetch)

        user_notifs = [
            n for n in notifications if n.kind in Notification.USER_NOTIFICATION_KINDS
        ]
        event_notifs = [
            n for n in notifications if n.kind in Notification.EVENT_NOTIFICATION_KINDS
        ]

        users_by_id = {
            u.id: u
            for u in User.objects.filter(id__in=[n.target_id for n in user_notifs])
        }
        events_by_id = {
            e.id: e
            for e in Event.objects.filter(id__in=[n.target_id for n in event_notifs])
        }

        result = []
        for n in notifications:
            entry = {
                "id": n.id,
                "time": n.time_added,
                "notification_type": n.kind,
            }
            if n.kind in Notification.USER_NOTIFICATION_KINDS:
                if n.target_id not in users_by_id:
                    continue
                entry["kind"] = "user"
                entry["user"] = users_by_id[n.target_id]
            elif n.kind in Notification.EVENT_NOTIFICATION_KINDS:
                if n.target_id not in events_by_id:
                    continue
                entry["kind"] = "event"
                entry["event"] = events_by_id[n.target_id]
            else:
                continue
            result.append(entry)
        return result

    @staticmethod
    def send_event_finished(event_id: int) -> None:
        NotificationService._broadcast_to_event_members(
            event_id, NotificationKind.EVENT_FINISHED
        )

    @staticmethod
    def send_event_started(event_id: int) -> None:
        NotificationService._broadcast_to_event_members(
            event_id, NotificationKind.EVENT_STARTED
        )

    @staticmethod
    def send_event_cancelled(event_id: int) -> None:
        NotificationService._broadcast_to_event_members(
            event_id, NotificationKind.EVENT_CANCELLED
        )

    @staticmethod
    def _broadcast_to_event_members(event_id: int, kind: NotificationKind) -> None:
        from main.event.models import EventMember

        member_ids = [
            x["user_id"]
            for x in EventMember.objects.filter(event_id=event_id).values("user_id")
        ]
        for member_id in member_ids:
            NotificationService.send(member_id, event_id, kind)
