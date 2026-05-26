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
    nickname = models.CharField(max_length=64, null=True)
    last_open = models.DateTimeField(null=True)
    notifications = models.SmallIntegerField(
        choices=ChatNotifications.choices(), default=ChatNotifications.ALL
    )

    class Meta:
        db_table = "main_app_chatmember"


class DirectChat(models.Model):
    pk = CompositePrimaryKey("user_1", "user_2")
    user_1 = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="direct_chats_as_user_1"
    )
    user_2 = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="direct_chats_as_user_2"
    )
    chat = models.OneToOneField(
        Chat, on_delete=models.CASCADE, related_name="direct_chat"
    )

    class Meta:
        db_table = "main_app_directchat"


class GroupChat(models.Model):
    chat = models.OneToOneField(
        Chat, on_delete=models.CASCADE, related_name="group_chat"
    )
    name = models.CharField(max_length=64, default="")

    class Meta:
        db_table = "main_app_groupchat"


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
