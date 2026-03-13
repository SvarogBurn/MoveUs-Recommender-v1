import datetime
from typing import Any

from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from django.db.models.functions import Now

from main.chat.models import Chat, ChatMember, ChatMessage
from main.event.models import Event
from main.social.models import Relationship
from main.user.models import User
from shared.errors.mu_error import MUError, MUErrorCode
from shared.storage import storage_backend


def messages_group(chat_id: int) -> str:
    return f"chat_{chat_id}_messages"


def last_open_group(chat_id: int) -> str:
    return f"chat_{chat_id}_last_open"


def serialize_message(
    msg_id: int,
    user_id: int,
    text_content: str,
    time_sent: datetime.datetime,
    attachment: str | None = None,
) -> dict[str, Any]:
    return {
        "id": msg_id,
        "userId": user_id,
        "textContent": text_content,
        "timeSent": str(time_sent),
        "attachmentUrl": storage_backend.generate_attachment_url(attachment) if attachment else None,
    }


class ChatService:
    @staticmethod
    def create_chat_for_event(event: Event) -> Chat:
        chat = Chat.objects.create()
        event.chat = chat
        event.save(update_fields=["chat"])
        return chat

    @staticmethod
    def add_chat_member(chat: Chat, user: User) -> ChatMember:
        if Relationship.objects.filter(chat_id=chat.id).exists():
            raise MUError(MUErrorCode.CANNOT_ADD_TO_FRIEND_CHAT)
        member, _ = ChatMember.objects.get_or_create(
            user=user,
            chat=chat,
            defaults={"nickname": user.username},
        )
        return member

    @staticmethod
    def remove_chat_member(chat_id: int, user_id: int) -> None:
        if Relationship.objects.filter(chat_id=chat_id).exists():
            raise MUError(MUErrorCode.CANNOT_LEAVE_FRIEND_CHAT)
        ChatMember.objects.filter(user_id=user_id, chat_id=chat_id).delete()

    @staticmethod
    def create_chat_for_relationship(relationship: Relationship) -> Chat:
        chat = Chat.objects.create()
        ChatMember.objects.create(
            user=relationship.user_1, chat=chat, nickname=relationship.user_1.username
        )
        ChatMember.objects.create(
            user=relationship.user_2, chat=chat, nickname=relationship.user_2.username
        )
        relationship.chat = chat
        relationship.save(update_fields=["chat"])
        return chat

    @staticmethod
    def get_chat_member(chat_id: int, user_id: int) -> ChatMember:
        try:
            return ChatMember.objects.get(user_id=user_id, chat_id=chat_id)
        except ChatMember.DoesNotExist:
            raise MUError(MUErrorCode.NOT_IN_CHAT)

    @staticmethod
    def send_message(
        chat_id: int,
        user_id: int,
        text_content: str,
        attachment: str | None = None,
    ) -> ChatMessage:
        msg = ChatMessage.objects.create(
            chat_id=chat_id,
            user_id=user_id,
            text_content=text_content,
            attachment=attachment,
        )
        channel_layer = get_channel_layer()
        data = serialize_message(
            msg.id, user_id, text_content, msg.time_sent, attachment
        )
        async_to_sync(channel_layer.group_send)(
            messages_group(chat_id),
            {
                "type": "chat.message",
                **data,
            },
        )
        return msg

    @staticmethod
    def notify_last_open(
        chat_id: int, user_id: int, last_open: datetime.datetime
    ) -> None:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            last_open_group(chat_id),
            {
                "type": "chat.last_open",
                "user_id": user_id,
                "last_open": str(last_open),
            },
        )

    @staticmethod
    @database_sync_to_async
    def get_initial_messages(
        chat_id: int, since: datetime.datetime
    ) -> list[dict[str, Any]]:
        messages = ChatMessage.objects.filter(
            chat_id=chat_id,
            time_sent__gt=since,
        ).values("id", "time_sent", "text_content", "user_id", "attachment")
        return [
            serialize_message(
                m["id"],
                m["user_id"],
                m["text_content"],
                m["time_sent"],
                m["attachment"],
            )
            for m in messages
        ]

    @staticmethod
    @database_sync_to_async
    def get_last_open_updates(
        chat_id: int, user_id: int, since: datetime.datetime
    ) -> list[dict[str, Any]]:
        members = (
            ChatMember.objects.filter(
                chat_id=chat_id,
                last_open__gt=since,
            )
            .exclude(user_id=user_id)
            .values("user_id", "last_open")
        )
        return [
            {
                "userId": m["user_id"],
                "lastOpen": str(m["last_open"]),
            }
            for m in members
        ]

    @staticmethod
    @database_sync_to_async
    def update_member_last_open(chat_member: ChatMember) -> datetime.datetime:
        chat_member.last_open = Now()
        chat_member.save(update_fields=["last_open"])
        chat_member.refresh_from_db(fields=["last_open"])
        return chat_member.last_open

    @staticmethod
    @database_sync_to_async
    def get_chat_member_async(chat_id: int, user_id: int) -> ChatMember:
        return ChatService.get_chat_member(chat_id, user_id)
