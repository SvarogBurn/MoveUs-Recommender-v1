from django.db import models
from django.db.models.fields.composite import CompositePrimaryKey

from main.user.models import User
from shared.enums import ChatNotifications


class Chat(models.Model):
    time_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "main_app_chat"


class ChatMember(models.Model):
    pk = CompositePrimaryKey("user", "chat")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name="members")
    nickname = models.CharField(max_length=64)
    last_open = models.DateTimeField(null=True)
    notifications = models.SmallIntegerField(
        choices=ChatNotifications.choices(), default=ChatNotifications.ALL
    )

    class Meta:
        db_table = "main_app_chatmember"


class ChatMessage(models.Model):
    chat = models.ForeignKey(
        Chat, on_delete=models.CASCADE, null=False, related_name="messages"
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=False)
    text_content = models.CharField(max_length=512)
    time_sent = models.DateTimeField(auto_now_add=True, db_index=True)
    attachment = models.CharField(null=True)

    class Meta:
        db_table = "main_app_chatmessage"
