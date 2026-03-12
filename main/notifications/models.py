from django.db import models

from main.users.models import User
from shared.enums import NotificationEnum


class Notification(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="notifications"
    )
    target_id = models.IntegerField()
    time_added = models.DateTimeField(auto_now_add=True)
    type = models.SmallIntegerField(choices=NotificationEnum.choices())

    USER_NOTIFICATION_TYPES = (
        NotificationEnum.FRIEND_ACCEPTED,
        NotificationEnum.FRIEND_REQUEST,
    )
    EVENT_NOTIFICATION_TYPES = (NotificationEnum.EVENT_FINISHED,)

    class Meta:
        db_table = "main_app_notification"
        indexes = [
            models.Index(fields=["user", "time_added"]),
            models.Index(fields=["user", "type"]),
        ]
