from main_app.models import Notification, EventMember
from main_app.models.enums import NotificationEnum, MemberRole

def send_notification(
        to: int,
        target: int,
        type: NotificationEnum
):
    Notification.objects.create(
        user_id = to,
        type = type,
        target_id = target
    )

def send_event_finished_notification(
        event_id: int
):
    
    member_ids = [x['user_id'] for x in EventMember.objects.filter(
        event_id = event_id,
    ).exclude(
        role = MemberRole.ORGANIZER
    ).values("user_id")];

    for member_id in member_ids:
        send_notification(
            member_id, event_id, NotificationEnum.EVENT_FINISHED
        )