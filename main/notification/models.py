from django.db import models

from main.user.models import User
from shared.enums import NotificationKind


class Notification(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="notifications"
    )
    target_id = models.IntegerField()
    time_added = models.DateTimeField(auto_now_add=True)
    kind = models.SmallIntegerField(choices=NotificationKind.choices())

    USER_NOTIFICATION_KINDS = (NotificationKind.NEW_FOLLOWER,)
    EVENT_NOTIFICATION_KINDS = (
        NotificationKind.EVENT_FINISHED,
        NotificationKind.EVENT_STARTED,
        NotificationKind.EVENT_CANCELLED,
    )

    class Meta:
        db_table = "main_app_notification"
        indexes = [
            models.Index(fields=["user", "time_added"]),
            models.Index(fields=["user", "kind"]),
        ]
